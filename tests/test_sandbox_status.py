"""Sandbox status signal (docs/T5_SANDBOX_UX_FIX.md).

Every guarded response says whether the caller's sandbox exists on this server
(`X-Demo-Sandbox: active|none`) and which one (`X-Demo-Sandbox-Id`). The browser
compares the id with the one it saw when it last edited, so it can tell the
visitor when temporary edits are gone.
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


def make_instance(template, tmp_path, name="sb"):
    api = public.create_public_api(template=template, sandbox_dir=tmp_path / name)
    root = FastAPI()
    root.mount("/api", api)
    return TestClient(root, raise_server_exceptions=False), api


def status(res):
    return res.headers.get("x-demo-sandbox"), res.headers.get("x-demo-sandbox-id")


@pytest.fixture
def inst(template, tmp_path):
    return make_instance(template, tmp_path)


def _draft(client):
    return client.get("/api/web/drafts").json()[0]["id"]


def test_no_session_or_unknown_session_reports_none(inst):
    client, _ = inst
    assert status(client.get("/api/web/overview")) == ("none", None)
    assert status(client.get("/api/web/overview", headers={"X-Demo-Session": secrets.token_hex(16)})) == ("none", None)


def test_edit_creates_a_sandbox_and_reads_keep_its_id(inst):
    client, _ = inst
    h = {"X-Demo-Session": secrets.token_hex(16)}
    state, token = status(client.post(f"/api/drafts/{_draft(client)}/approve", headers=h))
    assert state == "active" and token and len(token) == 16
    assert status(client.get("/api/web/drafts", headers=h)) == ("active", token)
    assert status(client.get("/api/web/methodology", headers=h)) == ("active", token)  # even routes without a DB session


def test_reset_reports_none_immediately(inst):
    client, _ = inst
    h = {"X-Demo-Session": secrets.token_hex(16)}
    client.post(f"/api/drafts/{_draft(client)}/approve", headers=h)
    assert status(client.post("/api/web/reset", headers=h)) == ("none", None)
    assert status(client.get("/api/web/drafts", headers=h)) == ("none", None)


def test_expired_sandbox_reports_none_then_a_new_id(inst):
    client, api = inst
    now = [0.0]
    api.state.sandboxes.clock = lambda: now[0]
    h = {"X-Demo-Session": secrets.token_hex(16)}
    _, first = status(client.post(f"/api/drafts/{_draft(client)}/approve", headers=h))
    now[0] = settings.DEMO_SANDBOX_TTL_SECONDS + 1
    assert status(client.get("/api/web/drafts", headers=h)) == ("none", None)          # missing/expired
    state, second = status(client.post(f"/api/drafts/{_draft(client)}/reject", headers=h))
    assert state == "active" and second != first                                         # recreated


def test_recreated_after_reset_gets_a_different_id(inst):
    client, _ = inst
    h = {"X-Demo-Session": secrets.token_hex(16)}
    _, first = status(client.post(f"/api/drafts/{_draft(client)}/approve", headers=h))
    client.post("/api/web/reset", headers=h)
    _, second = status(client.post(f"/api/drafts/{_draft(client)}/reject", headers=h))
    assert second and second != first


def test_evicted_sandbox_reports_none(inst):
    client, api = inst
    api.state.sandboxes.max_sandboxes = 1
    a, b = {"X-Demo-Session": secrets.token_hex(16)}, {"X-Demo-Session": secrets.token_hex(16)}
    client.post(f"/api/drafts/{_draft(client)}/approve", headers=a)
    client.post(f"/api/drafts/{_draft(client)}/approve", headers=b)
    assert status(client.get("/api/web/drafts", headers=a)) == ("none", None)


def test_another_server_instance_has_no_sandbox(template, tmp_path):
    one, _ = make_instance(template, tmp_path, "one")
    two, _ = make_instance(template, tmp_path, "two")
    h = {"X-Demo-Session": secrets.token_hex(16)}
    _, token = status(one.post(f"/api/drafts/{_draft(one)}/approve", headers=h))
    assert token
    assert status(two.get("/api/web/drafts", headers=h)) == ("none", None)
    _, other = status(two.post(f"/api/drafts/{_draft(two)}/reject", headers=h))
    assert other and other != token


def test_ids_are_per_sandbox_and_never_leak_across_visitors(inst, template):
    client, _ = inst
    a, b = {"X-Demo-Session": secrets.token_hex(16)}, {"X-Demo-Session": secrets.token_hex(16)}
    _, ta = status(client.post(f"/api/drafts/{_draft(client)}/approve", headers=a))
    assert status(client.get("/api/web/drafts", headers=b)) == ("none", None)
    _, tb = status(client.post(f"/api/drafts/{_draft(client)}/approve", headers=b))
    assert ta != tb and ta not in a["X-Demo-Session"] and tb not in b["X-Demo-Session"]


def test_status_headers_never_touch_shared_data(inst, template):
    client, _ = inst
    before = template.stat().st_mtime_ns
    h = {"X-Demo-Session": secrets.token_hex(16)}
    client.post(f"/api/drafts/{_draft(client)}/approve", headers=h)
    client.get("/api/web/drafts", headers=h)
    client.post("/api/web/reset", headers=h)
    assert template.stat().st_mtime_ns == before


def test_full_api_has_no_sandbox_headers():
    from app.api.main import create_app
    res = TestClient(create_app()).get("/health")
    assert "x-demo-sandbox" not in res.headers
