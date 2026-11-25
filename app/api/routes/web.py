"""Read-optimised endpoints for the public web app (web/).

These aggregate what one screen needs into one response. They never call an
LLM for a decision: scores, tiers and actions come from the deterministic
engines, and the playground computes without writing to the database.
"""
from __future__ import annotations

from collections import Counter
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai.mock_signals import analyze_note
from app.core.config import settings
from app.core.timeutil import utc_now
from app.db.database import get_db
from app.models import Account, Activity, Contact, Draft, ICPProfile, Product, Score, Signal
from app.schemas.executive import ExecutiveAnswer, ExecutiveQuestionRef, PrioritizationRow
from app.schemas.explain import AccountExplanation, ComparisonOut, FeaturedComparisonOut
from app.services import executive_analytics
from app.services.explainability import compare_accounts, explain_account, featured_comparisons
from app.services.recommendation_engine import RecommendationEngine
from app.services.scoring_engine import AccountData, ICPData, ScoringEngine
from app.services.signal_engine import NEGATIVE_SOURCE, derive_negative_signals, score_signals

router = APIRouter(prefix="/web", tags=["Web App"])

TIERS = ["Priority 1", "Priority 2", "Priority 3", "Low"]


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _product(db: Session) -> Product:
    product = db.query(Product).order_by(Product.id).first()
    if not product:
        raise HTTPException(status_code=503, detail="Demo workspace is not seeded yet.")
    return product


def _icp(db: Session, product: Product) -> Optional[ICPProfile]:
    return db.query(ICPProfile).filter_by(product_id=product.id).first()


def _icp_dict(icp: Optional[ICPProfile]) -> Optional[Dict[str, Any]]:
    if not icp:
        return None
    return {
        "industries": icp.industries or [],
        "company_size_min": icp.company_size_min,
        "company_size_max": icp.company_size_max,
        "geographies": icp.geographies or [],
        "buyer_roles": icp.buyer_roles or [],
        "pain_points": icp.pain_points or [],
        "technologies": icp.technologies or [],
        "buying_triggers": icp.buying_triggers or [],
        "exclusions": icp.exclusions or [],
    }


def _signal_dict(sig: Signal) -> Dict[str, Any]:
    return {
        "id": sig.id,
        "type": sig.signal_type,
        "description": sig.description,
        "evidence": sig.evidence,
        "source": sig.source,
        "detected_at": sig.detected_at.isoformat() if sig.detected_at else None,
        "confidence": sig.confidence,
        "strength": sig.strength,
        "negative": sig.source == NEGATIVE_SOURCE,
    }


def _account_summary(acc: Account, score: Optional[Score], action: Optional[str], top_signal: Optional[str]) -> Dict[str, Any]:
    return {
        "id": acc.id,
        "name": acc.name,
        "domain": acc.domain,
        "industry": acc.industry,
        "employee_count": acc.employee_count,
        "country": acc.country,
        "stage": acc.stage or "Research",
        "total_score": round(score.total_score, 1) if score else 0.0,
        "tier": score.tier if score else "Low",
        "intent_score": round(score.intent_score or 0.0, 1) if score else 0.0,
        "action": action,
        "top_signal": top_signal,
    }


def _rec_dict(rec: Any) -> Dict[str, Any]:
    return {
        "action": rec.action,
        "reason": rec.reason,
        "suggested_persona": rec.suggested_persona,
        "suggested_angle": rec.suggested_angle,
    }


def _signals_by_account(db: Session) -> Dict[int, List[Signal]]:
    grouped: Dict[int, List[Signal]] = {}
    for sig in db.query(Signal).all():
        grouped.setdefault(sig.account_id, []).append(sig)
    return grouped


def _positive(signals: List[Signal]) -> List[Signal]:
    return [s for s in signals if s.source != NEGATIVE_SOURCE]


