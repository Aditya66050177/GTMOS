"""T1 explainability regression tests (docs/T1_EXPLAINABILITY_REPORT.md).

Guarantees:
* original baseline outcomes are unchanged (golden file),
* explanations use the engine's own numbers (no parallel formula),
* rejected evidence is stored and contributes zero,
* synthetic demo additions stay separate from the baseline and the evaluation,
* the new endpoints stay read-only and sandbox-isolated behind the public guard.
"""
import csv
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.ai.mock_signals import analyze_note
from app.api import public
from app.api.main import create_app
from app.db.database import SessionLocal
from app.db.demo_seed import DEMO_ADDITIONS_CSV, reset_demo_database
from app.models import Account, Activity, ICPProfile, Product, Score, Signal
from app.schemas.signal import SignalListSchema
from app.services import research_engine as research_module
from app.services.recommendation_engine import ACTION_RULES, RecommendationEngine
from app.services.research_engine import ResearchEngine, anchor_shift
from app.services.signal_config import SIGNAL_WEIGHTS
from app.services.signal_engine import (
    AGING_AFTER_DAYS, EXPIRED_AFTER_DAYS, recency_decay, recency_status, score_signals, signal_contributions,
)

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = json.loads((Path(__file__).parent / "fixtures" / "baseline_outcomes.json").read_text(encoding="utf-8"))


def snapshot():
    db = SessionLocal()
    try:
        icp, rec, out = db.query(ICPProfile).first(), RecommendationEngine(), {}
        for a, s in db.query(Account, Score).join(Score, Score.account_id == Account.id).order_by(Account.id):
            pos = [x for x in db.query(Signal).filter_by(account_id=a.id).all() if x.source != "Internal CRM"]
            r = rec.get_recommendation(s, pos, icp)
            out[a.name] = {k: round(getattr(s, k), 4) for k in
                           ("icp_fit", "company_fit", "technology_fit", "intent_score", "geography_score", "total_score")}
            out[a.name].update(tier=s.tier, action=r.action, persona=r.suggested_persona,
                               angle=r.suggested_angle, stage=a.stage)
        return out
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# Baseline outcomes are unchanged                                              #
# --------------------------------------------------------------------------- #

def test_baseline_outcomes_match_the_golden_file():
    reset_demo_database(quiet=True, include_demo_additions=False)
    assert snapshot() == GOLDEN["accounts"]


def test_demo_additions_change_only_the_comparison_account_scores():
    reset_demo_database(quiet=True, include_demo_additions=True)
    current = snapshot()
    scored = ("icp_fit", "company_fit", "technology_fit", "intent_score", "geography_score", "total_score", "tier", "action")
    changed = {n for n in GOLDEN["accounts"] if any(current[n][k] != GOLDEN["accounts"][n][k] for k in scored)}
    assert changed == {"Company 36 B2B"}
    c36, c37 = current["Company 36 B2B"], current["Company 37 Cloud"]
    assert (c36["total_score"], c36["tier"], c36["action"], c36["intent_score"]) == (77.0, "Priority 2", "PRIORITIZE", 20.0)
    assert (c37["total_score"], c37["tier"], c37["action"], c37["intent_score"]) == (80.0, "Priority 2", "RESEARCH", 0.0)


# --------------------------------------------------------------------------- #
# Recency and contribution maths come from the engine                          #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("days,decay,status", [
    (0, 1.0, "current"), (AGING_AFTER_DAYS, 1.0, "current"), (AGING_AFTER_DAYS + 1, 0.5, "aging"),
    (EXPIRED_AFTER_DAYS, 0.5, "aging"), (EXPIRED_AFTER_DAYS + 1, 0.0, "expired"), (400, 0.0, "expired"),
])
def test_recency_bands(days, decay, status):
    assert recency_decay(days) == decay
    assert recency_status(days) == status


