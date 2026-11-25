"""Adversarial checks from the final pre-deployment review (docs/FINAL_PRE_DEPLOYMENT_REVIEW.md).

These complement tests/test_public_demo.py: they try to get around the guard
rather than confirm that it exists.
"""
import secrets

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import public
from app.core.config import settings
from app.db.demo_seed import reset_demo_database


@pytest.fixture(scope="module")
def template():
    reset_demo_database(quiet=True)
    return public._template_path()


@pytest.fixture
def demo(template, tmp_path):
    api = public.create_public_api(template=template, sandbox_dir=tmp_path / "sb")
    root = FastAPI()
    root.mount("/api", api)
    return TestClient(root, raise_server_exceptions=False), api


def sid() -> str:
    return secrets.token_hex(16)


def _first_draft(client):
    return client.get("/api/web/drafts").json()[0]["id"]


# --------------------------------------------------------------------------- #
# 1. Blocked writes cannot be reached through alternate paths or methods       #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("method,path", [
    ("POST", "/api/accounts/1/contacts/"),            # trailing slash
    ("POST", "/api//accounts/1/contacts"),            # double slash
    ("POST", "/api/Accounts/1/contacts"),             # case change
    ("POST", "/api/accounts/1/./contacts"),           # dot segment
    ("POST", "/api/accounts/1%2Fcontacts"),           # encoded slash
    ("POST", "/api/products/1/score-all?x=1"),        # query string
    ("POST", "/api/web/reset/"),                      # shared reset via slash
    ("POST", "/api/drafts/1/approve/"),               # allowed route + slash
    ("PUT", "/api/drafts/1"),
    ("DELETE", "/api/drafts/1"),
    ("PATCH", "/api/accounts/1"),
])
def test_alternate_paths_to_writes_are_refused(demo, method, path):
    client, _ = demo
    res = client.request(method, path, headers={"X-Demo-Session": sid()}, json={"name": "x"})
    assert res.status_code in (403, 404, 405), (path, res.status_code)
    assert res.status_code != 200


def test_method_override_headers_are_ignored(demo, template):
    client, _ = demo
    res = client.get("/api/products/1/score-all", headers={"X-HTTP-Method-Override": "POST"})
    assert res.status_code == 405


def test_head_and_options_cannot_mutate(demo):
    client, _ = demo
    for method in ("HEAD", "OPTIONS"):
        res = client.request(method, "/api/products/1/score-all")
        assert res.status_code == 405


def test_shared_reset_never_rebuilds_the_template(demo, template):
    client, api = demo
    before = template.stat().st_mtime_ns
    for path in ("/api/web/reset", "/api/web/reset/", "/api//web/reset"):
        client.post(path, headers={"X-Demo-Session": sid()})
    assert template.stat().st_mtime_ns == before


# --------------------------------------------------------------------------- #
# 2. Sandbox isolation                                                         #
# --------------------------------------------------------------------------- #

def _approve_as(client, session_id):
    draft = _first_draft(client)
    assert client.post(f"/api/drafts/{draft}/approve", headers={"X-Demo-Session": session_id}).status_code == 200
    return draft


def test_guessed_and_modified_ids_do_not_reach_another_sandbox(demo):
    client, _ = demo
    owner = sid()
    draft = _approve_as(client, owner)
    modified = owner[:-1] + ("0" if owner[-1] != "0" else "1")
    for other in (sid(), modified, "0" * 32, "f" * 32):
        assert client.get(f"/api/drafts/{draft}", headers={"X-Demo-Session": other}).json()["status"] == "pending"
    assert client.get(f"/api/drafts/{draft}", headers={"X-Demo-Session": owner}).json()["status"] == "approved"


@pytest.mark.parametrize("bad", ["", "A" * 32, "a" * 31, "a" * 33, "../" + "a" * 29, "g" * 32])
def test_invalid_ids_read_shared_data_and_cannot_write(demo, bad):
    client, _ = demo
    owner = sid()
    draft = _approve_as(client, owner)
    headers = {"X-Demo-Session": bad} if bad.strip() else {}
    assert client.get(f"/api/drafts/{draft}", headers=headers).json()["status"] == "pending"
    assert client.post(f"/api/drafts/{draft}/reject", headers=headers).status_code == 400


def test_missing_id_cannot_write(demo):
    client, _ = demo
    assert client.post(f"/api/drafts/{_first_draft(client)}/approve").status_code == 400


def test_expired_sandbox_falls_back_to_shared_data(demo):
    client, api = demo
    now = [0.0]
    api.state.sandboxes.clock = lambda: now[0]
    owner = sid()
    draft = _approve_as(client, owner)
    now[0] = settings.DEMO_SANDBOX_TTL_SECONDS + 1
    assert client.get(f"/api/drafts/{draft}", headers={"X-Demo-Session": owner}).json()["status"] == "pending"
    assert len(api.state.sandboxes) == 0
    # A later edit starts a fresh sandbox from shared data.
    assert client.post(f"/api/drafts/{draft}/reject", headers={"X-Demo-Session": owner}).status_code == 200