def _draft_dict(draft: Draft, account: Optional[Account], signals_by_id: Dict[int, Signal]) -> Dict[str, Any]:
    evidence = [_signal_dict(signals_by_id[i]) for i in (draft.evidence_ids or []) if i in signals_by_id]
    return {
        "id": draft.id,
        "account_id": draft.account_id,
        "account_name": account.name if account else f"Account {draft.account_id}",
        "account_stage": account.stage if account else None,
        "body": draft.body,
        "original_body": draft.original_body,
        "edited": (draft.body or "") != (draft.original_body or ""),
        "status": draft.status,
        "evidence": evidence,
        "created_at": draft.created_at.isoformat() if draft.created_at else None,
        "reviewed_at": draft.reviewed_at.isoformat() if draft.reviewed_at else None,
    }


# --------------------------------------------------------------------------- #
# Overview                                                                     #
# --------------------------------------------------------------------------- #

@router.get("/overview")
def overview(db: Session = Depends(get_db)) -> Dict[str, Any]:
    product = _product(db)
    icp = _icp(db, product)
    scores = db.query(Score).filter_by(product_id=product.id).all()
    tiers = Counter(s.tier for s in scores)
    accounts = {a.id: a for a in db.query(Account).all()}
    signals = db.query(Signal).filter(Signal.source != NEGATIVE_SOURCE).all()
    rejected = db.query(Activity).filter_by(activity_type="rejected_signal").count()
    stages = Counter(a.stage or "Research" for a in accounts.values())

    top = sorted(scores, key=lambda s: s.total_score or 0, reverse=True)[:5]
    return {
        "product": {"name": product.name, "description": product.description},
        "icp": _icp_dict(icp),
        "llm_mode": settings.LLM_MODE,
        "counts": {
            "accounts": len(accounts),
            "signals": len(signals),
            "rejected_claims": rejected,
            "pending_drafts": db.query(Draft).filter_by(status="pending").count(),
            "won": stages.get("Won", 0),
        },
        "tiers": {t: tiers.get(t, 0) for t in TIERS},
        "stages": dict(stages),
        "top_accounts": [
            _account_summary(accounts[s.account_id], s, None, None) for s in top if s.account_id in accounts
        ],
    }


# --------------------------------------------------------------------------- #
# Accounts                                                                     #
# --------------------------------------------------------------------------- #

