# GTMOS deployment readiness (Phase A audit)

Audited 2026-11-25 against branch `claude/modest-darwin-atz53w` at commit `322800d`.
Nothing was changed during this audit except this file.

**Verdict: not ready for a public deploy.** The app builds, tests pass and it runs in a
Vercel-like environment with no API key, but anyone on the internet could edit or wipe the
shared demo, store arbitrary personal data in it, and send unbounded payloads. The deploy
itself is also blocked on GitHub access and on one dependency question I could not verify.

---

## 1. Repository state

| Item | Finding |
|---|---|
| Branch | `claude/modest-darwin-atz53w`, working tree clean |
| Unpushed commits | 2 (`261500f` fixes, `322800d` web app). Push fails: Claude has no GitHub access to `Aditya66050177/GTMOS` (HTTP 403) |
| Tests | 190 passed (`python -m pytest`), isolated temp database, no warnings |
| Frontend build | `npm run build` passes (tsc + vite) |
| Secrets | None found in the working tree or the git history. `.env` and `*.db` are gitignored and untracked. The test keys are obvious placeholders |
| API key needed? | No. Default `LLM_MODE=mock` runs everything offline. `LLM_MODE=live` with no key fails loudly with a clear message, not silently |

## 2. What was verified, and how

| Check | Method | Result |
|---|---|---|
| Cold start in Vercel-like mode | `VERCEL=1`, no `DATABASE_URL`, imported `api/index.py` | DB placed at `/tmp/gtmos.db`, demo seeded, **4.5 s** cold start |
| Health endpoint | `GET /api/health` | `200 {"status":"healthy","database":"connected"}` |
| Frontend → API | `web/src/lib/api.ts` calls relative `/api/...` | Same-origin; works when frontend and API share a domain (the Vercel setup). No CORS needed |
| Path traversal | `GET /api/../../etc/passwd` | 404. No route reads files from user input; CSV paths are fixed server-side |
| Unknown records | `GET /api/accounts/999999` | Clean 404 |
| Function size, `api/requirements.txt` | `pip install --target`, measured | **162 MB** |
| Function size, root `requirements.txt` | same | **449 MB** (Streamlit + pyarrow alone ≈ 200 MB) |
| Vercel docs | Tried to read vercel.com | **Not reachable from this environment.** Vercel behaviour below is unverified |

## 3. Deployment blockers

### P0 — must fix before a public deploy

| # | Blocker | Evidence | Fix |
|---|---|---|---|
| P0-1 | **Anyone can change the shared demo for every visitor.** All write routes are public and unauthenticated: `POST /accounts/{id}/research`, `/stage`, `/contacts`, `/mark_sent`, `/score`, `POST /products`, `/generate-icp`, `/score-all`, `PATCH /drafts/{id}`, approve/reject, `POST /web/reset` | My probe posted a research note for Acme; after `score-all`, Acme went from **69.5 (Priority 3) to 83.9 (Priority 2)** for everyone. That breaks the landing page's "rumour test" claim | A public "demo mode" that turns off the routes the website doesn't need, and caps the ones it does |
| P0-2 | **The public demo stores arbitrary personal data.** `POST /accounts/{id}/contacts` accepted `name="Real Person", email="someone@realcompany.com"` and serves it back to every visitor | Probe returned 200 and the record | Disable contact creation in demo mode |
| P0-3 | **No size limits on several inputs.** Research text, draft body, analyst question and product name are unbounded | 200 KB research note, 1 MB draft body, 100 KB question, 50 KB product name: all accepted with 200 | `max_length` on every request schema, plus a global body-size cap |
| P0-4 | **No rate limiting.** `POST /web/reset` rebuilds the database (2.7 s of CPU) and `score-all` takes 0.9 s; both can be called in a loop. In live LLM mode, `/analytics/ask` and `/personalize` would spend your Gemini budget | Timings measured above | Per-IP limit in the app (only per instance on serverless), and Vercel's firewall rate limits as the real control (to verify in the dashboard). Throttle reset |
| P0-5 | **Synthetic contacts look like real people.** `data/contacts.csv` pairs invented names with real-looking domains (`acmetechnologies.com`, `fintechpulse.com`) and `linkedin.com/in/...` URLs that may belong to real people. Some account domains (`acme.com`, `nexuscloud.io`) are real sites | `head data/contacts.csv` | Move every synthetic email and domain to reserved `.example` domains; drop the LinkedIn URLs |
| P0-6 | **Which `requirements.txt` Vercel installs is unverified.** If Vercel installs the root file, the function is 449 MB, over the 250 MB limit I remember, and the deploy fails. I designed for `api/requirements.txt` but could not confirm Vercel reads it | Sizes above; docs unreachable | Make the root file runtime-only and move the dev tools to `requirements-dev.txt`. This conflicts with CLAUDE.md's `pip install -r requirements.txt` setup step, so it needs your OK |
| P0-7 | **Code is not on GitHub.** Vercel deploys from GitHub; push returns 403 | `git push` output | You: install the Claude GitHub App on the repo or reconnect GitHub, then authorise the push |

### P1 — must fix before customer pilots

