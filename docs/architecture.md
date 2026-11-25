# GTMOS architecture (summary)

> A short overview of the current system. The full explanation, with diagrams for the
> system, data flow and public-demo sandbox, is in
> **[TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md)**.
>
> *History:* this file used to describe the original Streamlit-plus-FastAPI build. GTMOS now
> also has a React web app and a guarded public-demo API. The Streamlit dashboard still
> exists as an internal, local-only tool.

All data is synthetic and the pipeline is simulated.

---

## System overview

```
 React web app (web/)                       Streamlit dashboard (app/dashboard/)
 landing · /demo · /app/*                    internal, local only
        │ /api/*                                     │ HTTP
        ▼                                            ▼
 Public demo API                              Full local API
 api/index.py → app/api/public.py             app/api/main.py  (create_app)
 write allowlist · rate limits ·              every route, no guard
 read-only template DB · per-browser
 sandboxes · LLM forced to mock
        └───────────────┬────────────────────────────┘
                        ▼  same routers: app/api/routes/
                           products · accounts · drafts · pipeline · analytics · web
                        ▼
 Services (app/services/)
 icp_engine · research_engine · signal_engine · scoring_engine · recommendation_engine ·
 personalization · crm_service · analytics_engine · analyst_service ·
 explainability · executive_analytics · methodology
                        ▼
 SQLAlchemy 2 → SQLite (gtmos.db locally; /tmp on Vercel)     app/ai/llm.py (mock | live)
```

- **Local full API:** `uvicorn app.api.main:app --reload` (port 8000).
- **Local public demo API:** `uvicorn api.index:app --reload --port 8000`. The React dev
  server (`web/`, port 5173) proxies `/api` to it.
- **Deployment target:** `vercel.json` builds `web/dist` and runs `api/index.py` as a Python
  function. It has not been deployed; see [deployment.md](deployment.md).

## Data flow

```
Product description
  ▼ ICPEngine: LLM → Pydantic ICP profile
  ▼ ResearchEngine: LLM proposes signals → code checks the quote against the note
      accepted → Signal rows · negated / unsupported / ambiguous → rejected_signal activities (0 pts)
      every note → research_note activity (provenance)
  ▼ SignalEngine: intent 0–20 = Σ weight × strength × confidence × decay, newest per type,
      minus disqualifier penalties (too_small, wrong_industry, wrong_geography, no_use_case)
  ▼ ScoringEngine: fit /80 (ICP 30 · company 20 · technology 15 · geography 15) + intent /20
      → Priority 1 ≥ 90 · Priority 2 ≥ 75 · Priority 3 ≥ 50 · Low < 50
  ▼ RecommendationEngine: fixed rule table (tier + intent) → action + rule_id
  ▼ Personalization: LLM draft → fact-check guardrail (failing drafts are not saved)
  ▼ Human review queue: pending → approved / rejected (approving never sends)
  ▼ CRM pipeline: Research → Contacted → Replied → Meeting → Opportunity → Won / Lost
  ▼ AnalyticsEngine (SQL + pandas) and AnalystService (question → one of 11 fixed functions)
  ▼ Web read models: explainability, executive analytics (observations vs hypotheses), methodology
```

## AI vs deterministic split

| Component | Type | Rationale |
|-----------|------|-----------|
| ICP generation | **LLM** | Needs language understanding of the product description |
| Signal extraction | **LLM** (mock: rule-based stand-in) | Reads and interprets research text |
| Evidence check | **Deterministic** | Quote match against the note (partial match for long quotes; see TECHNICAL_ARCHITECTURE.md) |
| Scoring (all components) | **Deterministic** | Reproducible and explainable |
| Recommendation action | **Deterministic** | Rule table with rule ids |
| Draft generation | **LLM** | Language, grounded in evidence ids |
| Draft fact-check | **Deterministic** | Numbers must appear in the evidence |
| Analytics and executive answers | **Deterministic** | SQL + pandas; no LLM arithmetic, no generated SQL |
| Analyst routing and wording | **LLM** | Picks a fixed function and explains computed numbers |

In the public demo, the LLM is always the offline mock.

## Database tables

```
products       id, name, description, target_market, geography, price_range, created_at
icp_profiles   id, product_id, industries, company_size_min/max, geographies, buyer_roles,
               pain_points, technologies, buying_triggers, exclusions
accounts       id, name, domain, industry, employee_count, country, description,
               technology_stack, funding, support_team_size, stage, created_at
scores         id, account_id, product_id, icp_fit, company_fit, technology_fit,
               intent_score, geography_score, total_score, tier, reasoning, created_at
signals        id, account_id, signal_type, description, strength, source, detected_at,
               confidence, evidence
drafts         id, account_id, contact_id, body, original_body, status, evidence_ids,
               created_at, reviewed_at
contacts       id, account_id, name, role, email, linkedin_url
activities     id, account_id, contact_id, activity_type, status, timestamp, metadata
opportunities  id, account_id, stage, deal_value, probability, created_at, closed_at
```

Generic SQLAlchemy `JSON` columns keep the schema database-agnostic.

## n8n workflows (exported, not run as part of the app; no Docker)

Workflow JSON files are in `n8n/workflows/`. They have been exported but not run against a
deployed GTMOS. To try them:

- **Local:** with Node.js 18+, run `npx n8n` (opens at <http://localhost:5678>) and import the JSON.
- **n8n Cloud trial:** import the files from `n8n/workflows/`.
- Point HTTP nodes at the **full local API** (`uvicorn app.api.main:app --port 8000`). The
  public demo API blocks these write routes. For n8n Cloud, expose the local API with a
  tunnel such as ngrok.

| Workflow | Flow |
|---|---|
| `research_and_score.json` | Webhook `{"account_id": …}` → `POST /accounts/{id}/score` → if Priority 1, a mock alert (`GET /health` with a header) |
| `weekly_analytics_summary.json` | Monday 9:00 cron → `GET /analytics/funnel` → extract totals → mock notification |

## Evaluation

Results and the method are in [evaluation.md](evaluation.md) and on the web app's
methodology page: 57% tier accuracy, 0% Priority 2 recall (the tier evaluation uses proxy
intent), and 100% signal precision/recall from a simplified keyword matcher. Run it with
`python -m app.ai.run_eval --mode mock`.

## Extension points

| Extension | Where |
|-----------|-------|
| Swap SQLite for Postgres | `DATABASE_URL` in `.env` (not yet exercised) |
| Add an LLM provider | `app/ai/llm.py`, `generate_structured()` live branch |
| Add signal types | `app/services/signal_config.py` + `app/schemas/signal.py` |
| Add a CRM stage | `app/schemas/crm.py`, `FORWARD_STAGE_ORDER` |
| Add an analytics function | `app/services/analytics_engine.py` + `app/services/analyst_service.py` |
| Add a web page | `web/src/pages/` + the router in `web/src/main.tsx` |
| Allow a new public write route | `WRITE_POLICY` in `app/api/public.py` (security review needed) |
| Add a Streamlit page | `app/dashboard/`, registered in `home.py` navigation |
