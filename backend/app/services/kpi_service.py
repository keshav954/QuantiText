"""
KPI service — computes dashboard KPIs with Redis caching.
Queries the SQL views for fast aggregation.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, timedelta

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

# Cache TTL in seconds (5 minutes)
CACHE_TTL = 300


def _cache_key(org_id: uuid.UUID, name: str, params: dict) -> str:
    """Build a deterministic Redis cache key."""
    param_str = "|".join(f"{k}={v}" for k, v in sorted(params.items()) if v is not None)
    return f"kpi:{org_id}:{name}:{param_str}"


async def _get_cached(redis: Redis, key: str) -> dict | None:
    """Try to fetch from Redis cache."""
    try:
        data = await redis.get(key)
        if data:
            return json.loads(data)
    except Exception:
        log.warning("Redis cache read failed for key=%s", key)
    return None


async def _set_cached(redis: Redis, key: str, data: dict) -> None:
    """Write to Redis cache with TTL."""
    try:
        await redis.setex(key, CACHE_TTL, json.dumps(data, default=str))
    except Exception:
        log.warning("Redis cache write failed for key=%s", key)


async def get_kpi_summary(
    db: AsyncSession,
    redis: Redis,
    *,
    org_id: uuid.UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    category: str | None = None,
    region: str | None = None,
) -> dict:
    """
    Compute top-level KPI summary: revenue, orders, AOV, customers, with trends.
    Uses v_kpi_daily view. Results cached in Redis for 5 minutes.
    """
    params = {
        "start_date": str(start_date) if start_date else None,
        "end_date": str(end_date) if end_date else None,
        "category": category,
        "region": region,
    }
    cache_key = _cache_key(org_id, "summary", params)

    # Try cache
    cached = await _get_cached(redis, cache_key)
    if cached:
        return cached

    # Build query with optional filters
    where_clauses = ["org_id = :org_id"]
    query_params: dict = {"org_id": str(org_id)}

    if start_date:
        where_clauses.append("sale_date >= :start_date")
        query_params["start_date"] = start_date
    if end_date:
        where_clauses.append("sale_date <= :end_date")
        query_params["end_date"] = end_date

    where_sql = " AND ".join(where_clauses)

    # Current period
    result = await db.execute(
        text(f"""
            SELECT
                COALESCE(SUM(total_revenue), 0) AS total_revenue,
                COALESCE(SUM(order_count), 0) AS total_orders,
                CASE WHEN SUM(order_count) > 0
                     THEN SUM(total_revenue) / SUM(order_count)
                     ELSE 0 END AS avg_order_value,
                COALESCE(SUM(unique_customers), 0) AS unique_customers
            FROM v_kpi_daily
            WHERE {where_sql}
        """),
        query_params,
    )
    row = result.mappings().first()

    summary = {
        "total_revenue": float(row["total_revenue"]) if row else 0,
        "total_orders": int(row["total_orders"]) if row else 0,
        "avg_order_value": round(float(row["avg_order_value"]), 2) if row else 0,
        "unique_customers": int(row["unique_customers"]) if row else 0,
        "revenue_trend": None,
        "orders_trend": None,
    }

    # Compute trend (compare to previous period of same length)
    if start_date and end_date:
        period_days = (end_date - start_date).days
        prev_start = start_date - timedelta(days=period_days)
        prev_end = start_date - timedelta(days=1)

        # Simpler: just re-query with shifted dates
        prev_result = await db.execute(
            text("""
                SELECT
                    COALESCE(SUM(total_revenue), 0) AS total_revenue,
                    COALESCE(SUM(order_count), 0) AS total_orders
                FROM v_kpi_daily
                WHERE org_id = :org_id
                  AND sale_date >= :prev_start
                  AND sale_date <= :prev_end
            """),
            {"org_id": str(org_id), "prev_start": prev_start, "prev_end": prev_end},
        )
        prev_row = prev_result.mappings().first()
        if prev_row:
            prev_rev = float(prev_row["total_revenue"])
            prev_ord = int(prev_row["total_orders"])
            if prev_rev > 0:
                summary["revenue_trend"] = round(
                    ((summary["total_revenue"] - prev_rev) / prev_rev) * 100, 1
                )
            if prev_ord > 0:
                summary["orders_trend"] = round(
                    ((summary["total_orders"] - prev_ord) / prev_ord) * 100, 1
                )

    await _set_cached(redis, cache_key, summary)
    return summary


async def get_revenue_trend(
    db: AsyncSession,
    redis: Redis,
    *,
    org_id: uuid.UUID,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """
    Daily revenue and order count time series.
    Returns sorted list of {date, revenue, order_count} dicts.
    """
    params = {
        "start_date": str(start_date) if start_date else None,
        "end_date": str(end_date) if end_date else None,
    }
    cache_key = _cache_key(org_id, "revenue_trend", params)

    cached = await _get_cached(redis, cache_key)
    if cached:
        return cached

    where_clauses = ["org_id = :org_id"]
    query_params: dict = {"org_id": str(org_id)}

    if start_date:
        where_clauses.append("sale_date >= :start_date")
        query_params["start_date"] = start_date
    if end_date:
        where_clauses.append("sale_date <= :end_date")
        query_params["end_date"] = end_date

    where_sql = " AND ".join(where_clauses)

    result = await db.execute(
        text(f"""
            SELECT sale_date, total_revenue AS revenue, order_count
            FROM v_kpi_daily
            WHERE {where_sql}
            ORDER BY sale_date
        """),
        query_params,
    )
    rows = result.mappings().all()

    data = [
        {
            "date": str(row["sale_date"]),
            "revenue": float(row["revenue"]),
            "order_count": int(row["order_count"]),
        }
        for row in rows
    ]

    period = ""
    if data:
        period = f"{data[0]['date']} to {data[-1]['date']}"

    response = {"data": data, "period": period}
    await _set_cached(redis, cache_key, response)
    return response


async def get_top_products(
    db: AsyncSession,
    redis: Redis,
    *,
    org_id: uuid.UUID,
    limit: int = 10,
) -> dict:
    """
    Top N products by total revenue.
    Uses v_sales_by_product view.
    """
    cache_key = _cache_key(org_id, "top_products", {"limit": str(limit)})

    cached = await _get_cached(redis, cache_key)
    if cached:
        return cached

    result = await db.execute(
        text("""
            SELECT product_id, sku, product_name, category_name,
                   total_revenue, total_qty
            FROM v_sales_by_product
            WHERE org_id = :org_id
            ORDER BY total_revenue DESC
            LIMIT :limit
        """),
        {"org_id": str(org_id), "limit": limit},
    )
    rows = result.mappings().all()

    products = [
        {
            "product_id": str(row["product_id"]),
            "sku": row["sku"],
            "product_name": row["product_name"],
            "category": row["category_name"],
            "total_revenue": float(row["total_revenue"]),
            "total_qty": int(row["total_qty"]),
        }
        for row in rows
    ]

    response = {"products": products, "limit": limit}
    await _set_cached(redis, cache_key, response)
    return response
