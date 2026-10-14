# GTMOS - AI GTM Command Center

## PRODUCT
GTMOS turns a product description into a structured ICP, scores target accounts with an explainable deterministic model, detects buying signals with evidence provenance, recommends next actions, generates human reviewed outreach drafts, and tracks the funnel in a lightweight CRM with analytics.

## ENVIRONMENT & DEPLOYMENT OVERRIDES (Windows / Local Dev)
1. **Database**: Use SQLite for local development via SQLAlchemy (`DATABASE_URL` defaulting to `sqlite:///./gtmos.db`). Code must be database-agnostic (no Postgres-specific features, use generic SQLAlchemy `JSON` column type) so switching to Postgres later only requires updating `DATABASE_URL`. Skip `docker-compose.yml` requirement.
2. **Commands & Scripts**: Use plain Python commands in Windows PowerShell format:
   - Environment setup: `python -m venv .venv` and `.venv\Scripts\activate`
   - Dependencies: `pip install -r requirements.txt`
   - Database initialization: `python -m app.db.init_db`
   - API server: `uvicorn app.api.main:app --reload`
   - Streamlit dashboard: `streamlit run app/dashboard/home.py`
   - Demo execution: `python scripts/demo.py` (Never use bash-only syntax, `make`, or shell scripts).
3. **Paths & OS**: Use `pathlib` for all file paths. Avoid Linux-only dependencies or syntax. All commands must be provided in PowerShell format.
4. **Verification & Testing**:
   - Phase 0 test: Verify database tables exist using SQLAlchemy `inspect` instead of Docker and `information_schema`.
   - Phase 5 n8n: Do not run via Docker. Document execution via `npx n8n` (Node.js) or n8n Cloud free trial in `docs/architecture.md`. Export workflow JSON files.
   - Phase 5 polish: Verify fresh clone using PowerShell README setup steps instead of Docker Compose. Optionally include a `Dockerfile` for future deployment, but do not require Docker to run.

## LOCAL DEV GOTCHAS
1. **SQLite Concurrency & Foreign Keys**: Create the SQLAlchemy engine with `connect_args={"check_same_thread": False}` and enable foreign keys via a `PRAGMA foreign_keys=ON` event listener on connect. Use short-lived sessions so FastAPI and Streamlit can share `gtmos.db` without lock errors.
2. **Streamlit Navigation**: Streamlit auto-detects pages only in a `pages/` folder. Since pages reside in `app/dashboard/`, build navigation explicitly in `home.py` using `st.navigation` and `st.Page` so `accounts.py`, `signals.py`, `pipeline.py`, and `analytics.py` appear in the sidebar.
3. **Pythonpath & Imports**: Always run terminal commands from the project root so package imports (e.g. `app`) resolve properly. Configure `pytest.ini` with `pythonpath = .` and `testpaths = tests`.
4. **Encoding & Windows Line Endings**: Open every CSV file with `encoding="utf-8"` and write files with `newline=""` to prevent Windows line ending (`\r\n`) issues.
5. **Gitignore & Secrets**: Maintain a `.gitignore` covering `.venv`, `gtmos.db`, `.env`, `__pycache__`, and `.pytest_cache`. Never commit real API keys or secrets.
6. **PHASE DISCIPLINE**: Build only the exact phase requested. When finished, stop and wait for the test prompt or user verification. Do not start the next phase independently.

## CORE RULES
1. The LLM interprets and writes. Code decides. The LLM is never used for scoring, arithmetic, filtering, or business rules.
2. LLM output must be structured JSON validated by Pydantic before any engine uses it.
3. All LLM calls go through one module, `app/ai/llm.py`, with a mock mode so the whole app and all tests run with no API key.
4. Every important claim about an account must carry evidence: claim, evidence text, source, detected_at, confidence.
5. No outreach is ever sent automatically. Every draft needs human approval.
6. Use synthetic, clearly labeled demo data only. No scraping.

## STACK
Python 3.11, FastAPI, SQLAlchemy 2, Pydantic v2, SQLite (Local Dev, database-agnostic), Streamlit, Pytest. (PostgreSQL and n8n optional/future).

## FOLDER STRUCTURE
gtmos/
  app/dashboard/ (home.py, accounts.py, signals.py, pipeline.py, analytics.py)
  app/api/ (main.py, routes/)
  app/services/ (icp_engine.py, research_engine.py, signal_engine.py, scoring_engine.py, recommendation_engine.py, personalization.py, analytics_engine.py)
  app/models/, app/schemas/, app/db/, app/ai/ (llm.py, prompts.py, evaluators.py)
  data/ (accounts.csv, contacts.csv, signals.csv)
  scripts/ (demo.py)
  n8n/workflows/, tests/, docs/ (architecture.md, scoring.md, decisions.md)
  .env.example, requirements.txt, README.md

## WORKING STYLE
Execute, do not over explain. After each task, list files changed, how to run it, and how to verify it. Keep functions small and typed. Write tests alongside code. Ask me only if something is truly blocking.
