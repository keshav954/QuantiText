# Latency & Cost Evaluation Results

> Generated: 2026-10-22 21:22
> Model: gemini-2.0-flash

## Endpoint Latency (simulated, milliseconds)

| Endpoint | p50 (ms) | p95 (ms) | p99 (ms) | Mean (ms) |
|----------|---------|---------|---------|----------|
| GET /kpi/summary | 45.2 | 118.0 | 161.5 | 52.6 |
| GET /kpi/revenue-trend | 53.6 | 140.0 | 223.6 | 63.2 |
| GET /kpi/top-products | 35.7 | 90.7 | 143.6 | 42.3 |
| GET /forecast/{product} | 79.6 | 196.9 | 312.6 | 93.0 |
| GET /inventory/status | 59.3 | 159.8 | 228.4 | 70.8 |
| GET /anomalies | 51.6 | 133.3 | 207.3 | 61.2 |
| POST /copilot/chat (NL2SQL) | 1156.8 | 3730.7 | 5156.3 | 1512.7 |
| POST /reports/generate | 2428.4 | 4792.1 | 6186.5 | 2671.6 |
| POST /admin/upload/preview | 306.5 | 785.5 | 1101.5 | 361.7 |

## LLM API Cost Estimates

| Metric | Value |
|--------|-------|
| Model | gemini-2.0-flash |
| Avg input tokens (NL2SQL) | 1500 |
| Avg output tokens (NL2SQL) | 300 |
| **Cost per NL2SQL query** | **$0.000202** |
| **Cost per 100 queries** | **$0.0202** |
| Cost per report generation | $0.000465 |
| Monthly estimate (500 queries) | $0.1012 |

## Notes

- Latencies are simulated from log-normal distributions matching observed development ranges
- NL2SQL queries include: schema linking + LLM SQL generation + DB execution + LLM explanation
- Report generation includes: data aggregation + LLM narrative
- Cost estimates use Gemini 2.0 Flash pricing (subject to change)
- All non-LLM endpoints complete in <200ms at p95

---
⚠️ Latencies are simulated distributions. Actual values depend on hardware and load.