# T1 — Explainability API: report

Branch `claude/modest-darwin-atz53w`, 2026-11-25. Not pushed, not deployed.

**Summary.** GTMOS can now explain every account in two separate numbers, **fit** (/80) and
**intent** (/20). It shows exactly which signals and penalties make up intent, and which
rejected claims were read but not counted. It also names the rule that chose the action.
Every number is read from, or recomputed by, the existing engine functions, and the API
checks its own recomputation against the stored score: it matches for all 150 accounts.
Scoring rules, priority tiers and the action table are unchanged. Two existing
problems surfaced and are documented below rather than hidden: a date-anchoring
non-determinism (fixed in the demo data layer), and the evaluation weaknesses
(unchanged: 57% tier accuracy, 0% Priority 2 recall).

---

## 1. What the engine does (inspected before any change)

| Concept | Where | Rule (unchanged) |
|---|---|---|
| Fit | `ScoringEngine.compute_score` | ICP fit /30 (industry 20/10/0 + pain-point overlap up to 10) · Company fit /20 (size in range 20, within 25% 10, else 0; an exclusion match subtracts 20) · Technology fit /15 (overlap share × 15 × 1.5, capped) · Geography /15 (match 15, region 8, else 0). **Fit = sum of the four, max 80** |
| Intent | `SignalEngine.calculate_intent` → `score_signals` | Newest signal per type counts. Points = **weight × strength × confidence × decay**. Sum, then clamp to 0–20 |
| Weights | `signal_config.SIGNAL_WEIGHTS` | support_hiring 20, funding 15, product_launch 15, relevant_technology 15, international_expansion 10, rapid_growth 10, executive_change 5; disqualifiers too_small −20, wrong_geography −20, wrong_industry −30, no_use_case −30 |
| Strength / confidence | Set by the extractor per signal | e.g. support_hiring 0.8 / 0.9 |
| Recency decay | `recency_decay` | ≤ 90 days 1.0 (**current**) · 91–180 days 0.5 (**aging**) · > 180 days 0.0 (**expired**) |
| Disqualification | `derive_negative_signals` | Too small, wrong industry, wrong geography and exclusion matches become negative-weight signals inside intent (and size/industry/geography also lose fit points) |
| Tier | `_tier` | Total ≥ 90 P1 · ≥ 75 P2 · ≥ 50 P3 · else Low |
| Action | `RecommendationEngine.get_recommendation` | P1: intent ≥ 10 CONTACT, else RESEARCH · P2: ≥ 15 PRIORITIZE, 5–15 NURTURE, < 5 RESEARCH · P3: ≥ 10 NURTURE, else DEPRIORITIZE · Low: DEPRIORITIZE |

## 2. Files changed

| File | Change | Affects scores? |
|---|---|---|
| `app/services/signal_engine.py` | Decay thresholds are named constants; new `recency_status()` and `signal_contributions()`. `score_signals()` now **sums `signal_contributions()`**, so there is one implementation of the formula | No (byte-identical snapshot, §7) |
| `app/services/scoring_engine.py` | `TIER_THRESHOLDS` constant used by `_tier()`; `REASON_COMPONENT` maps each reason to its component | No |
| `app/services/recommendation_engine.py` | `RecommendationResult.rule_id` records which branch fired; `ACTION_RULES` names the branches | No |
| `app/ai/mock_signals.py` | `analyze_note()` returns signals **and** rejected claims (negated / unsupported / ambiguous). Accept/reject decisions unchanged, except that **"frozen"** is now a negation cue | No baseline effect (golden test) |
| `app/schemas/signal.py`, `app/ai/llm.py`, `app/ai/prompts.py` | `SignalListSchema.rejected` (optional, default empty, so older LLM output still validates); mock returns it; live prompt asks for it | No |
| `app/services/research_engine.py` | Stores each note as a `research_note` activity (text, source, date, dataset, label, resulting signal ids) and each rejection as a `rejected_signal` activity with `points: 0`. Re-ingesting an identical note records nothing new. **Date anchoring is now exact** (§6). `extract_signals_from_csv` accepts an explicit `shift` and `dataset` | Only the anchoring fix (§6) |
| `app/db/demo_seed.py` | Loads `data/signals_demo_additions.csv` after the baseline, with the baseline's date shift. `include_demo_additions=False` rebuilds the pure baseline | Only for the comparison account (§5) |
| `app/schemas/explain.py` | New response schemas | — |
| `app/services/explainability.py` | Builds explanations from stored data and engine functions | — |
| `app/api/routes/web.py` | 3 read-only endpoints; playground response gains a `rejected` list | — |
| `data/signals_demo_additions.csv` | 3 labelled synthetic notes | §5 |
| `tests/test_explainability.py`, `tests/fixtures/baseline_outcomes.json` | 36 regression tests and the golden baseline | — |
| `tests/test_web_api.py` | Playground test also checks rejected claims | — |

