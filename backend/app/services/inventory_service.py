"""
Inventory service — safety stock, EOQ, ABC classification, stock status.

Data is SYNTHETIC unless stated otherwise.
All calculations follow standard inventory management formulas:
  - Safety Stock: z * σ_demand * √lead_time   (z=1.65 for 95% service level)
  - EOQ: √(2 * D * S / H)
  - ABC: A = top 70% of cumulative revenue, B = next 20%, C = remaining 10%
"""

from __future__ import annotations

import logging
import math
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

# 95% service level z-score
_Z_95 = 1.65
# Ordering cost (flat, synthetic)
_ORDERING_COST = 50.0


# ── Helpers ────────────────────────────────────────────────────────────────────

def _eoq(annual_demand: float, ordering_cost: float, holding_cost_per_unit: float) -> int:
    """Economic Order Quantity = sqrt(2DS/H)."""
    if holding_cost_per_unit <= 0 or annual_demand <= 0:
        return 0
    raw = math.sqrt((2 * annual_demand * ordering_cost) / holding_cost_per_unit)
    return max(1, round(raw))


def _safety_stock(avg_daily_demand: float, std_daily_demand: float, lead_time_days: int) -> int:
    """SS = z * σ * √L — for 95% service level."""
    ss = _Z_95 * std_daily_demand * math.sqrt(max(1, lead_time_days))
    return max(0, round(ss))


def _classify_abc(items: list[dict]) -> list[dict]:
    """
    Assign ABC classification based on cumulative revenue share.
    Modifies items in-place. Items must have 'annual_revenue' key.
    """
    total_rev = sum(i.get("annual_revenue", 0) for i in items)
    if total_rev == 0:
        for item in items:
            item["abc_class"] = "C"
        return items

    # Sort descending by revenue for classification
    sorted_items = sorted(items, key=lambda x: x.get("annual_revenue", 0), reverse=True)
    cumulative = 0.0
    for item in sorted_items:
        cumulative += item.get("annual_revenue", 0)
        pct = cumulative / total_rev
        if pct <= 0.70:
            item["abc_class"] = "A"
        elif pct <= 0.90:
            item["abc_class"] = "B"
        else:
            item["abc_class"] = "C"
    return items


def _stock_status(stock_on_hand: int, reorder_point: int, safety_stock: int, days_of_stock: float) -> str:
    """Classify stock status."""
    if stock_on_hand <= 0:
        return "critical"
    if stock_on_hand <= safety_stock:
        return "critical"
    if stock_on_hand <= reorder_point:
        return "low"
    if days_of_stock > 180:
        return "overstock"
    return "ok"


# ── Public API ─────────────────────────────────────────────────────────────────

