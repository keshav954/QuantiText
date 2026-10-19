"""
Inventory Policy Simulation — compares naive vs. optimized reorder policy.

Usage:
    python -m docs.eval.eval_inventory

Replays 90 days of synthetic demand history and compares:
  - Naive policy: reorder when stock hits 0, order fixed batch
  - Optimized policy: safety stock + EOQ + reorder point

Metrics: stockout rate, excess stock, total cost.
Outputs: docs/eval/inventory_results.md

Data is SYNTHETIC.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

RESULTS_PATH = Path(__file__).parent / "inventory_results.md"

# Parameters
N_PRODUCTS = 20
N_DAYS = 90
HOLDING_COST_RATE = 0.02  # per unit per day
ORDERING_COST = 50.0  # per order
STOCKOUT_PENALTY = 10.0  # per unit of lost demand
Z_95 = 1.65


def simulate_demand(n_products: int, n_days: int) -> np.ndarray:
    """Generate synthetic daily demand (products × days)."""
    rng = np.random.default_rng(42)
    base_demand = rng.uniform(5, 30, size=n_products)
    demand = np.zeros((n_products, n_days))
    for p in range(n_products):
        demand[p] = np.maximum(0, rng.normal(base_demand[p], base_demand[p] * 0.3, size=n_days))
    return demand.astype(int)


def naive_policy(demand: np.ndarray) -> dict:
    """Naive: reorder a fixed batch of 100 when stock reaches 0, lead time 5 days."""
    n_products, n_days = demand.shape
    lead_time = 5
    batch_size = 100

    total_stockouts = 0
    total_excess = 0
    total_orders = 0
    total_holding_cost = 0.0
    total_ordering_cost = 0.0
    total_stockout_cost = 0.0

    for p in range(n_products):
        stock = 100  # starting stock
        pending_delivery = 0
        delivery_day = -1

        for d in range(n_days):
            # Receive delivery
            if d == delivery_day:
                stock += pending_delivery
                pending_delivery = 0

            # Fulfil demand
            d_today = int(demand[p, d])
            if stock >= d_today:
                stock -= d_today
            else:
                total_stockouts += (d_today - stock)
                total_stockout_cost += (d_today - stock) * STOCKOUT_PENALTY
                stock = 0

            # Reorder if stock is 0
            if stock == 0 and pending_delivery == 0:
                pending_delivery = batch_size
                delivery_day = d + lead_time
                total_orders += 1
                total_ordering_cost += ORDERING_COST

            total_holding_cost += stock * HOLDING_COST_RATE

        total_excess += stock  # leftover at end

    return {
        "stockouts": total_stockouts,
        "excess_stock": total_excess,
        "total_orders": total_orders,
        "holding_cost": round(total_holding_cost, 2),
        "ordering_cost": round(total_ordering_cost, 2),
        "stockout_cost": round(total_stockout_cost, 2),
        "total_cost": round(total_holding_cost + total_ordering_cost + total_stockout_cost, 2),
    }


def optimized_policy(demand: np.ndarray) -> dict:
    """Optimized: safety stock + EOQ + reorder point, lead time 5 days."""
    n_products, n_days = demand.shape
    lead_time = 5

    total_stockouts = 0
    total_excess = 0
    total_orders = 0
    total_holding_cost = 0.0
    total_ordering_cost = 0.0
    total_stockout_cost = 0.0

    for p in range(n_products):
        # Compute parameters from demand history (first 30 days as training)
        train = demand[p, :30]
        avg_demand = train.mean()
        std_demand = train.std()

        safety_stock = int(Z_95 * std_demand * np.sqrt(lead_time))
        eoq = int(np.sqrt(2 * avg_demand * 365 * ORDERING_COST / (HOLDING_COST_RATE * 365)))
        eoq = max(eoq, 10)  # minimum order
        reorder_point = int(avg_demand * lead_time + safety_stock)

        stock = int(avg_demand * 14)  # starting: 2 weeks of demand
        pending_delivery = 0
        delivery_day = -1

        for d in range(n_days):
            # Receive delivery
            if d == delivery_day:
                stock += pending_delivery
                pending_delivery = 0

            # Fulfil demand
            d_today = int(demand[p, d])
            if stock >= d_today:
                stock -= d_today
            else:
                total_stockouts += (d_today - stock)
                total_stockout_cost += (d_today - stock) * STOCKOUT_PENALTY
                stock = 0

            # Reorder at reorder point
            if stock <= reorder_point and pending_delivery == 0:
                pending_delivery = eoq
                delivery_day = d + lead_time
                total_orders += 1
                total_ordering_cost += ORDERING_COST

            total_holding_cost += stock * HOLDING_COST_RATE

        total_excess += stock

    return {
        "stockouts": total_stockouts,
        "excess_stock": total_excess,
        "total_orders": total_orders,
        "holding_cost": round(total_holding_cost, 2),
        "ordering_cost": round(total_ordering_cost, 2),
        "stockout_cost": round(total_stockout_cost, 2),
        "total_cost": round(total_holding_cost + total_ordering_cost + total_stockout_cost, 2),
    }


def main():
    print(f"Generating synthetic demand: {N_PRODUCTS} products × {N_DAYS} days...")
    demand = simulate_demand(N_PRODUCTS, N_DAYS)

    print("Running naive policy...")
    naive = naive_policy(demand)
    print(f"  Stockouts: {naive['stockouts']}, Excess: {naive['excess_stock']}, Cost: £{naive['total_cost']:,.2f}")

    print("Running optimized policy...")
    optimized = optimized_policy(demand)
    print(f"  Stockouts: {optimized['stockouts']}, Excess: {optimized['excess_stock']}, Cost: £{optimized['total_cost']:,.2f}")

    # Improvements
    stockout_improvement = (
        (naive["stockouts"] - optimized["stockouts"]) / naive["stockouts"] * 100
        if naive["stockouts"] > 0 else 0
    )
    cost_improvement = (
        (naive["total_cost"] - optimized["total_cost"]) / naive["total_cost"] * 100
        if naive["total_cost"] > 0 else 0
    )

    lines = [
        "# Inventory Policy Simulation Results",
        "",
        f"> Generated: {time.strftime('%Y-%m-%d %H:%M')}",
        f"> Simulation: {N_PRODUCTS} products × {N_DAYS} days",
        "> Data is **SYNTHETIC**",
        "",
        "## Policy Comparison",
        "",
        "| Metric | Naive Policy | Optimized (SS+EOQ+ROP) | Improvement |",
        "|--------|-------------|----------------------|-------------|",
        f"| Stockout Units | {naive['stockouts']} | {optimized['stockouts']} | {stockout_improvement:.1f}% |",
        f"| Excess Stock | {naive['excess_stock']} | {optimized['excess_stock']} | — |",
        f"| Total Orders | {naive['total_orders']} | {optimized['total_orders']} | — |",
        f"| Holding Cost | £{naive['holding_cost']:,.2f} | £{optimized['holding_cost']:,.2f} | — |",
        f"| Ordering Cost | £{naive['ordering_cost']:,.2f} | £{optimized['ordering_cost']:,.2f} | — |",
        f"| Stockout Cost | £{naive['stockout_cost']:,.2f} | £{optimized['stockout_cost']:,.2f} | — |",
        f"| **Total Cost** | **£{naive['total_cost']:,.2f}** | **£{optimized['total_cost']:,.2f}** | **{cost_improvement:.1f}%** |",
        "",
        "## Policy Parameters",
        "",
        "| Parameter | Naive | Optimized |",
        "|-----------|-------|-----------|",
        "| Reorder trigger | Stock = 0 | Stock ≤ reorder point |",
        "| Order quantity | Fixed 100 | EOQ formula |",
        "| Safety stock | None | z × σ × √L (95% SL) |",
        "| Lead time | 5 days | 5 days |",
        "",
        "## Definitions",
        "",
        "- **Safety Stock**: z × σ_demand × √lead_time (z=1.65 for 95% service level)",
        "- **EOQ**: √(2 × D × S / H) — Economic Order Quantity",
        "- **Reorder Point**: avg_demand × lead_time + safety_stock",
        "",
        "---",
        "⚠️ All numbers from script execution. Data is SYNTHETIC.",
    ]

    RESULTS_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nResults written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
