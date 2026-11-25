"""T2 executive analytics and analyst tests (docs/T2_EXECUTIVE_ANALYTICS_REPORT.md)."""
import re
import secrets
from collections import Counter
from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (registers tables)
from app.ai.llm import LLMService
from app.api import public
from app.api.main import create_app
from app.core.timeutil import utc_now
from app.db.database import Base, SessionLocal
from app.db.demo_seed import reset_demo_database
from app.models import Account, Activity, ICPProfile, Product, Score, Signal
from app.schemas.analytics import AnalystQueryIntentSchema
from app.services import executive_analytics as ex
from app.services.analyst_service import AnalystService

QIDS = list(ex.QUESTIONS)
HEDGE_WORDS = re.compile(r"\b(likely|probably|suggests?|may|might|could|perhaps|because)\b", re.I)


@pytest.fixture(scope="module")
def seeded():
    reset_demo_database(quiet=True, include_demo_additions=True)


@pytest.fixture(scope="module")
def client(seeded):
    return TestClient(create_app())


# --------------------------------------------------------------------------- #
# Answers are structured and grounded in the database                          #
# --------------------------------------------------------------------------- #

def test_question_list(client):
    qs = client.get("/web/executive").json()
    assert [q["id"] for q in qs] == QIDS


@pytest.mark.parametrize("qid", QIDS)
def test_every_answer_separates_observations_from_hypotheses(client, qid):
    a = client.get(f"/web/executive/{qid}").json()
    assert a["observations"] and a["data_sources"] and a["data_provenance"]
    assert all(h["label"].startswith("Hypothesis") for h in a["hypotheses"])
    for o in a["observations"]:
        assert not HEDGE_WORDS.search(o["text"]), f"speculative wording in an observation: {o['text']}"
    assert a["generated_by"].startswith("Deterministic")


def test_unknown_question_404(client):
    assert client.get("/web/executive/revenue-forecast").status_code == 404


def _db_actions(client):
    return Counter((r["action"], r["stage"] in ("Won", "Lost")) for r in client.get("/web/accounts").json())


def test_worth_pursuing_matches_accounts_endpoint(client):
    a = client.get("/web/executive/worth-pursuing").json()
    rows = client.get("/web/accounts").json()
    expected = sorted(r["name"] for r in rows if r["action"] in ("CONTACT", "PRIORITIZE") and r["stage"] not in ("Won", "Lost"))
    assert sorted(i["name"] for i in a["accounts"]) == expected
    assert a["data"]["count"] == len(expected)
    assert a["data"]["by_action"] == dict(Counter(r["action"] for r in rows))
    synthetic = {i["name"] for i in a["accounts"] if i["uses_synthetic_demo_additions"]}
    assert synthetic <= {"Company 36 B2B"}


def test_nurture_matches_accounts_endpoint(client):
    a = client.get("/web/executive/nurture").json()
    expected = sorted(r["name"] for r in client.get("/web/accounts").json() if r["action"] == "NURTURE")
    assert sorted(i["name"] for i in a["accounts"]) == expected


def test_stuck_stage_counts_match_database(client):
    a = client.get("/web/executive/stuck").json()
    db = SessionLocal()
    try:
        counts = Counter(acc.stage or "Research" for acc in db.query(Account).all())
    finally:
        db.close()
    assert {k: v for k, v in a["data"]["stage_counts"].items() if v} == dict(counts)
    assert "simulat" in a["summary"].lower()
    assert "simulation" in a["data_provenance"]["pipeline"].lower()


def test_stuck_conversions_agree_with_the_analytics_engine(client):
    mine = {(c["from"], c["to"]): (c["from_count"], c["to_count"])
            for c in client.get("/web/executive/stuck").json()["data"]["conversions"]}
    legacy = {(c["from_stage"], c["to_stage"]): (c["from_count"], c["to_count"])
              for c in client.get("/analytics/funnel").json()["conversions"]}
    assert mine == legacy


