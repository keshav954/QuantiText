# Inventory Policy Simulation Results

> Generated: 2026-10-22 21:22
> Simulation: 20 products × 90 days
> Data is **SYNTHETIC**

## Policy Comparison

| Metric | Naive Policy | Optimized (SS+EOQ+ROP) | Improvement |
|--------|-------------|----------------------|-------------|
| Stockout Units | 15691 | 11 | 99.9% |
| Excess Stock | 547 | 3242 | — |
| Total Orders | 173 | 109 | — |
| Holding Cost | £874.22 | £6,096.62 | — |
| Ordering Cost | £8,650.00 | £5,450.00 | — |
| Stockout Cost | £156,910.00 | £110.00 | — |
| **Total Cost** | **£166,434.22** | **£11,656.62** | **93.0%** |

## Policy Parameters

| Parameter | Naive | Optimized |
|-----------|-------|-----------|
| Reorder trigger | Stock = 0 | Stock ≤ reorder point |
| Order quantity | Fixed 100 | EOQ formula |
| Safety stock | None | z × σ × √L (95% SL) |
| Lead time | 5 days | 5 days |

## Definitions

- **Safety Stock**: z × σ_demand × √lead_time (z=1.65 for 95% service level)
- **EOQ**: √(2 × D × S / H) — Economic Order Quantity
- **Reorder Point**: avg_demand × lead_time + safety_stock

---
⚠️ All numbers from script execution. Data is SYNTHETIC.