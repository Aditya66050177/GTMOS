# GTMOS — Product Case Study

*An evidence-backed account prioritization tool for B2B sales teams.*

> **Read this first.** GTMOS is a working product prototype, not a business. Every company,
> contact and research note in it is synthetic. The sales pipeline is a simulation. It has
> no customers, no deployments, no revenue and no customer interviews behind it. The
> numbers below describe how the software behaves on that synthetic data. They describe
> nothing about a market.

---

## 1. Executive summary

B2B sales teams have more accounts than time. Most prioritization collapses two different
questions into one score: *does this company look like our customer?* and *is there a reason
to talk to them now?* GTMOS keeps them apart:

- **Fit (out of 80)** comes from fixed rules: industry and pain points, company size,
  technology and geography.
- **Intent (out of 20)** comes only from buying signals whose quoted evidence is checked
  against the research notes, weighted, decayed by age, and reduced by disqualifier penalties.
- A fixed rule table turns tier plus intent into a next action:
  **CONTACT · PRIORITIZE · NURTURE · RESEARCH · DEPRIORITIZE**.
- Every number can be traced: each account page shows the rule behind each fit point, each
  signal's source sentence and `weight × strength × confidence × decay = points`, and
  every claim the system *refused* to count.
- Outreach drafts are grounded in verified evidence, and a person must approve and send
  every message. No code path sends email.

The core design principle is that **AI handles language; deterministic, tested code makes
business decisions.** A language model reads notes and writes drafts. It never scores,
filters or picks an action.

On the synthetic demo data (150 accounts), the system recommends outreach (CONTACT or
PRIORITIZE) for **3** accounts and nurturing for **5**. The other 142 get RESEARCH (23) or
DEPRIORITIZE (119). On a labelled evaluation set its **tier accuracy is 57%**, and it **never
identifies a true Priority 2 account (0% recall)**. Section 15 explains why, and why that
evaluation is easier than the real problem.

## 2. The B2B account prioritization problem

A seller or founder doing outbound faces three recurring questions every week:

1. **Who should we contact now?**
2. **Why does this account matter right now?**
3. **What should we say?**

The usual tools answer them poorly in different ways (this is reasoning about common
workflows, not research I ran):

- **Spreadsheets and CRM fields** capture firmographics well, but rarely encode *timing*.
- **Lead scores** are often opaque. A rep who can't see why an account scores 82 has no
  reason to trust it or to argue with it.
- **General-purpose chat assistants** write fluent research summaries and emails, but they
  can state things that are not in the source. In outbound that's a credibility risk:
  one wrong "congrats on your Series B" damages the relationship.

GTMOS frames the problem as **limited sales capacity plus incomplete information**. The job
isn't to rank everything perfectly. It's to make each decision explainable enough that a
sales leader can check it, disagree with it, and change the rule.

## 3. Why account fit and buying intent are different

| | Fit | Intent |
|---|---|---|
| Question | Does this company resemble our ideal customer? | Is there credible, recent evidence of a reason to act now? |
| Changes | Slowly (size, industry, location, stack) | Quickly (hiring, funding, launches, leadership changes) |
| Evidence | Firmographic attributes | Dated events quoted from sources |
| Failure if ignored | Selling to companies that can never buy | Calling good-fit companies with no reason to listen |

The demo shows why they must stay separate. These are real outputs of the current code:

| Account | Fit /80 | Intent /20 | Total | Tier | Action |
|---|---|---|---|---|---|
| Fintech Pulse Inc | 78.5 | 15.2 | 93.7 | Priority 1 | **CONTACT** |
| Company 37 Cloud | 80.0 | 0.0 | 80.0 | Priority 2 | **RESEARCH** |
| Company 36 B2B *(labelled synthetic demo notes)* | 57.0 | 20.0 | 77.0 | Priority 2 | **PRIORITIZE** |
| Acme Technologies | 69.5 | 0.0 | 69.5 | Priority 3 | **DEPRIORITIZE** |

Company 37 has the best possible fit and is told to *research*; Company 36 fits worse and is
told to *prioritize*. **Within a tier, intent decides the action.** A single blended score
would hide that.

