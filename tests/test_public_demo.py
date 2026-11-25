"""Security regression tests for the public demo API (app/api/public.py).

Each test maps to a finding in DEPLOYMENT_READINESS.md (P0-1 … P0-5, P1-5).
"""
import csv
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api import public
from app.api.main import create_app
from app.core.config import settings
from app.db.demo_seed import reset_demo_database

SID_A = "a" * 32
SID_B = "b" * 32
DATA = Path(__file__).resolve().parent.parent / "data"


def _mounted(api) -> TestClient:
    root = FastAPI()
    root.mount("/api", api)
    return TestClient(root, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def template():
    reset_demo_database(quiet=True)
    return public._template_path()


@pytest.fixture
def demo(template, tmp_path):
    api = public.create_public_api(template=template, sandbox_dir=tmp_path / "sandboxes")
    return _mounted(api), api


def _shared(template: Path, sql: str):
    con = sqlite3.connect(f"file:{template.as_posix()}?mode=ro", uri=True)
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()


def _acme_id(client) -> int:
    return next(r["id"] for r in client.get("/api/web/accounts").json() if r["name"] == "Acme Technologies")


# --------------------------------------------------------------------------- #
# P0-1: visitors cannot change shared data                                      #
# --------------------------------------------------------------------------- #

BLOCKED = [
    ("post", "/api/accounts/1/research", {"raw_text": "We are hiring 5 support staff.", "source": "x", "date_str": "2026-01-01"}),
    ("post", "/api/accounts/1/score", None),
    ("post", "/api/accounts/1/stage", {"stage": "Contacted"}),
    ("post", "/api/accounts/1/contacts", {"name": "Real Person", "email": "someone@realcompany.com"}),
    ("post", "/api/products", {"name": "x", "description": "y"}),
    ("post", "/api/products/1/generate-icp", None),
    ("post", "/api/products/1/score-all", None),
    ("delete", "/api/drafts/1", None),
    ("put", "/api/drafts/1", {"body": "x"}),
]


@pytest.mark.parametrize("method,path,body", BLOCKED)
def test_unneeded_write_routes_are_blocked(demo, method, path, body):
    client, _ = demo
    kwargs = {"headers": {"X-Demo-Session": SID_A}}
    if body is not None:
        kwargs["json"] = body
    res = getattr(client, method)(path, **kwargs)
    assert res.status_code == 403
    assert "disabled in the public demo" in res.json()["detail"]


def test_acme_score_cannot_be_changed_through_the_public_api(demo, template):
    client, _ = demo
    acme = _acme_id(client)
    before = client.get(f"/api/web/accounts/{acme}").json()["account"]["total_score"]
    client.post(f"/api/accounts/{acme}/research", headers={"X-Demo-Session": SID_A},
                json={"raw_text": "We are hiring 50 new support staff.", "source": "x", "date_str": "2026-01-01"})
    client.post("/api/products/1/score-all", headers={"X-Demo-Session": SID_A})
    assert client.get(f"/api/web/accounts/{acme}").json()["account"]["total_score"] == before == 69.5


def test_visitor_edits_stay_in_their_own_sandbox(demo, template):
    client, _ = demo
    draft_id = client.get("/api/web/drafts").json()[0]["id"]
    a = {"X-Demo-Session": SID_A}

    assert client.patch(f"/api/drafts/{draft_id}", headers=a, json={"body": "Edited by A"}).status_code == 200
    assert client.post(f"/api/drafts/{draft_id}/approve", headers=a).status_code == 200

    assert client.get(f"/api/drafts/{draft_id}", headers=a).json()["status"] == "approved"
    assert client.get(f"/api/drafts/{draft_id}").json()["status"] == "pending"
    assert client.get(f"/api/drafts/{draft_id}", headers={"X-Demo-Session": SID_B}).json()["status"] == "pending"
    assert _shared(template, f"select status, body from drafts where id={draft_id}")[0][0] == "pending"


def test_mark_sent_and_personalize_stay_in_sandbox(demo, template):
    client, _ = demo
    a = {"X-Demo-Session": SID_A}
    draft = client.get("/api/web/drafts").json()[0]
    client.post(f"/api/drafts/{draft['id']}/approve", headers=a)
    assert client.post(f"/api/accounts/{draft['account_id']}/mark_sent?draft_id={draft['id']}", headers=a).status_code == 200
    assert client.post(f"/api/accounts/{draft['account_id']}/personalize", headers=a).status_code == 200

    shared_drafts = _shared(template, "select count(*) from drafts")[0][0]
    assert client.get("/api/web/drafts").json().__len__() == shared_drafts
    assert len(client.get("/api/web/drafts", headers=a).json()) == shared_drafts + 1
    stage = _shared(template, f"select stage from accounts where id={draft['account_id']}")[0][0]
    assert client.get(f"/api/web/accounts/{draft['account_id']}").json()["account"]["stage"] == stage


def test_mutations_require_a_valid_session(demo):
    client, _ = demo
    assert client.post("/api/drafts/1/approve").status_code == 400
    assert client.post("/api/drafts/1/approve", headers={"X-Demo-Session": "../../etc/passwd"}).status_code == 400
    assert client.post("/api/drafts/1/approve", headers={"X-Demo-Session": "A" * 32}).status_code == 400


def test_shared_template_is_opened_read_only(demo):
    _, api = demo
    shared_override = api.dependency_overrides[public.get_db]

    class FakeRequest:
        method = "GET"
        headers: dict = {}
        scope: dict = {}

        class url:
            path = "/web/overview"

    gen = shared_override(FakeRequest())
    db = next(gen)
    with pytest.raises(Exception) as exc:
        db.execute(text("UPDATE accounts SET name='hacked'"))
        db.commit()
    assert "readonly" in str(exc.value).lower()
    gen.close()


# --------------------------------------------------------------------------- #
# P0-1 / P0-4: reset cannot be abused                                          #
# --------------------------------------------------------------------------- #

def test_reset_only_discards_the_callers_sandbox(demo, template):
    client, api = demo
    draft_id = client.get("/api/web/drafts").json()[0]["id"]
    for sid in (SID_A, SID_B):
        client.post(f"/api/drafts/{draft_id}/approve", headers={"X-Demo-Session": sid})
    assert len(api.state.sandboxes) == 2

    res = client.post("/api/web/reset", headers={"X-Demo-Session": SID_A})
    assert res.status_code == 200 and res.json()["had_changes"] is True
    assert len(api.state.sandboxes) == 1
    assert client.get(f"/api/drafts/{draft_id}", headers={"X-Demo-Session": SID_B}).json()["status"] == "approved"
    assert client.get(f"/api/drafts/{draft_id}", headers={"X-Demo-Session": SID_A}).json()["status"] == "pending"
    assert _shared(template, "select count(*) from accounts")[0][0] == 150


def test_reset_requires_session_and_is_rate_limited(template, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_RESET_LIMIT_PER_MINUTE", 3)
    client = _mounted(public.create_public_api(template=template, sandbox_dir=tmp_path / "sb"))
    # A rejected attempt still counts toward the limit, so failures are not free.
    assert client.post("/api/web/reset").status_code == 400
    h = {"X-Demo-Session": SID_A}
    assert [client.post("/api/web/reset", headers=h).status_code for _ in range(3)] == [200, 200, 429]


# --------------------------------------------------------------------------- #
# P0-3: request size and input length                                         #
# --------------------------------------------------------------------------- #

def test_oversized_body_is_rejected_with_413(demo):
    client, _ = demo
    res = client.patch("/api/drafts/1", headers={"X-Demo-Session": SID_A},
                       content=b'{"body":"' + b"a" * 20_000 + b'"}')
    assert res.status_code == 413


@pytest.mark.anyio
async def test_body_cap_also_applies_without_content_length():
    async def app(scope, receive, send):  # pragma: no cover - must never run
        raise AssertionError("app should not be reached")

    guard = public.PublicDemoGuard(app, public.RateLimiter(), max_body=100,
                                   per_minute=100, writes_per_minute=100, resets_per_minute=100)
    chunks = [{"type": "http.request", "body": b"x" * 60, "more_body": True}] * 3
    sent = []

    async def receive():
        return chunks.pop(0)

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "method": "POST", "path": "/web/playground", "headers": [], "client": ("1.2.3.4", 1)}
    await guard(scope, receive, send)
    assert sent[0]["status"] == 413


@pytest.fixture
def full_api():
    return TestClient(create_app(), raise_server_exceptions=False)


@pytest.mark.parametrize("method,path,body", [
    ("post", "/accounts/1/research", {"raw_text": "x" * 200_000, "source": "x", "date_str": "2026-01-01"}),
    ("post", "/accounts/1/research", {"raw_text": "We are hiring.", "source": "x", "date_str": "not-a-date"}),
    ("patch", "/drafts/1", {"body": "a" * 1_000_000}),
    ("post", "/analytics/ask", {"question": "funnel " * 15_000}),
    ("post", "/products", {"name": "x" * 50_000, "description": "y"}),
    ("post", "/accounts/1/contacts", {"name": "x" * 1_000}),
    ("post", "/accounts/1/stage", {"stage": "Contacted", "notes": "n" * 5_000}),
])
def test_input_length_limits_on_the_full_api(full_api, template, method, path, body):
    assert getattr(full_api, method)(path, json=body).status_code == 422


def test_playground_rejects_oversized_fields(demo):
    client, _ = demo
    base = {"industry": "B2B SaaS", "employee_count": 100, "country": "US"}
    assert client.post("/api/web/playground", json={**base, "technology_stack": ["x" * 500]}).status_code == 422
    assert client.post("/api/web/playground", json={**base, "technology_stack": ["a"] * 40}).status_code == 422


# --------------------------------------------------------------------------- #
# P0-4: rate limiting (per instance, best effort)                              #
# --------------------------------------------------------------------------- #

def test_requests_beyond_the_limit_get_429_with_retry_after(template, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_RATE_LIMIT_PER_MINUTE", 3)
    client = _mounted(public.create_public_api(template=template, sandbox_dir=tmp_path / "sb"))
    codes = [client.get("/api/health", headers={"X-Real-IP": "9.9.9.9"}).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
    limited = client.get("/api/health", headers={"X-Real-IP": "9.9.9.9"})
    assert int(limited.headers["Retry-After"]) >= 1
    assert client.get("/api/health", headers={"X-Real-IP": "8.8.8.8"}).status_code == 200


def test_rate_limiter_window_expires_and_memory_is_bounded():
    now = [0.0]
    limiter = public.RateLimiter(max_clients=3, window_seconds=60, clock=lambda: now[0])
    assert limiter.hit("all", "ip", 1) is None
    assert limiter.hit("all", "ip", 1) is not None
    now[0] = 61
    assert limiter.hit("all", "ip", 1) is None
    for i in range(10):
        limiter.hit("all", f"ip{i}", 5)
    assert len(limiter._hits) == 3


# --------------------------------------------------------------------------- #
# Sandbox storage is bounded                                                   #
# --------------------------------------------------------------------------- #

def test_sandbox_count_is_capped_and_old_sandboxes_expire(template, tmp_path):
    now = [0.0]
    reg = public.SandboxRegistry(template, tmp_path / "sb", max_sandboxes=2, ttl_seconds=100, clock=lambda: now[0])
    for sid in ("1" * 32, "2" * 32, "3" * 32):
        reg.session_factory(sid, create=True)
    assert len(reg) == 2
    assert sorted(p.name for p in (tmp_path / "sb").iterdir()) == ["2" * 32 + ".db", "3" * 32 + ".db"]
    now[0] = 500
    assert reg.session_factory("2" * 32, create=False) is None
    assert len(reg) == 0 and not list((tmp_path / "sb").iterdir())


# --------------------------------------------------------------------------- #
# P0-5: synthetic identities are clearly fictional                             #
# --------------------------------------------------------------------------- #

def _rows(name):
    with open(DATA / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_demo_contacts_use_reserved_example_domains():
    for row in _rows("contacts.csv"):
        assert row["email"].endswith(".example"), row
        assert row["linkedin_url"].startswith("https://linkedin.example/"), row


def test_demo_account_domains_are_reserved():
    assert all(r["domain"].endswith(".example") for r in _rows("accounts.csv"))


# --------------------------------------------------------------------------- #
# LLM never live in public; errors never leak internals (P1-5)                 #
# --------------------------------------------------------------------------- #

def test_public_api_forces_mock_llm(template, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "LLM_MODE", "live")
    public.create_public_api(template=template, sandbox_dir=tmp_path / "sb")
    assert settings.LLM_MODE == "mock"


def test_unexpected_errors_return_a_generic_message(full_api, monkeypatch):
    from app.services import analyst_service

    def boom(*_a, **_k):
        raise RuntimeError("secret path /var/db/password=hunter2")

    monkeypatch.setattr(analyst_service.AnalystService, "ask", boom)
    res = full_api.post("/analytics/ask", json={"question": "How is the funnel?"})
    assert res.status_code == 500
    assert "hunter2" not in res.text and "secret" not in res.text


def test_health_failure_does_not_leak_details(monkeypatch):
    from app.db.database import get_db

    api = create_app()

    class Broken:
        def execute(self, *_a, **_k):
            raise RuntimeError("sqlite:////tmp/private/location.db is locked")

    api.dependency_overrides[get_db] = lambda: Broken()
    res = TestClient(api).get("/health")
    assert res.status_code == 503
    assert "private" not in res.text


def test_path_traversal_is_not_served(demo):
    client, _ = demo
    assert client.get("/api/../../etc/passwd").status_code == 404
