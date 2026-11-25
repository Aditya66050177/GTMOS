import csv
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models import Account
from app.core.timeutil import utc_now

class ResearchEngine:
    """
    Engine for importing and managing account datasets.
    """
    def __init__(self, llm_service=None):
        self._llm = llm_service

    def load_accounts_from_csv(self, db: Session, csv_path: Optional[Path] = None) -> int:
        """
        Idempotently loads account records from CSV into the database.
        """
        if csv_path is None:
            csv_path = Path(__file__).parent.parent.parent / "data" / "accounts.csv"

        if not csv_path.exists():
            raise FileNotFoundError(f"Accounts CSV file not found at {csv_path}")

        loaded_count = 0

        with open(csv_path, mode="r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                domain = row.get("domain", "").strip()
                name = row.get("company", "").strip()

                if not name:
                    continue

                tech_str = row.get("technologies", "")
                tech_stack = [t.strip() for t in tech_str.replace(";", ",").split(",") if t.strip()]

                emp_str = row.get("employees", "0")
                try:
                    emp_count = int(emp_str)
                except ValueError:
                    emp_count = 0

                supp_str = row.get("support_team_size", "0")
                try:
                    supp_team_size = int(supp_str)
                except ValueError:
                    supp_team_size = 0

                existing_account = None
                if domain:
                    existing_account = db.query(Account).filter_by(domain=domain).first()
                if not existing_account and name:
                    existing_account = db.query(Account).filter_by(name=name).first()

                if existing_account:
                    existing_account.name = name
                    existing_account.domain = domain
                    existing_account.industry = row.get("industry", "").strip()
                    existing_account.employee_count = emp_count
                    existing_account.country = row.get("country", "").strip()
                    existing_account.description = row.get("description", "").strip()
                    existing_account.technology_stack = tech_stack
                    existing_account.funding = row.get("funding", "").strip()
                    existing_account.support_team_size = supp_team_size
                else:
                    account = Account(
                        name=name,
                        domain=domain,
                        industry=row.get("industry", "").strip(),
                        employee_count=emp_count,
                        country=row.get("country", "").strip(),
                        description=row.get("description", "").strip(),
                        technology_stack=tech_stack,
                        funding=row.get("funding", "").strip(),
                        support_team_size=supp_team_size
                    )
                    db.add(account)

                loaded_count += 1

        db.commit()
        return loaded_count

    def extract_signals_from_text(self, db: Session, account: Account, raw_text: str, source: str, date_str: str) -> list:
        """
        Uses LLM to extract signals from raw text and validates the evidence constraint.
        """
        from app.ai.llm import LLMService
        from app.schemas.signal import SignalListSchema
        from app.models import Signal, Activity
        from app.ai.prompts import EXTRACT_SIGNALS_PROMPT
        import logging
        from datetime import datetime, timezone

        logger = logging.getLogger(__name__)

        llm = self._llm or LLMService()
        prompt = EXTRACT_SIGNALS_PROMPT.format(
            raw_text=raw_text,
            source=source,
            date=date_str
        )

        extracted = llm.generate_structured(prompt, SignalListSchema)
        valid_signals = []
        raw_text_lower = raw_text.lower()

        for sig in extracted.signals:
            evidence_lower = sig.evidence.lower()
            rejected = False
            
            words = evidence_lower.split()
            if len(words) > 3:
                chunk1 = " ".join(words[:3])
                chunk2 = " ".join(words[-3:])
                if chunk1 not in raw_text_lower and chunk2 not in raw_text_lower and evidence_lower not in raw_text_lower:
                    rejected = True
            else:
                if evidence_lower not in raw_text_lower:
                    rejected = True

            if rejected:
                logger.warning(f"Rejected unsupported claim for {account.name}: {sig.type}. Evidence not found: {sig.evidence}")
                db.add(Activity(
                    account_id=account.id,
                    activity_type="rejected_signal",
                    status="rejected",
                    activity_metadata={"type": sig.type, "evidence": sig.evidence, "source": source}
                ))
                continue
            
            try:
                parsed_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if parsed_date.tzinfo is not None:
                    parsed_date = parsed_date.astimezone(timezone.utc).replace(tzinfo=None)
            except ValueError:
                parsed_date = utc_now()

            # evidence is a JSON column, so compare it in Python rather than SQL.
            same_slot = db.query(Signal).filter_by(
                account_id=account.id,
                signal_type=sig.type,
                source=source,
                detected_at=parsed_date,
            ).all()
            if any(existing.evidence == sig.evidence for existing in same_slot):
                continue

            new_sig = Signal(
                account_id=account.id,
                signal_type=sig.type,
                description=sig.description,
                strength=sig.strength,
                source=source,
                detected_at=parsed_date,
                confidence=sig.confidence,
                evidence=sig.evidence
            )
            db.add(new_sig)
            valid_signals.append(new_sig)
            
        db.commit()
        return valid_signals

    def extract_signals_from_csv(
        self,
        db: Session,
        csv_path: Optional[Path] = None,
        anchor_to_today: bool = False,
    ) -> int:
        """Extract signals from the research-notes CSV.

        With anchor_to_today=True, every note date is shifted by whole days so the
        newest note lands on today while relative ages stay the same. That keeps a
        long-running demo from silently decaying its synthetic signals to zero.
        """
        if csv_path is None:
            csv_path = Path(__file__).parent.parent.parent / "data" / "signals.csv"

        if not csv_path.exists():
            raise FileNotFoundError(f"Signals CSV file not found at {csv_path}")

        with open(csv_path, mode="r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))

        shift = _days_to_today(rows) if anchor_to_today else timedelta(0)
        accounts_by_name = {a.name: a for a in db.query(Account).all()}

        extracted_count = 0
        for row in rows:
            account_name = row.get("account", "").strip()
            raw_text = row.get("raw_text", "").strip()
            source = row.get("source", "").strip()
            date_str = _shift_iso(row.get("date", "").strip(), shift)

            account = accounts_by_name.get(account_name)
            if not account or not raw_text:
                continue

            valid_sigs = self.extract_signals_from_text(db, account, raw_text, source, date_str)
            extracted_count += len(valid_sigs)

        return extracted_count


def _parse_iso(date_str: str) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _days_to_today(rows: list) -> timedelta:
    dates = [d for d in (_parse_iso(r.get("date", "").strip()) for r in rows) if d]
    if not dates:
        return timedelta(0)
    return timedelta(days=(utc_now().date() - max(dates).date()).days)


def _shift_iso(date_str: str, shift: timedelta) -> str:
    parsed = _parse_iso(date_str)
    if parsed is None or not shift:
        return date_str
    return (parsed + shift).isoformat() + "Z"
