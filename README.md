# GTMOS — AI GTM Command Center

> An explainable, evidence-driven Go-To-Market intelligence system that turns a product description into scored accounts, detected buying signals, recommended actions, and human-reviewed outreach — tracked through a full CRM pipeline with AI analytics.

---

## Three Questions GTMOS Answers

1. **Who should I contact right now?** — Scored and tiered accounts with explainable fit breakdowns.
2. **Why do they matter?** — Evidence-backed buying signals extracted from research notes.
3. **What should I say to them?** — LLM-drafted outreach grounded only in verified evidence, requiring human approval before sending.

---

## Product Flow

```
Product Description
       │
       ▼
 ICP Engine (LLM)
 ─────────────────────────────────────────────────────────
  Generates structured Ideal Customer Profile:
  industries, employee range, geographies,
  pain points, tech stack, exclusion criteria
       │
       ▼
 Research Engine (LLM extraction)
 ─────────────────────────────────────────────────────────
  Reads raw research notes → extracts candidate signals
  Fuzzy evidence check rejects unsupported claims
  Accepted signals stored with evidence, source, date
       │
       ▼
 Scoring Engine (100-pt deterministic)
 ─────────────────────────────────────────────────────────
  ICP Fit /30 · Company Fit /20 · Tech Fit /15
  Buying Intent /20 (signal engine) · Geo Fit /15
  → Priority 1 / 2 / 3 / Low tier
       │
       ▼
 Recommendation Engine (deterministic rule table)
 ─────────────────────────────────────────────────────────
  Action: CONTACT / PRIORITIZE / NURTURE / RESEARCH / DEPRIORITIZE
  Suggested persona and outreach angle from signal type
       │
       ▼
 Personalization Engine (LLM, fact-checked)
 ─────────────────────────────────────────────────────────
  Drafts message from top 3 evidence-backed signals
  Guardrail rejects any invented statistics or events
  Draft stored with original_body and evidence_ids
       │
       ▼
 Human Review Queue
 ─────────────────────────────────────────────────────────
  pending → approved / rejected
  Only approved drafts can be marked as sent
       │
       ▼
 CRM Pipeline + Analytics
 ─────────────────────────────────────────────────────────
  Research → Contacted → Replied → Meeting → Opportunity → Won
  Every stage change logs a timestamped Activity
  AI Analyst answers natural-language funnel questions
```

---

## Worked Example — Acme Technologies

Acme Technologies is a B2B SaaS company (250 employees, US, Zendesk + Salesforce, Series B, support team of 18).

| Component | Score | Max | Rule Applied |
|-----------|-------|-----|--------------|
| ICP Fit | 30 | 30 | Industry exact match (20) + pain point overlap (10) |
| Company Fit | 20 | 20 | 250 employees inside 50–500 range |
| Technology Fit | 15 | 15 | Zendesk + Salesforce match ICP tech requirements |
| Buying Intent | 12 | 20 | support_hiring signal (weight 20, 0.8 confidence, 0.7 decay) |
| Geography Fit | 15 | 15 | US exact match |
| **Total** | **~87** | **100** | **Priority 2** |

**Recommendation:** PRIORITIZE — Priority 2 account with very high intent. Prioritize for immediate outreach.

**Suggested angle:** Support team scaling and efficiency → VP of Customer Support

---

## Core Principles

| Principle | How it's enforced |
|-----------|------------------|
| **Explainability** | Every score has a per-component breakdown with rule + points |
| **Evidence provenance** | Every signal carries source, date, confidence, and evidence text |
| **AI interprets, code decides** | LLM extracts and drafts; scoring and recommendations are deterministic |
| **Human in the loop** | Outreach requires explicit approval before mark-as-sent |
| **Grounded drafts** | Personalization guardrail rejects any claim not found in evidence |
| **Mock-first testing** | Full test suite runs without an API key via LLMService(mode="mock") |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Streamlit Dashboard                 │
│   Home · Accounts · Signals · Pipeline · Analytics  │
└────────────────────┬────────────────────────────────┘
                     │ HTTP
┌────────────────────▼────────────────────────────────┐
│              FastAPI Backend (port 8000)             │
│  /products  /accounts  /pipeline  /analytics        │
│  /drafts    /signals   /health                      │
└────────────────────┬────────────────────────────────┘
                     │ SQLAlchemy
┌────────────────────▼────────────────────────────────┐
│              SQLite (gtmos.db)                       │
│  accounts · scores · signals · drafts               │
│  contacts · activities · opportunities              │
│  products · icp_profiles                            │
└─────────────────────────────────────────────────────┘
         │ LLMService (mock/live)
┌────────▼──────────────────┐
│   Google Gemini API       │  (only for ICP gen,
│   (live mode only)        │   signal extraction,
└───────────────────────────┘   personalization,
                                analyst routing)
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + Uvicorn |
| Dashboard | Streamlit |
| ORM | SQLAlchemy (SQLite → Postgres-ready) |
| Validation | Pydantic v2 |
| Analytics | Pandas + SQL |
| LLM | Google Gemini (mock adapter for testing) |
| Testing | pytest (163 tests, all phases) |
| CI | GitHub Actions |
| Automation | n8n (no Docker required) |

