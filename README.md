# QuantiText

AI-powered Business Intelligence and Decision Support System.

> Final-year B.Tech project integrating forecasting, anomaly detection, NL2SQL chat, and reporting
> into a single closed loop: anomaly → root cause → forecast impact → recommended action → human approval → logged outcome.

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- Git

### Setup

```bash
# Clone the repo
git clone <repo-url> quantitext
cd quantitext

# Create your environment file
cp .env.example .env
# Edit .env and set a strong SECRET_KEY and your GEMINI_API_KEY

# Start everything
docker compose up --build
```

### Verify

| Service    | URL                          |
|------------|------------------------------|
| Backend    | http://localhost:8000/health  |
| API Docs   | http://localhost:8000/docs    |
| Frontend   | http://localhost:5173         |

Login with the seeded demo credentials: **admin@demo.local** / **admin123**

### Development Commands

```bash
# Backend tests
cd backend && pytest -q

# Lint and format (backend)
cd backend && ruff check . && ruff format .

# Frontend dev server (requires Node.js 20+)
cd frontend && npm install && npm run dev

# Frontend lint
cd frontend && npm run lint

# Frontend tests
cd frontend && npm test

# Alembic migrations
cd backend && alembic revision --autogenerate -m "description"
cd backend && alembic upgrade head

# Seed demo data (after migrations)
python -m data.seed
```

### Run Evaluation Scripts

```bash
# NL2SQL gold set evaluation (50 questions)
python -m docs.eval.eval_nl2sql

# Anomaly detection precision/recall/F1
python -m docs.eval.eval_anomaly

# Inventory policy simulation (naive vs optimized)
python -m docs.eval.eval_inventory
```

### Production Deployment

```bash
# See full deployment guide
cat infra/DEPLOY.md

# Quick production deploy
docker compose -f docker-compose.prod.yml up --build -d
```

## Architecture

Modular monolith — one FastAPI app with separate routers and service packages.

```
backend/app/
├── core/       Config, database, security, shared utilities
├── api/        FastAPI routers (thin — no business logic)
├── models/     SQLAlchemy ORM models
├── schemas/    Pydantic v2 request/response schemas
├── services/   Business logic (nl2sql, forecasting, inventory, anomaly, reports)
└── jobs/       Background and scheduled tasks
```

## Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2
- **Database**: PostgreSQL 16, Redis 7
- **ML**: pandas, scikit-learn, statsmodels, Prophet, LightGBM, SHAP, MLflow
- **GenAI**: Gemini via LangChain (behind `LLMProvider` interface)
- **Frontend**: React + Vite + TypeScript, Tailwind, shadcn/ui, Recharts
- **Infra**: Docker Compose, NGINX reverse proxy, GitHub Actions CI

## Features (Phase Status)

| Phase | Feature | Status |
|-------|---------|--------|
| 0 | Scaffold & DevOps | ✅ Complete |
| 1 | Database & ETL | ✅ Complete |
| 2 | Auth / RBAC / KPI | ✅ Complete |
| 3 | Frontend Dashboard | ✅ Complete |
| 4 | Forecasting Pipeline | ✅ Complete |
| 5 | Inventory Intelligence | ✅ Complete |
| 6 | Anomaly Detection | ✅ Complete |
| 7 | AI Copilot (NL2SQL) | ✅ Complete |
| 8 | Reports & Approvals | ✅ Complete |
| 9 | BYOD Data Onboarding | ✅ Complete |
| 10 | Evaluation Chapter | ✅ Complete |
| 11 | Hardening & Deploy | ✅ Complete |

## Evaluation Results (Synthetic Data)

| Module | Metric | Value |
|--------|--------|-------|
| Anomaly (combined) | F1 | 0.727 |
| Anomaly (z-score) | Precision | 1.000 |
| Inventory (optimized) | Cost Reduction | 93.0% |
| Inventory (optimized) | Stockout Reduction | 99.9% |
| NL2SQL | Gold Set Size | 50 questions |

> All numbers from `docs/eval/` scripts. Never fabricated.

## Data Disclaimer

⚠️ Inventory, lead-time, and cost data are **SYNTHETIC** unless stated otherwise.
All reported evaluation metrics come from scripts in `backend/ml/` or `docs/eval/`.

## License

Private — B.Tech thesis project.