| # | Gap | Why it matters |
|---|---|---|
| P1-1 | **No persistence.** SQLite in `/tmp` resets on every cold start and differs between instances | A pilot customer's ICP, accounts and approvals would vanish. Needs managed Postgres (Neon or Supabase) via `DATABASE_URL`; the code is already database-agnostic |
| P1-2 | **No authentication or tenant isolation** | Every visitor sees and edits the same data. A pilot needs at least one isolated workspace per customer behind real login. Don't build fake auth; use a provider (e.g. Clerk or Supabase Auth) or run pilots supervised on a private deploy |
| P1-3 | **The public deploy can't run live LLM calls safely**: no auth, no spend cap | Keep the public site in mock mode. Pilots need live mode behind auth, with per-workspace limits |
| P1-4 | **Unverified Gemini model name** (`gemini-3.8-flash` in config and `.env.example`) | Couldn't check it from here. Confirm it exists before turning on live mode |
| P1-5 | **Error messages leak internals.** `/health` and `/personalize` return `str(e)` on a 500; bad dates are silently replaced with "now" | Return generic messages, log the details, reject invalid dates with 422 |
| P1-6 | **No data import or export.** Pilots can't bring their own accounts | CSV import with validation is the minimum (Phase G) |
| P1-7 | **Analytics are simulated.** The pipeline is a seeded 40-day simulation | Fine for the demo; a pilot needs real activity logging and must label simulated data clearly |
| P1-8 | **Dependencies are unpinned** (`fastapi`, `sqlalchemy`, … with no versions) | A deploy can break when a library releases. Pin versions for reproducible builds |
| P1-9 | **No privacy or data-handling statement** | Needed before anyone uploads prospect data (GDPR/CCPA exposure: contacts are personal data) |

### P2 — can wait until after validation

- Security headers (CSP, `X-Frame-Options`, `Referrer-Policy`) in `vercel.json`. Low risk now: no auth, no cookies, no user-supplied HTML.
- `/api/docs` and `/api/openapi.json` are public. Harmless for a demo (they're even a portfolio plus), but hide or gate them for pilots.
- 4.5 s cold start. Acceptable for a demo; prebuilding the database at deploy time would cut it.
- Evaluation quality: 57% tier accuracy, and the eval checks a simplified copy of the signal matcher, not the real extractor. That matters for credibility claims, not for deploying.
- Streamlit dashboard and React app overlap. Keep Streamlit local-only.
- Python version mismatch: CLAUDE.md says 3.11, this container runs 3.13, and Vercel's default is unverified. Add a `.python-version` file.

## 4. Is the Vercel architecture actually compatible?

**Probably yes for a demo, with two caveats I could not verify** (vercel.com was unreachable):

1. **Dependency file selection (P0-6).** The fix above removes the uncertainty.
2. **FastAPI auto-detection.** Recent Vercel versions can auto-detect FastAPI apps. This repo has an `app/` package and an explicit `functions` + `rewrites` config for `api/index.py`, and I can't confirm how Vercel resolves that. The first deploy's build log will show it. If it misbehaves, the fallback is to host the FastAPI backend on Render, Railway or Fly.io (all run plain `uvicorn`, no Docker required) and point the frontend at it with a `VITE_API_BASE` variable.

Things that are compatible as written: the read-only filesystem is handled (database in `/tmp`), no background workers or WebSockets are used, the 30 s `maxDuration` covers a 4.5 s cold start, and `data/*.csv` plus `scripts/` are needed at runtime and are not excluded.

**SQLite on serverless is only acceptable because the demo data is disposable.** No customer data should go onto this setup.

## 5. Recommended first customer segment (hypothesis, not validated)

**Founder-led B2B SaaS companies at roughly seed to Series A (about 5–50 people), where a founder or the first one or two sellers still run outbound themselves.**

How it compares with the other options, using GTMOS as it exists today:

| Segment | Pain | Reachability | Will try new tools | Ability to pay | Fit today |
|---|---|---|---|---|---|
| **Founder-led B2B SaaS** | High: founders do research, targeting and writing themselves | High: founders are public on LinkedIn and X | High | Low–medium | **Best**: one product, one ICP, low volume, and they value explainability and control |
| Small B2B SaaS sales teams | Medium–high | Medium | Medium; often locked into existing tools | Medium | Needs CRM sync and seats, which GTMOS lacks |
| Outbound agencies | Very high | High | High | Medium–high | **Poor today**: they need many clients and ICPs, volume, enrichment and sending tools, none of which exist |
| Technical-product sellers | Medium | Medium | Medium | Medium–high | Overlaps founder-led; too broad as a first segment |

This is reasoning from GTMOS's current capabilities, not customer evidence. Phase D should test it in discovery calls before committing.

## 6. Next three implementation tasks (priority order)

1. **Public-safety hardening (fixes P0-1 to P0-5).** Add a `DEMO_MODE` setting that blocks the write routes the website doesn't use and keeps only sandbox actions (draft review, mark-as-logged, playground, throttled reset). Add `max_length` limits to every request schema, a body-size cap, simple per-IP rate limiting (documented as per-instance only), and generic 500 messages. Move synthetic contacts to `.example` domains with no LinkedIn URLs. Add tests for each.
2. **Deployment hardening (fixes P0-6, P1-8, part of P1-5).** Split runtime and dev dependencies (needs your decision on CLAUDE.md's install step), pin versions, add `.python-version`, add a production smoke-test script for `/api/health` and the key pages, and write the environment-variable documentation. Then, once GitHub access exists and you authorise it: push, and you import the repo into Vercel.
3. **Honest demo framing and a pilot call to action (rest of Phase B).** Add a persistent "Demo — synthetic data" banner, a limitations and data-handling section, and a "Become a design partner" link (`mailto:` or a link to your calendar, so the site itself collects no personal data).