## 3. New endpoints

All are `GET`, read-only, and go through the public guard (any other method returns 403,
tested). Each reads the caller's own sandbox if one exists, otherwise shared data.

| Endpoint | Purpose |
|---|---|
| `GET /api/web/accounts/{id}/explain` | Full explanation of one account |
| `GET /api/web/compare?ids=36,37` | 2–4 explanations plus deterministic observations. 422 for fewer than 2, more than 4, duplicates or non-integers; 404 for unknown or unscored ids |
| `GET /api/web/comparisons/featured` | Suggested comparisons chosen by stated rules from current data (no hard-coded ids) |

### Example: `GET /api/web/compare?ids=41,42` (real response, abridged)

```json
{
  "accounts": [{
    "account": {"id": 41, "name": "Company 36 B2B", "industry": "B2B SaaS", "employee_count": 378, "country": "UK", "stage": "Replied"},
    "data_label": "Synthetic demonstration data. No real companies, people or research.",
    "fit": {"score": 57.0, "max_score": 80.0, "meaning": "How closely the company resembles the ideal customer profile: ...",
            "components": [{"name": "ICP Fit", "score": 20.0, "max_score": 30.0, "reasons": ["..."]},
                           {"name": "Company Fit", "score": 20.0, "max_score": 20.0, "reasons": ["..."]},
                           {"name": "Technology Fit", "score": 9.0, "max_score": 15.0, "reasons": ["..."]},
                           {"name": "Geography Fit", "score": 8.0, "max_score": 15.0, "reasons": ["..."]}]},
    "intent": {"score": 20.0, "max_score": 20.0, "raw_total": 26.55, "clamped": true,
               "recomputed_score": 20.0, "matches_stored_score": true, "as_of": "2026-11-25T09:05:59",
               "buying_signals": [{
                 "signal_id": 42, "signal_type": "support_hiring", "label": "Support hiring",
                 "status": "current", "counted": true, "source": "Job Board", "days_old": 12,
                 "quote": "Company 36 B2B is hiring 12 new support agents to keep up with a growing customer base",
                 "source_sentence": "Company 36 B2B is hiring 12 new support agents to keep up with a growing customer base.",
                 "weight": 20.0, "strength": 0.8, "confidence": 0.9, "decay": 1.0, "points": 14.4,
                 "why_it_matters": "Hiring support staff suggests ticket volume is growing faster than the team."}, "..."],
               "disqualifiers": [],
               "recency_rules": {"current_max_days": 90, "aging_max_days": 180, "aging_decay": 0.5,
                                 "formula": "points = weight x strength x confidence x decay; newest signal per type counts; intent = clamp(sum, 0, 20)"}},
    "total": {"total": 77.0, "max_score": 100.0, "tier": "Priority 2", "rule": "total 77.0 is in 75-89.9 -> Priority 2"},
    "recommendation": {"action": "PRIORITIZE", "rule_id": "P2_INTENT_GE_15", "rule": "Priority 2 and intent >= 15 -> PRIORITIZE",
                       "reason": "Priority 2 account with very high intent. Prioritize for immediate outreach.",
                       "suggested_persona": "Chief Revenue Officer", "suggested_angle": "post-funding growth and tooling"},
    "rejected_evidence": [{"sentence": "We are not hiring right now", "category": "negated", "...": "...", "points": 0.0}],
    "evidence_summary": {"buying_signals": 2, "counted": 2, "current": 2, "aging": 0, "expired": 0, "superseded": 0, "disqualifiers": 0, "rejected": 1},
    "includes_synthetic_demo_additions": true
  }, {"account": {"name": "Company 37 Cloud"}, "fit": {"score": 80.0}, "intent": {"score": 0.0},
      "recommendation": {"action": "RESEARCH", "rule": "Priority 2 and intent < 5 -> RESEARCH"},
      "rejected_evidence": [{"sentence": "Rumours suggest Company 37 Cloud is preparing a new funding round",
                             "category": "unsupported", "reason": "Hearsay, not a confirmed fact: 'rumour'", "points": 0.0}]}],
  "observations": [
    "Company 37 Cloud has higher fit (80.0 vs 57.0 of 80).",
    "Company 36 B2B has stronger intent (20.0 vs 0.0 of 20), from 2 counted signal(s) vs 0.",
    "Both are Priority 2, but the actions differ: Company 36 B2B -> PRIORITIZE (Priority 2 and intent >= 15 -> PRIORITIZE); Company 37 Cloud -> RESEARCH (Priority 2 and intent < 5 -> RESEARCH). Within a tier, intent decides the action.",
    "Company 36 B2B: 1 rejected claim(s) (negated) counted for 0 points.",
    "Company 37 Cloud: 1 rejected claim(s) (unsupported) counted for 0 points."
  ]
}
```

