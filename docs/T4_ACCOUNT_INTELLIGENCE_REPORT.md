# T4 — Executive account intelligence experience: report

Branch `claude/modest-darwin-atz53w`, 2026-11-25. Not pushed, not deployed.

**Summary.** Account prioritization is now the centre of GTMOS:
- The **prioritized accounts** page shows fit (/80), intent (/20), total, tier, action and evidence status for every account, with filters and a **fit × intent map**.
- Each **account page** opens with the verdict and the exact rule behind it, then an **evidence inspector** that quotes source sentences verbatim, highlights the supporting text and shows `weight × strength × confidence × decay = points` per signal. Rejected claims are listed separately at 0 points.
- A **comparison page** puts Company 36 B2B, Company 37 Cloud and Acme side by side.
- The **review queue** links each draft to its evidence.

Everything reads from the T1 and T2 APIs, plus one new read-only endpoint (§2). Scoring,
recommendation rules and evaluation results are unchanged.

---

## 1. What a GTM leader sees

| Question | Where it is answered |
|---|---|
| Does it fit the ICP? | Fit /80 on every list row, the account verdict, and "Why the fit is X / 80" with each component's rules and points |
| Is there credible buying intent? | Intent /20, evidence status chips (current / aging / expired / rejected), and the evidence inspector |
| What evidence supports it? | Exact source sentence with the supporting quote highlighted, plus source, date, age, status and the contribution formula |
| Why this action? | Plain-English rule, plus the exact rule id and condition from the API (e.g. `P2_INTENT_GE_15: Priority 2 and intent >= 15 -> PRIORITIZE`) and the tier band (`total 77.0 is in 75-89.9 -> Priority 2`) |
| What should sales do next? | Persona and angle from the rule table, a "Draft outreach from this evidence" button (disabled when the rules forbid it), and the account's drafts with their review status |

## 2. API change (explained before implementing)

**`GET /api/web/prioritization`** is new, read-only and behind the public guard.

- **Why it was needed:** the list needs fit, intent and evidence status for 150 accounts.
  `/web/accounts` has no fit or evidence status. Calling `/explain` 150 times would exceed
  the public rate limit (120 requests per minute), and computing fit in the browser as
  total − intent would duplicate scoring logic.
- **What it returns:** per account: fit (the sum of the four stored fit components, the same
  number `/explain` shows), intent, total, tier, action, rule id, counts of current / aging /
  expired / superseded signals and rejected claims, and a synthetic-additions flag. It is
  built on the existing T2 snapshot (same engine calls).
- **Tests** (`tests/test_prioritization.py`):
  - Every row equals `/explain` for all 150 accounts.
  - Rows are sorted, and the comparison accounts have the expected values.
  - Empty and unscored databases are handled.
  - Non-GET requests return 403, the template file is unchanged, and one visitor's
    logged outreach changes only their own view.

**Bug fixed in T1 code:** the tier-band text in `/explain` named the wrong band for Priority 3
and Low (e.g. "0-89.9 -> Low" instead of "0-49.9"), because it picked the first higher
threshold rather than the nearest. Only the explanation text was wrong; tiers come from the
unchanged scoring engine. A new test covers all four bands.

No other backend change. `/web/accounts`, `/explain`, `/compare` and all other contracts are as before.

## 3. Pages and components