---

## Module Summaries

| Module | Purpose |
|--------|---------|
| `app/services/icp_engine.py` | LLM → structured ICPProfile (Pydantic-validated) |
| `app/services/research_engine.py` | CSV research notes → fuzzy-validated Signal objects |
| `app/services/signal_engine.py` | Recency-decayed, deduplicated intent score (0–20) |
| `app/services/scoring_engine.py` | 100-pt deterministic scorer, pure function |
| `app/services/recommendation_engine.py` | Rule table → action, persona, angle. No LLM. |
| `app/services/personalization.py` | LLM draft + factual guardrail |
| `app/services/crm_service.py` | Stage transitions, activity log, mark-as-sent |
| `app/services/analytics_engine.py` | SQL+pandas funnel metrics, trends, breakdowns |
| `app/services/analyst_service.py` | Routes NL questions → deterministic analytics |
| `app/ai/llm.py` | LLMService with mock adapter for CI |
| `app/ai/evaluators.py` | ICP accuracy, signal precision/recall, consistency |
| `app/ai/run_eval.py` | CLI runner → docs/evaluation.md + timestamped JSON |

---

## Evaluation Results (Mock Mode)

> Computed by `python -m app.ai.run_eval --mode mock` on the 100 labeled accounts and 60 labeled signals dataset.
> See [docs/evaluation.md](docs/evaluation.md) for detailed confusion matrices and per-type breakdowns.

| Metric | Measured Value | Evaluation Set |
|--------|----------------|----------------|
| **ICP Tier Accuracy** | **57.0%** (57 / 100) | 100 labeled accounts (`data/eval/eval_accounts.csv`) |
| **Priority 1 Recall** | **100.0%** | All labeled high-fit accounts correctly tiered |
| **Low Fit Recall** | **100.0%** | All non-fit / disqualified accounts filtered |
| **Signal Extraction Precision** | **100.0%** | 60 labeled signal texts (`data/eval/eval_signals.csv`) |
| **Signal Extraction Recall** | **100.0%** | Supported signals extracted via keyword grounding |
| **Signal Extraction F1** | **100.0%** | Zero false negatives across all 7 signal categories |
| **Unsupported Claim Rate (Signals)** | **0.0%** | Unsupported claims rejected by extraction filter |
| **Unsupported Claim Rate (Drafts)** | **0.0%** | 30/30 generated outreach drafts strictly grounded |
| **Scoring Determinism** | **100.0% (True)** | 5 repeated runs across 100 accounts (0 drift) |

---

## PowerShell Run Steps

```powershell
# 1. Create and activate virtual environment (Python 3.11)
py -3.11 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize SQLite DB tables (optional manual step)
python -m app.db.init_db

# 4. Run the full demo (resets DB, generates ICP, scores 150 accounts, seeds 40-day pipeline)
python scripts/demo.py

# 5. Start the FastAPI backend
.\.venv\Scripts\uvicorn.exe app.api.main:app --host 127.0.0.1 --port 8000

# 6. Start the Streamlit dashboard (new terminal, venv activated)
.\.venv\Scripts\streamlit.exe run app/dashboard/home.py --server.port 8501

# 7. Run all tests with services coverage
python -m pytest --cov=app/services -v

# 8. Run the evaluation suite
python -m app.ai.run_eval --mode mock

# 9. Ask the AI analyst questions
python scripts/ask_three_questions.py
```

---

## Status Checklist

- [x] **Phase 0** — Foundation: DB, models, FastAPI, LLM mock
- [x] **Phase 1** — ICP engine, research engine, 100-pt scoring, 150 synthetic accounts
- [x] **Phase 2** — Signal engine with recency decay, evidence validation, negative signals
- [x] **Phase 3** — Recommendation engine, personalization + guardrail, human review queue
- [x] **Phase 4** — CRM pipeline, stage transitions, analytics engine, AI analyst
- [x] **Phase 5** — Evaluation suite, n8n workflows, demo script, full documentation, CI
- [x] **163 tests passing** (all phases, mock mode)
- [x] **GitHub Actions** CI runs pytest on every push

---

## Roadmap

| Feature | Status |
|---------|--------|
| Postgres migration (one config line) | Ready when needed |
| Live LLM mode with Gemini API | Config via `LLM_MODE=live` + `LLM_API_KEY` |
| Email/Slack integration via n8n | Workflows in `n8n/workflows/` |
| Multi-product support | DB schema supports it |
| Contact enrichment API | Extension point in `CRMService` |
| Bulk CSV import via dashboard | Planned |
| Role-based access control | Planned |

---

## Why This Project

Most GTM tools are black boxes: they score accounts without explaining why, send AI-drafted emails without human review, and give analytics without evidence. GTMOS is built on the opposite philosophy:

- **Every score is explainable** — see exactly which rule contributed which points
- **Every signal has a source** — extraction is grounded, rejected claims are logged
- **No email is sent automatically** — humans approve, humans send
- **Every metric is computed, not invented** — the AI analyst only cites numbers that came from the analytics engine
- **The test suite is the contract** — 163 tests across all phases, runnable without an API key

> All dataset accounts, contacts, and signals are 100% synthetic demo data. No actual company data is scraped or used.