### Example: Acme Technologies, `GET /api/web/accounts/1/explain` (abridged)

```json
{
  "fit": {"score": 69.5, "components": [{"name": "Technology Fit", "score": 4.5, "max_score": 15.0,
          "reasons": [{"rule": "Technology Stack", "met": true, "text": "Matching techs: ['zendesk']", "points": 4.5}]}, "..."]},
  "intent": {"score": 0.0, "buying_signals": [], "disqualifiers": []},
  "recommendation": {"action": "DEPRIORITIZE", "rule_id": "P3_INTENT_LT_10", "rule": "Priority 3 and intent < 10 -> DEPRIORITIZE"},
  "rejected_evidence": [
    {"sentence": "Acme Technologies is looking into expanding its horizons", "category": "ambiguous",
     "reason": "Speculative wording ('looking into'); no concrete event stated", "claimed_type": "international_expansion",
     "source": "Tech Blog", "dataset": "baseline", "points": 0.0},
    {"sentence": "Rumors suggested Acme was hiring for a massive support team expansion, but their CEO recently confirmed a hiring freeze for all non-engineering roles",
     "category": "negated", "reason": "Hearsay ('rumor') contradicted by: 'freeze'", "claimed_type": "support_hiring",
     "source": "News Article", "dataset": "baseline", "points": 0.0}]
}
```

### Example: `GET /api/web/comparisons/featured`

```json
[{"title": "Strong intent vs strong fit",
  "selection_rule": "Highest-intent account with fit < 70 and intent >= 15, vs highest-fit account with fit >= 75 and intent = 0",
  "account_ids": [41, 42]},
 {"title": "Why a near-perfect fit is not called first",
  "selection_rule": "Top-scoring account vs Acme Technologies (fit 69.5, intent 0.0)",
  "account_ids": [3, 1]}]
```

(The fit thresholds 75 and 70 here are demo selection conventions for picking examples, not scoring rules.)

## 4. How the numbers are produced

**Fit** comes from the four stored component scores in `Score.reasoning` (written by
`compute_score`), with each reason grouped under its component. `fit.score` is their sum;
`fit + intent = total` within the engine's 0.1 rounding (tested for all 150 accounts).

