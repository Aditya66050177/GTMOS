import csv
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
from app.models import Account

class ResearchEngine:
    """
    Engine for importing and managing account datasets.
    """
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
        from datetime import datetime

        logger = logging.getLogger(__name__)

        llm = LLMService()
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
            except ValueError:
                parsed_date = datetime.utcnow()

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

    def extract_signals_from_csv(self, db: Session, csv_path: Optional[Path] = None) -> int:
        if csv_path is None:
            csv_path = Path(__file__).parent.parent.parent / "data" / "signals.csv"

        if not csv_path.exists():
            raise FileNotFoundError(f"Signals CSV file not found at {csv_path}")

        extracted_count = 0
        with open(csv_path, mode="r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                account_name = row.get("account", "").strip()
                raw_text = row.get("raw_text", "").strip()
                source = row.get("source", "").strip()
                date_str = row.get("date", "").strip()

                if not account_name or not raw_text:
                    continue

                account = db.query(Account).filter_by(name=account_name).first()
                if not account:
                    continue

                valid_sigs = self.extract_signals_from_text(db, account, raw_text, source, date_str)
                extracted_count += len(valid_sigs)

        return extracted_count
