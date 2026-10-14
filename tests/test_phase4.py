"""
tests/test_phase4.py
Tests for CRM, Pipeline Transitions, Mark-as-Sent, Analytics Engine, and AI Analyst.
"""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.models import Product, ICPProfile, Account, Score, Contact, Activity, Opportunity, Draft
from app.services.crm_service import CRMService
from app.services.analytics_engine import AnalyticsEngine
from app.services.analyst_service import AnalystService
from app.schemas.crm import PipelineStage
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

def _create_sample_account(db, name="CRMTestCo", stage="Research"):
    acc = Account(
        name=name,
        industry="B2B SaaS",
        employee_count=100,
        country="US",
        stage=stage
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc

# ──────────────────────────────────────────────────────────────────────────────
# 1. CRM & Pipeline Stage Transition Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_valid_forward_stage_transitions(db):
    crm = CRMService()
    acc = _create_sample_account(db, name="ForwardCo", stage="Research")

    # Research -> Contacted
    crm.update_account_stage(db, acc.id, "Contacted")
    assert acc.stage == "Contacted"

    # Contacted -> Replied
    crm.update_account_stage(db, acc.id, "Replied")
    assert acc.stage == "Replied"

    # Replied -> Meeting
    crm.update_account_stage(db, acc.id, "Meeting")
    assert acc.stage == "Meeting"

    # Meeting -> Opportunity
    crm.update_account_stage(db, acc.id, "Opportunity")
    assert acc.stage == "Opportunity"

    # Opportunity -> Won
    crm.update_account_stage(db, acc.id, "Won")
    assert acc.stage == "Won"

def test_backward_stage_transitions_rejected(db):
    crm = CRMService()
    acc = _create_sample_account(db, name="BacktrackCo", stage="Opportunity")

    # Trying to move backwards from Opportunity to Contacted should raise ValueError
    with pytest.raises(ValueError, match="Invalid stage transition"):
        crm.update_account_stage(db, acc.id, "Contacted")

def test_lost_reachable_from_any_stage(db):
    crm = CRMService()
    
    for start_stage in ["Research", "Contacted", "Replied", "Meeting", "Opportunity"]:
        acc = _create_sample_account(db, name=f"LostFrom{start_stage}", stage=start_stage)
        crm.update_account_stage(db, acc.id, "Lost")
        assert acc.stage == "Lost"

def test_stage_change_logs_activity_with_timestamp(db):
    crm = CRMService()
    acc = _create_sample_account(db, name="LogActCo", stage="Research")

    db.query(Activity).filter_by(account_id=acc.id).delete()
    db.commit()

    crm.update_account_stage(db, acc.id, "Contacted", notes="Outreach launched")
    
    act = db.query(Activity).filter_by(account_id=acc.id).first()
    assert act is not None
    assert act.activity_type == "stage_changed_to_contacted"
    assert act.timestamp is not None
    assert act.activity_metadata["from_stage"] == "Research"
    assert act.activity_metadata["to_stage"] == "Contacted"

def test_mark_as_sent_moves_account_to_contacted(db):
    crm = CRMService()
    acc = _create_sample_account(db, name="MarkSentCo", stage="Research")

    draft = Draft(
        account_id=acc.id,
        body="Ready outreach message",
        status="approved",
        created_at=datetime.utcnow()
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    crm.mark_outreach_sent(db, acc.id, draft_id=draft.id)

    db.refresh(acc)
    db.refresh(draft)

    assert acc.stage == "Contacted"
    assert draft.status == "sent"

    # Verify outreach_sent activity logged
    sent_act = db.query(Activity).filter_by(account_id=acc.id, activity_type="outreach_sent").first()
    assert sent_act is not None

# ──────────────────────────────────────────────────────────────────────────────
# 2. Analytics Engine Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_analytics_funnel_and_conversions(db):
    engine = AnalyticsEngine()
    res = engine.get_funnel_analytics(db)

    assert res.totals.total_accounts >= 0
    assert len(res.conversions) == 5
    for conv in res.conversions:
        assert 0.0 <= conv.conversion_rate_pct <= 100.0 or conv.from_count == 0

    assert len(res.performance_by_tier) == 4
    assert len(res.performance_by_industry) >= 0
    assert len(res.performance_by_angle) >= 0

def test_analytics_weekly_trends(db):
    engine = AnalyticsEngine()
    trends_res = engine.get_weekly_trends(db)

    assert isinstance(trends_res.weekly_trends, list)
    for point in trends_res.weekly_trends:
        assert point.week is not None
        assert point.contacted >= 0

# ──────────────────────────────────────────────────────────────────────────────
# 3. AI GTM Analyst Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_analyst_routing_and_explanation(db):
    analyst = AnalystService()

    # Question on conversion rates
    q_conv = "What are the stage-to-stage conversion rates?"
    resp_conv = analyst.ask(db, q_conv)
    assert resp_conv.function_called == "get_conversion_rates"
    assert "conversions" in resp_conv.data
    assert len(resp_conv.explanation) > 10

    # Question on weekly trends
    q_trends = "Show me the weekly trends over time"
    resp_trends = analyst.ask(db, q_trends)
    assert resp_trends.function_called == "get_weekly_trends"
    assert "weekly_trends" in resp_trends.data

    # Unmapped question
    q_unmapped = "What is the weather in San Francisco today?"
    resp_unmapped = analyst.ask(db, q_unmapped)
    assert resp_unmapped.function_called == "unknown"
    assert "cannot be mapped" in resp_unmapped.explanation

# ──────────────────────────────────────────────────────────────────────────────
# 4. API Endpoints Integration Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_crm_and_analytics_api_endpoints(db):
    acc = _create_sample_account(db, name="ApiCrmCo", stage="Research")

    # 1. POST /accounts/{id}/contacts
    resp_contact = client.post(f"/accounts/{acc.id}/contacts", json={
        "name": "Jane Doe",
        "role": "VP of Customer Support",
        "email": "jane.doe@apicrm.com"
    })
    assert resp_contact.status_code == 200
    assert resp_contact.json()["name"] == "Jane Doe"

    # 2. POST /accounts/{id}/stage
    resp_stage = client.post(f"/accounts/{acc.id}/stage", json={
        "stage": "Contacted",
        "notes": "Testing stage advance API"
    })
    assert resp_stage.status_code == 200
    assert resp_stage.json()["stage"] == "Contacted"

    # 3. GET /accounts/{id}/activities
    resp_acts = client.get(f"/accounts/{acc.id}/activities")
    assert resp_acts.status_code == 200
    assert len(resp_acts.json()) >= 1

    # 4. GET /pipeline
    resp_pipe = client.get("/pipeline")
    assert resp_pipe.status_code == 200
    assert "stages" in resp_pipe.json()

    # 5. GET /analytics/funnel
    resp_funnel = client.get("/analytics/funnel")
    assert resp_funnel.status_code == 200
    assert "totals" in resp_funnel.json()

    # 6. GET /analytics/trends
    resp_trends = client.get("/analytics/trends")
    assert resp_trends.status_code == 200
    assert "weekly_trends" in resp_trends.json()

    # 7. POST /analytics/ask
    resp_ask = client.post("/analytics/ask", json={"question": "What is our overall funnel summary?"})
    assert resp_ask.status_code == 200
    assert resp_ask.json()["function_called"] == "get_funnel_summary"
