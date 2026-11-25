# T3 — Visual system refresh: report

Branch `claude/modest-darwin-atz53w`, 2026-11-25. Not pushed, not deployed.

**Summary.** The React app moved from a dark neon look to a restrained, light, information-dense
B2B interface with one accent colour (teal), a single typeface, and consistent badges, tables
and panels. Only `web/` and docs changed. No backend file, API contract, scoring rule or
security safeguard was touched, and all 336 backend tests pass unchanged. No new dependencies.
Every page was checked in a real browser at 1440 px and 390 px, with 0 console errors, 0
horizontal overflow and 0 axe WCAG 2 A/AA violations.

---

## 1. Design system

### Colour tokens (`web/tailwind.config.js`)

| Token | Hex | Use | Contrast |
|---|---|---|---|
| `canvas` | #F6F7F9 | Page background | — |
| `surface` | #FFFFFF | Panels, tables, header | — |
| `subtle` | #F9FAFB | Table headers, insets | — |
| `line` / `line-strong` | #E4E7EC / #D0D5DD | Dividers, panel borders (decorative) | — |
| `line-input` | #868E9C | Form-field borders | **3.30:1** (≥ 3:1 for UI boundaries) |
| `ink` | #101828 | Primary text | 17.75:1 |
| `ink-2` | #344054 | Body text | 10.46:1 |
| `ink-3` | #475467 | Secondary text | 7.69:1 |
| `ink-4` | #667085 | Muted labels | 4.97:1 on white, 4.64:1 on canvas |
| `accent-600` | #0F766E | **The one accent**: primary buttons, active nav, bars, links, focus ring | 5.47:1 (both directions) |
| `accent-700` on `accent-50` | #115E59 / #F0FDFA | Subtle accent badges | 7.27:1 |
| `warn-700` on `warn-50` | #B54708 / #FFFAEB | NURTURE, pending | 5.20:1 |
| `danger-700` on `danger-50` | #B42318 / #FEF3F2 | Disqualifiers, errors, reject | 6.05:1 |

All text pairs meet WCAG AA (4.5:1). Ratios were computed with the WCAG formula.

### Typography and shape
- **One typeface:** Inter (400/500/600/700), with tabular numerals everywhere. Space Grotesk and
  JetBrains Mono were removed (two fewer font downloads); code uses the system monospace.
- **Scale:** 11 px labels (`text-2xs`, uppercase `eyebrow`), 14 px body, 20/24 px page titles,
  24 px KPI values.
- **Shape:** 6–8 px radius (was 16 px), a 1 px border plus a barely visible shadow. No glows,
  gradients, blurred blobs, grid backgrounds, pulsing dots or entrance animations. Motion is
  limited to colour transitions and is removed under `prefers-reduced-motion`.

### Status and priority language (`web/src/lib/format.ts`)

| Element | Rule |
|---|---|
| **Tier** (ordinal) | One hue at decreasing strength: Priority 1 solid teal · Priority 2 teal tint · Priority 3 outlined · Low grey |
| **Action** (urgency) | CONTACT solid teal · PRIORITIZE teal tint · NURTURE amber · RESEARCH outlined · DEPRIORITIZE grey |
| **Draft status** | pending amber · approved teal tint · logged as sent outlined · rejected grey |
| **Evidence** | 3 px left rule: teal for a buying signal, red for a disqualifier |
| **Provenance** | `DataTag` ("Demo · synthetic data · simulated pipeline", "Simulated", "Fictional") wherever a number could be mistaken for a real outcome |

Colour is never the only carrier: every badge has its text label.

