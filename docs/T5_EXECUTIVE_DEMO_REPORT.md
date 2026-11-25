# T5 — Guided executive demonstration: report

Branch `claude/modest-darwin-atz53w`, 2026-11-25. Not pushed, not deployed.

**Summary.**
- **`/demo`** is a guided five-minute walkthrough of the **real application**. A guide panel
  (docked beside the app on desktop, a collapsible bottom sheet on phones) steps a visitor
  through six screens, with progress, timings, "what to notice", Back / Next / Restart / Exit,
  and links to the exact accounts and evidence.
- **`/app/methodology`** explains the model to a business audience and shows the evaluation
  honestly: 57% tier accuracy, a confusion matrix, 0% Priority 2 recall with the reason, and
  what the evaluation does not measure.
- **Analytics** now leads with the five executive question cards, keeping observations
  separate from labelled hypotheses.
- **The landing page** leads with "Explore the 5-minute demo".

One read-only endpoint was added and explained before implementing (§3). No scoring,
recommendation or security change.

---

## 1. The walkthrough

`/demo` sets the scenario ("150 accounts. Limited sales capacity. Which ones deserve your
team's attention?"), lists the six steps with timings (total 5:00), and offers **Start**,
**Jump to step N**, **Resume** and **Explore GTMOS on your own**. It also states what is
synthetic and links the 57% evaluation result.

| # | Step | Time | Opens (real screen) | What the guide points out |
|---|---|---|---|---|
| 1 | The business problem | 0:30 | `/app`: overview | 150 accounts, limited capacity; fit (looks like our customer) vs intent (credible reason to act now); only a handful combine both |
| 2 | Define the ICP | 0:45 | `/app/methodology#icp` | Product description → schema-validated ICP; fit 80 points (ICP 30, company 20, technology 15, geography 15) plus intent 20; deterministic, every point traceable |
| 3 | Prioritize accounts | 1:15 | `/app/accounts?view=map` | **Live values**: Company 37 Cloud (fit 80.0, intent 0.0 → RESEARCH), Company 36 B2B (fit 57.0, intent 20.0 → PRIORITIZE), Fintech Pulse (fit 78.5, intent 15.2 → CONTACT); within a tier, intent decides. Link: compare the three |
| 4 | Inspect evidence | 1:15 | `/app/accounts/{Company 36}#evidence` | Verbatim sentence with the quote highlighted; weight × strength × confidence × decay; rejected "We are not hiring right now" at 0 points; Company 36's signals are labelled synthetic notes. Links: Acme (rumour rejected), Company 37 (unsupported rumour) |
| 5 | Prepare outreach | 0:45 | `/app/review` | Draft → its signal and quoted evidence; fact-check; **approving does not send**, a person sends and logs; **sandbox caveat**: edits live about two hours on one server and can reset. Link: draft for Company 36 |
| 6 | Ask the analyst | 0:30 | `/app/analytics#executive` | Click a question; observations from data vs labelled hypotheses; no generated SQL; the pipeline is a simulation. Link: methodology and known weaknesses |

**How it guides through the real app.** The guide is part of the app shell, so it stays
visible as visitors click around. Next and Back navigate to the step's screen and scroll to
the section (waiting for async content). If a visitor wanders off, the guide offers "Open
<screen>"; when they're there, it says "You're on the … screen".

**Scenario integrity.**
- Demo accounts are resolved **by name** from `/web/prioritization`; IDs are never
  hard-coded, and every number in the step text comes from that response.
- If an account is missing, the step falls back to the account list and says so (tested).
- Synthetic demo notes are called out in step 4 and on `/demo`.
- State is per browser tab (`sessionStorage`, with an in-memory fallback). It stores no
  personal data.

## 2. Methodology page (`/app/methodology`)

All eight sections are in plain business language:
1. ICP (live), and the product description it came from.
2. The 100-point model: fit vs intent, a component table with rules and maximum points.
3. Signal weights, recency decay (90 / 180 days, ×0.5), and disqualifier penalties, noting
   that they also lower fit (double penalty).
4. Tier thresholds and the full action table with plain-English explanations.
5. Evidence rejection categories (negated / unsupported / ambiguous, 0 points).
6. Human approval (no code path sends email).
7. **Evaluation**: KPI tiles (tier accuracy **57.0%**, Priority 2 recall **0%**, Priority 1
   recall 100% / precision 36.7%, signal precision 100%*); the **confusion matrix** with
   correct cells in teal and wrong cells in red; a warning box explaining:
   - *Why P2 recall is 0%*: the labelled accounts have no research notes, so the evaluation
     uses the engine's built-in proxy intent (support-team size and funding stage), which
     pushes good-fit accounts past 90. All 19 true P2 accounts are predicted P1.
   - *What the evaluation doesn't measure*: tier accuracy uses that proxy, not verified
     signals; the signal metrics use **a simplified keyword matcher**, not the production
     extractor, on easy synthetic sentences.
8. **Known weaknesses**: P2 recall, double-counted disqualifiers, extractor gaps
   ("reportedly"/"may"), evaluation easier than reality, the debatable Acme rule,
   synthetic/simulated data, untuned thresholds.

I confirmed the proxy-intent explanation in this task from the evaluator code
(`evaluate_scoring` builds `AccountData` without an intent override). It wasn't spelled out
in earlier reports.

## 3. API change (explained before implementing)

**`GET /api/web/methodology`** is new, read-only and behind the guard. It returns:
- component maxima and rule text
- `SIGNAL_WEIGHTS` split into weights and penalties
- the decay constants, `TIER_THRESHOLDS` and `ACTION_RULES`
- the rejection categories
- the evaluation, **computed on each call** with the existing `GTMOSEvaluator` on
  `data/eval/` (about 10 ms), with the method notes above

**Why:** no endpoint exposed these numbers, and hard-coding them in the frontend would let
the page drift from the code and data.

**Tests** (`tests/test_methodology.py`):
- The reported constants equal the code's.
- The evaluation reports 57%, 0% P2 recall and the 19 P2→P1 cell, and its method notes
  mention the proxy and the simplified matcher.
- The endpoint is GET-only in the public API.

## 4. Analyst experience

Analytics now opens (after the KPIs) with an **Executive questions** panel: five cards
calling `/web/executive/{id}`. Each answer shows:
- the summary
- **Observations · from database values**
- **Hypotheses · not established by the data**, each tagged "Hypothesis"
- the accounts involved, linked to their evidence inspector and tagged "demo note" where relevant
- a collapsible block with provenance (simulated pipeline), selection rules, sources and data quality

The free-text analyst also shows observations, hypotheses and its data label. There is no
generated SQL; routing still uses the fixed allowlist from T2.

## 5. Other changes

- **Landing page:** primary CTA **"Explore the 5-minute demo"** (`/demo`), secondary
  **"Explore GTMOS"** (`/app`). The 57% note links to the methodology.
- **App shell:**
  - a "5-minute guided demo" button and a Methodology nav item
  - anchor scrolling that waits for async content
  - the guide docked as a third column on large screens, so it never covers content
- **Accessibility:** every horizontally scrollable table region is keyboard-focusable
  (8 wrappers).

### Files
- **New:** `web/src/demo/DemoContext.tsx`, `web/src/demo/steps.ts`,
  `web/src/components/DemoGuide.tsx`, `web/src/pages/Demo.tsx`,
  `web/src/pages/Methodology.tsx`, `app/services/methodology.py`, `tests/test_methodology.py`
- **Modified:** `web/src/main.tsx`, `web/src/lib/api.ts`, `web/src/pages/AppShell.tsx`,
  `Analytics.tsx`, `AccountDetail.tsx` (evidence anchor), `Landing.tsx`, `Overview.tsx` and
  `Compare.tsx` (focusable scroll regions), `app/api/routes/web.py` (one route)

## 6. Verification

| Check | Result |
|---|---|
| Backend suite | **347 passed** (+3 methodology) |
| Frontend production build | Passes |
| Full walkthrough, desktop 1440 px and mobile 390 px (Playwright, production build with the guarded API in `VERCEL=1` mode) | Landing CTA → `/demo` → Start → Next ×5. Visited exactly `/app`, `/app/methodology#icp`, `/app/accounts?view=map`, `/app/accounts/41#evidence` (Company 36), `/app/review`, `/app/analytics#executive` at both widths. Each step's target section is **in view** after navigation. Step label correct at every step |
| Back / Restart / Exit | Back from step 6 → `/app/review`; Restart → `/app`, step 1 of 6; Exit removes the guide |
| Evidence links | Step 4 links: Acme `/app/accounts/1#evidence` (2 rejected claims at 0 pts) and Company 37 `/app/accounts/42#evidence` (1 rejected claim at 0 pts) |
| Analyst | Clicking "Which accounts are worth pursuing?" shows observations and 2 hypotheses tagged "Hypothesis" |
| Missing data | With the demo accounts absent (API returning `[]`), Jump to step 4 → falls back to `/app/accounts` with a visible warning |
| Sandbox honesty | Step 5 text states the sandbox is temporary, one-server and can reset (checked at both widths); `/demo` and the shell repeat it |
| No fabricated metrics | Methodology numbers match the API (57.0%, 0%, the 19-account cell). Step text uses only live API values |
| Console errors / overflow | **0 / 0** at both widths |
| Accessibility (axe-core, WCAG 2 A + AA) | **0 violations** on `/demo`, all six steps with the guide open, and the methodology page |
| Smoke test through the frontend | 15/15 |

Fixed during verification:
- Interactive step buttons inside a progressbar role (axe); now a labelled step nav with
  `aria-current`.
- The missing-data warning never showed; fixed with the context's `ready` flag.
- The guide covered the map's key points on desktop; now docked as a column.
- Scrollable table regions weren't keyboard-focusable.

### Screenshots (`docs/screenshots/t5/`)
- **Landing:** `d-landing.png`, `m-landing.png` (CTAs).
- **Demo entry:** `d-0-demo.png` (scenario and step list).
- **Steps 1–6 (desktop, guide docked):**
  - `d-1.png`: Overview
  - `d-2.png`: Methodology ICP
  - `d-3.png`: fit × intent map
  - `d-4.png`: Company 36 evidence
  - `d-5.png`: Review queue
  - `d-6.png`: Executive question answered
- **Mobile walkthrough:** `m-walkthrough-steps-1-3-4-6.png` (bottom sheet).
- **Methodology:** `d-methodology.png` (evaluation, confusion matrix, weaknesses).
- **Missing data:** `d-missing-data.png` (fallback with warning).

## 7. Limitations and remaining issues

1. **The guide is large on phones.** Expanded, it uses about half of a 390 px screen. It
   collapses to a slim bar and the app scrolls above it, but the demo reads best on a
   laptop or tablet.
2. **Narrower content column on desktop.** Docking the guide (360 px) means some wide
   tables scroll horizontally during the tour; they're keyboard-focusable.
3. **The walkthrough can't detect a lost sandbox.** It explains that edits can reset, but
   if a visitor's next request reaches another server instance, their approval silently
   reverts (pre-deployment review P1-1). Detecting this needs a small backend signal.
4. **Step timings are estimates** for a presenter talking over the screens, not
   auto-advancing timers.
5. **Methodology prose is static text** (weaknesses, explanations), while every number comes
   from the API. If the model changes, the prose needs a review.
6. **Underlying model limits are unchanged and shown:** 57% tier accuracy, 0% Priority 2
   recall, proxy-intent evaluation, simplified signal matcher, double penalty, synthetic
   data, simulated pipeline.

## 8. Git state

T5 is committed locally as one commit after this report. Nothing pushed, nothing deployed.
