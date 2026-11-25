"""Explain an account's score, intent and recommendation from stored data.

Nothing here recomputes fit or decides anything. It reads:
* the Score row (fit components and reasons exactly as compute_score() produced them),
* the account's Signal rows, run through signal_contributions() — the same function
  score_signals() sums — at the time the account was scored,
* RecommendationEngine.get_recommendation(), the same call the rest of the app makes,
* research_note / rejected_signal activities recorded at ingestion (provenance only).

It then checks that the recomputed intent equals the stored intent and says so.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import Account, Activity, ICPProfile, Product, Score, Signal
from app.schemas.explain import (
    AccountExplanation, AccountRefOut, ComparisonOut, EvidenceSummaryOut, FeaturedComparisonOut,
    FitComponentOut, FitOut, IntentOut, ReasonOut, RecencyRulesOut, RecommendationOut,
    RejectedEvidenceOut, ResearchNoteOut, SignalContributionOut, TierOut,
)
from app.services.recommendation_engine import ACTION_RULES, RecommendationEngine
from app.services.scoring_engine import REASON_COMPONENT, TIER_THRESHOLDS
from app.services.signal_engine import (
    AGING_AFTER_DAYS, AGING_DECAY, EXPIRED_AFTER_DAYS, INTENT_MAX, NEGATIVE_SOURCE,
    recency_status, score_signals, signal_contributions,
)

FIT_COMPONENTS = ("ICP Fit", "Company Fit", "Technology Fit", "Geography Fit")
FIT_MEANING = ("How closely the company resembles the ideal customer profile: industry and pain points, "
               "company size, technology stack and geography. It does not say whether they need us now.")
INTENT_MEANING = ("Whether there is credible, recent evidence the company might need the product now. "
                  "Built only from verified buying signals, minus penalties for hard disqualifiers.")
DATA_LABEL = "Synthetic demonstration data. No real companies, people or research."

SIGNAL_LABELS = {
    "support_hiring": "Support hiring", "funding": "Funding", "product_launch": "Product launch",
    "international_expansion": "International expansion", "relevant_technology": "Relevant technology",
    "rapid_growth": "Rapid growth", "executive_change": "Executive change", "too_small": "Too small",
    "wrong_industry": "Wrong industry", "wrong_geography": "Wrong geography", "no_use_case": "No use case",
}
# Product hypotheses (why a support-automation product cares). Stated as hypotheses, not facts.
WHY_IT_MATTERS = {
    "support_hiring": "Hiring support staff suggests ticket volume is growing faster than the team.",
    "funding": "New funding often comes with a mandate to scale and budget for tooling.",
    "product_launch": "A launch usually brings a wave of new customer questions.",
    "international_expansion": "New regions mean new languages, time zones and support load.",
    "relevant_technology": "Runs tools the product integrates with, which lowers adoption cost.",
    "rapid_growth": "Fast growth tends to outpace support capacity.",
    "executive_change": "A new leader often reviews tooling and sets new initiatives.",
    "too_small": "Below the size where the ICP says the problem is painful enough to pay for.",
    "wrong_industry": "Outside the industries the ICP targets.",
    "wrong_geography": "Outside the regions the ICP targets.",
    "no_use_case": "Matches an ICP exclusion, so there is no fit for the product.",
}
_SENTENCES = re.compile(r"(?<=[.!?])\s+")


def _label(signal_type: Optional[str]) -> str:
    return SIGNAL_LABELS.get(signal_type or "", (signal_type or "unknown").replace("_", " ").capitalize())


def tier_rule(total: float, tier: str) -> str:
    for name, minimum in TIER_THRESHOLDS:
        if name == tier:
            upper = next((m for n, m in TIER_THRESHOLDS if m > minimum), None)
            span = f">= {minimum:g}" if upper is None else f"{minimum:g}-{upper - 0.1:g}"
            return f"total {total:.1f} is in {span} -> {tier}"
    return f"total {total:.1f} -> {tier}"


def _scored_at(score: Score, signals: List[Signal]) -> datetime:
    """When intent was last computed. Disqualifier rows are rewritten at every scoring,
    so the newest one is the best timestamp; otherwise the score row's creation time."""
    negative_times = [s.detected_at for s in signals if s.source == NEGATIVE_SOURCE and s.detected_at]
    candidates = [t for t in [score.created_at, *negative_times] if t]
    return max(candidates)


def _notes(db: Session, account_id: int) -> Tuple[List[Activity], List[Activity]]:
    acts = db.query(Activity).filter(
        Activity.account_id == account_id,
        Activity.activity_type.in_(["research_note", "rejected_signal"]),
    ).order_by(Activity.id).all()
    return ([a for a in acts if a.activity_type == "research_note"],
            [a for a in acts if a.activity_type == "rejected_signal"])


def _source_sentence(quote: Optional[str], signal_id: int, notes: List[Activity]) -> Optional[str]:
    if not quote:
        return None
    for note in notes:
        meta = note.activity_metadata or {}
        if signal_id not in (meta.get("signal_ids") or []):
            continue
        for sentence in _SENTENCES.split(meta.get("raw_text") or ""):
            if quote.lower() in sentence.lower():
                return sentence.strip()
    return None


