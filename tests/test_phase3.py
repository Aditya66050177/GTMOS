import pytest
from datetime import datetime
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.models import Product, ICPProfile, Account, Signal, Draft, Activity, Score
from app.services.recommendation_engine import RecommendationEngine, RecommendationResult
from app.services.personalization import PersonalizationEngine
from app.schemas.scoring import ScoreResult
from app.schemas.draft import PersonalizationOutputSchema
from app.api.main import app

client = TestClient(app)

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

def _create_sample_data(db, suffix=""):
    p = Product(name=f"Phase3 Product{suffix}", description="AI automation tool")
    db.add(p)
    db.commit()
    db.refresh(p)

    icp = ICPProfile(
        product_id=p.id,
        industries=["B2B SaaS", "Software"],
        company_size_min=50,
        company_size_max=500,
        buyer_roles=["VP of Customer Support", "Chief Revenue Officer", "Head of Product"],
        geographies=["US"]
    )
    db.add(icp)

    a = Account(
        name=f"Phase3 Account{suffix}",
        industry="B2B SaaS",
        employee_count=120,
        country="US",
        description="Scaling SaaS company with support challenges.",
        technology_stack=["Zendesk", "Salesforce"]
    )
    db.add(a)
    db.commit()
    db.refresh(p)
    db.refresh(icp)
    db.refresh(a)

    return p, icp, a

# ──────────────────────────────────────────────────────────────────────────────
# 1. Recommendation Engine Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_recommendation_rules_deterministic():
    engine = RecommendationEngine()

    # P1 + high intent -> CONTACT
    score_p1_high = Score(total_score=95.0, tier="Priority 1", intent_score=18.0)
    sig_hiring = [Signal(signal_type="support_hiring", strength=0.9, source="Job Board")]
    icp = ICPProfile(buyer_roles=["VP of Customer Support", "Chief Revenue Officer"])

    rec = engine.get_recommendation(score_p1_high, sig_hiring, icp)
    assert rec.action == "CONTACT"
    assert rec.suggested_persona == "VP of Customer Support"
    assert "support team scaling" in rec.suggested_angle

    # P1 + weak intent -> RESEARCH
    score_p1_low = Score(total_score=90.0, tier="Priority 1", intent_score=5.0)
    rec2 = engine.get_recommendation(score_p1_low, [], icp)
    assert rec2.action == "RESEARCH"

    # P2 + very high intent -> PRIORITIZE
    score_p2_high = Score(total_score=85.0, tier="Priority 2", intent_score=16.0)
    sig_funding = [Signal(signal_type="funding", strength=0.9, source="TechCrunch")]
    rec3 = engine.get_recommendation(score_p2_high, sig_funding, icp)
    assert rec3.action == "PRIORITIZE"
    assert rec3.suggested_persona == "Chief Revenue Officer"
    assert "post-funding growth" in rec3.suggested_angle

    # P2 + moderate intent -> NURTURE
    score_p2_mid = Score(total_score=80.0, tier="Priority 2", intent_score=8.0)
    rec4 = engine.get_recommendation(score_p2_mid, [], icp)
    assert rec4.action == "NURTURE"

    # Low fit -> DEPRIORITIZE
    score_low = Score(total_score=30.0, tier="Low", intent_score=0.0)
    rec5 = engine.get_recommendation(score_low, [], icp)
    assert rec5.action == "DEPRIORITIZE"

# ──────────────────────────────────────────────────────────────────────────────
# 2. Personalization Engine & Guardrail Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_personalization_deprioritize_rejected(db):
    p, icp, a = _create_sample_data(db, " Deprioritize")

    # Score as Low
    score = Score(
        account_id=a.id,
        product_id=p.id,
        total_score=20.0,
        tier="Low",
        intent_score=0.0
    )
    db.add(score)
    db.commit()

    engine = PersonalizationEngine()
    with pytest.raises(ValueError, match="Cannot generate outreach draft for DEPRIORITIZE account"):
        engine.generate_draft(db, a.id, p.id)