def test_contributions_match_formula_and_score_signals():
    now = datetime(2026, 11, 1)
    sigs = [
        {"signal_type": "support_hiring", "strength": 0.8, "confidence": 0.9, "detected_at": now - timedelta(days=10)},
        {"signal_type": "funding", "strength": 0.9, "confidence": 0.9, "detected_at": now - timedelta(days=120)},
        {"signal_type": "product_launch", "strength": 0.7, "confidence": 0.8, "detected_at": now - timedelta(days=200)},
        {"signal_type": "support_hiring", "strength": 0.8, "confidence": 0.9, "detected_at": now - timedelta(days=40)},
        {"signal_type": "too_small", "strength": 1.0, "confidence": 1.0, "detected_at": now},
    ]
    c = signal_contributions(sigs, now)
    assert c[0].points == pytest.approx(20 * 0.8 * 0.9 * 1.0) and c[0].counted
    assert c[1].points == pytest.approx(15 * 0.9 * 0.9 * 0.5) and c[1].decay == 0.5
    assert c[2].points == 0.0 and c[2].decay == 0.0
    assert not c[3].counted and c[3].points == 0.0          # older duplicate superseded
    assert c[4].points == -20.0                             # disqualifier penalty
    assert score_signals(sigs, now) == max(0.0, min(20.0, sum(x.points for x in c)))


# --------------------------------------------------------------------------- #
# Account explanations                                                         #
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def full_client():
    reset_demo_database(quiet=True, include_demo_additions=True)
    return TestClient(create_app())


@pytest.fixture(scope="module")
def all_explanations(full_client):
    ids = [r["id"] for r in full_client.get("/web/accounts").json()]
    return [full_client.get(f"/web/accounts/{i}/explain").json() for i in ids]


def test_every_explanation_reproduces_the_stored_scores(all_explanations):
    assert len(all_explanations) == 150
    for e in all_explanations:
        assert e["intent"]["matches_stored_score"], e["account"]["name"]
        assert e["fit"]["score"] + e["intent"]["score"] == pytest.approx(e["total"]["total"], abs=0.051)
        assert e["fit"]["score"] == pytest.approx(sum(c["score"] for c in e["fit"]["components"]), abs=0.051)
        assert e["fit"]["max_score"] == 80 and e["intent"]["max_score"] == 20
        assert e["recommendation"]["rule_id"] in ACTION_RULES
        assert ACTION_RULES[e["recommendation"]["rule_id"]][2] == e["recommendation"]["action"]


def test_signal_points_follow_the_formula(all_explanations):
    for e in all_explanations:
        for s in e["intent"]["buying_signals"] + e["intent"]["disqualifiers"]:
            expected = s["weight"] * s["strength"] * s["confidence"] * s["decay"] if s["counted"] else 0.0
            assert s["points"] == pytest.approx(expected, abs=1e-4)
            assert s["weight"] == SIGNAL_WEIGHTS.get(s["signal_type"], 0.0)


def test_all_recency_states_appear_in_the_demo(all_explanations):
    states = {s["status"] for e in all_explanations for s in e["intent"]["buying_signals"]}
    assert {"current", "aging", "expired"} <= states


def test_signal_quotes_trace_back_to_their_note(all_explanations):
    for e in all_explanations:
        for s in e["intent"]["buying_signals"]:
            assert s["source_sentence"] and s["quote"].lower() in s["source_sentence"].lower()


def test_acme_rejected_evidence_contributes_zero(full_client):
    acme = next(r for r in full_client.get("/web/accounts").json() if r["name"] == "Acme Technologies")
    e = full_client.get(f"/web/accounts/{acme['id']}/explain").json()
    cats = sorted(r["category"] for r in e["rejected_evidence"])
    assert cats == ["ambiguous", "negated"]
    assert all(r["points"] == 0 for r in e["rejected_evidence"])
    assert e["intent"]["score"] == 0.0 and e["intent"]["buying_signals"] == []
    assert e["recommendation"]["rule_id"] == "P3_INTENT_LT_10"


def test_comparison_endpoint(full_client):
    featured = full_client.get("/web/comparisons/featured").json()
    ids = featured[0]["account_ids"]
    res = full_client.get(f"/web/compare?ids={ids[0]},{ids[1]}").json()
    names = [a["account"]["name"] for a in res["accounts"]]
    assert names == ["Company 36 B2B", "Company 37 Cloud"]
    assert any("Within a tier, intent decides the action" in o for o in res["observations"])
    c37 = res["accounts"][1]
    assert [r["category"] for r in c37["rejected_evidence"]] == ["unsupported"]
    assert c37["includes_synthetic_demo_additions"] is True


