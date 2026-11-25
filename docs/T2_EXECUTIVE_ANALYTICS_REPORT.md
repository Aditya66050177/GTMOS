# T2 — Executive analytics and analyst: report

Branch `claude/modest-darwin-atz53w`, 2026-11-25. Not pushed, not deployed.

**Summary.** GTMOS answers five executive questions with deterministic database queries.
Each answer separates **Observations** (read off database values) from **Hypotheses**
(labelled interpretations), names its data sources and selection rules, and reports data
quality problems instead of hiding them. Pipeline answers say plainly that the pipeline is
a simulation. The analyst can route to these five questions, but only by picking a name
from a fixed allowlist: no generated SQL, no arbitrary execution, and no LLM-written text
in executive answers. Scoring, evidence and recommendation rules are unchanged; the T1
golden-baseline test still passes.

---

## 1. Endpoints (read-only, behind the public guard)

| Endpoint | Returns |
|---|---|
| `GET /api/web/executive` | The five questions and their endpoints |
| `GET /api/web/executive/worth-pursuing` | Which accounts are worth pursuing? |
| `GET /api/web/executive/nurture` | Which accounts should be nurtured? |
| `GET /api/web/executive/stuck` | Where are opportunities getting stuck? |
| `GET /api/web/executive/signals-by-tier` | Which buying signals appear across priority tiers? (signal type × tier matrix) |
| `GET /api/web/executive/investigate-next` | Which accounts should the team investigate next? |
| `POST /api/analytics/ask` (existing) | Now also routes to the five questions |

Any method other than GET on `/web/executive/*` returns 403 from the guard (tested, also over
real HTTP). Each request reads the caller's own sandbox if it has one, otherwise shared data.
An unknown question id returns 404.

### Answer shape (every question)

```json
{
  "question_id": "worth-pursuing",
  "question": "Which accounts are worth pursuing?",
  "summary": "3 accounts are worth pursuing now: Fintech Pulse Inc, Company 4 B2B, Company 36 B2B.",
  "observations": [{"text": "3 of 150 scored accounts have a CONTACT or PRIORITIZE action and are not closed.", "value": null}, "..."],
  "hypotheses":  [{"text": "These accounts combine ICP fit with verified, recent intent, so they are the most likely to respond. This has not been validated against real reply or win data.",
                   "label": "Hypothesis: not established by the data"}],
  "accounts": [{"id": 41, "name": "Company 36 B2B", "stage": "Replied", "tier": "Priority 2", "total": 77.0,
                "fit": 57.0, "intent": 20.0, "action": "PRIORITIZE", "rule_id": "P2_INTENT_GE_15",
                "why": ["Priority 2, intent 20.0/20 -> PRIORITIZE (P2_INTENT_GE_15)", "2 counted signals"],
                "evidence": "Company 36 B2B is hiring 12 new support agents to keep up with a growing customer base",
                "uses_synthetic_demo_additions": true}],
  "data": {"by_action": {"CONTACT": 2, "PRIORITIZE": 1, "NURTURE": 5, "RESEARCH": 23, "DEPRIORITIZE": 119}, "count": 3},
  "selection_rules": ["Action is CONTACT or PRIORITIZE (from the rule table)", "Stage is not Won or Lost"],
  "data_sources": ["scores (...)", "signals (...)", "RecommendationEngine.get_recommendation over scores + signals", "accounts (name, stage)"],
  "data_provenance": {
    "accounts_and_signals": "Synthetic demonstration data (no real companies or research).",
    "pipeline": "Seeded 40-day simulation (scripts/seed_activity.py). Not real sales activity, replies or revenue.",
    "comparison_notes": "data/signals_demo_additions.csv adds labelled synthetic notes for two accounts."
  },
  "data_quality": [],
  "generated_by": "Deterministic database query (no LLM)"
}
```

## 2. The five queries

All five build one snapshot (`load_snapshot`) from the database, using the same engines as
the rest of the app:
- Fit and intent come from the `Score` rows written by the scoring engine (fit = total − intent).
- The action comes from `RecommendationEngine.get_recommendation` with the account's positive signals.
- Per-signal status and points come from `signal_contributions()` at the account's scoring time (as in T1).
- Pipeline facts come from `Account.stage` and pipeline-type `Activity` rows.