Honest caveat: the two dimensions are **not independent**. Disqualifiers (too small, wrong
industry, wrong geography) lower fit *and* subtract from intent, so poor-fit accounts are
penalised twice. The product says this openly on the map and the methodology page.

## 4. Initial ICP hypothesis and target user

**The product being sold in the demo** (synthetic): an AI customer-support automation
platform for B2B SaaS. Its ICP, generated from that product description and schema-validated:

- **Industries:** B2B SaaS, Software, Cloud Services
- **Size:** 50–500 employees
- **Geographies:** US, United States, North America
- **Buyer roles:** VP of Customer Support, Head of Customer Experience, Chief Revenue Officer
- **Pain points:** high ticket volume, slow response time, high support costs, help-desk overload
- **Technologies:** Zendesk, Intercom, Salesforce, Freshdesk, Jira
- **Exclusions:** B2C only, Government, Hardware manufacturing

**GTMOS's own target user** (a hypothesis, untested): founder-led or early sales teams at
seed to Series A B2B SaaS companies, where a founder or one or two sellers still research
and write outbound themselves. The reasoning: GTMOS handles one product, one ICP and low
volume; it values control and explainability over automation; and it has no CRM integration
or contact data, which larger teams would need. See `docs/GTM_STRATEGY.md`.

## 5. Product hypothesis

> If sales teams see **fit and intent separately**, with **every point traceable to a rule or a
> quoted source**, they will spend outreach on fewer, better-timed accounts and trust the
> recommendations enough to act on them, while staying in control of every message sent.

What would prove it wrong (none of this has been measured): reps ignoring the
recommendations; verified signals being too sparse to matter on real accounts (they are
sparse in the synthetic data: 137 of 150 accounts have zero intent); or the evidence check
rejecting too many real signals.

## 6. GTMOS product experience

The public site has these screens:

| Screen | Route | What it is for |
|---|---|---|
| Landing | `/` | The problem, a live account card from the API, and the entry to the demo |
| Guided demo | `/demo` | A six-step, five-minute walkthrough of the real app with a docked guide |
| Overview | `/app` | Accounts scored, tier distribution, simulated pipeline, ICP |
| Prioritized accounts | `/app/accounts` | Fit, intent, total, tier, action and evidence status per account; filters; **fit × intent map** |
| Account | `/app/accounts/:id` | Verdict and rule, fit breakdown, **evidence inspector**, outreach, provenance, activity |
| Compare | `/app/compare` | 2–4 accounts side by side (defaults to Company 36, Company 37, Acme) |
| Review queue | `/app/review` | Drafts with their evidence; approve, edit, reject, log as sent |
| Pipeline | `/app/pipeline` | Simulated stages |
| Analytics | `/app/analytics` | Five executive questions; weekly activity; conversions; analyst |
| Playground | `/app/playground` | Score any described company without saving anything |
| Methodology | `/app/methodology` | Weights, rules, evaluation, confusion matrix, known weaknesses |

A Streamlit dashboard (`app/dashboard/`) remains as the original internal tool for local use.

## 7. Scoring and recommendation methodology

**Problem.** Scores that can't be explained don't get trusted, and scores that change between
runs can't be audited.

**Decision.** A 100-point, rule-based score in plain code (`app/services/scoring_engine.py`),
with a fixed action table (`app/services/recommendation_engine.py`).

| Component | Max | Rule |
|---|---|---|
| ICP fit | 30 | Industry: exact 20, adjacent 10, else 0; plus up to 10 for pain-point overlap |
| Company fit | 20 | Size in range 20, within 25% 10, else 0; a matched exclusion subtracts 20 |
| Technology fit | 15 | Share of the ICP's tools the company runs, scaled to 15 |
| Geography fit | 15 | Target country 15, target region 8, else 0 |
| Buying intent | 20 | Verified signals (below), clamped to 0–20 |

**Tiers:** Priority 1 ≥ 90 · Priority 2 ≥ 75 · Priority 3 ≥ 50 · Low < 50.

**Action table** (each row has a rule id the UI cites):