@pytest.mark.parametrize("ids,status", [("1", 422), ("1,2,3,4,5", 422), ("1,1", 422), ("a,b", 422),
                                        ("1,999999", 404), ("x" * 100, 422)])
def test_comparison_validation(full_client, ids, status):
    assert full_client.get(f"/web/compare?ids={ids}").status_code == status


def test_explain_unknown_account_404(full_client):
    assert full_client.get("/web/accounts/999999/explain").status_code == 404


# --------------------------------------------------------------------------- #
# Rejected evidence storage                                                    #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("text,category", [
    ("The company has frozen hiring.", "negated"),
    ("The company is not currently hiring.", "negated"),
    ("Rumours suggest they are raising a new funding round.", "unsupported"),
    ("They might be looking into expanding internationally next year.", "ambiguous"),
])
def test_rejections_are_categorised(text, category):
    result = analyze_note(text)
    assert result["signals"] == []
    assert result["rejected"] and result["rejected"][0]["category"] == category


def _fresh_account(db, name):
    product = Product(name=f"P-{name}", description="d", target_market=[], geography=[])
    db.add(product)
    db.commit()
    db.add(ICPProfile(product_id=product.id, industries=["B2B SaaS"], company_size_min=50, company_size_max=500,
                      geographies=["US"], pain_points=[], technologies=[], exclusions=[]))
    acc = Account(name=name, industry="B2B SaaS", employee_count=100, country="US")
    db.add(acc)
    db.commit()
    return acc


def test_rejected_claims_are_stored_with_zero_points_and_never_change_intent():
    db = SessionLocal()
    try:
        acc = _fresh_account(db, f"Rejection Co {secrets.token_hex(3)}")
        re = ResearchEngine()
        re.extract_signals_from_text(db, acc, "We are not hiring right now. Rumours suggest a funding round.",
                                     "News", "2026-10-01T00:00:00Z")
        rows = db.query(Activity).filter_by(account_id=acc.id, activity_type="rejected_signal").all()
        assert sorted(r.activity_metadata["category"] for r in rows) == ["negated", "unsupported"]
        assert all(r.activity_metadata["points"] == 0.0 for r in rows)
        assert db.query(Signal).filter_by(account_id=acc.id).count() == 0
        note = db.query(Activity).filter_by(account_id=acc.id, activity_type="research_note").one()
        assert note.activity_metadata["signal_ids"] == []

        # Re-ingesting the identical note records nothing new.
        re.extract_signals_from_text(db, acc, "We are not hiring right now. Rumours suggest a funding round.",
                                     "News", "2026-10-01T00:00:00Z")
        assert db.query(Activity).filter_by(account_id=acc.id, activity_type="rejected_signal").count() == 2
        assert db.query(Activity).filter_by(account_id=acc.id, activity_type="research_note").count() == 1
    finally:
        db.close()


def test_unsupported_quote_is_stored_as_unsupported():
    db = SessionLocal()
    try:
        acc = _fresh_account(db, f"Quote Co {secrets.token_hex(3)}")

        class Hallucinating:
            def generate_structured(self, prompt, schema):
                return SignalListSchema(signals=[{
                    "type": "funding", "description": "Raised", "strength": 0.9, "source": "x",
                    "detected_at": "2026-01-01T00:00:00Z", "confidence": 0.9, "evidence": "raised $90M last week",
                }])

        ResearchEngine(llm_service=Hallucinating()).extract_signals_from_text(
            db, acc, "The company held an offsite.", "Blog", "2026-10-01T00:00:00Z")
        row = db.query(Activity).filter_by(account_id=acc.id, activity_type="rejected_signal").one()
        assert row.activity_metadata["category"] == "unsupported"
        assert row.activity_metadata["points"] == 0.0
    finally:
        db.close()


def test_llm_output_without_rejected_list_still_validates():
    parsed = SignalListSchema.model_validate({"signals": []})
    assert parsed.rejected == []


# --------------------------------------------------------------------------- #
# Synthetic additions stay separate                                            #
# --------------------------------------------------------------------------- #