| Question | Query | Demo answer (with demo additions) |
|---|---|---|
| **Worth pursuing** | Action CONTACT or PRIORITIZE, stage not Won/Lost; ranked by total | 3 accounts: Fintech Pulse Inc (P1, CONTACT), Company 4 B2B (P1, CONTACT), Company 36 B2B (P2, PRIORITIZE, flagged as using synthetic notes). Actions overall: CONTACT 2, PRIORITIZE 1, NURTURE 5, RESEARCH 23, DEPRIORITIZE 119 |
| **Nurture** | Action NURTURE; shows the rule and, for P2, the points short of PRIORITIZE (15) | 5 accounts, all via `P2_INTENT_5_TO_15`, 0.6–8.9 points short; led by Company 31 Software |
| **Stuck** | Stage counts; stage-to-stage conversion (an account has reached a stage if it is at or past it, or has the activity proving it); stalled = open stage with no pipeline activity for 14+ days; inconsistencies | Weakest step Contacted → Replied, 42.7% (32 of 75). 42 open accounts stalled 14+ days (Contacted 28, Replied 12, Meeting 2). **33 of the 42 are Priority 3 or Low.** Conversions match the existing `/analytics/funnel` exactly (tested). Labelled simulated |
| **Signals by tier** | Signal type × tier: accounts with the signal, accounts where it adds points (before penalties), rejected claims of that type; intent bands | 41 of 150 accounts carry a verified signal; 13 have intent > 0; **2** have intent ≥ 15. **23 accounts have signal points that disqualifier penalties cancel completely.** 5 have only expired signals. 10 rejected claims, 0 points |
| **Investigate next** | Open accounts matching: fit ≥ 70/80 and intent < 5 (find a trigger); fit ≥ 60 with rejected claims (verify); P1/P2 whose counted evidence is aging (refresh). Ranked by rules matched, then fit; top 10 | 31 match; top is Company 37 Cloud (fit 80, intent 0, one unsupported rumour). 29 high-fit/weak-intent accounts |

### Signal type × tier (cells: accounts with signal / accounts where it adds points / rejected claims)

| Signal type | Priority 1 | Priority 2 | Priority 3 | Low |
|---|---|---|---|---|
| executive_change | 0/0/0 | 2/1/0 | 2/1/0 | 4/3/0 |
| funding | 0/0/0 | 2/2/1 | 1/0/0 | 4/4/0 |
| international_expansion | 1/1/0 | 0/0/0 | 2/1/1 | 5/5/0 |
| product_launch | 1/1/0 | 4/4/0 | 1/1/0 | 4/4/0 |
| support_hiring | 1/1/0 | 3/3/3 | 1/1/2 | 5/5/3 |

Tier sizes: Priority 1: 2, Priority 2: 29, Priority 3: 19, Low: 100. Every matrix cell is
tested against a direct count of `signals` joined to `scores`.

The answer's first hypothesis is deliberate: *"Read this as co-occurrence, not cause. Tiers
partly depend on intent, and intent is built from these signals, so signals appearing in
higher tiers is partly true by construction."*

## 3. Observations vs hypotheses

- **Observations** restate database values: counts, ranges and names. A test rejects
  speculative wording in any observation (*likely, probably, suggest, may, might, could,
  perhaps, because*).
