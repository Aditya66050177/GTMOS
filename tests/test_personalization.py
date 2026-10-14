"""
tests/test_personalization.py
Tests for PersonalizationEngine, prompt generation, factual guardrails, and DB persistence.
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.models import Product, ICPProfile, Account, Signal, Draft, Score
from app.services.personalization import PersonalizationEngine
from app.schemas.draft import PersonalizationOutputSchema
from app.ai.llm import LLMService

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

def _setup_target_account(db, name="PersonalizeCo", tier="Priority 1", intent=18.0):
    p = Product(name=f"Product {name}", description="AI automation for support tickets.")
    db.add(p)
    db.commit()
    db.refresh(p)

    icp = ICPProfile(
        product_id=p.id,
        industries=["B2B SaaS"],
        company_size_min=50,
        company_size_max=500,
        buyer_roles=["VP of Customer Support"],
        geographies=["US"]
    )
    db.add(icp)

    a = Account(
        name=name,
        industry="B2B SaaS",
        employee_count=150,
        country="US",
        description="Fast growing SaaS platform.",
        technology_stack=["Zendesk"]
    )
    db.add(a)
    db.commit()
    db.refresh(a)

    score = Score(
        account_id=a.id,
        product_id=p.id,
        total_score=92.0 if tier == "Priority 1" else (40.0 if tier == "Low" else 78.0),
        tier=tier,
        intent_score=intent
    )
    db.add(score)
    db.commit()
    db.refresh(score)

    return p, icp, a, score

def test_invented_statistic_is_rejected():
    """A draft that invents a statistic/number not grounded in evidence is rejected."""
    engine = PersonalizationEngine()
    account = Account(name="Acme Corp", employee_count=100)
    signals = [Signal(evidence="hiring support reps")]

    # Draft has hallucinated number 8500
    hallucinated_draft = "Hi Acme team, noticed your 8500 ticket backlog. We can help resolve them."
    is_valid, msg = engine._validate_draft_facts(hallucinated_draft, account, signals)
    
    assert is_valid is False
    assert "8500" in msg

def test_valid_draft_grounded_in_evidence(db):
    """Valid draft passes guardrails and references correct evidence IDs."""
    p, icp, a, score = _setup_target_account(db, name="GroundedCo")

    sig1 = Signal(
        account_id=a.id,
        signal_type="support_hiring",
        strength=0.9,
        source="Job Board",
        evidence="expanding support team",
        detected_at=datetime.utcnow()
    )
    sig2 = Signal(
        account_id=a.id,
        signal_type="funding",
        strength=0.8,
        source="TechCrunch",
        evidence="Series A funding",
        detected_at=datetime.utcnow()
    )
    db.add_all([sig1, sig2])
    db.commit()
    db.refresh(sig1)
    db.refresh(sig2)

    engine = PersonalizationEngine()
    draft = engine.generate_draft(db, a.id, p.id)

    assert draft is not None
    assert draft.id is not None
    assert draft.account_id == a.id
    assert draft.status == "pending"
    assert set(draft.evidence_ids) == {sig1.id, sig2.id}
    assert draft.original_body == draft.body

def test_deprioritize_accounts_produce_no_draft(db):
    """DEPRIORITIZE accounts immediately raise ValueError and produce no draft."""
    p, icp, a, score = _setup_target_account(db, name="LowFitCo", tier="Low", intent=0.0)

    engine = PersonalizationEngine()
    with pytest.raises(ValueError, match="Cannot generate outreach draft for DEPRIORITIZE account"):
        engine.generate_draft(db, a.id, p.id)

    # Ensure no draft was saved to DB
    count = db.query(Draft).filter_by(account_id=a.id).count()
    assert count == 0

def test_draft_length_under_limit(db):
    """Generated draft must stay strictly under the 120 word limit."""
    p, icp, a, score = _setup_target_account(db, name="LengthTestCo")

    engine = PersonalizationEngine()
    draft = engine.generate_draft(db, a.id, p.id)

    words = draft.body.split()
    assert len(words) < 120
    assert len(words) > 5