@router.get("/accounts")
def accounts(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    product = _product(db)
    icp = _icp(db, product)
    score_map = {s.account_id: s for s in db.query(Score).filter_by(product_id=product.id).all()}
    by_account = _signals_by_account(db)
    rec = RecommendationEngine()

    rows = []
    for acc in db.query(Account).all():
        score = score_map.get(acc.id)
        positives = _positive(by_account.get(acc.id, []))
        action = rec.get_recommendation(score, positives, icp).action if score else None
        top = max(positives, key=lambda s: s.strength or 0).signal_type if positives else None
        rows.append(_account_summary(acc, score, action, top))
    rows.sort(key=lambda r: r["total_score"], reverse=True)
    return rows


@router.get("/accounts/{account_id}")
def account_detail(account_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    product = _product(db)
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found.")
    icp = _icp(db, product)
    score = db.query(Score).filter_by(account_id=acc.id, product_id=product.id).first()
    signals = db.query(Signal).filter_by(account_id=acc.id).order_by(Signal.detected_at.desc()).all()
    positives = _positive(signals)
    rec = RecommendationEngine().get_recommendation(score, positives, icp) if score else None
    signals_by_id = {s.id: s for s in signals}
    activities = (
        db.query(Activity).filter_by(account_id=acc.id).order_by(Activity.timestamp.desc()).limit(25).all()
    )

    return {
        "account": {
            **_account_summary(acc, score, rec.action if rec else None, None),
            "description": acc.description,
            "technology_stack": acc.technology_stack or [],
            "funding": acc.funding,
            "support_team_size": acc.support_team_size,
        },
        "score": {
            "total": score.total_score,
            "tier": score.tier,
            "components": (score.reasoning or {}).get("components", []),
            "reasons": (score.reasoning or {}).get("reasons", []),
        } if score else None,
        "recommendation": _rec_dict(rec) if rec else None,
        "signals": [_signal_dict(s) for s in signals],
        "contacts": [
            {"id": c.id, "name": c.name, "role": c.role, "email": c.email}
            for c in db.query(Contact).filter_by(account_id=acc.id).all()
        ],
        "drafts": [
            _draft_dict(d, acc, signals_by_id)
            for d in db.query(Draft).filter_by(account_id=acc.id).order_by(Draft.created_at.desc()).all()
        ],
        "activities": [
            {
                "id": a.id,
                "type": a.activity_type,
                "status": a.status,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                "metadata": a.activity_metadata or {},
            }
            for a in activities
        ],
    }


# --------------------------------------------------------------------------- #
# Explainability (read-only)                                                   #
# --------------------------------------------------------------------------- #

@router.get("/accounts/{account_id}/explain", response_model=AccountExplanation)
def explain(account_id: int, db: Session = Depends(get_db)) -> AccountExplanation:
    """Fit vs intent, per-signal contributions, rejected evidence and the exact rule behind the action."""
    _product(db)
    result = explain_account(db, account_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found or not scored.")
    return result


@router.get("/compare", response_model=ComparisonOut)
def compare(
    ids: str = Query(..., max_length=60, description="2 to 4 comma-separated account ids, e.g. 36,37"),
    db: Session = Depends(get_db),
) -> ComparisonOut:
    try:
        parsed = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=422, detail="ids must be comma-separated integers.")
    if not 2 <= len(parsed) <= 4 or len(set(parsed)) != len(parsed):
        raise HTTPException(status_code=422, detail="Compare 2 to 4 distinct accounts.")
    _product(db)
    result = compare_accounts(db, parsed)
    if result is None:
        raise HTTPException(status_code=404, detail="One or more accounts were not found or not scored.")
    return result


@router.get("/comparisons/featured", response_model=List[FeaturedComparisonOut])
def featured(db: Session = Depends(get_db)) -> List[FeaturedComparisonOut]:
    """Suggested comparisons, chosen by the stated selection rules from current data."""
    _product(db)
    return featured_comparisons(db)


# --------------------------------------------------------------------------- #
# Executive questions (read-only, deterministic)                               #
# --------------------------------------------------------------------------- #

@router.get("/prioritization", response_model=List[PrioritizationRow])
def prioritization(db: Session = Depends(get_db)) -> List[PrioritizationRow]:
    """Fit (/80), intent (/20), total, tier, action and evidence status for every account."""
    return executive_analytics.prioritization_rows(db)


@router.get("/executive", response_model=List[ExecutiveQuestionRef])
def executive_questions() -> List[ExecutiveQuestionRef]:
    """The five executive questions this API can answer."""
    return executive_analytics.question_list()


@router.get("/executive/{question_id}", response_model=ExecutiveAnswer)
def executive_answer(question_id: str, db: Session = Depends(get_db)) -> ExecutiveAnswer:
    """Observations (from the database) and labelled hypotheses for one executive question."""
    result = executive_analytics.answer(db, question_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Unknown question. See /web/executive for the list.")
    return result


# --------------------------------------------------------------------------- #
# Review queue                                                                 #
# --------------------------------------------------------------------------- #

@router.get("/drafts")
def drafts(status: Optional[str] = None, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    query = db.query(Draft)
    if status:
        query = query.filter(Draft.status == status)
    items = query.order_by(Draft.created_at.desc()).all()
    accounts = {a.id: a for a in db.query(Account).filter(Account.id.in_({d.account_id for d in items})).all()}
    evidence_ids = {i for d in items for i in (d.evidence_ids or [])}
    signals_by_id = {s.id: s for s in db.query(Signal).filter(Signal.id.in_(evidence_ids)).all()}
    return [_draft_dict(d, accounts.get(d.account_id), signals_by_id) for d in items]


# --------------------------------------------------------------------------- #
# Playground: score any company without touching the database                  #
# --------------------------------------------------------------------------- #

class PlaygroundRequest(BaseModel):
    name: str = Field("Your company", max_length=80)
    industry: str = Field(..., max_length=60)
    employee_count: int = Field(..., ge=1, le=1_000_000)
    country: str = Field(..., max_length=60)
    description: str = Field("", max_length=300)
    technology_stack: List[Annotated[str, Field(max_length=40)]] = Field(default_factory=list, max_length=15)
    research_note: str = Field("", max_length=1200)


@router.post("/playground")
def playground(req: PlaygroundRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    product = _product(db)
    icp_row = _icp(db, product)
    if not icp_row:
        raise HTTPException(status_code=503, detail="Demo ICP is missing.")

    now = utc_now()
    note = req.research_note.strip()
    analysis = analyze_note(note, source="Your research note") if note else {"signals": [], "rejected": []}
    extracted = analysis["signals"]
    accepted = [s for s in extracted if s["evidence"].lower() in note.lower()]
    positives = [
        {
            "signal_type": s["type"],
            "description": s["description"],
            "evidence": s["evidence"],
            "source": s["source"],
            "detected_at": now,
            "strength": s["strength"],
            "confidence": s["confidence"],
        }
        for s in accepted
    ]
    negatives = [
        {**n, "source": NEGATIVE_SOURCE, "detected_at": now, "strength": 1.0, "confidence": 1.0}
        for n in derive_negative_signals(req.employee_count, req.industry, req.country, req.description, icp_row)
    ]
    intent = score_signals(positives + negatives, now)

    icp = ICPData(
        industries=icp_row.industries or [],
        company_size_min=icp_row.company_size_min or 50,
        company_size_max=icp_row.company_size_max or 500,
        geographies=icp_row.geographies or [],
        pain_points=icp_row.pain_points or [],
        technologies=icp_row.technologies or [],
        exclusions=icp_row.exclusions or [],
    )
    acc = AccountData(
        industry=req.industry,
        description=req.description or None,
        employee_count=req.employee_count,
        country=req.country,
        technology_stack=[t.strip() for t in req.technology_stack if t.strip()],
        intent_score_override=intent,
    )
    result = ScoringEngine().compute_score(acc, icp, product_id=product.id)

    class _Sig:  # RecommendationEngine reads attributes, not dict keys
        def __init__(self, d: Dict[str, Any]):
            self.signal_type, self.strength = d["signal_type"], d["strength"]

    rec = RecommendationEngine().get_recommendation(result, [_Sig(p) for p in positives], icp_row)

    def _out(sig: Dict[str, Any], negative: bool) -> Dict[str, Any]:
        return {
            "type": sig["signal_type"],
            "description": sig["description"],
            "evidence": sig["evidence"],
            "source": sig["source"],
            "confidence": sig["confidence"],
            "negative": negative,
        }

    return {
        "score": result.model_dump(),
        "recommendation": _rec_dict(rec),
        "signals": [_out(p, False) for p in positives] + [_out(n, True) for n in negatives],
        "note_had_text": bool(note),
        # Claims that were read but not counted (negated, hearsay, speculative). Always 0 points.
        "rejected": [
            {"sentence": r["sentence"], "category": r["category"], "reason": r["reason"],
             "claimed_type": r["claimed_type"], "points": 0.0}
            for r in analysis["rejected"]
        ],
    }


# --------------------------------------------------------------------------- #
# Reset                                                                        #
# --------------------------------------------------------------------------- #

@router.post("/reset")
def reset() -> Dict[str, Any]:
    from app.db.demo_seed import reset_demo_database

    return {"status": "reset", **reset_demo_database(quiet=True)}