| Tier | Intent | Action |
|---|---|---|
| Priority 1 | ≥ 10 / < 10 | CONTACT / RESEARCH |
| Priority 2 | ≥ 15 / 5–15 / < 5 | PRIORITIZE / NURTURE / RESEARCH |
| Priority 3 | ≥ 10 / < 10 | NURTURE / DEPRIORITIZE |
| Low | any | DEPRIORITIZE |

**Why.** Deterministic rules are auditable and repeatable: the evaluation confirms zero drift
across repeated runs. Sales leaders can disagree with a specific rule and change it.

**Trade-offs.** The weights and thresholds are reasoned defaults, **not fitted to outcomes**.
Rules are brittle at the edges: Acme (fit 69.5/80, a close match) lands in Priority 3 and is
deprioritized, and arguably it should be researched instead.

**Unsolved.** Calibration against real wins and losses; per-team rule editing in the UI.

## 8. Evidence-backed signal detection

**Problem.** A keyword matcher sees "hiring" in *"Rumours suggested Acme was hiring… but the
CEO confirmed a hiring freeze"* and calls the account hot.

**Decision.** A signal counts only if its quoted evidence appears in the source note.
Negated, hearsay and speculative claims are **recorded as rejected, with 0 points**, not
silently dropped.

**Implementation.**
- `ResearchEngine.extract_signals_from_text` (`app/services/research_engine.py`) asks the
  language model for structured signals, validates them with Pydantic, and rejects any whose
  quote isn't in the text. The check is case-insensitive and partial: a quote of more than
  three words passes if the whole quote, its first three words or its last three words
  appear in the note. The offline extractor always returns whole sentences, so in the demo
  every accepted quote is verbatim; a live model could pass a partly paraphrased quote.
- Each note is stored with provenance (a `research_note` activity holding the text, source,
  date, dataset and resulting signal ids). Each rejection is stored as a `rejected_signal`
  activity with its category: **negated**, **unsupported** or **ambiguous**.
- **Intent formula** (`app/services/signal_engine.py`, one shared implementation):
  `points = weight × strength × confidence × decay`. Only the newest signal per type counts.
  Decay is 1.0 up to 90 days, 0.5 up to 180, then 0. Intent = clamp(sum, 0, 20).
- **Weights:** support hiring 20, funding 15, product launch 15, relevant technology 15,
  international expansion 10, rapid growth 10, executive change 5.
- **Penalties:** wrong industry −30, no use case −30, too small −20, wrong geography −20.

**What the product shows.** The evidence inspector displays the original sentence with the
quote highlighted, never paraphrased, plus status (current / aging / expired / superseded),
the formula with real numbers, and a check that recomputed intent equals the stored score
(true for all 150 demo accounts).

**Trade-offs.**
- In the public demo the "language model" is an **offline rule-based stand-in**
  (`app/ai/mock_signals.py`). It catches "not", "freeze", "frozen", "rumour" and hedges, but
  accepts "reportedly" or "may" sentences that match a signal rule.
- Strength and confidence are fixed per signal type, not measured.

**Unsolved.** Evaluating a live model's extraction on real notes; a stricter, whole-quote
evidence check; claim-level source tracing inside drafts.

## 9. Human-in-the-loop outreach

**Problem.** Automated outreach that states something false, or sends without review,
damages trust and brand.

**Decision.** Drafts are written only from verified evidence; a fact-check refuses numbers
not found in the evidence or account profile; deprioritized accounts can't get drafts; and
**no code path sends email**.

**Implementation.**
- `PersonalizationEngine` (`app/services/personalization.py`) builds the draft (under 120
  words) and retries once if the fact-check fails, then **refuses** to save it.
- Earlier, a failed draft was logged but saved anyway. That bug was fixed in this project.
- Drafts move pending → approved / rejected. "Mark as sent" only *logs* that a person sent
  it, and moves the account to Contacted.

**Trade-offs.** The fact-check verifies numbers, not every claim. Drafts show which evidence
they used, but not which words came from which quote.

**Unsolved.** Integration with a real sending tool, keeping the approval gate.

## 10. Executive analytics

**Problem.** Dashboards of charts don't answer what a GTM leader asks: *who to pursue, who
to nurture, where deals stall.*

