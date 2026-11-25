# GTMOS final pre-deployment review

Reviewed on 2026-11-25 against commits `feb93c0` (public-demo security) and `29fb1e5`
(dependency split), on branch `claude/modest-darwin-atz53w`. I re-checked the code
rather than relying on earlier reports.

**Conclusion: the public, synthetic-data demo is safe to deploy.** No genuine P0
security issue was found, so no application code changed in this review; it added
tests only. The remaining items are P1 and P2 limitations, listed below. This demo
must never hold real customer data.

---

## 1. Checks performed and results

| # | Area | How it was checked | Result |
|---|---|---|---|
| 1 | Public routes go through the guard | Read `api/index.py` and `app/api/public.py`; every request to `/api/*` passes `PublicDemoGuard`, then routes whose only database access is the overridden `get_db` | ✅ No route opens its own session (`grep SessionLocal` finds only seeding code) |
| 1 | Alternate paths to blocked writes | Trailing slash, double slash, case change, `./` and `../` segments, encoded slash, query string, PUT/DELETE/PATCH, method-override header, HEAD/OPTIONS. Tested in-process **and over real HTTP** with `curl --path-as-is` | ✅ All refused (403, 404 or 405); none reached a handler |
| 1 | Shared data read-only | SQLite opened with `mode=ro`; a direct UPDATE through the shared session fails with "readonly database" | ✅ |
| 1 | Shared reset unreachable | `/web/reset`, `/web/reset/`, `//web/reset`: template file modification time unchanged | ✅ |
| 2 | Guessed or modified ids | Random ids, one-character change, all-zero and all-`f` ids | ✅ Each sees shared data, never the owner's edits |
| 2 | Missing or invalid ids | Empty, uppercase, 31/33 chars, `../` traversal, non-hex | ✅ Reads get shared data; writes get 400 |
| 2 | Expired ids | Fake clock past the 2 h TTL | ✅ Owner falls back to shared data; a later write starts a fresh sandbox |
| 2 | Header injection | Raw socket request with a newline inside `X-Demo-Session` | ✅ Rejected with 400 by the HTTP server (h11) before reaching the app |
| 3 | Reset scope | Reset with another visitor's id format; reset own id | ✅ Only the caller's sandbox is deleted; `had_changes:false` for unknown ids |
| 3 | Capacity | 3 sandboxes with a cap of 2 | ✅ Least-recently-used evicted, file deleted (see P1-3) |
| 3 | Rate limits | General, write and reset buckets; failed resets counted | ✅ 429 with `Retry-After`; a rejected reset counts toward the limit |
| 4 | Error exposure | 404, 422 (bad JSON, wrong types), domain 400s, forced 500 in a route, forced 500 in a service | ✅ No paths, stack traces, SQL, environment names or secrets. 500 bodies are `{"detail": "Internal server error."}` or a fixed sentence; details go to the server log |
| 5 | API docs | `/api/docs`, `/api/openapi.json` | ✅ Informational only (see §3) |
| 6 | Offline AI | `LLM_MODE` = `live`, `LIVE`, `mock`; key empty, invalid or present. Analyst, draft generation and playground called while the Gemini call functions were patched to record any call | ✅ Zero provider calls; the overview reports `llm_mode: mock`. A real server started with `LLM_MODE=live LLM_API_KEY=…` also reported `mock` |
| 7 | Frontend sandbox handling | Read `web/src/lib/api.ts`, `useAsync.ts`, `AppShell.tsx` | ⚠️ Works, but a lost sandbox is not explained (P1-1) |
| 8 | Runtime-only install | Fresh Python 3.12 venv, `pip install -r requirements.txt` | ✅ 159 MB; none of streamlit, pytest, pytest-cov, httpx, pyarrow, pydeck, altair. `requests` is present only as a dependency of `google-genai` |
| 8 | App start + smoke test | `uvicorn api.index:app` from that venv with `VERCEL=1`, then `scripts/smoke_test.py` | ✅ 13/13 checks |
| 8 | Python version consistency | `.python-version`, CI, Dockerfile, README | ⚠️ Mixed 3.11 / 3.12 (P2-2) |

### Test results

| Suite | Result |
|---|---|
| `tests/test_public_demo.py` (task 1 regressions) | 35 passed |
| `tests/test_public_demo_review.py` (this review, adversarial) | 32 passed |
| Smoke test against the slim runtime server | 13/13 |

Full-suite numbers after T1 are in `docs/T1_EXPLAINABILITY_REPORT.md`.

---

## 2. Findings

### Genuine P0 issues
**None.**

### P1 — before anyone relies on the demo for more than a walkthrough

| # | Finding | Detail | Recommendation |
|---|---|---|---|
| P1-1 | **Lost sandbox edits are not explained to the visitor** | If a request lands on another Vercel instance, or the 2 h TTL passes, the visitor silently sees shared data again: an approved draft reverts to pending with no message | Return an `X-Demo-Sandbox: active/none` response header and show a one-line notice ("Your demo edits were reset; temporary sandboxes expire and don't follow you between servers") |
| P1-2 | **Rate limits and sandboxes are per instance** | Counters live in memory, sandboxes in `/tmp`. An abuser spread across instances gets more than the limit | Add a rate-limit rule in Vercel's firewall (check your plan) |
| P1-3 | **Sandbox eviction can be forced** | A client creating many ids (bounded by 30 writes/min/IP per instance) can evict other visitors' sandboxes once 200 exist | Acceptable for disposable demo data; the firewall rule in P1-2 reduces it |
| P1-4 | **The browser id is not authentication** | It is a random 128-bit value: guessing is infeasible, but anyone who sees it (shared screen, browser devtools) can act on that sandbox | Never use it for real data. Real pilots need real authentication and per-customer workspaces |

