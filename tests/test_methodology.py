"""T5: /web/methodology reports the code's own constants and the real evaluation results."""
import secrets

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import public
from app.api.main import create_app
from app.db.demo_seed import reset_demo_database
from app.services.recommendation_engine import ACTION_RULES
from app.services.signal_config import SIGNAL_WEIGHTS


@pytest.fixture(scope="module")
def m():
    return TestClient(create_app()).get("/web/methodology").json()


def test_evaluation_weaknesses_are_reported_not_hidden(m):
    tier = m["evaluation"]["tier"]
    assert tier["accuracy"] == pytest.approx(0.57) and tier["total"] == 100
    assert tier["recall"]["Priority 2"] == 0.0
    assert tier["confusion_matrix"]["Priority 2"]["Priority 1"] == 19
    assert "proxy" in tier["method"]
    assert "simplified keyword matcher" in m["evaluation"]["signals"]["method"]


def test_constants_come_from_the_code(m):
    assert m["fit_max"] == 80 and m["intent_max"] == 20
    assert sum(c["max"] for c in m["components"]) == 100
    assert {**m["signal_weights"], **m["disqualifier_penalties"]} == SIGNAL_WEIGHTS
    assert [r["rule_id"] for r in m["action_rules"]] == list(ACTION_RULES)
    assert m["decay"] == {"current_max_days": 90, "aging_max_days": 180, "aging_decay": 0.5}
    assert [t["min_total"] for t in m["tiers"]] == [90.0, 75.0, 50.0, 0.0]


def test_methodology_is_read_only_in_public(tmp_path):
    reset_demo_database(quiet=True)
    root = FastAPI()
    root.mount("/api", public.create_public_api(template=public._template_path(), sandbox_dir=tmp_path / "sb"))
    c = TestClient(root, raise_server_exceptions=False)
    assert c.get("/api/web/methodology").status_code == 200
    assert c.post("/api/web/methodology", headers={"X-Demo-Session": secrets.token_hex(16)}).status_code == 403
