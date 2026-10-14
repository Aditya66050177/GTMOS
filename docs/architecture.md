# GTMOS System Architecture

> GTMOS (Go-To-Market Operating System) is an AI-powered GTM intelligence platform built on FastAPI, SQLite, Streamlit, and Pydantic with a mock-first LLM adapter for zero-API-key development and testing.

---

## System Overview

```
 ┌──────────────────────────────────────────────────────────────┐
 │                   Streamlit Dashboard (:8501)                │
 │   Home  ·  Accounts  ·  Signals  ·  Pipeline  ·  Analytics  │
 └─────────────────────────┬────────────────────────────────────┘
                           │ HTTP (local)
 ┌─────────────────────────▼────────────────────────────────────┐
 │              FastAPI Backend (:8000)                         │
 │                                                              │
 │  /products          /accounts/{id}/score                     │
 │  /accounts          /accounts/{id}/stage                     │
 │  /accounts/{id}     /accounts/{id}/contacts                  │
 │  /pipeline          /accounts/{id}/activities                │
 │  /analytics/funnel  /accounts/{id}/mark_sent                 │
 │  /analytics/trends  /analytics/ask                           │
 │  /drafts/{id}       /health                                  │
 └────────────┬──────────────────────────────────────────────────┘
              │ SQLAlchemy ORM
 ┌────────────▼──────────────────────────────────────────────────┐
 │                   SQLite (gtmos.db)                           │
 │                                                               │
 │  accounts       scores          signals                       │
 │  contacts       activities      opportunities                 │
 │  products       icp_profiles    drafts                        │
 └───────────────────────────────────────────────────────────────┘
              │
 ┌────────────▼──────────────────────────────────────────────────┐
 │            LLMService (mock | live)                           │
 │                                                               │
 │  mock: returns deterministic fixture data per schema          │
 │  live: calls Google Gemini API with Pydantic validation       │
 └───────────────────────────────────────────────────────────────┘
```

---

## Data Flow

```
Product Description
    │
    ▼ ICPEngine (LLM → Pydantic ICPProfile)
Structured ICP: industries, employee range, geographies,
                pain points, tech stack, exclusion criteria
    │
    ▼ ResearchEngine (LLM extracts signals from raw text)
Candidate Signals → fuzzy evidence check → accepted/rejected
    │
    ▼ SignalEngine (deterministic)
Intent score 0–20: weights × confidence × recency decay
Negative signals: too_small, wrong_industry, wrong_geography
    │
    ▼ ScoringEngine (deterministic, 100pt)
ICP Fit /30 · Company Fit /20 · Tech Fit /15
Intent /20 · Geography /15  →  Priority 1/2/3/Low
    │
    ▼ RecommendationEngine (deterministic rule table)
Action: CONTACT / PRIORITIZE / NURTURE / RESEARCH / DEPRIORITIZE
Persona + Angle: from signal type mapping
    │
    ▼ PersonalizationEngine (LLM → draft → fact guardrail)
Draft references only verified evidence IDs
Guardrail rejects invented statistics or events
    │
    ▼ Human Review Queue
pending → approved (only then) → mark_sent → Contacted
    │
    ▼ CRM Pipeline
Research → Contacted → Replied → Meeting → Opportunity → Won
Every move: timestamped Activity log
    │
    ▼ AnalyticsEngine (SQL + pandas, no LLM)
Funnel totals · Stage-to-stage conversions · Weekly trends
Tier/Industry/Angle breakdowns
    │
    ▼ AnalystService (LLM routing + deterministic execution)
Natural language → predefined analytics function → grounded explanation
```

---

## AI vs Deterministic Split

| Component | Type | Rationale |
|-----------|------|-----------|
| ICP generation | **LLM** | Requires language understanding of product description |
| Signal extraction | **LLM** | Requires reading and interpreting research text |
| Evidence guardrail | **Deterministic** | Keyword match — no hallucination allowed |
| Scoring (all 5 components) | **Deterministic** | Reproducibility + explainability |
| Recommendation action | **Deterministic** | Rule table — no LLM decision-making for sales actions |
| Draft generation | **LLM** | Creative language, grounded by evidence IDs |
| Draft fact-check | **Deterministic** | Number/event check against evidence |
| Analytics computation | **Deterministic** | SQL + pandas — no arithmetic by LLM |
| Analyst explanation | **LLM** | Explains pre-computed numbers, cannot invent new ones |

---

## Database Schema Overview

