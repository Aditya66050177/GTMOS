"""Vercel serverless entrypoint for the public GTMOS demo.

Vercel routes /api/* here (see vercel.json). The function filesystem is
read-only except /tmp, so the demo's template database lives in /tmp and is
rebuilt from the synthetic CSVs on each cold start. Visitors read it read-only;
the few edits the website allows go to per-browser sandbox copies
(see app/api/public.py).

Local run of the public demo (PowerShell, from the project root):
    uvicorn api.index:app --reload --port 8000
For the full, unguarded local API use:
    uvicorn app.api.main:app --reload --port 8000
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if os.environ.get("VERCEL"):
    os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/gtmos.db")
# The public demo never calls a live LLM; create_public_api() enforces this too.
os.environ["LLM_MODE"] = "mock"

from fastapi import FastAPI  # noqa: E402

from app.api.public import create_public_api  # noqa: E402
from app.db.demo_seed import ensure_demo_database  # noqa: E402

ensure_demo_database()

app = FastAPI(title="GTMOS public demo", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", create_public_api())