def explain_account(db: Session, account_id: int, product: Optional[Product] = None) -> Optional[AccountExplanation]:
    account = db.get(Account, account_id)
    if account is None:
        return None
    product = product or db.query(Product).order_by(Product.id).first()
    score = db.query(Score).filter_by(account_id=account.id, product_id=product.id).first() if product else None
    if score is None:
        return None
    icp = db.query(ICPProfile).filter_by(product_id=product.id).first()

    signals = db.query(Signal).filter_by(account_id=account.id).order_by(Signal.id).all()
    as_of = _scored_at(score, signals)
    contributions = signal_contributions(signals, as_of)
    note_acts, rejected_acts = _notes(db, account.id)

    buying, disqualifiers = [], []
    for c in contributions:
        sig = c.signal
        if c.weight < 0:
            status = "disqualifier"
        elif c.weight == 0:
            status = "not_weighted"
        elif not c.counted:
            status = "superseded"
        else:
            status = recency_status(c.days_old)
        out = SignalContributionOut(
            signal_id=sig.id, signal_type=c.signal_type, label=_label(c.signal_type), status=status,
            counted=c.counted, source=sig.source, detected_at=sig.detected_at, days_old=max(0, c.days_old),
            quote=sig.evidence if isinstance(sig.evidence, str) else None,
            source_sentence=None if c.weight < 0 else _source_sentence(sig.evidence, sig.id, note_acts),
            weight=c.weight, strength=c.strength, confidence=c.confidence, decay=c.decay,
            points=round(c.points, 4), why_it_matters=WHY_IT_MATTERS.get(c.signal_type),
        )
        (disqualifiers if c.weight < 0 else buying).append(out)

    raw_sum = sum(c.points for c in contributions)
    raw_total = round(raw_sum, 4)
    recomputed = score_signals(signals, as_of)

    reasons = (score.reasoning or {}).get("reasons", [])
    comp_scores = {c["component"]: c for c in (score.reasoning or {}).get("components", [])}
    fit_components = [
        FitComponentOut(
            name=name,
            score=comp_scores[name]["score"],
            max_score=comp_scores[name]["max_score"],
            reasons=[ReasonOut(**r) for r in reasons if REASON_COMPONENT.get(r["rule"]) == name],
        )
        for name in FIT_COMPONENTS if name in comp_scores
    ]
    fit_score = round(sum(c.score for c in fit_components), 1)

    positives = [s for s in signals if s.source != NEGATIVE_SOURCE]
    rec = RecommendationEngine().get_recommendation(score, positives, icp)
    rule_tier, rule_condition, _action = ACTION_RULES[rec.rule_id]

    rejected = [
        RejectedEvidenceOut(
            sentence=m.get("sentence") or m.get("evidence"), category=m.get("category") or "unsupported",
            reason=m.get("reason"), claimed_type=m.get("claimed_type") or m.get("type"),
            source=m.get("source"), date=m.get("date"), dataset=m.get("dataset"), points=0.0,
        )
        for m in ((a.activity_metadata or {}) for a in rejected_acts)
    ]

    disq_reasons = [d.label + ": " + (sig_desc or "") for d, sig_desc in
                    ((d, next((s.description for s in signals if s.id == d.signal_id), None)) for d in disqualifiers)]
    disq_reasons += [f"{r.rule}: {r.text}" for comp in fit_components for r in comp.reasons if not r.met]

    notes = [
        ResearchNoteOut(
            source=m.get("source"), date=m.get("date"), dataset=m.get("dataset"), label=m.get("label"),
            raw_text=m.get("raw_text"), signals_extracted=len(m.get("signal_ids") or []),
        )
        for m in ((a.activity_metadata or {}) for a in note_acts)
    ]

    counted = [b for b in buying if b.counted]
    return AccountExplanation(
        account=AccountRefOut(id=account.id, name=account.name, industry=account.industry,
                              employee_count=account.employee_count, country=account.country, stage=account.stage),
        data_label=DATA_LABEL,
        fit=FitOut(score=fit_score, meaning=FIT_MEANING, components=fit_components),
        intent=IntentOut(
            score=score.intent_score, max_score=INTENT_MAX, meaning=INTENT_MEANING, raw_total=raw_total,
            clamped=raw_sum < 0.0 or raw_sum > INTENT_MAX, recomputed_score=recomputed,
            matches_stored_score=abs(recomputed - (score.intent_score or 0.0)) < 1e-9, as_of=as_of,
            buying_signals=buying, disqualifiers=disqualifiers,
            recency_rules=RecencyRulesOut(current_max_days=AGING_AFTER_DAYS, aging_max_days=EXPIRED_AFTER_DAYS,
                                          aging_decay=AGING_DECAY),
        ),
        total=TierOut(total=score.total_score, tier=score.tier, rule=tier_rule(score.total_score, score.tier)),
        recommendation=RecommendationOut(
            action=rec.action, rule_id=rec.rule_id, rule=f"{rule_tier} and {rule_condition} -> {rec.action}",
            reason=rec.reason, suggested_persona=rec.suggested_persona, suggested_angle=rec.suggested_angle,
        ),
        disqualification_reasons=disq_reasons,
        rejected_evidence=rejected,
        research_notes=notes,
        evidence_summary=EvidenceSummaryOut(
            buying_signals=len(buying), counted=len(counted),
            current=sum(b.status == "current" for b in buying), aging=sum(b.status == "aging" for b in buying),
            expired=sum(b.status == "expired" for b in buying), superseded=sum(b.status == "superseded" for b in buying),
            disqualifiers=len(disqualifiers), rejected=len(rejected),
        ),
        includes_synthetic_demo_additions=any(n.dataset == "demo_addition" for n in notes),
    )