**Decision.** Five fixed questions answered by deterministic queries
(`app/services/executive_analytics.py`). Each answer separates **Observations** (database
values) from **Hypotheses** (labelled "not established by the data").

| Question | Demo answer (synthetic) |
|---|---|
| Which accounts are worth pursuing? | 3: Fintech Pulse, Company 4 B2B, Company 36 B2B |
| Which should we nurture? | 5, all Priority 2 and 0.6–8.9 intent points short of PRIORITIZE |
| Where are opportunities getting stuck? | Contacted → Replied at 42.7% (32 of 75); 42 open accounts silent 14+ days, 33 of them Priority 3 or Low |
| Which signals appear across tiers? | 41 accounts carry verified signals; 2 have intent ≥ 15; 23 have signal points cancelled entirely by disqualifier penalties |
| Which accounts to investigate next? | 31 match the rules; top is Company 37 Cloud (fit 80, intent 0, one unverified rumour) |

**The analyst** maps a free-text question to one of 11 fixed functions; anything else
becomes "unknown". There is no generated SQL, router parameters are ignored, and executive
answers contain no model-written text.

**Trade-off.** The pipeline is a **seeded 40-day simulation**, so "stuck" findings describe
the simulation, not buyers. Every pipeline answer says so.

## 11. Explainability and trust

The explainability API (`GET /api/web/accounts/{id}/explain`, `/web/compare`,
`/web/comparisons/featured`) returns, for any account:
- fit components with their rules
- every signal's contribution, plus disqualifiers and rejected claims
- the tier rule and the exact action rule id
- a self-check that recomputed intent matches the stored score

The UI never computes scores. It displays API values, and restates rules in plain English
next to the verbatim rule string.

Deliberate honesty features:
- Synthetic records are tagged.
- The pipeline is labelled simulated.
- The landing page shows the 57% accuracy.
- The methodology page lists seven known weaknesses.
- The demo explains that visitor edits are temporary.

## 12. Technical architecture

The stack:
- **Backend:** Python, FastAPI, SQLAlchemy 2, Pydantic v2, SQLite.
- **Frontend:** React, Vite, Tailwind.
- **Public demo:** designed for Vercel, with a static frontend plus FastAPI as a serverless
  function at `/api`. It has not been deployed yet.
- **Language model:** one adapter, `app/ai/llm.py`, with an offline mock and optional Gemini.

Full detail and diagrams: `docs/TECHNICAL_ARCHITECTURE.md`.

## 13. Product and engineering trade-offs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Scoring | Deterministic rules | Model-scored or ML model | Auditable and repeatable; no outcome data to train on |
| Signals | Quote-verified, rejections stored | Trust model output | Prevents invented claims; makes refusals inspectable |
| Fit vs intent | Two scores, one total | Single blended score | Within a tier, intent should decide the action |
| Demo model | Offline stand-in | Live Gemini publicly | No cost or abuse risk; reproducible demo; but less realistic |
| Database | SQLite, rebuilt per serverless instance | Hosted Postgres | Zero setup for a disposable demo; not for customer data |
| Visitor edits | Per-browser temporary sandboxes | Shared writable demo | No visitor can change what others see; edits can be lost (and the UI says so) |
| Evaluation | Shown openly (57%, 0% P2 recall) | Hide weak metrics | Credibility with a technical or commercial audience |
| Synthetic comparison | 3 labelled notes in a separate file | Edit baseline data | Shows the fit-vs-intent contrast without touching baseline or eval data |

## 14. Security and synthetic-data boundaries

