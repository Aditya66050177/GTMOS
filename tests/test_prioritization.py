"""T4: /web/prioritization agrees with /explain and stays read-only and sandbox-aware."""
import secrets

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.api import public
from app.api.main import create_app
from app.db.database import Base
from app.db.demo_seed import reset_demo_database
from app.services.executive_analytics import prioritization_rows


@pytest.fixture(scope="module")
def client():
    reset_demo_database(quiet=True, include_demo_additions=True)
    return TestClient(create_app())


def test_rows_agree_with_explain_for_every_account(client):
    rows = client.get("/web/prioritization").json()
    assert len(rows) == 150
    for r in rows:
        e = client.get(f"/web/accounts/{r['id']}/explain").json()
        assert r["fit"] == pytest.approx(e["fit"]["score"], abs=0.05), r["name"]
        assert r["intent"] == pytest.approx(e["intent"]["score"], abs=0.05)
        assert r["total"] == pytest.approx(e["total"]["total"], abs=0.05)
        assert r["tier"] == e["total"]["tier"]
        assert (r["action"], r["rule_id"]) == (e["recommendation"]["action"], e["recommendation"]["rule_id"])
        s = e["evidence_summary"]
        assert r["evidence"] == {k: s[k] for k in ("current", "aging", "expired", "superseded", "rejected")}
        assert r["uses_synthetic_demo_additions"] == e["includes_synthetic_demo_additions"]


def test_rows_sorted_by_total_and_comparison_accounts_present(client):
    rows = client.get("/web/prioritization").json()
    totals = [r["total"] for r in rows]
    assert totals == sorted(totals, reverse=True)
    by_name = {r["name"]: r for r in rows}
    assert (by_name["Company 36 B2B"]["fit"], by_name["Company 36 B2B"]["intent"], by_name["Company 36 B2B"]["action"]) == (57.0, 20.0, "PRIORITIZE")
    assert (by_name["Company 37 Cloud"]["fit"], by_name["Company 37 Cloud"]["action"]) == (80.0, "RESEARCH")
    assert by_name["Company 37 Cloud"]["evidence"]["rejected"] == 1
    assert (by_name["Acme Technologies"]["fit"], by_name["Acme Technologies"]["intent"]) == (69.5, 0.0)


def test_empty_and_unscored_databases(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'e.db').as_posix()}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    assert prioritization_rows(db) == []
    db.add(app.models.Account(name="Unscored Co", stage=None))
    db.commit()
    [row] = prioritization_rows(db)
    assert row.scored is False and row.fit is None and row.action is None and row.stage == "Research"
    db.close()


def test_public_prioritization_is_read_only_and_sandbox_aware(tmp_path):
    reset_demo_database(quiet=True, include_demo_additions=True)
    template = public._template_path()
    root = FastAPI()
    root.mount("/api", public.create_public_api(template=template, sandbox_dir=tmp_path / "sb"))
    c = TestClient(root, raise_server_exceptions=False)
    before = template.stat().st_mtime_ns
    owner, other = secrets.token_hex(16), secrets.token_hex(16)

    assert c.get("/api/web/prioritization").status_code == 200
    for m in ("post", "put", "patch", "delete"):
        assert getattr(c, m)("/api/web/prioritization", headers={"X-Demo-Session": owner}).status_code == 403

    draft = next(d for d in c.get("/api/web/drafts").json() if d["account_stage"] == "Research")
    h = {"X-Demo-Session": owner}
    assert c.post(f"/api/drafts/{draft['id']}/approve", headers=h).status_code == 200
    assert c.post(f"/api/accounts/{draft['account_id']}/mark_sent?draft_id={draft['id']}", headers=h).status_code == 200

    def stage(headers):
        return next(r for r in c.get("/api/web/prioritization", headers=headers).json() if r["id"] == draft["account_id"])["stage"]

    assert stage(h) == "Contacted"
    assert stage({"X-Demo-Session": other}) == stage({}) == "Research"
    assert template.stat().st_mtime_ns == before
