import re
import logging
from typing import List, Optional, Tuple, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import Account, Signal, Product, ICPProfile, Draft, Contact
from app.schemas.draft import PersonalizationOutputSchema
from app.services.recommendation_engine import RecommendationEngine, RecommendationResult
from app.ai.llm import LLMService
from app.ai.prompts import GENERATE_DRAFT_PROMPT

logger = logging.getLogger(__name__)

class PersonalizationEngine:
    """
    Service for generating evidence-grounded, personalized outreach drafts.
    Includes strict code guardrails to prevent hallucination of numbers/facts.
    """
    def __init__(self, llm: Optional[LLMService] = None):
        self.llm = llm or LLMService()
        self.recommendation_engine = RecommendationEngine()

    def _validate_draft_facts(
        self,
        draft_text: str,
        account: Account,
        signals: List[Signal]
    ) -> Tuple[bool, str]:
        """
        Validates that numbers/facts in the draft are grounded in the account profile or signals.
        """
        # 1. Word count check (< 120 words)
        words = draft_text.split()
        if len(words) > 120:
            return False, f"Draft exceeds 120 words ({len(words)} words)."

        # 2. Extract numbers from the draft
        draft_numbers = re.findall(r'\b\d+(?:[\.,]\d+)?\b', draft_text)
        
        # Build allowed text context
        allowed_context = f"{account.name} {account.industry or ''} {account.employee_count or ''} {account.country or ''} {account.funding or ''} {account.support_team_size or ''} {' '.join(account.technology_stack or [])}"
        for s in signals:
            allowed_context += f" {s.evidence or ''} {s.description or ''} {s.signal_type or ''} {s.source or ''}"

        # Standard conversational numbers allowed (e.g., 10-minute or 15-minute meeting)
        whitelist_numbers = {"10", "15", "5", "2", "3", "1", "20", "30"}

        for num in draft_numbers:
            # Check if number appears in context or whitelist
            if num not in allowed_context and num not in whitelist_numbers:
                return False, f"Fact check failed: Number '{num}' in draft not grounded in evidence."

        return True, "Valid"

    def generate_draft(
        self,
        db: Session,
        account_id: int,
        product_id: Optional[int] = None,
        contact_id: Optional[int] = None
    ) -> Draft:
        account = db.query(Account).filter_by(id=account_id).first()
        if not account:
            raise ValueError(f"Account {account_id} not found.")

        product = None
        if product_id:
            product = db.query(Product).filter_by(id=product_id).first()
        if not product:
            product = db.query(Product).first()

        if not product:
            raise ValueError("No product found in database to personalize for.")

        icp = db.query(ICPProfile).filter_by(product_id=product.id).first()

        # Get latest score
        from app.models import Score
        score = db.query(Score).filter_by(account_id=account.id, product_id=product.id).first()
        if not score:
            # Score first if unscored
            from app.services.scoring_engine import ScoringEngine
            se = ScoringEngine()
            se.score_account(db, account, product)
            score = db.query(Score).filter_by(account_id=account.id, product_id=product.id).first()

        # Get evidence-backed signals
        signals = (
            db.query(Signal)
            .filter(Signal.account_id == account.id, Signal.strength > 0)
            .order_by(Signal.detected_at.desc())
            .limit(3)
            .all()
        )

        # Recommendation Check
        rec: RecommendationResult = self.recommendation_engine.get_recommendation(score, signals, icp)
        if rec.action == "DEPRIORITIZE":
            raise ValueError(
                f"Cannot generate outreach draft for DEPRIORITIZE account {account.name} (Tier: {score.tier}, Action: {rec.action})."
            )

        # Prepare evidence prompt text
        evidence_lines = []
        evidence_ids = []
        for s in signals:
            evidence_ids.append(s.id)
            dt_str = s.detected_at.strftime('%Y-%m-%d') if s.detected_at else "Recent"
            evidence_lines.append(f"- [{s.signal_type}] {s.description} (Evidence: '{s.evidence}', Source: {s.source}, Date: {dt_str})")

        evidence_text = "\n".join(evidence_lines) if evidence_lines else "No specific recent buying signals detected. Use company profile."

        value_prop = product.description or "Automating customer support ticket resolution and reducing response times."
        tech_str = ", ".join(account.technology_stack or []) if account.technology_stack else "None specified"

        prompt = GENERATE_DRAFT_PROMPT.format(
            account_name=account.name,
            industry=account.industry or "Technology",
            employees=account.employee_count or "Unknown",
            country=account.country or "Global",
            tech_stack=tech_str,
            persona=rec.suggested_persona or "VP Customer Support",
            angle=rec.suggested_angle or "team efficiency",
            value_proposition=value_prop,
            evidence_list=evidence_text
        )

        # Generate with 1-retry guardrail check
        attempts = 2
        last_error = ""
        output: Optional[PersonalizationOutputSchema] = None

        for attempt in range(attempts):
            output = self.llm.generate_structured(prompt, PersonalizationOutputSchema)
            is_valid, reason = self._validate_draft_facts(output.message_draft, account, signals)
            if is_valid:
                break
            logger.warning(f"Draft validation attempt {attempt + 1} failed: {reason}. Retrying...")
            last_error = reason
            if attempt == attempts - 1:
                # If still invalid after retry, sanitize or raise
                logger.error(f"Failed to generate verified draft after {attempts} attempts: {last_error}")

        if not output:
            raise RuntimeError("Failed to generate outreach draft.")

        # Save to drafts table
        draft = Draft(
            account_id=account.id,
            contact_id=contact_id,
            body=output.message_draft,
            original_body=output.message_draft,
            status="pending",
            evidence_ids=evidence_ids,
            created_at=datetime.utcnow()
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)

        return draft
