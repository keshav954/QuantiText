# QuantiText: Agent Instructions

Final-year B.Tech project: an AI-powered Business Intelligence and Decision Support System.
Thesis: forecasting, anomaly detection, NL2SQL chat and reporting are usually separate tools.
We integrate them into one closed loop:
anomaly -> root cause -> forecast impact -> recommended action -> human approval -> logged outcome.

## Stack (do not swap without asking)
- Backend: Python 3.11, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, pytest
- DB: PostgreSQL 16 (+ pgvector later), Redis for cache and jobs
- ML: pandas, numpy, scikit-learn, statsmodels, prophet, lightgbm, shap, mlflow
- GenAI: Gemini via LangChain, behind a provider interface (`LLMProvider`) so models can be swapped
- Frontend: React + Vite + TypeScript, Tailwind, shadcn/ui, Recharts, TanStack Query
- Infra: Docker Compose for local, GitHub Actions for CI

## Architecture
Modular monolith: ONE FastAPI app, separate routers and service packages. Do not create microservices.
Layers: presentation -> api -> services -> data. Routers contain no business logic.

```
backend/app/{core,api,models,schemas,services/{nl2sql,forecasting,inventory,anomaly,reports},jobs}
backend/ml/        experiments, saved models
backend/tests/
frontend/src/{pages,components,hooks,api,store}
data/              seed scripts and sample datasets
docs/              diagrams, eval results, prompts
infra/             nginx, CI, deploy notes
```

## Commands
- Start everything: `docker compose up --build`
- Backend tests: `cd backend && pytest -q`
- Lint/format: `ruff check . && ruff format .` (backend), `npm run lint` (frontend)
- Frontend tests: `cd frontend && npm test`
- Migrations: `alembic revision --autogenerate -m "msg" && alembic upgrade head`
- Seed demo data: `python -m data.seed`

## Conventions
- Type hints everywhere. Pydantic schemas for all request/response bodies.
- Config only via environment variables (`.env`, never committed). Keep `.env.example` updated.
- Every new endpoint needs: schema, RBAC check, audit log entry, and at least one test.
- Every ML module exposes `train()`, `evaluate()`, `predict()` and logs metrics (MAPE, RMSE).
- Small commits with clear messages. One feature branch per phase.

## Definition of done (for any task)
1. Code runs via Docker Compose with no manual steps.
2. Tests added and passing; lint clean.
3. README or docs updated if behaviour or setup changed.
4. Summarise what changed, what was verified, and what is still untested.

## Data honesty
Inventory, lead-time and cost data are SYNTHETIC unless stated otherwise. Label them as synthetic in docs and UI.
Never invent evaluation numbers. All reported metrics must come from a script in `backend/ml/` or `docs/eval/`.

## Never
- Never run generated SQL on a read-write connection.
- Never send customer-level or PII data to the LLM. Only aggregated figures.
- Never commit secrets or API keys.
- Never disable tests or loosen validation to make something pass.
