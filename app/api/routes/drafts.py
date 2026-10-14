from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.models import Draft, Account, Activity
from app.schemas.draft import DraftResponse, DraftUpdateRequest

router = APIRouter(prefix="/drafts", tags=["Drafts & Outreach Review"])

def _to_draft_response(draft: Draft, db: Session) -> DraftResponse:
    account = db.query(Account).filter_by(id=draft.account_id).first()
    return DraftResponse(
        id=draft.id,
        account_id=draft.account_id,
        contact_id=draft.contact_id,
        account_name=account.name if account else f"Account {draft.account_id}",
        body=draft.body,
        original_body=draft.original_body,
        status=draft.status,
        evidence_ids=draft.evidence_ids or [],
        created_at=draft.created_at,
        reviewed_at=draft.reviewed_at
    )

@router.get("", response_model=List[DraftResponse])
def list_drafts(status: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Draft)
    if status:
        query = query.filter(Draft.status == status)
    drafts = query.order_by(Draft.created_at.desc()).all()
    return [_to_draft_response(d, db) for d in drafts]

@router.get("/{id}", response_model=DraftResponse)
def get_draft(id: int, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter_by(id=id).first()
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft {id} not found.")
    return _to_draft_response(draft, db)

@router.patch("/{id}", response_model=DraftResponse)
def update_draft(id: int, payload: DraftUpdateRequest, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter_by(id=id).first()
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft {id} not found.")
    if draft.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot edit draft with status '{draft.status}'. Only pending drafts can be edited."
        )

    draft.body = payload.body
    db.commit()
    db.refresh(draft)
    return _to_draft_response(draft, db)

@router.post("/{id}/approve", response_model=DraftResponse)
def approve_draft(id: int, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter_by(id=id).first()
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft {id} not found.")
    if draft.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve draft with status '{draft.status}'. Only pending drafts can be approved."
        )

    draft.status = "approved"
    draft.reviewed_at = datetime.utcnow()

    # Create outreach_approved Activity
    activity = Activity(
        account_id=draft.account_id,
        contact_id=draft.contact_id,
        activity_type="outreach_approved",
        status="approved",
        activity_metadata={"draft_id": draft.id, "body": draft.body}
    )
    db.add(activity)
    db.commit()
    db.refresh(draft)

    return _to_draft_response(draft, db)

@router.post("/{id}/reject", response_model=DraftResponse)
def reject_draft(id: int, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter_by(id=id).first()
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft {id} not found.")
    if draft.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject draft with status '{draft.status}'. Only pending drafts can be rejected."
        )

    draft.status = "rejected"
    draft.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(draft)

    return _to_draft_response(draft, db)

