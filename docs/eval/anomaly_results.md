# Anomaly Detection Evaluation Results

> Generated: 2026-10-17 15:20
> Synthetic dataset: 10 products × 90 days
> Ground truth anomalies: 48

## Precision / Recall / F1 per Detector

| Detector | TP | FP | FN | Precision | Recall | F1 |
|----------|----|----|----|-----------|---------|----|
| zscore | 18 | 0 | 30 | 1.000 | 0.375 | 0.545 |
| iforest | 21 | 15 | 27 | 0.583 | 0.438 | 0.500 |
| data_quality | 15 | 0 | 33 | 1.000 | 0.312 | 0.476 |
| combined | 36 | 15 | 12 | 0.706 | 0.750 | 0.727 |

## Notes

- Data is **SYNTHETIC** — generated for evaluation only.
- Injected anomalies: 15 revenue spikes (5×), 10 revenue drops, 5 zero-sales streaks.
- Isolation Forest uses contamination=0.05, random_state=42.
- Z-score threshold: 2.5 (matches production config).
- Data Quality flags 3+ consecutive zero-sales days.

---
⚠️ All numbers in this file are from script execution. Never fabricated.