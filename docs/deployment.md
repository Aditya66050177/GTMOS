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
pip install -r requirements.txt
uvicorn api.index:app --reload --port 8000

# Terminal 2 — frontend
cd web
npm install
npm run dev     # http://localhost:5173, proxies /api to port 8000
```

`npm run build` then `npx vite preview` serves the production build on port 4173
with the same proxy.

## Things to know

- Python dependencies for the function come from `api/requirements.txt` (no Streamlit,
  so the bundle stays small). If a deploy log shows Vercel installing the root
  `requirements.txt` instead and the function exceeds the size limit, move Streamlit,
  pytest and friends into a `requirements-dev.txt`.
- The Streamlit dashboard (`app/dashboard/`) is still the internal tool for local use.
  Streamlit can't run on Vercel; the React app replaces it for the public site.
- Interactive API docs are served at `/api/docs`.