def test_personalization_draft_generation_and_persistence(db):
    p, icp, a = _create_sample_data(db, " ValidDraft")

    score = Score(
        account_id=a.id,
        product_id=p.id,
        total_score=92.0,
        tier="Priority 1",
        intent_score=18.0
    )
    db.add(score)

    sig = Signal(
        account_id=a.id,
        signal_type="support_hiring",
        description="Hiring 50 support staff",
        strength=0.9,
        source="Job Board",
        confidence=0.95,
        evidence="hiring 50 support staff",
        detected_at=datetime.utcnow()
    )
    db.add(sig)
    db.commit()

    engine = PersonalizationEngine()
    draft = engine.generate_draft(db, a.id, p.id)

    assert draft.id is not None
    assert draft.account_id == a.id
    assert draft.status == "pending"
    assert draft.original_body == draft.body
    assert sig.id in draft.evidence_ids

    words = draft.body.split()
    assert len(words) <= 120

def test_fact_check_guardrail_detects_hallucination():
    engine = PersonalizationEngine()
    account = Account(name="TestCo", employee_count=100)
    signals = [Signal(evidence="raised 5M in seed funding")]

    # Valid draft (number 5 and 100 are in evidence/account, 10 is whitelisted)
    is_valid, msg = engine._validate_draft_facts("Hi TestCo with 100 staff, congrats on 5M round. Quick 10 min call?", account, signals)
    assert is_valid is True

    # Invalid draft with ungrounded number 9999
    is_valid2, msg2 = engine._validate_draft_facts("We noticed you cut 9999 tickets last month.", account, signals)
    assert is_valid2 is False
    assert "9999" in msg2

# ──────────────────────────────────────────────────────────────────────────────
# 3. Human Review API Endpoint Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_drafts_api_workflow(db):
    p, icp, a = _create_sample_data(db, " ApiTest")

    score = Score(
        account_id=a.id,
        product_id=p.id,
        total_score=95.0,
        tier="Priority 1",
        intent_score=20.0
    )
    db.add(score)
    db.commit()

    # 1. Generate personalization draft via API
    resp_gen = client.post(f"/accounts/{a.id}/personalize?product_id={p.id}")
    assert resp_gen.status_code == 200
    draft_data = resp_gen.json()
    draft_id = draft_data["id"]
    assert draft_data["status"] == "pending"

    # 2. List drafts with status filter
    resp_list = client.get("/drafts?status=pending")
    assert resp_list.status_code == 200
    pending_ids = [d["id"] for d in resp_list.json()]
    assert draft_id in pending_ids

    # 3. Edit draft body via PATCH
    updated_body = "Updated custom body for outreach review."
    resp_patch = client.patch(f"/drafts/{draft_id}", json={"body": updated_body})
    assert resp_patch.status_code == 200
    assert resp_patch.json()["body"] == updated_body
    assert resp_patch.json()["original_body"] != updated_body

    # 4. Approve draft
    resp_approve = client.post(f"/drafts/{draft_id}/approve")
    assert resp_approve.status_code == 200
    assert resp_approve.json()["status"] == "approved"
    assert resp_approve.json()["reviewed_at"] is not None

    # Verify Activity record created
    activity = db.query(Activity).filter_by(account_id=a.id, activity_type="outreach_approved").first()
    assert activity is not None
    assert activity.activity_metadata["draft_id"] == draft_id

    # 5. Create another draft and reject it
    draft2 = Draft(
        account_id=a.id,
        body="Draft 2 body",
        original_body="Draft 2 body",
        status="pending",
        created_at=datetime.utcnow()
    )
    db.add(draft2)
    db.commit()
    db.refresh(draft2)

    resp_reject = client.post(f"/drafts/{draft2.id}/reject")
    assert resp_reject.status_code == 200
    assert resp_reject.json()["status"] == "rejected"
