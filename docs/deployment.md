# Deploying the GTMOS web app (Vercel)

The public site is two pieces in one Vercel project:

| Piece | Path | What Vercel does with it |
|-------|------|--------------------------|
| React frontend (Vite + Tailwind) | `web/` | `buildCommand` builds it to `web/dist`, served as static files |
| FastAPI backend | `api/index.py` | Python serverless function; every `/api/*` request is rewritten to it |

`vercel.json` holds the build command, output folder, rewrites and function settings.

## How the database works on Vercel

Serverless functions have a read-only filesystem except `/tmp`. On a cold start,
`api/index.py` points `DATABASE_URL` at `sqlite:////tmp/gtmos.db` and rebuilds the
synthetic demo workspace from `data/*.csv` (about 3 seconds). Consequences:

- The demo is a **sandbox**: approvals, edits and stage changes made by visitors live
  until that function instance goes cold, then reset on their own.
- Each warm instance has its own copy, so two visitors can occasionally see different
  sandbox state. That's fine for a demo. For persistent data, set `DATABASE_URL` to a
  hosted Postgres (for example Neon or Supabase) in the Vercel project's environment variables.
- Signal dates are re-anchored to today on every rebuild, so recency decay never
  silently zeroes the demo's buying intent.

## First deploy

1. Push this branch to GitHub (or merge it to `main`).
2. In Vercel: **Add New → Project → Import** the `gtmos` repository.
3. Leave **Root Directory** as the repository root. Vercel reads `vercel.json`, so the
   framework preset can stay on "Other".
4. Optional environment variables (Project → Settings → Environment Variables):
   - `LLM_MODE` = `mock` (default; no API key needed, no cost)
   - `LLM_MODE` = `live` plus `LLM_API_KEY` = your Gemini key, to use a real model.
     Leave this off for a public demo unless you want to pay for visitors' traffic.
5. Deploy. Check `https://<your-app>.vercel.app/api/health` returns `{"status": "healthy"}`.

## Run the web app locally (PowerShell)

```powershell
# Terminal 1 — API (from the project root, venv active)
pip install -r requirements-dev.txt
uvicorn api.index:app --reload --port 8000   # the guarded public API, as deployed

# Terminal 2 — frontend
cd web
npm install
npm run dev     # http://localhost:5173, proxies /api to port 8000
```

`npm run build` then `npx vite preview` serves the production build on port 4173
with the same proxy.

## Things to know

- Python dependencies for the function come from the root `requirements.txt`, which
  holds runtime packages only (about 160 MB installed, measured on Python 3.12).
  Streamlit and test tools live in `requirements-dev.txt`, so whichever file Vercel
  picks up, the bundle stays small.
- The Streamlit dashboard (`app/dashboard/`) is still the internal tool for local use.
  Streamlit can't run on Vercel; the React app replaces it for the public site.
- Interactive API docs are served at `/api/docs`.

## Public demo safeguards

The deployed API is built by `app/api/public.py`, not the full local API. Read
DEPLOYMENT_READINESS.md for why. In short:

| Safeguard | Behaviour | Limit |
|---|---|---|
| Read-only shared data | Shared demo data is opened with SQLite `mode=ro` | Rebuilt on each cold start |
| Write allowlist | Only draft, edit, approve, reject, log-as-sent, playground, analyst and reset are allowed. Everything else returns **403** | Defined in `WRITE_POLICY` |
| Per-visitor sandbox | Allowed edits go to a private copy of the database keyed by a random `X-Demo-Session` id from the browser | At most `DEMO_MAX_SANDBOXES` (200), each expires after `DEMO_SANDBOX_TTL_SECONDS` (2 h) |
| Reset | Deletes only the caller's sandbox; never rebuilds shared data | `DEMO_RESET_LIMIT_PER_MINUTE` (5) |
| Body cap | Bodies over `DEMO_MAX_BODY_BYTES` (16 KB) get **413**, with or without `Content-Length` | |
| Rate limits | Per client IP: `DEMO_RATE_LIMIT_PER_MINUTE` (120) for all requests, `DEMO_WRITE_LIMIT_PER_MINUTE` (30) for writes; over the limit gets **429** + `Retry-After` | **Per instance only** |
| Offline LLM | `LLM_MODE` is forced to `mock` | Live Gemini is never reachable from the public site |

**Not global.** Rate-limit counters and sandboxes live in each serverless
instance's memory and `/tmp`. Vercel can run several instances, so an abuser
spread across them gets more than the limit, and a visitor whose next request
lands on another instance sees the shared data instead of their own edits.
For real protection, also add a rate-limit rule in Vercel's firewall settings
(check the plan you're on), and move to managed Postgres before pilots.

**Not authentication.** The `X-Demo-Session` id only keeps visitors' demo edits
apart. It is random, carries no personal data, and must never guard real customer data.

## Environment variables

| Variable | Default | Public demo | Notes |
|---|---|---|---|
| `DATABASE_URL` | `sqlite:///./gtmos.db` | leave unset | On Vercel `api/index.py` uses `sqlite:////tmp/gtmos.db` |
| `LLM_MODE` | `mock` | ignored, always `mock` | Only the local full API can use `live` |
| `LLM_API_KEY` | empty | **do not set** | Secret. Only for local live-mode testing |
| `LLM_PROVIDER` / `LLM_MODEL` | `gemini` / `gemini-3.8-flash` | ignored | Model name unverified; confirm before using live mode |
| `DEMO_MAX_BODY_BYTES` | `16384` | optional | |
| `DEMO_RATE_LIMIT_PER_MINUTE` | `120` | optional | per instance |
| `DEMO_WRITE_LIMIT_PER_MINUTE` | `30` | optional | per instance |
| `DEMO_RESET_LIMIT_PER_MINUTE` | `5` | optional | per instance |
| `DEMO_MAX_SANDBOXES` | `200` | optional | ~0.5 MB of `/tmp` each |
| `DEMO_SANDBOX_TTL_SECONDS` | `7200` | optional | |
| `DEMO_SANDBOX_DIR` | next to the template DB | optional | |

## Smoke test after deploying

```powershell
python scripts/smoke_test.py https://<your-app>.vercel.app --frontend
```

It checks health, the data endpoints, the Acme score, that writes are blocked,
that oversized bodies are rejected, and that an approval stays in a sandbox. It
exits non-zero on any failure.