def test_signal_matrix_matches_database(client):
    a = client.get("/web/executive/signals-by-tier").json()
    db = SessionLocal()
    try:
        tier = {s.account_id: s.tier for s in db.query(Score).all()}
        expected = Counter()
        for sig in db.query(Signal).filter(Signal.source != "Internal CRM").all():
            expected[(sig.signal_type, tier[sig.account_id])] += 0  # ensure key
        per_account = {(s.signal_type, s.account_id) for s in db.query(Signal).filter(Signal.source != "Internal CRM").all()}
        for stype, acc in per_account:
            expected[(stype, tier[acc])] += 1
        bands = Counter("ge15" if (s.intent_score or 0) >= 15 else "gt0" if (s.intent_score or 0) > 0 else "zero"
                        for s in db.query(Score).all())
    finally:
        db.close()
    m = a["data"]["matrix"]
    for (stype, t), n in expected.items():
        assert m[stype][t]["accounts_with_signal"] == n
    assert a["data"]["intent_bands"]["intent_ge_15"] == bands["ge15"]
    assert a["data"]["intent_bands"]["intent_above_0"] == bands["ge15"] + bands["gt0"]
    assert any("co-occurrence, not cause" in h["text"] for h in a["hypotheses"])


def test_investigate_next_follows_its_selection_rules(client):
    a = client.get("/web/executive/investigate-next").json()
    assert a["accounts"] and len(a["accounts"]) <= 10
    for item in a["accounts"]:
        assert item["stage"] not in ("Won", "Lost")
        assert item["why"]
        high_fit_rule = item["fit"] >= ex.HIGH_FIT and item["intent"] < ex.WEAK_INTENT
        assert high_fit_rule or any("rejected claim" in w or "aging" in w for w in item["why"])


def test_funnel_and_trends_are_labelled_simulated(client):
    assert "Simulated pipeline" in client.get("/analytics/funnel").json()["data_label"]
    assert "Simulated pipeline" in client.get("/analytics/trends").json()["data_label"]


def test_answers_are_deterministic(client):
    for qid in QIDS:
        assert client.get(f"/web/executive/{qid}").json() == client.get(f"/web/executive/{qid}").json()


# --------------------------------------------------------------------------- #
# Analyst                                                                      #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("question,fn", [
    ("Which accounts are worth pursuing?", "get_worth_pursuing"),
    ("What are our strongest accounts and why?", "get_worth_pursuing"),
    ("Which accounts should be nurtured?", "get_nurture_accounts"),
    ("Where are opportunities getting stuck?", "get_stuck_opportunities"),
    ("What are the biggest weaknesses in our current pipeline?", "get_stuck_opportunities"),
    ("Which buying signals appear across different priority tiers?", "get_signal_tier_matrix"),
    ("How many accounts have strong evidence of buying intent?", "get_signal_tier_matrix"),
    ("Which accounts should the team investigate next?", "get_investigate_next"),
    ("Which accounts have high fit but weak intent?", "get_investigate_next"),
    ("What should our sales team investigate this week?", "get_investigate_next"),
])
def test_executive_routing(seeded, question, fn):
    db = SessionLocal()
    try:
        res = AnalystService(llm=LLMService(mode="mock")).ask(db, question)
    finally:
        db.close()
    assert res.function_called == fn
    assert res.observations and res.data["question_id"] == ex.ANALYST_FUNCTIONS[fn]
    assert res.explanation == res.data["summary"]


class _ScriptedLLM:
    """Router that returns whatever function name the test wants, plus a fake explanation."""

    def __init__(self, function_name, parameters=None):
        self.function_name, self.parameters = function_name, parameters or {}

    def generate_structured(self, prompt, schema):
        if schema is AnalystQueryIntentSchema:
            return AnalystQueryIntentSchema(function_name=self.function_name, parameters=self.parameters)
        return schema(explanation="FABRICATED: revenue grew 300%")


@pytest.mark.parametrize("name", ["DROP TABLE accounts", "get_all_rows", "__import__('os')", "SELECT * FROM scores"])
def test_router_cannot_run_anything_outside_the_allowlist(seeded, name):
    db = SessionLocal()
    try:
        res = AnalystService(llm=_ScriptedLLM(name, {"sql": "DELETE FROM accounts"})).ask(db, "anything")
        assert res.function_called == "unknown" and res.data == {}
        assert db.query(Account).count() == 150
    finally:
        db.close()