| File | What it does |
|---|---|
| `web/src/components/intel.tsx` (new) | `ScoreTriplet` (fit / intent / total with one-line meanings), `Meter`, `EvidenceChips`, `StatusBadge`, `QuotedSentence`, `SignalRow` (formula and status note), `RejectedRow`, `EvidenceInspector`, `RuleExplanation`, `FitIntentMap` |
| `pages/Accounts.tsx` | Table with Fit and Intent meters, Total, Tier, Action, Evidence chips, Stage and a "demo note" tag. Filters (search, tier, action, evidence: current / only aging or expired / rejected / none), sort by total, fit, intent or name, all kept in the URL. **Table / Fit × intent map** toggle. Mobile cards |
| `pages/AccountDetail.tsx` | Verdict (score triplet and recommended action with rule) → fit breakdown → evidence inspector → outreach for this account → contacts, research-note provenance, activity. Handles invalid ids, missing accounts and unscored accounts |
| `pages/Compare.tsx` (new, `/app/compare`) | Defaults to Company 36 B2B, Company 37 Cloud and Acme (the API's featured pair plus Acme by name). Pick 2–4 accounts. Shows the code-generated observations, an aligned table (fit, intent, total, priority, action, rule in plain English and verbatim, signals counted, rejected claims, disqualifiers), and evidence columns with supporting and rejected evidence. Synthetic records tagged |
| `pages/Review.tsx` | Each draft shows its signal, evidence with dates, the fact-check note, a link to the account's evidence, and status wording that never implies sending: "awaiting review", "approved — not sent", "logged as sent by a person" |
| `AppShell.tsx`, `main.tsx` | "Compare accounts" in the navigation and route |

### Evidence rules in the UI
- **Quotes are never rewritten.** `QuotedSentence` highlights the quote only if it occurs
  verbatim (case-insensitive) in the stored source sentence. If it doesn't, both strings are
  shown exactly as stored. If no sentence was recorded, the stored quote is labelled as such.
- **Statuses** come from the API (current, aging, expired, superseded, disqualifier), each
  with a note using the API's own thresholds (e.g. "91–180 days old: counts at 0.5 weight").
- **Rejected claims** have their own section with category, reason and **0 pts**.
- The inspector ends with `intent = clamp(raw sum, 0, 20)` and states whether it matches the
  stored score. It does for every demo account.
- "Why it matters" text is labelled as a product hypothesis.

### Fit × intent map
- Custom SVG, no new dependency. Every point is keyboard-focusable, has an accessible label,
  and opens a side list of the accounts at that point.
- **Tier boundaries are drawn as lines of constant total** (fit + intent = 90, 75, 50), which
  is exactly how tiers are defined. No invented quadrants.
- Points are **not jittered**. Accounts with identical scores share a point, which shows a
  count (e.g. 54 low-fit accounts at fit 0, intent 0).
- A note says plainly that **fit and intent are not independent**: disqualifiers lower fit
  and also subtract from intent.
- **Colour** follows the bundled data-viz method. A scatter can carry at most 3 colours, so
  actions are grouped into Act now (Contact + Prioritize), Nurture and Research, with
  Deprioritize as grey context. Validated with `--pairs all`: all checks pass; low-contrast
  relief comes from the legend, the exact action shown on selection, and the table view.

## 4. Verification

| Check | Result |
|---|---|
| Backend suite | **344 passed** (+4 prioritization, +4 tier-band) |
| Frontend production build | Passes |
| Browser, production build with the guarded API in `VERCEL=1` mode, 1440 px and 390 px | Accounts table and map; Company 36, Company 37, Acme; a disqualified account (Company 97 Manufacturing); an aging-only account (Company 116 Software); an account with no evidence (Company 38 Software); compare; review: **0 console errors, 0 horizontal overflow** |
| Comparison accounts | All three load by default; Company 36: fit 57.0, intent 20.0, PRIORITIZE; Company 37: fit 80.0, intent 0.0, RESEARCH, 1 unsupported rumour; Acme: fit 69.5, intent 0.0, DEPRIORITIZE, 2 rejected claims |
| Quote highlighting | Company 36: 2 highlighted quotes inside their source sentences |
| Missing data | Unknown id → "Account 999999 not found." · invalid id (`/abc`) → message with **no API call** · unscored (explain returning 404) → "This account has no score yet" · empty evidence, empty drafts and no-match filters → empty states |
| Draft review and sandbox isolation | Visitor A approves one draft and rejects another (6 → 4 pending; the approved one reads "approved — not sent"); visitor B in a separate browser still sees 6 pending |
| Accessibility (axe-core, WCAG 2 A + AA) | **0 violations** on all 12 views |
| Smoke test through the frontend | 15/15 |

Fixed during verification:
- An invalid-id request fired before the error message.
- Comparison header names rendered in capitals.
- Map points covered the axis labels and a tier label.
- The tier-band text bug (§2).
- Mobile header alignment.

### Screenshots (`docs/screenshots/t4/`)
- **Desktop:**
  - `d-accounts.png`: prioritization table
  - `d-map.png`: fit × intent map with Company 36 selected
  - `d-c36.png`: full account page with the evidence inspector
  - `d-c37.png`: rumour rejected
  - `d-acme.png`: ambiguous and negated rejections
  - `d-disq.png`: disqualifier penalties
  - `d-compare.png`: three-account comparison
  - `d-review.png`: drafts linked to evidence
- **Mobile:** `mobile-account-accounts-compare.png`

## 5. Constraints honoured
- No change to scoring, intent calculation, signal detection, recommendation rules or
  evaluation (the golden-baseline test and the 57% evaluation test still pass).
- No scoring logic in the frontend: fit, intent, totals, tiers, actions, statuses and points
  are all displayed from API values. The frontend's only rule text is the plain-English
  restatement keyed by `rule_id`, always shown next to the API's own rule string.
- Public-demo safeguards unchanged; the new endpoint is GET-only behind the guard.
- No authentication, billing, email sending or live AI. Nothing is ever shown as sent unless
  the database has the "sent" status, which only a person's "log it" action sets.

## 6. Limitations

1. **The map is crowded at zero intent.** 137 of 150 accounts have intent 0, so most points
   sit on the x-axis. That reflects the data and isn't hidden or jittered; the table view
   is the precise alternative.
2. **The comparison table scrolls sideways on phones** (minimum 640 px); the evidence columns
   below stack vertically.
3. **The observations in the comparison repeat a fact** when three accounts are compared
   (pairwise statements). They're API output, shown as-is.
4. **Plain-English rule text lives in the frontend,** keyed by rule id. If the rule table
   changes, this text must be updated; the verbatim API rule string is always shown beside it.
5. **Drafts show the evidence they used, but not which words of the draft came from which
   quote.** Claim-level tracing would need the backend to record it.
6. **The "high fit" label for Acme** (69.5/80) is a judgement; on totals it is Priority 3.
   The UI shows the numbers and the rule rather than the label.
7. **Visitor edits stay per instance** (sandbox caveats from the pre-deployment review still apply).

## 7. Git state

T4 is committed locally as one commit after this report. Nothing pushed, nothing deployed.