### Charts (following the bundled data-viz method)
- **Weekly activity line chart:** categorical slots 1–4 of the validated reference palette
  (#257de0, #f47230, #00b894, #f2a600). `validate_palette.js --mode light`: all checks pass;
  worst adjacent colour-blind ΔE 11.8, normal-vision ΔE 23.8. Three colours are below 3:1
  against white, so the panel has a **Chart / Table** toggle (the required table view), plus a
  legend. 2 px lines, recessive grid, single y-axis, tooltip with crosshair.
- **Tier distribution:** a sequential single-hue ramp (teal 800 / 600 / 300, Low grey) with
  2 px gaps between segments and an exact-value table beside it.
- **Score, components, conversion, pipeline:** thin single-series bars in the accent colour,
  each with its number in text.

### Component classes (`web/src/index.css`)
`panel`, `panel-head`, `panel-pad`, `eyebrow`, `h-page`, `h-section`, `btn-primary`,
`btn-secondary`, `btn-danger`, `btn-ghost`, `input`, `label`, `segmented` (with
`aria-pressed`), `badge`, and `tbl` (sticky header, right-aligned tabular numbers via `.r`).
A global `.grid > * { min-width: 0 }` stops wide tables from forcing grid columns past the
viewport (this fixed a 449 px overflow on mobile analytics).

## 2. Components and pages changed

| File | Change |
|---|---|
| `components/ui.tsx` | Rewritten. New `ScoreBlock` (number + thin bar) replaces the decorative ring; new `Panel`, `Kpi` (was `Stat`), `EmptyState`, `DataTag`. Restyled `TierBadge`, `ActionBadge`, `ComponentBars` (now a `ul` for valid semantics), `EvidenceCard`, `Loading` (skeleton rows + `role="status"`), `ErrorBox` (`role="alert"`), `PageHeader` (title, description, actions) |
| `lib/format.ts` | New tier/action styles; `TIER_FILL` ramp; removed `scoreColor` |
| `pages/AppShell.tsx` | Light sidebar grouped as **Accounts · Execution · Insight**; persistent "Demo · synthetic data · simulated pipeline" tag; mobile header with Demo tag and an accessible menu (`aria-expanded`, `aria-modal`); sandbox note and reset unchanged in behaviour |
| `pages/Overview.tsx` | KPI row (now includes Priority 1+2 and drafts awaiting review); top-accounts table; tier distribution bar plus exact table; pipeline bars tagged Simulated; ICP as a definition grid |
| `pages/Accounts.tsx` | "Prioritized accounts": dense table with sticky header and scrolling body, tier filter with counts, sort select, result count, empty state, mobile card list |
| `pages/AccountDetail.tsx` | Header with tier and action badges and a score/stage/intent column; rule-by-rule table; recommendation panel; evidence panel with empty state; activity as a dated list |
| `pages/Review.tsx` | Status badges, evidence side panel with accent rules, secondary/danger buttons, "I sent it myself — log it" wording, empty states per tab |
| `pages/Pipeline.tsx` | Light kanban columns with count chips, "simulated deal value", empty-column text, Simulated tag |
| `pages/Analytics.tsx` | Simulated label and description; validated chart palette with Chart/Table toggle; light tooltip; restyled conversion bars, analyst panel and tables |
| `pages/Playground.tsx` | Form in a panel with presets in its header; result with `ScoreBlock`, badges and empty states |
| `pages/Landing.tsx` | Restrained product page: plain hero with live account panel, facts strip, three questions as a bordered grid, the six stages as a table with owner badges, scoring model tables, worked Acme example, guardrails, CTA, footer. Adds a visible note: synthetic data, simulated pipeline, **57% tier accuracy** |
| `pages/NotFound.tsx`, `index.html`, `public/favicon.svg` | Light styling; one font family; new mark |

Unchanged behaviour (checked): routing, filters in the URL, sandbox header and reset, draft
approve/edit/reject/log, personalize, playground, analyst. **The analyst UI still shows the
explanation and raw data; displaying T2's observations and hypotheses is left for T5.**

## 3. Verification

| Check | Result |
|---|---|
| Frontend production build (`npm run build`) | Passes. 234 KB JS (72 KB gzip) main, analytics chunk lazy-loaded; CSS 29 KB |
| Backend suite (`python -m pytest`) | **336 passed** |
| Browser walkthrough (Playwright, production build plus guarded API in `VERCEL=1` mode), desktop 1440 × 900 and mobile 390 × 844 | Landing, Overview, Accounts, Fintech Pulse and Acme detail, Review, Pipeline, Analytics, Playground (after scoring), 404, and the mobile menu: **0 console errors, 0 horizontal overflow** |
| States | Loading (API delayed 1.5 s), error (API returning 503, with Retry), empty (accounts search with no match, Rejected tab) all render as designed |
| Accessibility: axe-core 4.10 (WCAG 2 A + AA) on every desktop page | **0 violations** (first run found invalid `dl` markup in the score bars; fixed) |
| Contrast | All token pairs computed (table in §1); keyboard focus shows a 2 px teal outline |
| Smoke test through the frontend (`scripts/smoke_test.py … --frontend`) | 15/15 |

Screenshots (`docs/screenshots/t3/`): `d-landing.png`, `d-overview.png`, `d-accounts.png`,
`d-detail-acme.png`, `d-review.png`, `d-analytics.png`, `m-combo.png` (mobile detail,
accounts, review), `states-combo.png` (loading, error, empty).

## 4. Remaining issues

1. **Light theme only.** There's no dark mode; `color-scheme: light` is declared.
2. **Fit and intent aren't shown side by side yet.** The accounts table shows score and intent
   only; the fit × intent view, comparison and evidence inspector are T4, using the T1 endpoints.
3. **The analyst panel doesn't yet show T2's observations and hypotheses** (T5).
4. **"Signal Engine Intent" shows a check mark at +0.0** because the engine reports `met: true`
   for that rule. That's an engine data quirk, displayed faithfully and unchanged.
5. **The pipeline board needs horizontal scrolling on small screens** (7 columns); this is
   intentional, and the board scrolls inside its own container.
6. **Charts:** 3 of the 4 line colours are below 3:1 contrast. That's mitigated by the legend
   and the table view, but colour alone doesn't identify a line at a glance for low-vision users.
7. **Fonts:** Inter still loads from Google Fonts. Self-hosting would remove the external request.
8. **Contact names:** the fictional `.example` names (e.g. "Ada Placeholder") are deliberately
   obvious, which looks less realistic in a demo.

## 5. Git state

T3 is committed locally as one commit after this report. Nothing pushed, nothing deployed.