### P2 — hardening and housekeeping

| # | Finding | Detail |
|---|---|---|
| P2-1 | Session regex uses `$` | `^[a-f0-9]{32}$` also matches the id plus one trailing newline. Not reachable over real HTTP (h11 rejects newlines in headers, verified). Fix: `fullmatch` or `\Z` |
| P2-2 | Python version labels disagree | `.python-version` 3.12 (deploy target); CI, Dockerfile and README say 3.11. Tests pass on 3.11, 3.12 and 3.13. Add 3.12 to CI and align the docs |
| P2-3 | `.env.example` lists no `DEMO_*` variables | They're documented in `docs/deployment.md`, with defaults that are safe |
| P2-4 | Public OpenAPI lists blocked routes | Informational (see §3) |
| P2-5 | Streamlit `use_container_width` deprecation warnings | Local dashboard only; pinned version works |
| P2-6 | No security headers | No auth, cookies or user-supplied HTML (no `dangerouslySetInnerHTML`; React escapes text), so the risk is low. Add `X-Content-Type-Options`, `Referrer-Policy` and `frame-ancestors` in `vercel.json` later |

---

## 3. API documentation exposure

`/api/docs` and `/api/openapi.json` are public and list every route of the full API,
including ones the guard blocks. **This is informational, not a vulnerability:** the
guard decides on method + path, independently of what the docs show, and every listed
write that isn't allowlisted returns 403 (tested). The docs help reviewers and
interviewers explore the API, so I've kept them. Hide them only once real data exists.

## 4. Serverless-specific limitations

- **Cold start ≈ 4.5 s** while the template database is rebuilt in `/tmp`.
- **No persistence:** the template and all sandboxes vanish when an instance stops.
- **Sandboxes don't follow visitors between instances** (P1-1).
- **Per-instance rate limits** (P1-2).
- **Vercel's runtime choices are unverified from here:** vercel.com was unreachable from
  this environment, so which Python version and requirements file Vercel uses, and how
  its FastAPI auto-detection treats this layout, are confirmed only by the first build log.

## 5. Environment variables

| Variable | Read by | Default | Set it on Vercel? |
|---|---|---|---|
| `VERCEL` | `api/index.py` | set by Vercel | Automatic |
| `DATABASE_URL` | `app/core/config.py` | `sqlite:///./gtmos.db`; `sqlite:////tmp/gtmos.db` on Vercel | **No** |
| `LLM_MODE` | config; forced to `mock` by `api/index.py` and `create_public_api()` | `mock` | No (ignored) |
| `LLM_API_KEY` | config (local live mode only) | empty | **Never** for the public demo |
| `LLM_PROVIDER`, `LLM_MODEL` | config | `gemini`, `gemini-3.8-flash` (unverified name) | No |
| `DEMO_MAX_BODY_BYTES` | public guard | `16384` | Optional |
| `DEMO_RATE_LIMIT_PER_MINUTE` | public guard | `120` | Optional |
| `DEMO_WRITE_LIMIT_PER_MINUTE` | public guard | `30` | Optional |
| `DEMO_RESET_LIMIT_PER_MINUTE` | public guard | `5` | Optional |
| `DEMO_MAX_SANDBOXES` | public guard | `200` (~0.4 MB each) | Optional |
| `DEMO_SANDBOX_TTL_SECONDS` | public guard | `7200` | Optional |
| `DEMO_SANDBOX_DIR` | public guard | next to the template DB | Optional |

**No environment variables are required** for the public demo.

## 6. Manual deployment steps

1. Give Claude GitHub access to `Aditya66050177/GTMOS` (or push the branch yourself), and
   merge or select the branch to deploy.
2. In Vercel, choose **Add New → Project** and import the repository. Leave **Root
   Directory** at the repository root and the framework preset on **Other**; `vercel.json`
   supplies the build command, output directory, function config and rewrites.
3. Don't add environment variables. In particular, don't add `LLM_API_KEY`.
4. Click **Deploy**, then open the build log and confirm:
   - the Python function installed from the root `requirements.txt`,
   - the Python version used (3.12 expected from `.python-version`),
   - the function size is under the platform limit,
   - nothing auto-detected a second FastAPI entrypoint.
5. Optional but recommended: add a rate-limit rule for `/api/*` in Vercel's firewall settings.

## 7. Post-deployment verification

```powershell
python scripts/smoke_test.py https://<your-app>.vercel.app --frontend
```

All checks should pass: health, data endpoints, the Acme score (69.5, Priority 3), the
offline LLM, the 403 on blocked writes, the 413 on oversized bodies, the 400 without a
session, sandbox isolation and reset. On a multi-instance deployment, "approval stays in
the visitor's sandbox" can occasionally fail because the follow-up request reached
another instance; re-run before treating it as a bug.

Then, manually:
1. Open `/` and `/app`. Confirm the pages load and the API card on the landing page fills in.
2. Approve a draft in the review queue; refresh; it should still be approved (same instance).
3. Click **Reset my sandbox**; the draft returns to pending.
4. Open `/api/health` directly: `{"status":"healthy","database":"connected"}`.