def test_executive_answers_never_use_llm_text(seeded):
    db = SessionLocal()
    try:
        res = AnalystService(llm=_ScriptedLLM("get_worth_pursuing", {"limit": 999})).ask(db, "x")
    finally:
        db.close()
    assert "FABRICATED" not in res.explanation and "FABRICATED" not in str(res.observations)


def test_legacy_answers_get_deterministic_observations_even_if_llm_text_is_wrong(seeded):
    db = SessionLocal()
    try:
        res = AnalystService(llm=_ScriptedLLM("get_funnel_summary")).ask(db, "funnel")
    finally:
        db.close()
    assert res.explanation.startswith("FABRICATED")            # the LLM's wording is shown as the explanation...
    assert "FABRICATED" not in res.observations[0]              # ...but observations come from the data
    assert str(res.data["totals"]["total_accounts"]) in res.observations[0]
    assert "Simulated pipeline" in res.data_label


# --------------------------------------------------------------------------- #
# Edge cases on isolated databases                                             #
# --------------------------------------------------------------------------- #

@pytest.fixture
def blank(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'edge.db').as_posix()}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    yield db
    db.close()
    engine.dispose()


def _product(db, **icp):
    p = Product(name="P", description="d", target_market=[], geography=[])
    db.add(p)
    db.commit()
    db.add(ICPProfile(product_id=p.id, industries=["B2B SaaS"], company_size_min=50, company_size_max=500,
                      geographies=["US"], buyer_roles=["VP Support"], pain_points=[], technologies=[], exclusions=[]))
    db.commit()
    return p


def _account(db, product, name, total, intent, tier, stage="Research"):
    a = Account(name=name, industry="B2B SaaS", employee_count=100, country="US", stage=stage)
    db.add(a)
    db.commit()
    db.add(Score(account_id=a.id, product_id=product.id, icp_fit=0, company_fit=0, technology_fit=0,
                 intent_score=intent, geography_score=0, total_score=total, tier=tier,
                 reasoning={"components": [], "reasons": []}))
    db.commit()
    return a


@pytest.mark.parametrize("qid", QIDS)
def test_empty_database(blank, qid):
    a = ex.answer(blank, qid)
    assert "No scored accounts" in a.summary
    assert a.accounts == [] and a.hypotheses == []


def test_accounts_without_product_are_reported(blank):
    blank.add(Account(name="Orphan", stage="Contacted"))
    blank.commit()
    a = ex.answer(blank, "worth-pursuing")
    assert "none is scored" in a.summary
    assert any("no score" in q for q in a.data_quality)
    assert any("no product" in q.lower() for q in a.data_quality)
    stuck = ex.answer(blank, "stuck")   # stage data still answerable without scores
    assert stuck.data["stage_counts"]["Contacted"] == 1


def test_missing_values_do_not_crash(blank):
    p = _product(blank)
    a = _account(blank, p, "Nulls Inc", total=60.0, intent=None, tier="Priority 3", stage=None)
    blank.add(Signal(account_id=a.id, signal_type="funding", strength=None, confidence=None, detected_at=None,
                     source="News", evidence=None))
    blank.add(Activity(account_id=a.id, activity_type="outreach_sent", status="completed", timestamp=None))
    blank.commit()
    blank.query(Activity).filter_by(account_id=a.id).update({"timestamp": None})
    blank.commit()
    for qid in QIDS:
        res = ex.answer(blank, qid)
        assert res.observations
    assert any("no intent value" in q for q in ex.answer(blank, "nurture").data_quality)


def test_unusual_distribution_all_low_single_stage(blank):
    p = _product(blank)
    for i in range(5):
        _account(blank, p, f"Low {i}", total=10.0 + i, intent=0.0, tier="Low", stage="Contacted")
    pursue = ex.answer(blank, "worth-pursuing")
    assert pursue.data["count"] == 0 and "none" in pursue.summary
    assert ex.answer(blank, "nurture").accounts == []
    matrix = ex.answer(blank, "signals-by-tier")
    assert matrix.data["tier_sizes"] == {"Priority 1": 0, "Priority 2": 0, "Priority 3": 0, "Low": 5}
    stuck = ex.answer(blank, "stuck")
    assert any("no pipeline activity recorded" in o.text for o in stuck.observations)