def _fmt(n: float) -> str:
    return f"{n:.1f}"


def compare_observations(items: List[AccountExplanation]) -> List[str]:
    """Plain statements derived only from the numbers in the explanations."""
    obs: List[str] = []
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            an, bn = a.account.name, b.account.name
            if a.fit.score != b.fit.score:
                hi, lo = (a, b) if a.fit.score > b.fit.score else (b, a)
                obs.append(f"{hi.account.name} has higher fit ({_fmt(hi.fit.score)} vs {_fmt(lo.fit.score)} of 80).")
            if a.intent.score != b.intent.score:
                hi, lo = (a, b) if a.intent.score > b.intent.score else (b, a)
                obs.append(f"{hi.account.name} has stronger intent ({_fmt(hi.intent.score)} vs {_fmt(lo.intent.score)} of 20), "
                           f"from {hi.evidence_summary.counted} counted signal(s) vs {lo.evidence_summary.counted}.")
            if a.total.tier == b.total.tier and a.recommendation.action != b.recommendation.action:
                obs.append(f"Both are {a.total.tier}, but the actions differ: {an} -> {a.recommendation.action} "
                           f"({a.recommendation.rule}); {bn} -> {b.recommendation.action} ({b.recommendation.rule}). "
                           f"Within a tier, intent decides the action.")
            elif a.recommendation.action == b.recommendation.action:
                obs.append(f"{an} and {bn} get the same action ({a.recommendation.action}).")
            else:
                obs.append(f"{an} is {a.total.tier} -> {a.recommendation.action}; {bn} is {b.total.tier} -> {b.recommendation.action}.")
    for item in items:
        if item.rejected_evidence:
            cats = sorted({r.category for r in item.rejected_evidence})
            obs.append(f"{item.account.name}: {len(item.rejected_evidence)} rejected claim(s) ({', '.join(cats)}) counted for 0 points.")
    return obs


def compare_accounts(db: Session, ids: List[int]) -> Optional[ComparisonOut]:
    items = [explain_account(db, i) for i in ids]
    if any(x is None for x in items):
        return None
    return ComparisonOut(accounts=items, observations=compare_observations(items))


def featured_comparisons(db: Session) -> List[FeaturedComparisonOut]:
    """Comparison sets picked by stated rules from the current data (no hand-picked ids)."""
    product = db.query(Product).order_by(Product.id).first()
    if not product:
        return []
    rows = db.query(Account, Score).join(Score, Score.account_id == Account.id).filter(Score.product_id == product.id).all()
    fit = {a.id: (s.total_score - (s.intent_score or 0.0)) for a, s in rows}
    intent = {a.id: (s.intent_score or 0.0) for a, s in rows}
    names = {a.id: a.name for a, _ in rows}

    out: List[FeaturedComparisonOut] = []
    high_fit_no_intent = sorted((i for i in fit if fit[i] >= 75 and intent[i] == 0), key=lambda i: (-fit[i], i))
    moderate_fit_strong_intent = sorted((i for i in fit if fit[i] < 70 and intent[i] >= 15), key=lambda i: (-intent[i], -fit[i], i))
    if high_fit_no_intent and moderate_fit_strong_intent:
        out.append(FeaturedComparisonOut(
            title="Strong intent vs strong fit",
            selection_rule="Highest-intent account with fit < 70 and intent >= 15, vs highest-fit account with fit >= 75 and intent = 0",
            account_ids=[moderate_fit_strong_intent[0], high_fit_no_intent[0]],
        ))
    top = sorted(fit, key=lambda i: (-(fit[i] + intent[i]), i))[:1]
    acme = [i for i, n in names.items() if n == "Acme Technologies"]
    if top and acme and top[0] != acme[0]:
        out.append(FeaturedComparisonOut(
            title="Why a near-perfect fit is not called first",
            selection_rule=(f"Top-scoring account vs Acme Technologies (fit {fit[acme[0]]:.1f}, "
                            f"intent {intent[acme[0]]:.1f})"),
            account_ids=[top[0], acme[0]],
        ))
    return out
