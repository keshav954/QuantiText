# Phase prompts for Antigravity (paste one per task/conversation)

How to use: open Agent Manager, create ONE task per phase, pick a Claude model for backend/ML/NL2SQL work,
use Planning mode, and read the Implementation Plan artifact before approving. Commit after every phase.
If the agent drifts, say: "Stop. Re-read AGENTS.md and the rules, then redo the plan."

---
## Phase 0: Scaffold
Read AGENTS.md. Create the monorepo skeleton exactly as described: docker-compose.yml (postgres, redis, backend, frontend),
FastAPI app with `/health`, Alembic configured, React+Vite+TS+Tailwind+shadcn app that calls `/health`,
`.env.example`, ruff config, pytest config, and a GitHub Actions workflow (lint + test + build).
Acceptance: `docker compose up --build` works from a clean clone; `/health` is shown in the UI; CI file is valid.

## Phase 1: Database, synthetic data, ETL
Design the PostgreSQL schema: orgs, users, roles, products, categories, customers, orders, order_items, inventory
(stock_on_hand, reorder_point, lead_time_days, min_order_qty, unit_cost, holding_cost),
daily_sales (pre-aggregated), forecasts, anomalies, alerts, recommendations (status: pending/approved/rejected), reports, audit_log.
Add `org_id` to tenant tables. Create Alembic migrations. Create a read-only role `bi_readonly` with access ONLY to analytics views.
Write an ETL (pandas) that loads a public retail dataset (UCI Online Retail II or Superstore) with cleaning
(dupes, nulls, formats, daily index alignment), and a seed generator for synthetic inventory/lead-time/cost data (clearly marked synthetic).
Create SQL views: v_kpi_daily, v_sales_by_product, v_sales_by_region, v_inventory_status.
Acceptance: `python -m data.seed` fills the DB; views return sensible rows; ER diagram saved to docs/.

## Phase 2: Auth, RBAC, audit, KPI API
Implement login (JWT), roles, a shared RBAC dependency, audit middleware, and KPI endpoints with date/category/region filters and Redis caching.
Acceptance: tests for auth, permission denied, and KPI correctness against hand-computed values.

## Phase 3: Frontend shell and dashboard
Build the app shell: sidebar (Dashboard, Copilot, Forecasts, Inventory, Alerts, Reports, Admin), top bar with global date range,
light/dark mode, and the Dashboard page: KPI cards with trend arrows, revenue trend chart, top products, regional view, alerts strip.
Design rules: green=healthy, amber=warning, red=critical, blue=forecast; designed loading, empty and error states; keyboard accessible.
Acceptance: dashboard renders live data from the API; no console errors; responsive at 375px and 1280px.

## Phase 4: Forecasting
Implement the pipeline: features (lags 1/7/14/28, rolling means, calendar and Indian festival flags), baselines (naive, seasonal-naive),
SARIMA or Prophet, LightGBM. Use walk-forward validation, choose the best model per category by MAPE, produce 1/7/30-day forecasts with
conformal prediction intervals, store in `forecasts`, log runs to MLflow, add SHAP explanations, and a scheduled weekly retrain job.
Add `/forecast/{product}` and the Forecast page (horizon toggle, confidence band, MAPE badge).
Acceptance: `backend/ml/benchmark.py` prints a MAPE/RMSE table across models vs baselines; tests for leakage and metric correctness.

## Phase 5: Inventory intelligence
Classify items (low-stock, overstock, slow-moving, healthy) using days-of-cover from forecasts.
Compute safety stock = z*sigma_d*sqrt(L), reorder point, and EOQ. Generate recommendations with a plain-English reason and store them as pending.
Add a what-if endpoint (demand +/- %, supplier delay). Build the Inventory page with tabs and an Approve/Reject flow.
Acceptance: a simulation script replays history comparing a naive policy vs ours (stockout rate, excess stock, total cost) and saves a table.

## Phase 6: Anomaly detection and alerts
Implement rolling Z-score and Isolation Forest on daily features, plus data-quality checks (price=0, negative stock).
Add root-cause drill-down (decompose deviation by product/category/region). Score severity by estimated money impact,
dedupe alerts, and add a "not an anomaly" feedback button. Push alerts over WebSocket. LLM writes a 2-line explanation from numbers only.
Acceptance: a script injects synthetic anomalies and reports precision/recall/F1 per detector; Alerts page works.

## Phase 7: AI Copilot (NL2SQL)
Build the Copilot following `.agents/rules/nl2sql-safety.md`. Components: metric dictionary (YAML) for revenue/profit/etc. with synonyms,
schema linking (retrieve relevant views/columns), few-shot retrieval from past question-SQL pairs (pgvector), `LLMProvider` interface (Gemini first),
SQL validator, read-only executor, self-repair loop (max 2 retries), grounding check on the explanation, conversation memory for follow-ups,
and tools the agent can call: run_sql, get_forecast, get_anomalies, simulate_scenario.
UI: chat with starter chips, answer + chart/table + collapsible "View SQL", feedback buttons, streaming responses, clarifying-question flow.
Acceptance: a 50+ question gold set in docs/eval/nl2sql_gold.jsonl and `/eval-nl2sql` produces the ablation table
(baseline -> +metric dictionary -> +schema linking/RAG -> +self-repair).

## Phase 8: Reports and approvals
Aggregator collects KPIs, trends, forecasts, inventory flags, anomalies into one JSON. LLM writes the narrative from that JSON only,
with the grounding check. Export PDF (and DOCX). Weekly schedule + on demand. Approved reorder recommendations generate a PDF purchase order.
Acceptance: generated report numbers match the aggregator JSON exactly (test).

## Phase 9: Bring-your-own-data onboarding
CSV/Excel upload, column auto-detection and mapping UI, validation report, then load into the standard schema and refresh views.
Acceptance: upload a different retail CSV and see the dashboard and Copilot work on it.

## Phase 10: Evaluation chapter
Create scripts and tables for: NL2SQL ablation, forecast benchmark, anomaly P/R/F1, inventory simulation, hallucination rate with/without grounding,
latency (p50/p95) and cost per 100 queries. Save all to docs/eval/ and generate a Markdown summary. Never fabricate numbers.

## Phase 11: Hardening and deployment
Security pass (rate limits, headers, secrets), Nginx + HTTPS config, production compose file, deployment notes for AWS (EC2 + RDS),
health/metrics endpoints, backup script, and a seeded demo mode. Run `/verify`.
Acceptance: a fresh machine can deploy using the README only.