```
products          → id, name, description, target_market, geography, price_range
icp_profiles      → id, product_id, industries, min/max_employees, geographies,
                     pain_points, technologies, exclusions
accounts          → id, name, industry, country, employee_count, description,
                     technology_stack, funding, support_team_size, stage
scores            → id, account_id, product_id, total_score, tier,
                     icp_fit, company_fit, technology_fit, intent_score, geography_score
signals           → id, account_id, signal_type, description, strength, confidence,
                     source, detected_at, evidence, raw_text
drafts            → id, account_id, body, original_body, status, evidence_ids
contacts          → id, account_id, name, role, email, linkedin_url
activities        → id, account_id, contact_id, activity_type, status,
                     timestamp, activity_metadata
opportunities     → id, account_id, stage, deal_value, probability, created_at, closed_at
```

---

## n8n Workflow Integration (No Docker Required)

Workflow JSON files are in `n8n/workflows/`. Two ways to run n8n:

### Option 1 — Local with Node.js (npx n8n)
```bash
# Requires Node.js 18+ installed
npx n8n
# n8n opens at http://localhost:5678
# Import workflow JSON via Settings > Import
```

### Option 2 — n8n Cloud Free Trial
1. Sign up at [cloud.n8n.io](https://cloud.n8n.io)
2. Click **Import** and upload files from `n8n/workflows/`
3. No installation required

### Pointing n8n at the Local GTMOS API
- Start GTMOS backend: `.venv\Scripts\uvicorn app.api.main:app --port 8000`
- n8n HTTP Request nodes use `http://localhost:8000` as base URL
- For n8n Cloud → use [ngrok](https://ngrok.com): `ngrok http 8000`, then use the ngrok URL

### Workflow 1 — Research & Score (`research_and_score.json`)
```
POST /webhook/new-account  body: {"account_id": 123}
  → POST localhost:8000/accounts/123/score
  → IF tier == "Priority 1"
      → GET /health with X-GTMOS-Notification header (mock alert)
  → Set output message with tier and score
```

### Workflow 2 — Weekly Analytics Summary (`weekly_analytics_summary.json`)
```
Cron: every Monday 9:00 AM
  → GET localhost:8000/analytics/funnel
  → Set: extract totals (contacted, won, meetings)
  → GET /health with X-GTMOS-Summary header (mock notification)
```

---

## Module Descriptions

| Module | Lines | Purpose |
|--------|-------|---------|
| `app/ai/llm.py` | ~160 | LLMService with mock adapter; all schemas return deterministic fixtures |
| `app/ai/evaluators.py` | ~250 | ICP accuracy, signal P/R/F1, determinism evaluation |
| `app/ai/run_eval.py` | ~180 | CLI runner → evaluation.md + timestamped JSON |
| `app/services/icp_engine.py` | ~60 | LLM → validated ICPProfile |
| `app/services/research_engine.py` | ~140 | CSV → LLM extraction → evidence validation |
| `app/services/signal_engine.py` | ~120 | Recency decay, deduplication, negative signals |
| `app/services/scoring_engine.py` | ~315 | Pure 100-pt deterministic scorer |
| `app/services/recommendation_engine.py` | ~100 | Rule table, SIGNAL_TO_ANGLE map |
| `app/services/personalization.py` | ~150 | LLM draft + _validate_draft_facts guardrail |
| `app/services/crm_service.py` | ~215 | Stage transitions, mark-as-sent, activity log |
| `app/services/analytics_engine.py` | ~250 | SQL + pandas funnel metrics |
| `app/services/analyst_service.py` | ~101 | NL → analytics → grounded explanation |

---

## Evaluation and Quality Assurance

See [`docs/evaluation.md`](evaluation.md) for the latest evaluation results.

Metrics computed:
- **ICP Tier Classification**: accuracy + per-tier precision, recall, F1, confusion matrix
- **Signal Extraction**: precision, recall, F1, unsupported claim rate per signal type
- **Scoring Consistency**: 5 repeated runs — must be 100% deterministic

Run the evaluation:
```powershell
python -m app.ai.run_eval --mode mock
```

Results saved to `docs/eval_results/eval_<timestamp>.json` for comparison over time.

---

## Extension Points

| Extension | Where |
|-----------|-------|
| Swap SQLite → Postgres | Change `DATABASE_URL` in `.env`; schema unchanged |
| Add LLM provider | `app/ai/llm.py` `generate_structured()` live branch |
| Add signal types | `app/services/signal_config.py` + `app/schemas/signal.py` |
| Add CRM stage | `app/schemas/crm.py` `FORWARD_STAGE_ORDER` |
| Add analytics function | `app/services/analyst_service.py` + `app/services/analytics_engine.py` |
| Add dashboard page | New file in `app/dashboard/`, add to `home.py` navigation |
| Add n8n notification | Edit workflow JSON in `n8n/workflows/` |
