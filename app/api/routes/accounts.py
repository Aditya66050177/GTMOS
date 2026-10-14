from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.models import Account, Product, Score
from app.schemas.account import AccountResponse
from app.schemas.scoring import ScoreResult
from app.services.scoring_engine import ScoringEngine
from app.services.research_engine import ResearchEngine

router = APIRouter(prefix="/accounts", tags=["Accounts"])

@router.get("", response_model=List[AccountResponse])
def list_accounts(db: Session = Depends(get_db)):
    accounts = db.query(Account).all()
    if not accounts:
        re = ResearchEngine()
        re.load_accounts_from_csv(db)
        accounts = db.query(Account).all()
    return accounts

@router.get("/{id}")
def get_account(id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter_by(id=id).first()
    if not account:
        raise HTTPException(status_code=404, detail=f"Account {id} not found.")

    scores = db.query(Score).filter_by(account_id=id).all()
    scores_data = []
    for s in scores:
        scores_data.append({
            "product_id": s.product_id,
            "total_score": s.total_score,
            "tier": s.tier,
            "icp_fit": s.icp_fit,
            "company_fit": s.company_fit,
            "technology_fit": s.technology_fit,
            "intent_score": s.intent_score,
            "geography_score": s.geography_score,
            "reasoning": s.reasoning
        })

    return {
        "id": account.id,
        "name": account.name,
        "domain": account.domain,
        "industry": account.industry,
        "employee_count": account.employee_count,
        "country": account.country,
        "description": account.description,
        "technology_stack": account.technology_stack,
        "funding": account.funding,
        "support_team_size": account.support_team_size,
        "created_at": account.created_at,
        "scores": scores_data
    }

@router.post("/{id}/score", response_model=ScoreResult)
def score_account(id: int, product_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    account = db.query(Account).filter_by(id=id).first()
    if not account:
        raise HTTPException(status_code=404, detail=f"Account {id} not found.")
    if product_id is not None:
        product = db.query(Product).filter_by(id=product_id).first()
    else:
        product = db.query(Product).first()
    if not product:
        raise HTTPException(status_code=404, detail="No product found in database to score against.")

    engine = ScoringEngine()
    return engine.score_account(db, account, product)

from app.schemas.research import ResearchRequest
from app.schemas.signal import SignalSchema

@router.post("/{id}/research", response_model=List[SignalSchema])
def perform_research(id: int, req: ResearchRequest, db: Session = Depends(get_db)):
    account = db.query(Account).filter_by(id=id).first()
    if not account:
        raise HTTPException(status_code=404, detail=f"Account {id} not found.")

    re = ResearchEngine()
    signals = re.extract_signals_from_text(
        db=db,
        account=account,
        raw_text=req.raw_text,
        source=req.source,
        date_str=req.date_str
    )
    
    # Return in Pydantic schema format
    res = []
    for s in signals:
        res.append(SignalSchema(
            type=s.signal_type,
            description=s.description,
            strength=s.strength,
            source=s.source,
            detected_at=s.detected_at,
            confidence=s.confidence,
            evidence=s.evidence
        ))
    return res

@router.get("/{id}/signals", response_model=List[SignalSchema])
def get_signals(id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter_by(id=id).first()
    if not account:
        raise HTTPException(status_code=404, detail=f"Account {id} not found.")
        
    from app.models import Signal
    signals = db.query(Signal).filter_by(account_id=id).order_by(Signal.detected_at.desc()).all()
    
    res = []
    for s in signals:
        res.append(SignalSchema(
            type=s.signal_type,
            description=s.description,
            strength=s.strength,
            source=s.source,
            detected_at=s.detected_at,
            confidence=s.confidence,
            evidence=s.evidence
        ))
    return res

from app.schemas.draft import DraftResponse
from app.services.personalization import PersonalizationEngine

@router.post("/{id}/personalize", response_model=DraftResponse)
def personalize_account(
    id: int,
    product_id: Optional[int] = Query(None),
    contact_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    account = db.query(Account).filter_by(id=id).first()
    if not account:
        raise HTTPException(status_code=404, detail=f"Account {id} not found.")

    engine = PersonalizationEngine()
    try:
        draft = engine.generate_draft(
            db=db,
            account_id=id,
            product_id=product_id,
            contact_id=contact_id
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Personalization error: {str(e)}")

    return DraftResponse(
        id=draft.id,
        account_id=draft.account_id,
        contact_id=draft.contact_id,
        account_name=account.name,
        body=draft.body,
        original_body=draft.original_body,
        status=draft.status,
        evidence_ids=draft.evidence_ids or [],
        created_at=draft.created_at,
        reviewed_at=draft.reviewed_at
    )

from app.schemas.crm import StageUpdateRequest, ContactCreateRequest, ContactResponse, ActivityResponse
from app.services.crm_service import CRMService

@router.post("/{id}/stage", response_model=AccountResponse)
def update_stage(id: int, payload: StageUpdateRequest, db: Session = Depends(get_db)):
    crm = CRMService()
    try:
        updated_account = crm.update_account_stage(
            db=db,
            account_id=id,
            to_stage=payload.stage.value,
            notes=payload.notes
        )
        return updated_account
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.post("/{id}/contacts", response_model=ContactResponse)
def add_contact(id: int, payload: ContactCreateRequest, db: Session = Depends(get_db)):
    crm = CRMService()
    try:
        contact = crm.add_contact(
            db=db,
            account_id=id,
            name=payload.name,
            role=payload.role,
            email=payload.email,
            linkedin_url=payload.linkedin_url
        )
        return contact
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.get("/{id}/activities", response_model=List[ActivityResponse])
def get_account_activities(id: int, db: Session = Depends(get_db)):
    from app.models import Activity
    account = db.query(Account).filter_by(id=id).first()
    if not account:
        raise HTTPException(status_code=404, detail=f"Account {id} not found.")

    activities = (
        db.query(Activity)
        .filter_by(account_id=id)
        .order_by(Activity.timestamp.desc())
        .all()
    )
    res = []
    for act in activities:
        res.append(ActivityResponse(
            id=act.id,
            account_id=act.account_id,
            contact_id=act.contact_id,
            activity_type=act.activity_type,
            status=act.status,
            timestamp=act.timestamp,
            metadata=act.activity_metadata or {}
        ))
    return res

@router.post("/{id}/mark_sent", response_model=AccountResponse)
def mark_sent(
    id: int,
    draft_id: Optional[int] = Query(None),
    contact_id: Optional[int] = Query(None),
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    crm = CRMService()
    try:
        updated_account = crm.mark_outreach_sent(
            db=db,
            account_id=id,
            draft_id=draft_id,
            contact_id=contact_id,
            notes=notes
        )
        return updated_account
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