def test_capacity_eviction_drops_least_recently_used(demo, monkeypatch):
    """Known limitation, documented: a flood of new ids can evict other visitors' sandboxes."""
    client, api = demo
    api.state.sandboxes.max_sandboxes = 2
    first, second, third = sid(), sid(), sid()
    draft = _approve_as(client, first)
    _approve_as(client, second)
    _approve_as(client, third)
    assert len(api.state.sandboxes) == 2
    assert client.get(f"/api/drafts/{draft}", headers={"X-Demo-Session": first}).json()["status"] == "pending"


def test_reset_with_another_visitors_id_shape_only_touches_that_id(demo):
    client, api = demo
    owner, attacker = sid(), sid()
    draft = _approve_as(client, owner)
    res = client.post("/api/web/reset", headers={"X-Demo-Session": attacker})
    assert res.json() == {"status": "reset", "had_changes": False}
    assert client.get(f"/api/drafts/{draft}", headers={"X-Demo-Session": owner}).json()["status"] == "approved"


# --------------------------------------------------------------------------- #
# 4. Error responses do not leak internals                                     #
# --------------------------------------------------------------------------- #

LEAK_MARKERS = ("/tmp", "/home", "Traceback", "sqlite", "sqlalchemy", "File \"", ".py", "DATABASE_URL", "LLM_API_KEY")


def _assert_clean(res):
    for marker in LEAK_MARKERS:
        assert marker not in res.text, (marker, res.text[:300])


def test_error_responses_are_generic(demo, monkeypatch):
    client, _ = demo
    _assert_clean(client.get("/api/does-not-exist"))
    _assert_clean(client.get("/api/web/accounts/999999"))
    _assert_clean(client.post("/api/web/playground", json={"employee_count": "lots"}))
    _assert_clean(client.patch("/api/drafts/1", headers={"X-Demo-Session": sid()}, content=b"{not json"))

    from app.services.analyst_service import AnalystService

    def boom(*_a, **_k):
        raise RuntimeError("sqlite:////tmp/gtmos.db at /home/user/app/secret.py LLM_API_KEY=abc")

    monkeypatch.setattr(AnalystService, "ask", boom)
    res = client.post("/api/analytics/ask", json={"question": "funnel?"})
    assert res.status_code == 500
    _assert_clean(res)


def test_unhandled_exception_in_a_public_route_is_generic(demo, monkeypatch):
    client, _ = demo
    from app.api.routes import web

    def boom(*_a, **_k):
        raise RuntimeError("Traceback /home/user/GTMOS/app/x.py sqlite failure")

    monkeypatch.setattr(web, "_product", boom)
    res = client.get("/api/web/overview")
    assert res.status_code == 500
    assert res.json() == {"detail": "Internal server error."}


# --------------------------------------------------------------------------- #
# 6. Offline AI is enforced                                                    #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("mode,key", [("live", ""), ("live", "invalid-key"), ("mock", ""), ("LIVE", "x")])
def test_public_demo_never_calls_gemini(template, tmp_path, monkeypatch, mode, key):
    from app.ai.llm import LLMService

    calls = []
    monkeypatch.setattr(settings, "LLM_MODE", mode)
    monkeypatch.setattr(settings, "LLM_API_KEY", key)
    monkeypatch.setattr(LLMService, "_call_live_provider", lambda *a, **k: calls.append(a) or "{}")
    monkeypatch.setattr(LLMService, "_call_gemini", lambda *a, **k: calls.append(a) or "{}")

    api = public.create_public_api(template=template, sandbox_dir=tmp_path / "sb")
    root = FastAPI()
    root.mount("/api", api)
    client = TestClient(root, raise_server_exceptions=False)
    s = {"X-Demo-Session": sid()}

    assert client.post("/api/analytics/ask", json={"question": "How is the funnel doing?"}).status_code == 200
    target = next(r for r in client.get("/api/web/accounts").json() if r["action"] in ("CONTACT", "PRIORITIZE", "NURTURE"))
    assert client.post(f"/api/accounts/{target['id']}/personalize", headers=s).status_code == 200
    assert client.post("/api/web/playground", json={"industry": "B2B SaaS", "employee_count": 100, "country": "US",
                                                    "research_note": "We are hiring 5 support agents."}).status_code == 200
    assert calls == []
    assert client.get("/api/web/overview").json()["llm_mode"] == "mock"


# --------------------------------------------------------------------------- #
# 5. Docs exposure is informational only                                       #
# --------------------------------------------------------------------------- #

def test_openapi_is_served_but_blocked_routes_stay_blocked(demo):
    client, _ = demo
    spec = client.get("/api/openapi.json").json()
    assert "/accounts/{id}/contacts" in spec["paths"]
    assert client.post("/api/accounts/1/contacts", headers={"X-Demo-Session": sid()}, json={"name": "x"}).status_code == 403