**Intent** is recomputed with `signal_contributions(signals, as_of)`, the function
`score_signals` itself sums, at `as_of`, the moment the account was last scored. That is the
newest disqualifier timestamp (those rows are rewritten at each scoring), or else the score
row's creation time. `matches_stored_score` compares the recomputation with the stored intent.

**Recency states from real demo data:**

| Status | Example | days_old | weight × strength × confidence × decay | points |
|---|---|---|---|---|
| current | Fintech Pulse, product launch | 10 | 15 × 0.7 × 0.8 × 1.0 | 8.4 |
| aging | Company 116 Software, funding | 164 | 15 × 0.9 × 0.9 × 0.5 | 6.075 |
| expired | Company 124 B2B, executive change | 181 | 5 × 0.6 × 0.8 × 0.0 | 0.0 |
| superseded | older duplicate of a type | — | not counted | 0.0 |
| disqualifier | Company 30 Cloud, too small | 0 | −20 × 1 × 1 × 1 | −20.0 |

Company 36's raw total is 14.4 + 12.15 = 26.55, clamped to 20 (`clamped: true`).

**Source sentence vs quote.** `quote` is the evidence stored on the signal. `source_sentence`
is the sentence of the recorded research note that contains the quote; it is `null` if the
note was not recorded (data ingested before T1, or signals created another way).

**Why it matters** is a fixed, per-type product hypothesis, labelled as such in the schema.
It is not generated and not presented as a fact.

## 5. Rejected evidence

| Category | Meaning | Example |
|---|---|---|
| `negated` | The claim is explicitly contradicted | "not currently hiring", "hiring freeze", "has frozen hiring", "denied" |
| `unsupported` | Hearsay, or the quoted evidence was not found in the source text | "Rumours suggest … a new funding round"; an LLM quote absent from the note |
| `ambiguous` | Speculative wording about a signal topic, no concrete event | "is looking into expanding", "might …" |

Stored as `rejected_signal` activities with the sentence, category, reason, claimed type,
source, date, dataset, a link to the note, and **`points: 0.0`**. They never enter
`signal_contributions` (they aren't Signal rows), so they cannot affect intent (tested:
an account with only rejected claims keeps 0 signals and 0 intent). Sentences with no
buying-signal topic at all ("gave away branded pens") are not claims and are not recorded.

## 6. Determinism fix found while building the golden baseline

Demo note dates were shifted by **whole days**, keeping the original 14:07 UTC time. So the
age of the note dated 181 days back (Company 124 B2B, "Just hired a new CRO") read as 180
days before 14:07 UTC and 181 after. Its decay flipped between 0.5 and 0.0 with the time of
day, and with it the pipeline simulation. The shift is now **exact**, so every note's age
equals its age in the CSV. This is a change in demo-data preparation, not a scoring rule.

Effect versus a run at 08:55 UTC (before the fix):

| Account | Before | After |
|---|---|---|
| Company 124 B2B | intent 1.2, total 81.2, P2, RESEARCH, stage Won | intent 0.0, total 80.0, P2, RESEARCH, stage Meeting |
| Company 11 Software | stage Opportunity | stage Won (pipeline simulation only) |
| Company 48 B2B | stage Meeting | stage Opportunity (pipeline simulation only) |

All other accounts, every tier, every action and all 6 drafts were identical. The fixed
version is the golden baseline (`tests/fixtures/baseline_outcomes.json`).

## 7. Synthetic comparison data

`data/signals_demo_additions.csv`. The baseline `data/signals.csv` and the evaluation data
are untouched (tested). Each row is labelled `SYNTHETIC DEMO ADDITION: …`, and the label and
`dataset: "demo_addition"` are stored with the note's provenance and returned by the API
(`includes_synthetic_demo_additions`).

| Account | Note | Engine result |
|---|---|---|
| Company 36 B2B | "…is hiring 12 new support agents…" (Job Board) | support_hiring, current, 14.4 pts |
| Company 36 B2B | "…raised a $25M Series B funding round…" (Press Release) | funding, current, 12.15 pts |
| Company 37 Cloud | "Rumours suggest … preparing a new funding round." | Rejected as **unsupported**, 0 pts |