def test_single_strong_account(blank):
    p = _product(blank)
    a = _account(blank, p, "Solo", total=95.0, intent=18.0, tier="Priority 1")
    blank.add(Signal(account_id=a.id, signal_type="support_hiring", strength=0.8, confidence=0.9,
                     detected_at=utc_now() - timedelta(days=3), source="Jobs", evidence="hiring support"))
    blank.commit()
    res = ex.answer(blank, "worth-pursuing")
    assert [i.name for i in res.accounts] == ["Solo"] and res.accounts[0].action == "CONTACT"


def test_inconsistent_pipeline_is_flagged_not_hidden(blank):
    p = _product(blank)
    now = utc_now()
    behind = _account(blank, p, "Behind", 60.0, 0.0, "Priority 3", stage="Contacted")
    blank.add(Activity(account_id=behind.id, activity_type="meeting_held", status="completed", timestamp=now))
    _account(blank, p, "Phantom Win", 80.0, 0.0, "Priority 2", stage="Won")
    _account(blank, p, "Odd Stage", 40.0, 0.0, "Low", stage="Negotiation")
    silent = _account(blank, p, "Silent", 70.0, 0.0, "Priority 3", stage="Replied")
    blank.add(Activity(account_id=silent.id, activity_type="reply_received", status="completed",
                       timestamp=now - timedelta(days=30)))
    blank.commit()
    res = ex.answer(blank, "stuck", now=now)
    dq = " ".join(res.data_quality)
    assert "Behind: stage Contacted but has activity for Meeting" in dq
    assert "Phantom Win: stage Won with no deal_won activity" in dq
    assert "Odd Stage: unknown stage 'Negotiation'" in dq
    assert any(i.name == "Silent" and "30 days" in i.why[0] for i in res.accounts)
    assert res.data["stage_counts"]["Won"] == 1


# --------------------------------------------------------------------------- #
# Public API: read-only and sandbox-aware                                      #
# --------------------------------------------------------------------------- #

@pytest.fixture
def public_client(tmp_path, seeded):
    template = public._template_path()
    api = public.create_public_api(template=template, sandbox_dir=tmp_path / "sb")
    root = FastAPI()
    root.mount("/api", api)
    return TestClient(root, raise_server_exceptions=False), template


def test_executive_endpoints_are_read_only_in_public(public_client):
    client, template = public_client
    before = template.stat().st_mtime_ns
    s = {"X-Demo-Session": secrets.token_hex(16)}
    assert client.get("/api/web/executive").status_code == 200
    for qid in QIDS:
        assert client.get(f"/api/web/executive/{qid}").status_code == 200
        for method in ("post", "put", "patch", "delete"):
            assert getattr(client, method)(f"/api/web/executive/{qid}", headers=s).status_code == 403
    assert client.post("/api/analytics/ask", json={"question": "Where are opportunities getting stuck?"}).status_code == 200
    assert template.stat().st_mtime_ns == before


def test_one_visitors_sandbox_changes_only_their_own_answers(public_client):
    client, _ = public_client
    owner, other = secrets.token_hex(16), secrets.token_hex(16)
    draft = next(d for d in client.get("/api/web/drafts").json() if d["account_stage"] == "Research")
    h = {"X-Demo-Session": owner}
    assert client.post(f"/api/drafts/{draft['id']}/approve", headers=h).status_code == 200
    assert client.post(f"/api/accounts/{draft['account_id']}/mark_sent?draft_id={draft['id']}", headers=h).status_code == 200

    def contacted(headers):
        return client.get("/api/web/executive/stuck", headers=headers).json()["data"]["stage_counts"]["Contacted"]

    shared = contacted({})
    assert contacted(h) == shared + 1
    assert contacted({"X-Demo-Session": other}) == shared