async def get_inventory_list(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    status_filter: str | None = None,
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """
    Return paginated inventory list with computed analysis fields.
    Joins inventory + products + categories + recent daily_sales for demand stats.
    """
    # 1. Load raw inventory with product/category info
    rows = await _load_inventory_rows(db, org_id)

    # 2. Load demand stats (avg + std daily demand per product)
    demand_stats = await _load_demand_stats(db, org_id)

    # 3. Enrich each row
    items: list[dict] = []
    for row in rows:
        product_id_str = str(row["product_id"])
        stats = demand_stats.get(product_id_str, {"avg": 0.0, "std": 0.0, "annual": 0.0})

        avg_daily = stats["avg"]
        std_daily = stats["std"]
        lead_time = int(row["lead_time_days"])
        stock = int(row["stock_on_hand"])
        unit_cost = float(row["unit_cost"])
        holding_pct = float(row["holding_cost_pct"])

        ss = _safety_stock(avg_daily, std_daily, lead_time)
        annual_demand = avg_daily * 365
        holding_cost_per_unit = unit_cost * holding_pct
        eoq = _eoq(annual_demand, _ORDERING_COST, holding_cost_per_unit)
        days_of_stock = (stock / avg_daily) if avg_daily > 0 else 9999.0

        item = {
            "product_id": row["product_id"],
            "sku": row["sku"],
            "product_name": row["product_name"],
            "category": row["category_name"],
            "stock_on_hand": stock,
            "reorder_point": int(row["reorder_point"]),
            "lead_time_days": lead_time,
            "min_order_qty": int(row["min_order_qty"]),
            "unit_cost": unit_cost,
            "holding_cost_pct": holding_pct,
            "avg_daily_demand": round(avg_daily, 2),
            "safety_stock": ss,
            "eoq": eoq,
            "days_of_stock": round(min(days_of_stock, 9999), 1),
            "annual_revenue": stats["annual"],
            "last_updated": row["last_updated"],
        }
        item["status"] = _stock_status(stock, int(row["reorder_point"]), ss, days_of_stock)
        items.append(item)

    # 4. ABC classification (modifies in-place)
    _classify_abc(items)

    # 5. Apply filters
    if status_filter:
        items = [i for i in items if i["status"] == status_filter]
    if category:
        items = [i for i in items if (i["category"] or "").lower() == category.lower()]

    # 6. Compute summary counts before pagination
    low_stock = sum(1 for i in items if i["status"] == "low")
    critical = sum(1 for i in items if i["status"] == "critical")

    total = len(items)
    page_items = items[offset: offset + limit]

    return {
        "items": page_items,
        "total": total,
        "low_stock_count": low_stock,
        "critical_count": critical,
    }


async def get_inventory_summary(db: AsyncSession, *, org_id: uuid.UUID) -> dict:
    """Aggregate inventory health numbers."""
    result = await get_inventory_list(db, org_id=org_id, limit=10000)
    items = result["items"]

    total_value = sum(i["stock_on_hand"] * i["unit_cost"] for i in items)

    return {
        "total_products": result["total"],
        "low_stock_count": result["low_stock_count"],
        "critical_count": result["critical_count"],
        "overstock_count": sum(1 for i in items if i["status"] == "overstock"),
        "total_inventory_value": round(total_value, 2),
    }


async def get_reorder_suggestions(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    limit: int = 20,
) -> list[dict]:
    """Return products that should be reordered, ranked by urgency."""
    result = await get_inventory_list(db, org_id=org_id, limit=10000)
    items = result["items"]

    needs_reorder = [
        i for i in items
        if i["status"] in ("critical", "low") and i["eoq"] > 0
    ]

    suggestions = []
    for item in needs_reorder:
        eoq = item["eoq"]
        suggested_qty = max(eoq, item["min_order_qty"])
        suggestions.append({
            "product_id": item["product_id"],
            "sku": item["sku"],
            "product_name": item["product_name"],
            "current_stock": item["stock_on_hand"],
            "reorder_point": item["reorder_point"],
            "eoq": eoq,
            "suggested_qty": suggested_qty,
            "estimated_cost": round(suggested_qty * item["unit_cost"], 2),
            "urgency": "immediate" if item["status"] == "critical" else "soon",
        })

    # Sort by urgency then by current stock ascending
    suggestions.sort(key=lambda x: (0 if x["urgency"] == "immediate" else 1, x["current_stock"]))
    return suggestions[:limit]


# ── Private DB helpers ─────────────────────────────────────────────────────────

async def _load_inventory_rows(db: AsyncSession, org_id: uuid.UUID) -> list:
    result = await db.execute(
        text("""
            SELECT
                i.product_id, p.sku, p.name AS product_name,
                c.name AS category_name,
                i.stock_on_hand, i.reorder_point, i.lead_time_days,
                i.min_order_qty, i.unit_cost, i.holding_cost_pct,
                i.last_updated
            FROM inventory i
            JOIN products p ON p.id = i.product_id
            LEFT JOIN categories c ON c.id = p.category_id
            WHERE i.org_id = :org_id
            ORDER BY p.name
        """),
        {"org_id": str(org_id)},
    )
    return result.mappings().all()


async def _load_demand_stats(db: AsyncSession, org_id: uuid.UUID) -> dict[str, dict]:
    """
    Compute avg/std daily demand per product from the last 90 days of daily_sales.
    Returns {product_id_str: {avg, std, annual}}.
    """
    result = await db.execute(
        text("""
            SELECT
                product_id::text,
                AVG(quantity_sold) AS avg_qty,
                STDDEV(quantity_sold) AS std_qty,
                SUM(revenue) AS total_revenue
            FROM daily_sales
            WHERE org_id = :org_id
              AND sale_date >= CURRENT_DATE - INTERVAL '90 days'
            GROUP BY product_id
        """),
        {"org_id": str(org_id)},
    )
    rows = result.mappings().all()
    return {
        r["product_id"]: {
            "avg": float(r["avg_qty"] or 0),
            "std": float(r["std_qty"] or 0),
            "annual": float(r["total_revenue"] or 0) * (365 / 90),
        }
        for r in rows
    }
