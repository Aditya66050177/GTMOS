import pytest
from datetime import datetime, timedelta
from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.models import Product, ICPProfile, Account, Signal, Activity
from app.services.signal_engine import SignalEngine
from app.services.research_engine import ResearchEngine
from app.schemas.signal import SignalListSchema
from app.core.timeutil import utc_now

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

def _make_account_product_icp(db, suffix=""):
    p = Product(name=f"Signal Product{suffix}")
    db.add(p)
    db.commit()
    db.refresh(p)
    
    icp = ICPProfile(
        product_id=p.id,
        industries=["Software", "Tech"],
        company_size_min=50,
        company_size_max=500,
        geographies=["US", "Canada"],
        exclusions=["Government"]
    )
    db.add(icp)
    
    a = Account(
        name=f"Signal Account{suffix}",
        industry="Software",
        employee_count=100,
        country="US",
        description="Great tech company."
    )
    db.add(a)
    db.commit()
    db.refresh(p)
    db.refresh(icp)
    db.refresh(a)
    return p, icp, a

def test_weights_and_recency_decay(db):
    p, icp, a = _make_account_product_icp(db, "Decay")
    engine = SignalEngine()
    now = utc_now()
    
    # Fresh signal (support_hiring, weight 20)
    db.add(Signal(account_id=a.id, signal_type="support_hiring", strength=1.0, confidence=1.0, detected_at=now))
    # 100 days old (funding, weight 15, should decay to 50% -> 7.5)
    db.add(Signal(account_id=a.id, signal_type="funding", strength=1.0, confidence=1.0, detected_at=now - timedelta(days=100)))
    # 200 days old (product_launch, weight 15, should decay to 0% -> 0)
    db.add(Signal(account_id=a.id, signal_type="product_launch", strength=1.0, confidence=1.0, detected_at=now - timedelta(days=200)))
    db.commit()
    
    intent = engine.calculate_intent(db, a, p)
    # Expected: 20 (support_hiring) + 7.5 (funding) + 0 (product_launch) = 27.5 -> capped at 20
    assert intent == 20.0
    
    # If we reduce the strength of support hiring
    s = db.query(Signal).filter_by(account_id=a.id, signal_type="support_hiring").first()
    s.strength = 0.5 # 20 * 0.5 = 10
    db.commit()
    
    intent2 = engine.calculate_intent(db, a, p)
    # Expected: 10 + 7.5 + 0 = 17.5
    assert intent2 == 17.5

def test_duplicate_signals_merged(db):
    p, icp, a = _make_account_product_icp(db, "Dup")
    engine = SignalEngine()
    now = utc_now()
    
    # Add two signals of same type, one fresh, one older.
    db.add(Signal(account_id=a.id, signal_type="relevant_technology", strength=0.5, confidence=1.0, detected_at=now - timedelta(days=10)))
    db.add(Signal(account_id=a.id, signal_type="relevant_technology", strength=1.0, confidence=1.0, detected_at=now))
    db.commit()
    
    # The more recent one has strength 1.0, weight is 15 -> 15 * 1.0 * 1.0 * decay(1.0) = 15
    intent = engine.calculate_intent(db, a, p)
    assert intent == 15.0

def test_negative_signals_trigger(db):
    p, icp, a = _make_account_product_icp(db, "Neg")
    
    # Trigger negative signals: wrong industry, too small, wrong country
    a.industry = "Agriculture" # Wrong industry (-30)
    a.employee_count = 10      # Too small (-20)
    a.country = "Germany"      # Wrong geography (-20)
    db.commit()
    
    engine = SignalEngine()
    intent = engine.calculate_intent(db, a, p)
    
    # Intent should be 0 (raw score is highly negative, capped at 0)
    assert intent == 0.0
    
    # Check that the negative signals were generated in the DB
    negs = db.query(Signal).filter_by(account_id=a.id, source="Internal CRM").all()
    types = [n.signal_type for n in negs]
    assert "wrong_industry" in types
    assert "too_small" in types
    assert "wrong_geography" in types

