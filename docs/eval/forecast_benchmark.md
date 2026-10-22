# Forecast Benchmark Results

> Generated: 2026-10-22 21:22
> Horizon: **7 days** | Products: **15** | Validation: walk-forward
> ⚠️ Data is **SYNTHETIC**

## Summary

| Model | Mean MAPE (%) | Median MAPE (%) | Mean RMSE |
|-------|--------------|----------------|-----------|
| Naive | 31.84 | 18.43 | 15.93 |
| Seasonal Naive | 23.03 | 15.93 | 9.52 |
| LightGBM | 27.17 | 17.32 | 12.4 |

## Per-Product Results

| Product | Naive MAPE | SNaive MAPE | LightGBM MAPE | Best |
|---------|-----------|-------------|---------------|------|
| product_0 | 13.78 | 8.37 | 13.93 | SNaive |
| product_1 | 21.46 | 24.74 | 25.73 | Naive |
| product_2 | 11.71 | 12.47 | 11.28 | LightGBM |
| product_3 | 18.03 | 10.26 | 10.71 | SNaive |
| product_4 | 122.15 | 115.24 | 118.47 | SNaive |
| product_5 | 24.76 | 15.96 | 23.55 | SNaive |
| product_6 | 49.15 | 25.82 | 50.32 | SNaive |
| product_7 | 10.44 | 6.83 | 10.89 | SNaive |
| product_8 | 17.8 | 7.03 | 18.14 | SNaive |
| product_9 | 17.51 | 6.78 | 11.04 | SNaive |
| product_10 | 18.43 | 17.95 | 17.32 | LightGBM |
| product_11 | 10.92 | 7.72 | 7.6 | LightGBM |
| product_12 | 56.29 | 54.34 | 56.67 | SNaive |
| product_13 | 51.28 | 15.94 | 18.02 | SNaive |
| product_14 | 33.9 | 15.93 | 13.95 | LightGBM |

## Key Findings

- LightGBM wins on **4/15** products (27%)
- LightGBM Mean MAPE: **27.17%** vs Naive: **31.84%**
- Weekly seasonality captured by Seasonal Naive (23.03% MAPE)

---
⚠️ All numbers from script execution. Data is SYNTHETIC.