import csv
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import Account, Contact, Activity, Opportunity, Draft
from app.schemas.crm import PipelineStage, FORWARD_STAGE_ORDER

logger = logging.getLogger(__name__)

class CRMService:
    """
    CRM and Pipeline Service managing contacts, stage transitions, and activity logs.
    """

    @staticmethod
    def is_valid_transition(from_stage: str, to_stage: str) -> bool:
        """
        Enforce valid forward transitions in code (Lost reachable from any stage).
        """
        if from_stage == to_stage:
            return True
        if to_stage == PipelineStage.LOST.value:
            return True

        # Forward index check
        try:
            from_idx = [s.value for s in FORWARD_STAGE_ORDER].index(from_stage)
        except ValueError:
            from_idx = 0

        try:
            to_idx = [s.value for s in FORWARD_STAGE_ORDER].index(to_stage)
        except ValueError:
            return False

        # Only allow advancing forward
        return to_idx > from_idx

    def update_account_stage(
        self,
        db: Session,
        account_id: int,
        to_stage: str,
        notes: Optional[str] = None,
        contact_id: Optional[int] = None,
        timestamp: Optional[datetime] = None
    ) -> Account:
        account = db.query(Account).filter_by(id=account_id).first()
        if not account:
            raise ValueError(f"Account {account_id} not found.")

        current_stage = account.stage or PipelineStage.RESEARCH.value

        if not self.is_valid_transition(current_stage, to_stage):
            raise ValueError(
                f"Invalid stage transition from '{current_stage}' to '{to_stage}'. Forward transitions or 'Lost' only."
            )

        account.stage = to_stage
        ts = timestamp or datetime.utcnow()

        # If reaching Opportunity or Won, ensure Opportunity record exists
        if to_stage in [PipelineStage.OPPORTUNITY.value, PipelineStage.WON.value, PipelineStage.LOST.value]:
            opp = db.query(Opportunity).filter_by(account_id=account.id).first()
            if not opp and to_stage in [PipelineStage.OPPORTUNITY.value, PipelineStage.WON.value]:
                opp = Opportunity(
                    account_id=account.id,
                    stage=to_stage,
                    deal_value=35000.0,
                    probability=0.8 if to_stage == PipelineStage.WON.value else 0.5,
                    created_at=ts,
                    closed_at=ts if to_stage == PipelineStage.WON.value else None
                )
                db.add(opp)
            elif opp:
                opp.stage = to_stage
                if to_stage in [PipelineStage.WON.value, PipelineStage.LOST.value]:
                    opp.closed_at = ts
                    opp.probability = 1.0 if to_stage == PipelineStage.WON.value else 0.0

        # Log Activity
        activity = Activity(
            account_id=account.id,
            contact_id=contact_id,
            activity_type=f"stage_changed_to_{to_stage.lower()}",
            status="completed",
            timestamp=ts,
            activity_metadata={
                "from_stage": current_stage,
                "to_stage": to_stage,
                "notes": notes or ""
            }
        )
        db.add(activity)
        db.commit()
        db.refresh(account)
        return account

    def mark_outreach_sent(
        self,
        db: Session,
        account_id: int,
        draft_id: Optional[int] = None,
        contact_id: Optional[int] = None,
        notes: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> Account:
        """
        An approved draft only moves the account to Contacted when a human marks it as sent manually.
        """
        account = db.query(Account).filter_by(id=account_id).first()
        if not account:
            raise ValueError(f"Account {account_id} not found.")

        ts = timestamp or datetime.utcnow()

        if draft_id:
            draft = db.query(Draft).filter_by(id=draft_id).first()
            if not draft:
                raise ValueError(f"Draft {draft_id} not found.")
            if draft.status != "approved":
                raise ValueError(f"Cannot mark draft as sent: draft status is '{draft.status}', but must be 'approved'.")
            draft.status = "sent"

        # Advance to Contacted if still in Research
        if account.stage == PipelineStage.RESEARCH.value or not account.stage:
            self.update_account_stage(
                db=db,
                account_id=account.id,
                to_stage=PipelineStage.CONTACTED.value,
                notes=notes or "Manual outreach sent by SDR",
                contact_id=contact_id,
                timestamp=ts
            )

        # Log outreach_sent activity
        sent_act = Activity(
            account_id=account.id,
            contact_id=contact_id,
            activity_type="outreach_sent",
            status="completed",
            timestamp=ts,
            activity_metadata={"draft_id": draft_id, "notes": notes or ""}
        )
        db.add(sent_act)
        db.commit()
        db.refresh(account)
        return account

    def add_contact(
        self,
        db: Session,
        account_id: int,
        name: str,
        role: Optional[str] = None,
        email: Optional[str] = None,
        linkedin_url: Optional[str] = None
    ) -> Contact:
        account = db.query(Account).filter_by(id=account_id).first()
        if not account:
            raise ValueError(f"Account {account_id} not found.")

        contact = Contact(
            account_id=account.id,
            name=name,
            role=role,
            email=email,
            linkedin_url=linkedin_url
        )
        db.add(contact)
        db.commit()
        db.refresh(contact)
        return contact

    def load_contacts_from_csv(self, db: Session, csv_path: Optional[Path] = None) -> int:
        """
        Loads contacts from CSV into the database matching on company name.
        """
        if csv_path is None:
            csv_path = Path(__file__).parent.parent.parent / "data" / "contacts.csv"

        if not csv_path.exists():
            return 0

        loaded = 0
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                comp_name = row.get("company", "").strip()
                name = row.get("name", "").strip()
                if not comp_name or not name:
                    continue

                account = db.query(Account).filter_by(name=comp_name).first()
                if not account:
                    continue

                existing = db.query(Contact).filter_by(account_id=account.id, name=name).first()
                if not existing:
                    contact = Contact(
                        account_id=account.id,
                        name=name,
                        role=row.get("role", "").strip(),
                        email=row.get("email", "").strip(),
                        linkedin_url=row.get("linkedin_url", "").strip()
                    )
                    db.add(contact)
                    loaded += 1

        db.commit()
        return loaded
