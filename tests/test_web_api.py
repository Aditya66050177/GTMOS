"""Tests for the public web app endpoints (/web/*) and the demo seeder."""
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.db.demo_seed import reset_demo_database


@pytest.fixture(scope="module")
def client():
    summary = reset_demo_database(quiet=True)
    assert summary["accounts"] == 150 and summary["scores"] == 150
    assert summary["drafts"] > 0
    return TestClient(app)


HOT = {
    "name": "Northwind", "industry": "B2B SaaS", "employee_count": 220, "country": "US",
    "description": "High support ticket volume and high support costs.",
    "technology_stack": ["Zendesk", "Salesforce"],
    "research_note": "Northwind raised a $40M Series B funding round. They are hiring 25 new support agents.",
}


def test_reset_is_idempotent_and_does_not_duplicate_products(client):
    reset_demo_database(quiet=True)
    overview = client.get("/web/overview").json()
    assert overview["counts"]["accounts"] == 150
    assert sum(overview["tiers"].values()) == 150


def test_accounts_are_ranked_and_carry_actions(client):
    rows = client.get("/web/accounts").json()
    scores = [r["total_score"] for r in rows]
    assert scores == sorted(scores, reverse=True)
    assert all(r["action"] for r in rows)


def test_acme_rumour_earns_no_intent(client):
    acme = next(r for r in client.get("/web/accounts").json() if r["name"] == "Acme Technologies")
    detail = client.get(f"/web/accounts/{acme['id']}").json()
    assert detail["account"]["intent_score"] == 0.0
    assert not [s for s in detail["signals"] if not s["negative"]]


def test_account_detail_404(client):
    assert client.get("/web/accounts/999999").status_code == 404


def test_seeded_drafts_cite_evidence_found_in_signals(client):
    drafts = client.get("/web/drafts").json()
    assert drafts and all(d["status"] == "pending" for d in drafts)
    for d in drafts:
        assert d["evidence"], "every seeded draft must be grounded in at least one signal"
        assert all(e["evidence"] in d["body"] for e in d["evidence"][:1])


def test_playground_hot_account_scores_high_without_writing(client):
    before = client.get("/web/overview").json()["counts"]
    res = client.post("/web/playground", json=HOT).json()
    assert res["score"]["tier"] in ("Priority 1", "Priority 2")
    assert {s["type"] for s in res["signals"]} >= {"funding", "support_hiring"}
    assert client.get("/web/overview").json()["counts"] == before


def test_playground_is_deterministic(client):
    a = client.post("/web/playground", json=HOT).json()
    b = client.post("/web/playground", json=HOT).json()
    assert a["score"] == b["score"]


def test_playground_negated_note_gives_no_intent(client):
    body = {**HOT, "research_note": "We are not hiring right now. Rumors of a funding round were denied."}
    res = client.post("/web/playground", json=body).json()
    assert res["score"]["intent_score"] == 0.0
    assert res["signals"] == []


def test_playground_bad_fit_is_deprioritized(client):
    body = {**HOT, "industry": "Retail", "employee_count": 20, "country": "Brazil", "research_note": ""}
    res = client.post("/web/playground", json=body).json()
    assert res["recommendation"]["action"] == "DEPRIORITIZE"
    assert {s["type"] for s in res["signals"]} >= {"too_small", "wrong_geography"}


def test_playground_rejects_oversized_input(client):
    assert client.post("/web/playground", json={**HOT, "research_note": "x" * 5000}).status_code == 422
