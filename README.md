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
- **ML**: pandas, numpy, scikit-learn, LightGBM, SHAP, MLflow
- **GenAI**: Gemini via LangChain (behind `LLMProvider` interface)
- **Frontend**: React + Vite + TypeScript, Tailwind, shadcn/ui, Recharts
- **Infra**: Docker Compose, NGINX reverse proxy, GitHub Actions CI

## Features & Implementation Status

| Feature / Subsystem | Status | Details |
|---------------------|--------|---------|
| **Scaffold & DevOps** | Done | Docker Compose, multi-stage non-root Dockerfile with dev arg, CI workflow |
| **Database & Migrations** | Done | PostgreSQL 16, Alembic migrations (0001–0004), read-only role permissions |
| **Auth & RBAC** | Done | JWT bearer authentication, 60m expiry, bcrypt hashing, password change, robust key validation |
| **Audit Logging** | Done | Audit trails on auth, kpi, inventory, anomalies, forecasting, copilot, and reports |
| **Frontend Dashboard** | Done | React + Vite + TypeScript, KPI tracking, Recharts, dark mode, alert feed, copilot chat |
| **Forecasting Pipeline** | Done | LightGBM lag/rolling regression with baseline models, walk-forward leakage tests, metrics |
| **Inventory Intelligence** | Done | Dynamic reorder points, safety stock, what-if simulation, ReportLab PDF purchase orders |
| **Anomaly Detection** | Done | Ensemble Z-Score + Isolation Forest, alert thresholds, authenticated `/alerts/ws` stream |
| **Closed-Loop Decision Engine** | Done | Anomaly → root cause → forecast impact → recommendation → human approval → logged outcome |
| **AI Copilot (NL2SQL)** | Done | AST table subquery org scoping (`scope_to_org`), function allowlist, repair loop with `rollback()` |
| **Report Generation** | Done | Executive and operational PDF reports generated via ReportLab |
| **BYOD Data Onboarding** | Done | Multi-tenant CSV upload, schema mapping, and validation |
| **Copilot Message Feedback** | Done | Interactive Thumbs-Up / Thumbs-Down feedback buttons on copilot responses |
| **pgvector Few-Shot Retrieval** | Partial | Fallback & schema few-shot examples in place; dedicated pgvector embedding index planned |
| **Weekly Scheduled Report Cron** | Partial | Core service method and schema ready; standing daemon requires production beat worker |
| **DOCX Report Export** | Not built | High-fidelity PDF export implemented via ReportLab; DOCX export omitted |

## Evaluation Results (Synthetic Data)

| Module / Pipeline | Metric | Value | Source Evaluation Script |
|-------------------|--------|-------|--------------------------|
| **Anomaly Detection (combined)** | F1 Score | 0.727 | `docs/eval/eval_anomaly.py` |
| **Anomaly Detection (z-score)** | Precision | 1.000 | `docs/eval/eval_anomaly.py` |
| **Anomaly Detection (isolation forest)** | Recall | 0.647 | `docs/eval/eval_anomaly.py` |
| **Inventory Policy Optimization** | Cost Reduction | 93.0%* | `docs/eval/eval_inventory.py` |
| **Inventory Policy Optimization** | Stockout Reduction | 99.9% | `docs/eval/eval_inventory.py` |
| **NL2SQL Semantic Accuracy** | Gold Set Exec Accuracy | 100.0% (50/50) | `docs/eval/eval_nl2sql.py --live` |
| **NL2SQL Tenant Security** | Org Scoping Enforcement | 100.0% (50/50) | `docs/eval/eval_nl2sql.py --live` |
| **NL2SQL Robustness** | Penetration Vectors Blocked | 5/5 Bypass Tests | `backend/tests/test_copilot_service.py` |

> \* **Caveat on Inventory Results**: The 93.0% cost reduction was evaluated on synthetic benchmark distributions assuming a severe stockout penalty (£150/unit) against an unoptimized static reorder-point baseline. In real deployment settings with moderate margin loss or different holding-to-stockout ratios, the observed cost reduction will depend on company-specific penalty parameters. All reported evaluation numbers originate directly from scripts in `backend/ml/` or `docs/eval/`. Never fabricated.

## Data Disclaimer

⚠️ Inventory, lead-time, and cost data are **SYNTHETIC** unless stated otherwise.
All reported evaluation metrics come from scripts in `backend/ml/` or `docs/eval/`.

## License

Private — B.Tech thesis project.