def test_synthetic_additions_are_labelled_and_separate():
    with open(DEMO_ADDITIONS_CSV, encoding="utf-8", newline="") as f:
        additions = list(csv.DictReader(f))
    assert 2 <= len(additions) <= 3
    assert all(r["label"].startswith("SYNTHETIC DEMO ADDITION") for r in additions)
    baseline = (ROOT / "data" / "signals.csv").read_text(encoding="utf-8")
    assert "SYNTHETIC DEMO ADDITION" not in baseline
    assert not any(r["raw_text"] in baseline for r in additions)
    for eval_file in (ROOT / "data" / "eval").glob("*.csv"):
        text = eval_file.read_text(encoding="utf-8")
        assert not any(r["raw_text"] in text for r in additions)


def test_evaluation_results_are_unchanged():
    from app.ai.evaluators import GTMOSEvaluator
    from app.ai.run_eval import EVAL_ICP

    result = GTMOSEvaluator().evaluate_scoring(EVAL_ICP, ROOT / "data" / "eval" / "eval_accounts.csv")
    assert result["accuracy"] == pytest.approx(0.57)
    assert result["per_tier_recall"]["Priority 2"] == 0.0


def test_synthetic_notes_are_traceable_in_provenance(full_client):
    e = full_client.get("/web/compare?ids=" + ",".join(
        str(i) for i in full_client.get("/web/comparisons/featured").json()[0]["account_ids"])).json()
    c36_notes = [n for n in e["accounts"][0]["research_notes"] if n["dataset"] == "demo_addition"]
    assert len(c36_notes) == 2 and all(n["label"].startswith("SYNTHETIC DEMO ADDITION") for n in c36_notes)


# --------------------------------------------------------------------------- #
# Deterministic date anchoring                                                 #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("clock", ["2026-11-25T03:00:00", "2026-11-25T20:30:00"])
def test_anchored_ages_do_not_depend_on_time_of_day(monkeypatch, clock):
    monkeypatch.setattr(research_module, "utc_now", lambda: datetime.fromisoformat(clock))
    rows = [{"date": "2026-10-02T14:07:33Z"}, {"date": "2026-04-04T14:07:33Z"}]  # 181 days apart
    shift = anchor_shift(rows)
    now = datetime.fromisoformat(clock)
    oldest = datetime(2026, 4, 4, 14, 7, 33) + shift
    assert (now - oldest).days == 181


# --------------------------------------------------------------------------- #
# Public API: read-only, isolated                                              #
# --------------------------------------------------------------------------- #

@pytest.fixture
def public_client(tmp_path):
    reset_demo_database(quiet=True, include_demo_additions=True)
    template = public._template_path()
    api = public.create_public_api(template=template, sandbox_dir=tmp_path / "sb")
    root = FastAPI()
    root.mount("/api", api)
    return TestClient(root, raise_server_exceptions=False), template


def test_explainability_endpoints_are_read_only_in_public(public_client):
    client, template = public_client
    before = template.stat().st_mtime_ns
    s = {"X-Demo-Session": secrets.token_hex(16)}
    assert client.get("/api/web/accounts/1/explain").status_code == 200
    assert client.get("/api/web/compare?ids=1,3").status_code == 200
    assert client.get("/api/web/comparisons/featured").status_code == 200
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)("/api/web/accounts/1/explain", headers=s).status_code == 403
        assert getattr(client, method)("/api/web/compare?ids=1,3", headers=s).status_code == 403
    assert template.stat().st_mtime_ns == before


def test_explanations_do_not_reveal_another_visitors_sandbox(public_client):
    client, _ = public_client
    owner, other = secrets.token_hex(16), secrets.token_hex(16)
    draft = client.get("/api/web/drafts").json()[0]
    assert client.post(f"/api/drafts/{draft['id']}/approve", headers={"X-Demo-Session": owner}).status_code == 200
    mine = client.get(f"/api/web/accounts/{draft['account_id']}/explain", headers={"X-Demo-Session": owner}).json()
    theirs = client.get(f"/api/web/accounts/{draft['account_id']}/explain", headers={"X-Demo-Session": other}).json()
    shared = client.get(f"/api/web/accounts/{draft['account_id']}/explain").json()
    assert theirs == shared
    assert mine["total"] == shared["total"]  # approvals never change scores
