# Architecture Decision Records (ADR)

## ADR 001: Local SQLite Engine
- **Context**: Windows local development without Docker.
- **Decision**: Default `DATABASE_URL` to `sqlite:///./gtmos.db` with generic SQLAlchemy `JSON` types and thread-safe PRAGMA configuration.

## ADR 002: Recommendation Engine Rule Table
- **Context**: Need deterministic, explainable next-action recommendations without relying on LLM hallucination for decision-making.
- **Decision**: Actions, personas, and angles are derived via deterministic rule templates:

### Action Matrix
| Fit Tier | Intent Score | Recommended Action | Deterministic Reason Template |
|---|---|---|---|
| **Priority 1** | >= 10.0 | `CONTACT` | Priority 1 account with strong intent signals detected. |
| **Priority 1** | < 10.0 | `RESEARCH` | Priority 1 account but lacking strong intent. Research for recent triggers. |
| **Priority 2** | >= 15.0 | `PRIORITIZE` | Priority 2 account with very high intent. Prioritize for immediate outreach. |
| **Priority 2** | 5.0 – 14.9 | `NURTURE` | Priority 2 account with moderate intent. Nurture until strong buying triggers emerge. |
| **Priority 2** | < 5.0 | `RESEARCH` | Priority 2 account with weak intent. Research to find active buying signals. |
| **Priority 3** | >= 10.0 | `NURTURE` | Priority 3 account showing some buying signals. Add to automated nurture sequence. |
| **Priority 3** | < 10.0 | `DEPRIORITIZE` | Priority 3 account with weak intent. Deprioritize for direct outreach. |
| **Low** | Any | `DEPRIORITIZE` | Low fit account. Disqualify or deprioritize. |

### Signal to Angle Mapping Table
| Signal Type | Outreach Angle | Target Persona Focus |
|---|---|---|
| `support_hiring` | support team scaling and efficiency | VP of Customer Support / CX Lead |
| `funding` | post-funding growth and tooling | CRO / VP Sales / CEO |
| `product_launch` | supporting new product rollouts | Head of Product / VP Support |
| `international_expansion` | managing global operations and localization | VP Operations / Global Support Lead |
| `relevant_technology` | integrating with your existing tech stack | Head of Tech / IT / Support Ops |
| `rapid_growth` | handling increased volume at scale | VP Customer Support / COO |
| `executive_change` | new strategic initiatives | Incoming Executive / Department Head |

## ADR 003: Deterministic Scoring
- **Context**: B2B sales teams require predictable, auditable scoring criteria. LLMs used for scoring suffer from non-deterministic variance, arithmetic drift, and hallucinated evaluations.
- **Decision**: Keep scoring 100% deterministic using a pure 100-point model in `ScoringEngine`. The LLM extracts qualitative facts (what happened), while deterministic code evaluates qualification points (how good the fit is).

## ADR 004: Structured LLM Outputs with Pydantic
- **Context**: Free-form LLM text completions frequently break downstream pipelines due to format inconsistencies and missing fields.
- **Decision**: All LLM calls pass strict Pydantic schemas via `generate_structured()`. Outputs are validated at runtime; if validation fails, the service retries with error feedback before returning clean domain objects.

## ADR 005: Mock Adapter Pattern
- **Context**: Automated tests and local developer environments need to run without requiring external cloud API keys, network access, or incurring per-test token costs.
- **Decision**: `LLMService` implements an internal `mode="mock"` adapter that deterministically generates schema-conforming mock responses without network calls. This powers all unit, integration, and CI tests.

## ADR 006: SQLite First
- **Context**: Easy setup and zero developer friction during onboarding and local development on Windows or macOS.
- **Decision**: Use SQLite (`gtmos.db`) via SQLAlchemy as the default database. SQLAlchemy's dialect abstraction enables an instant one-line environment variable switch (`DATABASE_URL=postgresql://...`) for production deployment.

## ADR 007: Human-in-the-Loop for Outreach
- **Context**: Autonomous AI cold outreach creates compliance, brand reputation, and hallucination risks if dispatched without human oversight.
- **Decision**: Outreach drafts require explicit manual approval in the Review Queue. Furthermore, drafts can only advance accounts to `Contacted` when an SDR manually triggers `Mark as Sent`. No automated background dispatch is permitted.


## ADR 008: Public Web App on Vercel (React + FastAPI serverless)
- **Context**: The project needs a public, shareable demo. Streamlit cannot run on Vercel, and a portfolio piece needs a landing page as well as the tool.
- **Decision**: A React (Vite + Tailwind) frontend in `web/` calls the existing FastAPI app, mounted under `/api` by `api/index.py` as a Vercel Python function. New read-optimised endpoints live in `app/api/routes/web.py`; every score and action still comes from the deterministic engines.
- **Data**: The function rebuilds the synthetic demo database in `/tmp` on cold start (`app/db/demo_seed.py`), anchoring signal dates to today. The public demo is a self-resetting sandbox; `DATABASE_URL` can point at hosted Postgres for persistence.
- **LLM**: The public demo runs in mock mode, so it costs nothing and needs no key. Mock extraction, drafting and analyst explanations are rule-based and quote their sources, so the guardrails stay meaningful offline.
