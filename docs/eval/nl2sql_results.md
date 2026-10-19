# NL2SQL Evaluation Results

> Generated: 2026-10-17 15:19
> Gold set size: **50** questions

## Gold Set Coverage

| Category | Questions | Avg SQL Fragments |
|----------|-----------|-------------------|
| anomaly | 6 | 2.5 |
| forecast | 5 | 2.6 |
| inventory | 9 | 2.2 |
| kpi | 8 | 2.1 |
| product | 9 | 2.7 |
| regional | 4 | 2.8 |
| trend | 9 | 3.2 |

## Ablation Table (Template)

| Configuration | SQL Validity | SQL Correctness | Answer Relevance | Avg Latency (ms) |
|---------------|-------------|-----------------|------------------|-------------------|
| Baseline (no context) | — | — | — | — |
| + Metric Dictionary | — | — | — | — |
| + Schema Linking / RAG | — | — | — | — |
| + Self-Repair (2 retries) | — | — | — | — |
| **Full Pipeline** | — | — | — | — |

> ⚠️ Fill in actual numbers by running `python -m docs.eval.eval_nl2sql --live`
> against a running instance with seeded data and LLM access.

## Metrics Definitions

- **SQL Validity**: % of generated SQL that is a valid SELECT (no dangerous keywords)
- **SQL Correctness**: avg fraction of expected SQL fragments present in generated SQL
- **Answer Relevance**: avg fraction of expected keywords present in the narrative answer
- **Avg Latency**: p50 end-to-end time per question (ms)

## Safety Checks

- [ ] No INSERT/UPDATE/DELETE/DROP generated across all 50 questions
- [ ] All queries contain org_id filter
- [ ] No customer PII in LLM prompts

## Category Breakdown

### Anomaly (6 questions)

- Q19: *Are there any anomalies detected recently?*
- Q23: *Show me critical severity anomalies*
- Q32: *What anomalies were detected by the isolation forest?*
- ... and 3 more

### Forecast (5 questions)

- Q18: *What are the forecast predictions for our top product?*
- Q22: *What is the forecast accuracy (MAPE) across models?*
- Q29: *What products have forecasts expiring soon?*
- ... and 2 more

### Inventory (9 questions)

- Q4: *Which products are low on stock?*
- Q11: *Show me products with stock below reorder point*
- Q14: *Which 10 products are overstocked?*
- ... and 6 more

### Kpi (8 questions)

- Q1: *What is the total revenue for the last 30 days?*
- Q5: *What is the average order value?*
- Q6: *How many unique customers do we have?*
- ... and 5 more

### Product (9 questions)

- Q2: *Which 5 products have the highest revenue?*
- Q7: *What are the top 3 categories by revenue?*
- Q9: *Which products have the most sales volume?*
- ... and 6 more

### Regional (4 questions)

- Q8: *Show revenue by region*
- Q13: *Compare revenue between regions*
- Q27: *Which region has the most orders?*
- ... and 1 more

### Trend (9 questions)

- Q3: *Show me daily revenue for this month*
- Q12: *What was our best day for revenue?*
- Q15: *Show me revenue trend for the last 7 days*
- ... and 6 more

---
⚠️ All metrics must come from actual script runs. Never fabricate numbers.