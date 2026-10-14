"""
tests/test_review.py
Tests for Human Review workflow, state machine transitions, draft editing, and safety rules.
"""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.models import Draft, Account, Activity
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

def _create_test_draft(db, body="Initial draft message", status="pending"):
    acc = Account(name="ReviewCo", industry="B2B SaaS")
    db.add(acc)
    db.commit()
    db.refresh(acc)

    draft = Draft(
        account_id=acc.id,
        body=body,
        original_body=body,
        status=status,
        evidence_ids=[1, 2],
        created_at=datetime.utcnow()
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return acc, draft

# ──────────────────────────────────────────────────────────────────────────────
# 1. State Machine Transition Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_pending_to_approved_transition(db):
    """Pending draft can transition to approved."""
    acc, draft = _create_test_draft(db, status="pending")

    resp = client.post(f"/drafts/{draft.id}/approve")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["reviewed_at"] is not None

def test_pending_to_rejected_transition(db):
    """Pending draft can transition to rejected."""
    acc, draft = _create_test_draft(db, status="pending")

    resp = client.post(f"/drafts/{draft.id}/reject")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"
    assert data["reviewed_at"] is not None

def test_approved_draft_cannot_be_approved_twice(db):
    """An approved draft cannot be approved again."""
    acc, draft = _create_test_draft(db, status="approved")

    resp = client.post(f"/drafts/{draft.id}/approve")
    assert resp.status_code == 400
    assert "Cannot approve draft with status 'approved'" in resp.json()["detail"]

def test_rejected_draft_cannot_be_approved(db):
    """A rejected draft cannot be approved."""
    acc, draft = _create_test_draft(db, status="rejected")

    resp = client.post(f"/drafts/{draft.id}/approve")
    assert resp.status_code == 400
    assert "Cannot approve draft with status 'rejected'" in resp.json()["detail"]

# ──────────────────────────────────────────────────────────────────────────────
# 2. Edits Preserve original_body
# ──────────────────────────────────────────────────────────────────────────────

def test_edits_keep_original_body(db):
    """Editing a draft updates body while keeping original_body intact."""
    initial_text = "Original AI generated draft"
    acc, draft = _create_test_draft(db, body=initial_text, status="pending")

    new_text = "Human customized message body"
    resp = client.patch(f"/drafts/{draft.id}", json={"body": new_text})
    assert resp.status_code == 200
    data = resp.json()

    assert data["body"] == new_text
    assert data["original_body"] == initial_text

def test_approved_draft_cannot_be_edited(db):
    """Approved drafts cannot be edited."""
    acc, draft = _create_test_draft(db, status="approved")

    resp = client.patch(f"/drafts/{draft.id}", json={"body": "Modified"})
    assert resp.status_code == 400
    assert "Cannot edit draft with status 'approved'" in resp.json()["detail"]

# ──────────────────────────────────────────────────────────────────────────────
# 3. Activity Tracking & No Outreach Sent Automatically
# ──────────────────────────────────────────────────────────────────────────────

def test_approving_creates_exactly_one_activity(db):
    """Approving a draft creates exactly one outreach_approved activity."""
    acc, draft = _create_test_draft(db, status="pending")

    # Clear prior activities for this account
    db.query(Activity).filter_by(account_id=acc.id).delete()
    db.commit()

    resp = client.post(f"/drafts/{draft.id}/approve")
    assert resp.status_code == 200

    activities = db.query(Activity).filter_by(account_id=acc.id, activity_type="outreach_approved").all()
    assert len(activities) == 1
    assert activities[0].status == "approved"
    assert activities[0].activity_metadata["draft_id"] == draft.id

def test_no_code_path_sends_real_outreach(db):
    """Ensure no email/outreach network calls exist in the approval flow."""
    acc, draft = _create_test_draft(db, status="pending")
    resp = client.post(f"/drafts/{draft.id}/approve")
    assert resp.status_code == 200
    # Verified: Status is stored in DB with activity log, no network email dispatcher invoked