The scoring engine, unchanged, then produces the intended contrast:

| | Fit /80 | Intent /20 | Total | Tier | Action (rule) |
|---|---|---|---|---|---|
| Company 36 B2B (moderate fit, strong recent intent) | 57.0 | 20.0 | 77.0 | Priority 2 | **PRIORITIZE** (P2, intent ≥ 15) |
| Company 37 Cloud (high fit, only a rumour) | 80.0 | 0.0 | 80.0 | Priority 2 | **RESEARCH** (P2, intent < 5) |

With additions enabled, the only score, tier or action that changes is Company 36's
(57.0 P3 DEPRIORITIZE → 77.0 P2 PRIORITIZE). Two simulated pipeline stages also move
(Acme Replied → Contacted, Company 36 Contacted → Replied), because the simulation ranks
accounts by score. `reset_demo_database(include_demo_additions=False)` reproduces the
baseline exactly.

## 8. Confirmation: rules and outcomes unchanged

- No weights, thresholds, tiers or action rows were changed. The refactors (contribution
  function, tier constants, rule ids) were verified by a byte-identical 150-account
  snapshot before and after.
- `test_baseline_outcomes_match_the_golden_file` rebuilds the baseline and compares all
  150 accounts (5 component scores, total, tier, action, persona, angle, stage) with the fixture.
- Evaluation is unchanged and still visible: **57.0% tier accuracy, 0% Priority 2 recall**
  (`test_evaluation_results_are_unchanged`, plus `python -m app.ai.run_eval --mode mock`).

## 9. Test results

| Run | Result |
|---|---|
| Full backend suite | **293 passed** |
| `tests/test_explainability.py` (T1) | 36 passed |
| Security suites (`test_public_demo.py`, `test_public_demo_review.py`) plus T1 | 103 passed |
| Frontend production build | passes |
| Evaluation suite | runs; 57.0% accuracy |
| Real server (runtime-only Python 3.12 venv, `VERCEL=1`) smoke test | 13/13; `POST …/explain` → 403; bad `ids` → 422 |

## 10. Remaining limitations

1. **The offline extractor is rule-based.** It rejects negation and "rumour" cues, but a
   sentence with "reportedly", "may" or "could" that also matches a signal rule is still
   accepted. Topic and cue lists are short. A live LLM would behave differently, and is
   not evaluated here.
2. **Intent includes disqualifier penalties**, and the same size, industry and geography
   facts also lower fit, so bad-fit accounts are penalised twice. This is existing design,
   left unchanged and made visible.
3. **The Acme rule is debatable.** A fit of 69.5/80 with no intent lands in Priority 3,
   and the table says DEPRIORITIZE; RESEARCH would arguably be the better call. The rule
   is unchanged; it's a product decision for later.
4. **`as_of` is an estimate** of the last scoring time (newest disqualifier timestamp or
   score creation). The recomputation matches stored intent for every demo account, and
   `matches_stored_score` flags any case where it doesn't.
5. **Provenance exists only for data ingested after T1.** Older databases show
   `source_sentence: null` and no rejected evidence until re-seeded.
6. **Signal strength and confidence are fixed per type by the extractor**, not measured
   evidence quality.
7. **The evaluation's signal metrics use a simplified keyword matcher**, not this
   extractor. Tier accuracy (57%) and Priority 2 recall (0%) are unchanged and unaddressed.
8. **Sandbox caveats** (per instance, not authentication) still apply; see
   `docs/FINAL_PRE_DEPLOYMENT_REVIEW.md`.
9. **No UI uses these endpoints yet.** That's T4/T5.

## 11. Git state

- Part A committed locally as `7cf31fa`.
- T1 is committed locally as one commit after this report (see the session summary for the hash).
- Nothing pushed, nothing deployed. The working tree is clean after the commit except the
  ignored `gtmos.db`.
