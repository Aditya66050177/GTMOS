"""Five executive questions answered with deterministic database queries.

Every number comes from the database through the existing engines:
* scores, tiers and fit/intent from the Score rows written by ScoringEngine,
* actions from RecommendationEngine.get_recommendation (the same call the app uses),
* per-signal status and points from signal_engine.signal_contributions,
* pipeline facts from Account.stage and pipeline Activity rows.

Nothing here changes data or calls an LLM. Each answer separates Observations
(read off the data) from Hypotheses (labelled interpretations). Pipeline activity
in the demo is a seeded simulation and every pipeline answer says so.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.timeutil import utc_now
from app.models import Account, Activity, ICPProfile, Product, Score, Signal
from app.schemas.executive import AccountItem, ExecutiveAnswer, ExecutiveQuestionRef, Hypothesis, Observation
from app.services.recommendation_engine import RecommendationEngine
from app.services.signal_engine import NEGATIVE_SOURCE, recency_status, signal_contributions

TIERS = ["Priority 1", "Priority 2", "Priority 3", "Low"]
OPEN_STAGES = ["Contacted", "Replied", "Meeting", "Opportunity"]
FUNNEL = ["Research", "Contacted", "Replied", "Meeting", "Opportunity", "Won"]
# Activity type that proves an account reached each stage.
STAGE_EVIDENCE = {"Contacted": "outreach_sent", "Replied": "reply_received", "Meeting": "meeting_held",
                  "Opportunity": "opportunity_created", "Won": "deal_won", "Lost": "deal_lost"}
PIPELINE_ACTIVITY_TYPES = set(STAGE_EVIDENCE.values()) | {"stage_change", "outreach_approved"}

STALL_DAYS = 14             # open-stage account with no pipeline activity for this long = stalled
HIGH_FIT = 70.0             # of 80, used only to pick "investigate next" candidates
WEAK_INTENT = 5.0
VERIFY_FIT = 60.0

DATA_PROVENANCE = {
    "accounts_and_signals": "Synthetic demonstration data (no real companies or research).",
    "pipeline": "Seeded 40-day simulation (scripts/seed_activity.py). Not real sales activity, replies or revenue.",
    "comparison_notes": "data/signals_demo_additions.csv adds labelled synthetic notes for two accounts.",
}
SOURCES = {
    "scores": "scores (fit components, intent_score, total_score, tier)",
    "signals": "signals (signal_type, strength, confidence, detected_at, evidence)",
    "actions": "RecommendationEngine.get_recommendation over scores + signals",
    "accounts": "accounts (name, stage)",
    "activities": "activities (pipeline activity types and timestamps)",
    "rejected": "activities of type rejected_signal (metadata.category, claimed_type)",
}


# --------------------------------------------------------------------------- #
# One pass over the database                                                   #
# --------------------------------------------------------------------------- #

@dataclass
class AccountView:
    account: Account
    score: Optional[Score]
    fit: Optional[float] = None
    intent: Optional[float] = None
    action: Optional[str] = None
    rule_id: Optional[str] = None
    signals: List[dict] = field(default_factory=list)       # positive signals with status + points
    rejected: List[dict] = field(default_factory=list)
    pipeline_acts: List[Activity] = field(default_factory=list)
    note_datasets: set = field(default_factory=set)

    @property
    def stage(self) -> str:
        return self.account.stage or "Research"

    @property
    def tier(self) -> Optional[str]:
        return self.score.tier if self.score else None

    def counted(self) -> List[dict]:
        return [s for s in self.signals if s["points"] > 0]

    def best_evidence(self) -> Optional[str]:
        best = max(self.counted(), key=lambda s: s["points"], default=None)
        return best["quote"] if best else None

    def item(self, why: List[str]) -> AccountItem:
        return AccountItem(
            id=self.account.id, name=self.account.name, stage=self.stage, tier=self.tier,
            total=round(self.score.total_score, 1) if self.score else None,
            fit=round(self.fit, 1) if self.fit is not None else None,
            intent=round(self.intent, 1) if self.intent is not None else None,
            action=self.action, rule_id=self.rule_id, why=why, evidence=self.best_evidence(),
            uses_synthetic_demo_additions="demo_addition" in self.note_datasets,
        )


@dataclass
class Snapshot:
    views: List[AccountView]
    data_quality: List[str]
    now: datetime

    @property
    def scored(self) -> List[AccountView]:
        return [v for v in self.views if v.score is not None]


def load_snapshot(db: Session, now: Optional[datetime] = None) -> Snapshot:
    now = now or utc_now()
    quality: List[str] = []
    product = db.query(Product).order_by(Product.id).first()
    icp = db.query(ICPProfile).filter_by(product_id=product.id).first() if product else None
    scores = {s.account_id: s for s in db.query(Score).filter_by(product_id=product.id).all()} if product else {}

    signals_by_acc: Dict[int, List[Signal]] = defaultdict(list)
    for sig in db.query(Signal).order_by(Signal.id).all():
        signals_by_acc[sig.account_id].append(sig)
    acts_by_acc: Dict[int, List[Activity]] = defaultdict(list)
    for act in db.query(Activity).order_by(Activity.id).all():
        acts_by_acc[act.account_id].append(act)

    rec_engine = RecommendationEngine()
    views: List[AccountView] = []
    missing_intent = 0
    for acc in db.query(Account).order_by(Account.id).all():
        score = scores.get(acc.id)
        view = AccountView(account=acc, score=score)
        sigs = signals_by_acc.get(acc.id, [])
        acts = acts_by_acc.get(acc.id, [])
        view.pipeline_acts = [a for a in acts if a.activity_type in PIPELINE_ACTIVITY_TYPES]
        view.rejected = [dict(a.activity_metadata or {}) for a in acts if a.activity_type == "rejected_signal"]
        view.note_datasets = {(a.activity_metadata or {}).get("dataset") for a in acts if a.activity_type == "research_note"}
        if score is not None:
            if score.intent_score is None:
                missing_intent += 1
            view.intent = score.intent_score or 0.0
            view.fit = (score.total_score or 0.0) - view.intent
            # Same timestamp logic as the explain endpoint: when intent was last computed.
            neg_times = [s.detected_at for s in sigs if s.source == NEGATIVE_SOURCE and s.detected_at]
            as_of = max([t for t in [score.created_at, *neg_times] if t], default=now)
            for c in signal_contributions(sigs, as_of):
                if c.signal.source == NEGATIVE_SOURCE or c.weight <= 0:
                    continue
                view.signals.append({
                    "type": c.signal_type, "points": c.points, "counted": c.counted,
                    "status": recency_status(c.days_old) if c.counted else "superseded",
                    "quote": c.signal.evidence if isinstance(c.signal.evidence, str) else None,
                })
            positives = [s for s in sigs if s.source != NEGATIVE_SOURCE]
            rec = rec_engine.get_recommendation(score, positives, icp)
            view.action, view.rule_id = rec.action, rec.rule_id
        views.append(view)

    unscored = sum(v.score is None for v in views)
    if unscored:
        quality.append(f"{unscored} account(s) have no score and are excluded from tier and action counts.")
    if missing_intent:
        quality.append(f"{missing_intent} score row(s) have no intent value; treated as 0.")
    if views and not product:
        quality.append("Accounts exist but no product/ICP is defined, so nothing is scored.")
    return Snapshot(views=views, data_quality=quality, now=now)


def _answer(qid: str, snap: Snapshot, summary: str, observations: List[str], hypotheses: List[str],
            sources: List[str], **extra) -> ExecutiveAnswer:
    return ExecutiveAnswer(
        question_id=qid, question=QUESTIONS[qid][0], summary=summary,
        observations=[Observation(text=t) for t in observations],
        hypotheses=[Hypothesis(text=t) for t in hypotheses],
        data_sources=[SOURCES[s] for s in sources], data_provenance=DATA_PROVENANCE,
        data_quality=snap.data_quality + extra.pop("extra_quality", []), **extra,
    )


def _empty(qid: str, snap: Snapshot, sources: List[str]) -> ExecutiveAnswer:
    total = len(snap.views)
    text = "No scored accounts in the database, so this question has no answer yet." if total == 0 else \
        f"{total} account(s) exist but none is scored, so this question has no answer yet."
    return _answer(qid, snap, text, [text], [], sources)


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


# --------------------------------------------------------------------------- #
# The five questions                                                           #
# --------------------------------------------------------------------------- #

def worth_pursuing(snap: Snapshot) -> ExecutiveAnswer:
    qid, sources = "worth-pursuing", ["scores", "signals", "actions", "accounts"]
    scored = snap.scored
    if not scored:
        return _empty(qid, snap, sources)
    actions = Counter(v.action for v in scored)
    pursue = sorted([v for v in scored if v.action in ("CONTACT", "PRIORITIZE") and v.stage not in ("Won", "Lost")],
                    key=lambda v: (-(v.score.total_score or 0), v.account.id))
    closed = sum(1 for v in scored if v.action in ("CONTACT", "PRIORITIZE") and v.stage in ("Won", "Lost"))
    items = [v.item([f"{v.tier}, intent {v.intent:.1f}/20 -> {v.action} ({v.rule_id})",
                     f"{_plural(len(v.counted()), 'counted signal')}"]) for v in pursue]
    obs = [
        f"{len(pursue)} of {len(scored)} scored accounts have a CONTACT or PRIORITIZE action and are not closed.",
        f"Actions across all scored accounts: " + ", ".join(f"{a} {actions.get(a, 0)}" for a in
                                                          ("CONTACT", "PRIORITIZE", "NURTURE", "RESEARCH", "DEPRIORITIZE")) + ".",
    ]
    if closed:
        obs.append(f"{closed} more CONTACT/PRIORITIZE account(s) are already Won or Lost in the simulated pipeline.")
    if pursue:
        obs.append(f"All {len(pursue)} have at least {min(len(v.counted()) for v in pursue)} counted buying signal(s); "
                   f"intent ranges {min(v.intent for v in pursue):.1f}-{max(v.intent for v in pursue):.1f} of 20.")
    hyp = []
    if pursue:
        hyp.append("These accounts combine ICP fit with verified, recent intent, so they are the most likely to respond. "
                   "This has not been validated against real reply or win data.")
    if len(pursue) < 10:
        hyp.append(f"With only {len(pursue)} account(s) ready to pursue, a small team likely has spare capacity; "
                   f"the 'investigate next' list is the natural place to look for more.")
    summary = (f"{_plural(len(pursue), 'account')} {'is' if len(pursue) == 1 else 'are'} worth pursuing now: "
               + (", ".join(v.account.name for v in pursue[:5]) + ("…" if len(pursue) > 5 else "") if pursue else "none") + ".")
    return _answer(qid, snap, summary, obs, hyp, sources, accounts=items,
                   data={"by_action": dict(actions), "count": len(pursue)},
                   selection_rules=["Action is CONTACT or PRIORITIZE (from the rule table)", "Stage is not Won or Lost"])


def nurture(snap: Snapshot) -> ExecutiveAnswer:
    qid, sources = "nurture", ["scores", "signals", "actions", "accounts"]
    scored = snap.scored
    if not scored:
        return _empty(qid, snap, sources)
    rows = sorted([v for v in scored if v.action == "NURTURE"], key=lambda v: (-(v.intent or 0), v.account.id))
    items = []
    obs = [f"{len(rows)} of {len(scored)} scored accounts have the NURTURE action."]
    by_rule = Counter(v.rule_id for v in rows)
    for rule, n in sorted(by_rule.items()):
        obs.append(f"{n} via rule {rule}.")
    for v in rows:
        why = [f"{v.tier}, intent {v.intent:.1f}/20 -> NURTURE ({v.rule_id})"]
        if v.rule_id == "P2_INTENT_5_TO_15":
            gap = 15.0 - v.intent
            why.append(f"{gap:.1f} intent points short of PRIORITIZE (needs >= 15 at Priority 2)")
        aging = [s for s in v.signals if s["status"] == "aging"]
        if aging:
            why.append(f"{_plural(len(aging), 'aging signal')} at half weight")
        items.append(v.item(why))
    p2 = [v for v in rows if v.rule_id == "P2_INTENT_5_TO_15"]
    if p2:
        obs.append(f"Priority 2 nurture accounts are {min(15 - v.intent for v in p2):.1f}-{max(15 - v.intent for v in p2):.1f} "
                   f"intent points short of the PRIORITIZE threshold (15).")
    hyp = []
    if rows:
        hyp.append("A new, current buying signal is what would move these accounts up; periodic re-research is likely "
                   "a better use of time than outreach now. Not tested against real outcomes.")
    summary = (f"{_plural(len(rows), 'account')} should be nurtured"
               + (f", led by {rows[0].account.name}." if rows else "; no account currently meets a NURTURE rule."))
    return _answer(qid, snap, summary, obs, hyp, sources, accounts=items,
                   data={"count": len(rows), "by_rule": dict(by_rule)},
                   selection_rules=["Action is NURTURE (P2 with 5 <= intent < 15, or P3 with intent >= 10)"])


def stuck(snap: Snapshot) -> ExecutiveAnswer:
    qid, sources = "stuck", ["accounts", "activities", "scores"]
    views = snap.views
    if not views:
        return _empty(qid, snap, sources)
    stage_counts = Counter(v.stage for v in views)
    order = FUNNEL + ["Lost"]

    # Stage reach: an account reached a stage if it is at or past it, or has the activity proving it.
    def reached(v: AccountView, stage: str) -> bool:
        if stage == "Research":            # every account starts in Research, including Lost ones
            return True
        if v.stage in FUNNEL and FUNNEL.index(v.stage) >= FUNNEL.index(stage):
            return True
        return STAGE_EVIDENCE.get(stage) in {a.activity_type for a in v.pipeline_acts}

    reach = {s: sum(reached(v, s) for v in views) for s in FUNNEL}
    conversions = []
    for a, b in zip(FUNNEL, FUNNEL[1:]):
        rate = round(100.0 * reach[b] / reach[a], 1) if reach[a] else None
        conversions.append({"from": a, "to": b, "from_count": reach[a], "to_count": reach[b], "rate_pct": rate})
    measurable = [c for c in conversions if c["rate_pct"] is not None and c["from"] != "Research"]
    worst = min(measurable, key=lambda c: c["rate_pct"], default=None)

    stalled, no_activity, inconsistent = [], [], []
    for v in views:
        acts = [a for a in v.pipeline_acts if a.timestamp]
        last = max((a.timestamp for a in acts), default=None)
        types = {a.activity_type for a in v.pipeline_acts}
        if v.stage in OPEN_STAGES:
            if last is None:
                no_activity.append(v)
            elif (snap.now - last).days >= STALL_DAYS:
                stalled.append((v, (snap.now - last).days))
        if v.stage in FUNNEL:
            ahead = [s for s in FUNNEL[FUNNEL.index(v.stage) + 1:] if STAGE_EVIDENCE.get(s) in types]
            if ahead:
                inconsistent.append(f"{v.account.name}: stage {v.stage} but has activity for {', '.join(ahead)}.")
        if v.stage in ("Won", "Lost") and STAGE_EVIDENCE[v.stage] not in types:
            inconsistent.append(f"{v.account.name}: stage {v.stage} with no {STAGE_EVIDENCE[v.stage]} activity recorded.")
        if v.stage not in order:
            inconsistent.append(f"{v.account.name}: unknown stage '{v.account.stage}'.")

    stalled.sort(key=lambda t: (-((t[0].score.total_score or 0) if t[0].score else 0), -t[1], t[0].account.id))
    by_stage = Counter(v.stage for v, _ in stalled)
    stalled_tiers = Counter((v.tier or "Unscored") for v, _ in stalled)
    obs = ["Stage counts: " + ", ".join(f"{s} {stage_counts.get(s, 0)}" for s in order) + "."]
    if worst:
        obs.append(f"Lowest stage conversion: {worst['from']} -> {worst['to']} at {worst['rate_pct']}% "
                   f"({worst['to_count']} of {worst['from_count']}).")
    obs.append(f"{len(stalled)} account(s) in an open stage have had no pipeline activity for {STALL_DAYS}+ days"
               + (": " + ", ".join(f"{s} {n}" for s, n in by_stage.most_common()) if stalled else "") + ".")
    if stalled:
        obs.append("Stalled accounts by tier: " + ", ".join(f"{t} {stalled_tiers[t]}" for t in TIERS + ["Unscored"]
                                                           if stalled_tiers.get(t)) + ".")
    if no_activity:
        obs.append(f"{len(no_activity)} account(s) are in an open stage with no pipeline activity recorded at all.")
    hyp = []
    if worst:
        hyp.append(f"In a real pipeline the weakest step ({worst['from']} -> {worst['to']}) would be the first place to look "
                   f"at messaging or qualification. Here it reflects the simulation's fixed rates, so it says nothing about real buyers.")
    low_stalled = stalled_tiers.get("Low", 0) + stalled_tiers.get("Priority 3", 0)
    if stalled and low_stalled:
        hyp.append(f"{low_stalled} of the stalled accounts are Priority 3 or Low; some of the stall may be the wrong accounts "
                   f"being worked rather than slow follow-up. In this demo that is an artefact of the simulation.")
    if stalled:
        hyp.append("Accounts silent for two weeks or more are the likeliest to be lost without a follow-up. "
                   "The 14-day threshold is a convention, not a measured benchmark.")
    summary = (f"Biggest drop-off: {worst['from']} -> {worst['to']} ({worst['rate_pct']}%); "
               f"{len(stalled)} open account(s) stalled {STALL_DAYS}+ days. Pipeline data is simulated."
               if worst else f"Not enough pipeline movement to measure conversion; {len(stalled)} stalled account(s). Pipeline data is simulated.")
    items = [v.item([f"In {v.stage} with no pipeline activity for {d} days"]) for v, d in stalled[:15]]
    items += [v.item([f"In {v.stage} with no pipeline activity recorded"]) for v in no_activity[:5]]
    return _answer(qid, snap, summary, obs, hyp, sources, accounts=items,
                   data={"stage_counts": {s: stage_counts.get(s, 0) for s in order}, "conversions": conversions,
                         "stalled_by_stage": dict(by_stage), "stall_days": STALL_DAYS},
                   selection_rules=[f"Stalled = stage in {OPEN_STAGES} and newest pipeline activity >= {STALL_DAYS} days old",
                                    "Reached a stage = current stage at or past it, or an activity proving it; every account has reached Research"],
                   extra_quality=inconsistent[:20] + ([f"…and {len(inconsistent) - 20} more."] if len(inconsistent) > 20 else []))


def signals_by_tier(snap: Snapshot) -> ExecutiveAnswer:
    qid, sources = "signals-by-tier", ["signals", "scores", "rejected"]
    scored = snap.scored
    if not scored:
        return _empty(qid, snap, sources)
    types = sorted({s["type"] for v in scored for s in v.signals} | {r.get("claimed_type") or r.get("type") or "unknown"
                                                                     for v in scored for r in v.rejected})
    matrix = {t: {tier: {"accounts_with_signal": 0, "accounts_where_it_counts": 0, "rejected_claims": 0}
                  for tier in TIERS} for t in types}
    tier_sizes = Counter(v.tier for v in scored)
    for v in scored:
        tier = v.tier if v.tier in TIERS else "Low"
        for t in {s["type"] for s in v.signals}:
            matrix[t][tier]["accounts_with_signal"] += 1
        for t in {s["type"] for s in v.counted()}:
            matrix[t][tier]["accounts_where_it_counts"] += 1
        for r in v.rejected:
            matrix[r.get("claimed_type") or r.get("type") or "unknown"][tier]["rejected_claims"] += 1

    def row_total(t, key):
        return sum(matrix[t][tier][key] for tier in TIERS)

    with_signal = [v for v in scored if v.signals]
    cancelled = [v for v in with_signal if not v.counted() and any(s["counted"] for s in v.signals)]
    penalised = [v for v in with_signal if v.counted() and (v.intent or 0) == 0]
    strong = sum(1 for v in scored if (v.intent or 0) >= 15)
    some = sum(1 for v in scored if (v.intent or 0) > 0)
    obs = [
        f"{len(with_signal)} of {len(scored)} scored accounts have at least one verified buying signal; "
        f"{some} have intent above 0 and {strong} have intent >= 15 of 20.",
        "Tier sizes: " + ", ".join(f"{t} {tier_sizes.get(t, 0)}" for t in TIERS) + ".",
    ]
    for t in types:
        present = row_total(t, "accounts_with_signal")
        if present:
            obs.append(f"{t}: on {present} account(s) (" + ", ".join(
                f"{tier} {matrix[t][tier]['accounts_with_signal']}" for tier in TIERS if matrix[t][tier]["accounts_with_signal"])
                + f"); adds points, before penalties, on {row_total(t, 'accounts_where_it_counts')}.")
    if cancelled:
        obs.append(f"{len(cancelled)} account(s) have a verified signal that adds no points: expired (over 180 days) "
                   f"or the newest signal of its type is expired.")
    if penalised:
        obs.append(f"{len(penalised)} account(s) have signal points that disqualifier penalties cancel completely (intent 0).")
    rej_total = sum(row_total(t, "rejected_claims") for t in types)
    if rej_total:
        obs.append(f"{rej_total} rejected claim(s) were recorded and counted for 0 points.")
    hyp = [
        "Read this as co-occurrence, not cause. Tiers partly depend on intent, and intent is built from these signals, "
        "so signals appearing in higher tiers is partly true by construction.",
    ]
    if any(row_total(t, "accounts_with_signal") and matrix[t]["Low"]["accounts_with_signal"] for t in types):
        hyp.append("Signals on Low-tier accounts are usually outweighed by poor fit and disqualifier penalties; "
                   "they may still be worth a glance if the ICP is too narrow.")
    summary = (f"{len(with_signal)} account(s) carry verified signals and {strong} show strong intent (>= 15/20); "
               f"see the signal-type x tier matrix.")
    return _answer(qid, snap, summary, obs, hyp, sources,
                   data={"tiers": TIERS, "matrix": matrix, "tier_sizes": {t: tier_sizes.get(t, 0) for t in TIERS},
                         "intent_bands": {"intent_0": len(scored) - some, "intent_above_0": some, "intent_ge_15": strong},
                         "signals_cancelled_by_penalties": len(penalised), "signals_expired_only": len(cancelled)},
                   selection_rules=["accounts_with_signal: at least one verified signal of the type, any recency",
                                    "accounts_where_it_counts: that signal adds points before disqualifier penalties (newest of its type, not expired)",
                                    "rejected_claims: negated, unsupported or ambiguous claims of that type (0 points)"])


def investigate_next(snap: Snapshot) -> ExecutiveAnswer:
    qid, sources = "investigate-next", ["scores", "signals", "actions", "accounts", "rejected"]
    scored = [v for v in snap.scored if v.stage not in ("Won", "Lost")]
    if not snap.scored:
        return _empty(qid, snap, sources)
    picked: Dict[int, List[str]] = {}
    for v in scored:
        why = []
        if (v.fit or 0) >= HIGH_FIT and (v.intent or 0) < WEAK_INTENT:
            why.append(f"High fit ({v.fit:.1f}/80) but weak intent ({v.intent:.1f}/20): look for a recent trigger")
        if (v.fit or 0) >= VERIFY_FIT and v.rejected:
            cats = sorted({r.get("category", "unsupported") for r in v.rejected})
            why.append(f"{_plural(len(v.rejected), 'rejected claim')} ({', '.join(cats)}): verify with a primary source")
        if v.tier in ("Priority 1", "Priority 2") and v.signals and not any(s["status"] == "current" for s in v.counted()):
            if any(s["status"] == "aging" for s in v.signals):
                why.append("Only aging evidence (half weight): refresh before outreach")
        if why:
            picked[v.account.id] = why
    ranked = sorted((v for v in scored if v.account.id in picked),
                    key=lambda v: (-len(picked[v.account.id]), -(v.fit or 0), v.account.id))[:10]
    counts = Counter()
    for v in scored:
        if v.account.id in picked:
            for w in picked[v.account.id]:
                counts[w.split(":")[0].split(" (")[0]] += 1
    obs = [f"{len(picked)} open account(s) match at least one investigation rule; the top {len(ranked)} are listed."]
    hf = sum(1 for v in scored if (v.fit or 0) >= HIGH_FIT and (v.intent or 0) < WEAK_INTENT)
    obs.append(f"{hf} open account(s) have fit >= {HIGH_FIT:.0f}/80 and intent < {WEAK_INTENT:.0f}/20.")
    rej = sum(1 for v in scored if (v.fit or 0) >= VERIFY_FIT and v.rejected)
    obs.append(f"{rej} open account(s) with fit >= {VERIFY_FIT:.0f}/80 have rejected claims worth verifying.")
    hyp = []
    if hf:
        hyp.append("High-fit, low-intent accounts are where one confirmed trigger would change the recommendation the most; "
                   "a short research pass may be worth more than cold outreach. Not validated.")
    if rej:
        hyp.append("A rejected rumour is not evidence of no need; confirming or ruling it out with a primary source "
                   "settles the account either way.")
    summary = (f"Investigate {_plural(len(ranked), 'account')} next"
               + (f", starting with {ranked[0].account.name}." if ranked else "; none matches the investigation rules."))
    return _answer(qid, snap, summary, obs, hyp, sources,
                   accounts=[v.item(picked[v.account.id]) for v in ranked],
                   data={"matching": len(picked), "high_fit_weak_intent": hf, "rejected_to_verify": rej},
                   selection_rules=[f"High fit, weak intent: fit >= {HIGH_FIT:.0f}/80 and intent < {WEAK_INTENT:.0f}/20",
                                    f"Verify: fit >= {VERIFY_FIT:.0f}/80 and at least one rejected claim",
                                    "Refresh: Priority 1/2 whose counted evidence is aging, not current",
                                    "Excludes Won/Lost; ranked by number of rules matched, then fit",
                                    "These thresholds select examples for review; they are not scoring rules"])


QUESTIONS: Dict[str, tuple] = {
    "worth-pursuing": ("Which accounts are worth pursuing?", worth_pursuing),
    "nurture": ("Which accounts should be nurtured?", nurture),
    "stuck": ("Where are opportunities getting stuck?", stuck),
    "signals-by-tier": ("Which buying signals appear across different priority tiers?", signals_by_tier),
    "investigate-next": ("Which accounts should the team investigate next?", investigate_next),
}
ANALYST_FUNCTIONS = {
    "get_worth_pursuing": "worth-pursuing",
    "get_nurture_accounts": "nurture",
    "get_stuck_opportunities": "stuck",
    "get_signal_tier_matrix": "signals-by-tier",
    "get_investigate_next": "investigate-next",
}


def answer(db: Session, question_id: str, now: Optional[datetime] = None) -> Optional[ExecutiveAnswer]:
    entry = QUESTIONS.get(question_id)
    if entry is None:
        return None
    fn: Callable[[Snapshot], ExecutiveAnswer] = entry[1]
    return fn(load_snapshot(db, now))


def question_list() -> List[ExecutiveQuestionRef]:
    return [ExecutiveQuestionRef(id=q, question=t, endpoint=f"/api/web/executive/{q}") for q, (t, _f) in QUESTIONS.items()]