- **Hypotheses** carry the label `"Hypothesis: not established by the data"` and say what
  they are not based on (e.g. "Not validated against real reply or win data"; "The 14-day
  threshold is a convention, not a measured benchmark"). None claims causation or impact.
- Selection thresholds (14 days, fit ≥ 70/60, intent < 5) are listed in `selection_rules`
  and described as conventions for picking examples. **They are not scoring rules.**

## 4. Synthetic vs actual

- Every answer includes `data_provenance`. Accounts and signals are synthetic; the
  **pipeline is a seeded 40-day simulation, not real sales activity, replies or revenue.**
- The stuck answer's summary ends with "Pipeline data is simulated", and its hypothesis says
  the weakest step "reflects the simulation's fixed rates, so it says nothing about real buyers".
- Accounts whose evidence uses the labelled synthetic notes have
  `uses_synthetic_demo_additions: true` (Company 36 B2B).
- `/analytics/funnel` and `/analytics/trends` now include
  `data_label: "Simulated pipeline: …not real sales outcomes."` (an extra field; existing
  consumers are unaffected).

## 5. Analyst changes

| Before | After |
|---|---|
| 6 fixed functions | 11 fixed functions: the 6 plus `get_worth_pursuing`, `get_nurture_accounts`, `get_stuck_opportunities`, `get_signal_tier_matrix`, `get_investigate_next` |
| Free-text `explanation` only | Also `observations`, `hypotheses`, `data_label`, `generated_by` (extra fields) |

**Safety model:**
- The routing model (mock keywords, or Gemini when run locally in live mode) returns only a
  function **name**. A name outside the allowlist becomes `unknown` with empty data. Tested
  with `"DROP TABLE accounts"`, `"SELECT * FROM scores"` and others; the database is untouched.
- `parameters` from the router are ignored, so there's nothing to inject.
- Executive answers are assembled entirely by code. A test makes the scripted LLM return a
  fabricated explanation ("revenue grew 300%") and checks it appears nowhere in the answer.
- For the six legacy functions the LLM may still word the `explanation`, but `observations`
  are always computed from the returned data (tested: correct even when the LLM text is wrong).
- The public demo stays offline (mock) regardless of configuration (Part A tests).

**Mock routing** checks the new, specific phrases first ("investigate", "this week", "high
fit", "weak intent", "nurture", "stuck", "stall", "bottleneck", "weakness", "signal" + "tier",
"strong evidence", "worth pursuing", "strongest accounts"…), then the original rules. All 10
original routing cases still pass, plus 10 new ones, including your five example questions.

## 6. Files changed

| File | Change |
|---|---|
| `app/services/executive_analytics.py` | New: snapshot loader and the five deterministic questions |
| `app/schemas/executive.py` | New: `ExecutiveAnswer`, `Observation`, `Hypothesis`, `AccountItem` |
| `app/api/routes/web.py` | `GET /web/executive`, `GET /web/executive/{question_id}` |
| `app/services/analyst_service.py` | Routes the 5 new functions to the service; deterministic observations for legacy answers |
| `app/schemas/analytics.py` | `data_label` on funnel/trends; analyst response gains observations/hypotheses/data_label/generated_by |
| `app/ai/prompts.py` | Router allowlist lists the 5 new functions |
| `app/ai/llm.py` | Mock router keywords for the new functions (checked first) |
| `app/ai/mock_analyst.py` | `describe(func, data)` extracted so observations can reuse it |
| `tests/test_executive_analytics.py` | New: 43 tests |

No scoring, signal, evidence, recommendation, tier or seeding code changed.

## 7. Tests

| Area | Tests |
|---|---|
| Structure | All 5 answers have observations, sources, provenance; hypotheses labelled; no speculative words in observations; deterministic across calls; unknown id 404 |
| Grounding | Worth-pursuing and nurture equal an independent filter over `/web/accounts`; stage counts equal a direct `accounts` count; conversions equal `/analytics/funnel`; every matrix cell equals a direct signals × scores count; intent bands equal direct score counts; investigate-next items satisfy their stated rules |
| Synthetic labelling | Funnel/trends `data_label`; stuck summary and provenance say simulated; synthetic flag only on Company 36 |
| Empty database | All 5 questions return a clear "No scored accounts" answer, with no hypotheses |
| Missing values | Accounts but no product (reported in `data_quality`); null intent (treated as 0 and reported); null signal strength, confidence, date and evidence; null activity timestamp; null stage |
| Unusual distributions | All accounts Low in a single stage (0 to pursue, empty nurture, matrix tier sizes, "no pipeline activity recorded"); a single strong account |
| Inconsistent pipeline | Stage behind recorded activity, Won with no `deal_won`, unknown stage `Negotiation`, a 30-day silent Replied account — all flagged in `data_quality` or listed as stalled, nothing hidden or crashing |
| Analyst | 10 routing cases; allowlist cannot be escaped; router parameters ignored; no LLM text in executive answers; legacy observations stay data-grounded |
| Public API | GET 200 and other methods 403 for every question; template database file unchanged; one visitor's logged outreach changes their own stuck counts (+1 Contacted) and nobody else's |

**Results:**

| Run | Result |
|---|---|
| Full backend suite | **336 passed** |
| `tests/test_executive_analytics.py` | 43 passed |
| T1 golden-baseline test | passes (scores, tiers, actions unchanged) |
| Frontend production build | passes |
| Evaluation | 57.0% tier accuracy (unchanged) |
| Real server, runtime-only, `VERCEL=1` | smoke 13/13; all 5 questions answered; `POST /api/web/executive/stuck` → 403; analyst routes "What should our sales team investigate this week?" to `get_investigate_next` |

## 8. Limitations

1. **The pipeline is simulated.** Stalls, conversions and stage counts describe
   `scripts/seed_activity.py`, not buyers. Real use needs real activity logging.
2. **Thresholds are conventions** (14-day stall, fit ≥ 70/60, intent < 5). They pick
   examples for review; they weren't tuned on outcomes.
3. **"Investigate next" is a heuristic list**, ranked by number of rules matched, then fit.
   It isn't a predicted-value model.
4. **The signal × tier matrix is circular by design**, since intent feeds the tier.
   The answer says so; use it to see coverage, not effect.
5. **Mock routing is keyword-based.** Paraphrases outside the keyword lists return
   `unknown` (safe, but unhelpful). Live-mode routing is not evaluated and is never used publicly.
6. **Stage reach is inferred** from current stage plus activity types; inconsistent records
   are reported, not repaired.
7. **One product.** Answers use the first product's scores.
8. **No UI yet.** These endpoints are API-only until T4/T5.
9. **Underlying model limits are unchanged:** 57% tier accuracy, 0% Priority 2 recall,
   disqualifiers counted in both fit and intent (see `docs/T1_EXPLAINABILITY_REPORT.md`).

## 9. Git state

T2 is committed locally as one commit after this report. Nothing pushed, nothing deployed.