The public API is a separate, guarded instance (`app/api/public.py`):
- **Shared data is read-only** (SQLite `mode=ro`).
- **Only eight non-GET routes are allowed:** draft edit, approve, reject, personalize,
  mark-sent, reset, the playground and the analyst question (the last two don't write data).
  Everything else returns 403.
- **Allowed writes go to a per-browser sandbox** keyed by a random ID. It's private to that
  browser, about two hours long, on one server instance, and capped at 200 sandboxes. That
  ID is **not authentication**.
- **Limits:** a 16 KB body cap, per-IP rate limits (per instance only) and field length
  limits on every request.
- **Errors and model:** error messages are generic, and the language model is forced offline.
- **Lost edits are detected:** each sandbox carries a random token, so the browser can tell
  when its edits are gone (expired, evicted, another server, recreated) and says so.
- **Data:** accounts and contacts use `.example` domains and obviously fictional names.

A pre-deployment review found no blocking issue for a synthetic-data demo. **It must never
hold real customer data.**

## 15. Evaluation methodology and results

Computed live by `GET /api/web/methodology` (and `python -m app.ai.run_eval --mode mock`).

**Tier classification on 100 labelled synthetic accounts:**

| | Precision | Recall |
|---|---|---|
| Priority 1 | 36.7% | 100% |
| Priority 2 | 0% | **0%** |
| Priority 3 | 100% | 31.4% |
| Low | 61.4% | 100% |

**Overall accuracy: 57% (57/100).** All 19 true Priority 2 accounts are predicted Priority 1,
and 22 of 35 true Priority 3 accounts are predicted Low.

**Why Priority 2 recall is 0%.** The labelled accounts have no research notes, so the
evaluation scores intent with the engine's built-in **proxy** (support-team size and funding
stage, up to 20 points), not verified signals. For good-fit accounts the proxy adds enough
to cross 90.

**Signals:** precision, recall and F1 are 100% on 60 labelled sentences. They're measured
with a **simplified keyword matcher**, not the production extractor, on short synthetic
sentences, so they say little about real-world quality.

**Determinism:** 0 drift across 5 repeated runs. **Draft fact-check:** 30 of 30 mock drafts
grounded (`docs/evaluation.md`).

**What this does not show:** anything about real accounts, real research notes, a live
language model, or sales outcomes. The labels were written by the project author.

## 16. Known weaknesses

1. Priority 2 is never predicted correctly on the evaluation set.
2. Disqualifiers count in both fit and intent.
3. The offline extractor accepts "reportedly" or "may" claims that match a rule.
4. The evaluation is easier than reality (proxy intent; simplified matcher).
5. Some rules are debatable (Acme).
6. All data is synthetic; the pipeline is simulated.
7. Thresholds and weights are untuned.
8. Visitor edits are temporary and per instance.
9. One product at a time; no CRM integration, contact data or real sending.

## 17. What I learned

*These are lessons the project's history supports. Personal framing is yours to add; see
the guidance in `docs/GTMO_INTERVIEW_PREPARATION.md`.*

- **The interesting product question was "why now", not "who fits".** Separating fit from
  intent changed recommendations more than any weight tuning would.
- **Explainability is a feature, not documentation.** The most persuasive thing in the demo
  is a quote highlighted inside its source sentence, plus the arithmetic underneath.
- **Data bugs masquerade as product insight.** An early version reported 37 Priority 1
  accounts. Each signal was being loaded twice, "We are not hiring right now" counted as
  hiring, and 52 of 66 research notes pointed at accounts that didn't exist. Fixing these
  cut Priority 1 to 2.
- **An honest weak metric beats an impressive unexplained one.** Explaining *why* Priority 2
  recall is 0% is more useful than a higher number would have been.
- **Determinism has to be tested, not assumed.** A note dated exactly 181 days back counted
  as 180 or 181 days depending on the time of day, flipping its decay. A golden-file test now
  pins every account's outcome.

## 18. Future roadmap

Ordered by what would most change the evidence, not by feature appeal. **None of this is built.**

1. **Validate with real teams:** about 10 discovery conversations and 2–3 supervised pilots
   with their own ICP and accounts. Measure whether recommended accounts reply or book
   meetings more often than the team's current choices.
2. **Recalibrate scoring:** fix the Priority 2 problem; decide whether disqualifiers belong
   in intent; tune thresholds on real outcomes.
3. **Evaluate a live model** on real research notes, against the production extractor, not
   the simplified matcher.
4. **Multi-tenant pilot infrastructure:** real authentication, per-customer workspaces,
   managed Postgres, a data-handling statement.
5. **CSV import/export and CRM sync,** so pilots can bring and return their own accounts.
6. **Editable rules** in the UI, with change history.
