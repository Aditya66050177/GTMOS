"""Vercel serverless entrypoint for the GTMOS API.

Vercel routes /api/* here (see vercel.json). The function filesystem is
read-only except /tmp, so the demo database lives in /tmp and is rebuilt from
the synthetic CSVs on each cold start. That keeps the public sandbox
self-healing: whatever visitors approve or move is reset on the next cold start.

Local run (PowerShell, from the project root):
    uvicorn api.index:app --reload --port 8000
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if os.environ.get("VERCEL"):
    os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/gtmos.db")
os.environ.setdefault("LLM_MODE", "mock")

from fastapi import FastAPI  # noqa: E402

from app.api.main import app as gtmos_api  # noqa: E402
from app.db.demo_seed import ensure_demo_database  # noqa: E402

ensure_demo_database()

app = FastAPI(title="GTMOS", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", gtmos_api)
