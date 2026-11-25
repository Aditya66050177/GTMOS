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

    def extract_signals_from_text(
        self,
        db: Session,
        account: Account,
        raw_text: str,
        source: str,
        date_str: str,
        dataset: str = "manual",
        label: Optional[str] = None,
    ) -> list:
        """
        Uses LLM to extract signals from raw text and validates the evidence constraint.

        Also records provenance as activities (they never affect scores):
        * ``research_note``: the full note, its source/date, dataset and resulting signal ids.
        * ``rejected_signal``: every claim that must not count (negated, hearsay,
          speculative, or quoted evidence not found in the note), with zero points.
        Re-ingesting an identical note records nothing new.
        """
        from app.ai.llm import LLMService
        from app.schemas.signal import SignalListSchema
        from app.models import Signal, Activity
        from app.ai.prompts import EXTRACT_SIGNALS_PROMPT
        import logging

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

        parsed_date = _parse_iso(date_str) or utc_now()
        note_meta = {"raw_text": raw_text, "source": source, "date": parsed_date.isoformat(),
                     "dataset": dataset, "label": label}
        already_recorded = any(
            (act.activity_metadata or {}).get("raw_text") == raw_text
            and (act.activity_metadata or {}).get("source") == source
            and (act.activity_metadata or {}).get("date") == note_meta["date"]
            for act in db.query(Activity).filter_by(account_id=account.id, activity_type="research_note").all()
        )
        note_activity = None
        if not already_recorded:
            note_activity = Activity(account_id=account.id, activity_type="research_note",
                                     status="ingested", activity_metadata=dict(note_meta, signal_ids=[]))
            db.add(note_activity)
            db.flush()

        def record_rejection(sentence: str, category: str, reason: str, claimed_type: Optional[str]) -> None:
            if already_recorded:
                return
            db.add(Activity(
                account_id=account.id,
                activity_type="rejected_signal",
                status="rejected",
                activity_metadata={
                    "sentence": sentence, "category": category, "reason": reason,
                    "claimed_type": claimed_type, "source": source, "date": note_meta["date"],
                    "dataset": dataset, "note_activity_id": note_activity.id if note_activity else None,
                    "points": 0.0,
                    # kept for older readers of this activity type
                    "type": claimed_type, "evidence": sentence,
                },
            ))

        for rej in extracted.rejected:
            record_rejection(rej.sentence, rej.category, rej.reason, rej.claimed_type)

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
                record_rejection(sig.evidence, "unsupported",
                                 "Quoted evidence was not found in the source text", sig.type)
                continue

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

        if note_activity is not None:
            db.flush()
            note_activity.activity_metadata = dict(note_meta, signal_ids=[s.id for s in valid_signals])
        db.commit()
        return valid_signals

    def extract_signals_from_csv(
        self,
        db: Session,
        csv_path: Optional[Path] = None,
        anchor_to_today: bool = False,
        shift: Optional[timedelta] = None,
        dataset: str = "baseline",
    ) -> int:
        """Extract signals from a research-notes CSV.

        With anchor_to_today=True, note dates are shifted so the newest note lands on
        the current moment while every relative age stays exact. Pass ``shift`` to
        reuse one dataset's shift for another (demo additions use the baseline's).
        An optional ``label`` column is stored with each note's provenance.
        """
        if csv_path is None:
            csv_path = Path(__file__).parent.parent.parent / "data" / "signals.csv"

        if not csv_path.exists():
            raise FileNotFoundError(f"Signals CSV file not found at {csv_path}")

        rows = read_notes(csv_path)
        if shift is None:
            shift = anchor_shift(rows) if anchor_to_today else timedelta(0)
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

            valid_sigs = self.extract_signals_from_text(
                db, account, raw_text, source, date_str,
                dataset=dataset, label=(row.get("label") or "").strip() or None,
            )
            extracted_count += len(valid_sigs)

        return extracted_count


def read_notes(csv_path: Path) -> list:
    with open(csv_path, mode="r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _parse_iso(date_str: str) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def anchor_shift(rows: list) -> timedelta:
    """Exact offset that moves the newest note to now.

    Exact (not whole days) so every note's age in days equals its age in the CSV,
    whatever the time of day. Whole-day shifts made a note dated 181 days back read
    as 180 or 181 days old depending on the clock, flipping its recency decay.
    """
    dates = [d for d in (_parse_iso(r.get("date", "").strip()) for r in rows) if d]
    if not dates:
        return timedelta(0)
    return utc_now() - max(dates)


def _shift_iso(date_str: str, shift: timedelta) -> str:
    parsed = _parse_iso(date_str)
    if parsed is None or not shift:
        return date_str
    return (parsed + shift).isoformat() + "Z"