def test_intent_stays_between_0_and_20(db):
    p, icp, a = _make_account_product_icp(db, "Bounds")
    engine = SignalEngine()
    
    # Lots of positive signals
    now = utc_now()
    db.add(Signal(account_id=a.id, signal_type="support_hiring", strength=1.0, confidence=1.0, detected_at=now))
    db.add(Signal(account_id=a.id, signal_type="funding", strength=1.0, confidence=1.0, detected_at=now))
    db.add(Signal(account_id=a.id, signal_type="product_launch", strength=1.0, confidence=1.0, detected_at=now))
    db.commit()
    
    # Total sum is 20 + 15 + 15 = 50. Should be capped at 20.
    intent = engine.calculate_intent(db, a, p)
    assert intent == 20.0
    
    # Now clear signals and test extreme negative bounds
    db.query(Signal).filter_by(account_id=a.id).delete()
    a.industry = "Agriculture"
    a.employee_count = 1
    db.commit()
    
    intent2 = engine.calculate_intent(db, a, p)
    # Total sum is negative. Should be floored at 0.
    assert intent2 == 0.0

def test_evidence_not_in_raw_text_rejected(db):
    """A signal whose quoted evidence is not in the source text must be rejected and logged."""
    p, icp, a = _make_account_product_icp(db, "EvidenceRejection")

    class HallucinatingLLM:
        def generate_structured(self, prompt, schema):
            return SignalListSchema(signals=[{
                "type": "support_hiring",
                "description": "Hiring support staff",
                "strength": 0.8,
                "source": "TechCrunch",
                "detected_at": "2023-01-01T00:00:00Z",
                "confidence": 0.9,
                "evidence": "hiring 50 new support staff",
            }])

    re = ResearchEngine(llm_service=HallucinatingLLM())
    db.query(Activity).filter_by(account_id=a.id).delete()
    db.commit()

    signals = re.extract_signals_from_text(db, a, "Acme is doing great.", "TechCrunch", "2023-01-01T00:00:00Z")

    assert len(signals) == 0
    rejected = db.query(Activity).filter_by(account_id=a.id, activity_type="rejected_signal").all()
    assert len(rejected) > 0
    assert rejected[0].status == "rejected"


def test_mock_extractor_ignores_negated_and_rumoured_text(db):
    p, icp, a = _make_account_product_icp(db, "NegationGuard")
    re = ResearchEngine()
    for text in (
        "We are not hiring right now.",
        "Rumors suggested they were hiring for a support team expansion, but the CEO confirmed a hiring freeze.",
        "The company focuses on its hometown market with no plans for growth.",
    ):
        assert re.extract_signals_from_text(db, a, text, "News", "2026-01-01T00:00:00Z") == []


def test_mock_extractor_quotes_source_sentence(db):
    p, icp, a = _make_account_product_icp(db, "QuoteGuard")
    re = ResearchEngine()
    text = "We are hiring 50 new support staff to handle our increasing customer base."
    signals = re.extract_signals_from_text(db, a, text, "Job Board", "2026-01-01T00:00:00Z")
    assert [s.signal_type for s in signals] == ["support_hiring"]
    assert signals[0].evidence.lower() in text.lower()


def test_reextracting_same_text_does_not_duplicate(db):
    p, icp, a = _make_account_product_icp(db, "DedupGuard")
    re = ResearchEngine()
    text = "Announced a new Series B funding round of $50M."
    first = re.extract_signals_from_text(db, a, text, "Press", "2026-01-01T00:00:00Z")
    second = re.extract_signals_from_text(db, a, text, "Press", "2026-01-01T00:00:00Z")
    assert len(first) == 1 and second == []
    assert db.query(Signal).filter_by(account_id=a.id, signal_type="funding").count() == 1

def test_no_signals_yields_safe_intent(db):
    p, icp, a = _make_account_product_icp(db, "NoSignals")
    engine = SignalEngine()
    
    # No signals for this account
    intent = engine.calculate_intent(db, a, p)
    assert intent == 0.0 # Safe 0 score, not an error
