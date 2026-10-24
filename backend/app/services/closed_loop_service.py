"""
Closed Loop Service — orchestrates the central thesis pipeline:
anomaly -> root cause -> forecast impact -> recommended action -> human approval -> logged outcome.

Integrates anomaly detection, demand forecasting, inventory economics, and human-in-the-loop decision logging.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


def diagnose_root_cause(
    anomaly_type: str,
    detector: str,
    severity: float,
    details: dict | None,
) -> str:
    """Infer root cause from anomaly metrics, detector signals, and historical shifts."""
    details = details or {}
    if "cause" in details and details["cause"]:
        return str(details["cause"])

    if anomaly_type == "revenue_drop":
        pct = details.get("pct_change", details.get("impact_pct", "-50%"))
        return (
            f"Severe demand contraction ({pct}) exceeding normal variance. "
            f"Possible supplier stockout or channel outage."
        )
    elif anomaly_type == "revenue_spike":
        pct = details.get("pct_change", details.get("impact_pct", "+100%"))
        return (
            f"Sudden demand velocity surge ({pct}). "
            f"Promotional burst, viral referral, or enterprise bulk purchase."
        )
    elif anomaly_type == "zero_sales":
        streak = details.get("streak_days", details.get("consecutive_zero_days", 3))
        return f"Product transaction hiatus for {streak} consecutive days despite active catalog listing."
    elif anomaly_type == "inventory_critical":
        return "Stock depletion rate critically exceeding forecast replenishment timeline."
    return f"Statistical divergence detected via {detector} with severity {severity:.2f}."


async def evaluate_forecast_impact(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    product_id: uuid.UUID,
    anomaly_type: str,
    severity: float,
) -> dict:
    """
    Project forecast impact: stockout risk, days of supply remaining, and estimated revenue impact.
    """
    # Load product inventory & price
    p_res = await db.execute(
        text("""
            SELECT p.id, p.sku, p.name, p.unit_price,
                   i.stock_on_hand, i.reorder_point, i.safety_stock, i.lead_time_days
            FROM products p
            LEFT JOIN inventory i ON i.product_id = p.id AND i.org_id = :org_id
            WHERE p.id = :product_id AND p.org_id = :org_id
        """),
        {"org_id": str(org_id), "product_id": str(product_id)},
    )
    prod = p_res.mappings().first()
    if not prod:
        return {
            "forecast_impact": "Product records unavailable",
            "days_of_supply": None,
            "estimated_impact_gbp": 0.0,
            "stock_on_hand": 0,
            "reorder_point": 0,
            "lead_time_days": 7,
            "unit_price": 20.0,
            "avg_daily_demand": 1.0,
        }

    stock = prod["stock_on_hand"] or 0
    reorder_pt = prod["reorder_point"] or 50
    lead_time = prod["lead_time_days"] or 7
    unit_price = float(prod["unit_price"] or 25.0)

    # Query recent 30-day average daily sales
    sales_res = await db.execute(
        text("""
            SELECT COALESCE(AVG(quantity_sold), 1.0) AS avg_daily
            FROM daily_sales
            WHERE org_id = :org_id AND product_id = :product_id
              AND sale_date >= CURRENT_DATE - INTERVAL '30 days'
        """),
        {"org_id": str(org_id), "product_id": str(product_id)},
    )
    avg_daily = float(sales_res.scalar() or 10.0)
    days_of_supply = round(stock / max(avg_daily, 0.1), 1)

    if anomaly_type in ("revenue_drop", "inventory_critical") or stock <= reorder_pt:
        shortfall_days = max(0, lead_time - days_of_supply)
        lost_units = shortfall_days * avg_daily
        projected_loss = round(lost_units * unit_price, 2)
        summary = (
            f"Projected stockout within {days_of_supply} days (lead time: {lead_time}d). "
            f"Estimated stockout penalty / lost revenue: £{projected_loss:,.2f}."
        )
    elif anomaly_type == "zero_sales":
        idle_value = round(stock * unit_price, 2)
        summary = f"Idle inventory lockup: {stock} units valued at £{idle_value:,.2f} generating zero turnover."
        projected_loss = -round(idle_value * 0.1, 2)
    elif anomaly_type == "revenue_spike":
        potential_upside = round(avg_daily * 14 * unit_price * 0.3, 2)
        summary = f"Demand upside opportunity: buffer capacity required to capture projected £{potential_upside:,.2f} surge."
        projected_loss = potential_upside
    else:
        summary = f"Estimated demand adjustment needed across {lead_time} days planning horizon."
        projected_loss = 0.0

    return {
        "forecast_impact": summary,
        "days_of_supply": days_of_supply,
        "estimated_impact_gbp": projected_loss,
        "stock_on_hand": stock,
        "reorder_point": reorder_pt,
        "lead_time_days": lead_time,
        "unit_price": unit_price,
        "avg_daily_demand": round(avg_daily, 1),
    }


async def generate_recommendation_for_anomaly(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    anomaly_id: uuid.UUID,
) -> dict | None:
    """
    Execute closed loop step for a specific anomaly:
    anomaly -> root cause -> forecast impact -> recommended action.
    Creates a pending Recommendation if one does not already exist.
    """
    # 1. Fetch anomaly
    res = await db.execute(
        text("""
            SELECT id, product_id, anomaly_type, detector, severity_score, estimated_impact, details
            FROM anomalies
            WHERE id = :id AND org_id = :org_id
        """),
        {"id": str(anomaly_id), "org_id": str(org_id)},
    )
    anom = res.mappings().first()
    if not anom or not anom["product_id"]:
        return None

    # Check if a recommendation already exists for this product in pending state
    existing = await db.execute(
        text("""
            SELECT id FROM recommendations
            WHERE org_id = :org_id AND product_id = :prod_id AND status = 'pending'
        """),
        {"org_id": str(org_id), "prod_id": str(anom["product_id"])},
    )
    if existing.scalar():
        return None

    # 2. Diagnose Root Cause
    root_cause = diagnose_root_cause(
        anom["anomaly_type"],
        anom["detector"],
        float(anom["severity_score"]),
        anom["details"],
    )

    # 3. Forecast Impact
    impact = await evaluate_forecast_impact(
        db,
        org_id=org_id,
        product_id=anom["product_id"],
        anomaly_type=anom["anomaly_type"],
        severity=float(anom["severity_score"]),
    )

    # 4. Synthesize Recommended Action
    anom_type = anom["anomaly_type"]
    prod_id = anom["product_id"]

    if (
        anom_type in ("inventory_critical", "revenue_drop")
        or impact["stock_on_hand"] <= impact["reorder_point"]
    ):
        action_type = "reorder"
        suggested_qty = int(max(impact["avg_daily_demand"] * (impact["lead_time_days"] + 7), 50))
        estimated_cost = round(suggested_qty * impact["unit_price"] * 0.7, 2)
        reason = (
            f"Root Cause: {root_cause} | "
            f"Forecast Impact: {impact['forecast_impact']} | "
            f"Recommendation: Issue replenishment purchase order for {suggested_qty} units."
        )
        params = {
            "suggested_qty": suggested_qty,
            "lead_time_days": impact["lead_time_days"],
            "urgency": "immediate" if (impact["days_of_supply"] or 0) <= 2 else "high",
            "estimated_cost": estimated_cost,
            "anomaly_id": str(anomaly_id),
            "root_cause": root_cause,
            "forecast_impact": impact["forecast_impact"],
        }
    elif anom_type == "zero_sales":
        action_type = "markdown"
        reason = (
            f"Root Cause: {root_cause} | "
            f"Forecast Impact: {impact['forecast_impact']} | "
            f"Recommendation: Launch 15% promotional markdown to stimulate demand and recover holding capital."
        )
        params = {
            "discount_pct": 15,
            "current_price": impact["unit_price"],
            "promo_price": round(impact["unit_price"] * 0.85, 2),
            "anomaly_id": str(anomaly_id),
            "root_cause": root_cause,
            "forecast_impact": impact["forecast_impact"],
        }
    else:
        action_type = "investigate"
        reason = (
            f"Root Cause: {root_cause} | "
            f"Forecast Impact: {impact['forecast_impact']} | "
            f"Recommendation: Inspect supplier capacity and adjust safety stock buffer to capture upside."
        )
        params = {
            "safety_stock_adjustment": "+50%",
            "anomaly_id": str(anomaly_id),
            "root_cause": root_cause,
            "forecast_impact": impact["forecast_impact"],
        }

    rec_id = uuid.uuid4()
    await db.execute(
        text("""
            INSERT INTO recommendations (id, org_id, product_id, action_type, reason, parameters, status, created_at)
            VALUES (:id, :org_id, :prod_id, :action, :reason, :params, 'pending', :created_at)
        """),
        {
            "id": str(rec_id),
            "org_id": str(org_id),
            "prod_id": str(prod_id),
            "action": action_type,
            "reason": reason,
            "params": json.dumps(params),
            "created_at": datetime.now(UTC),
        },
    )
    await db.commit()

    return {
        "recommendation_id": str(rec_id),
        "product_id": str(prod_id),
        "action_type": action_type,
        "root_cause": root_cause,
        "forecast_impact": impact["forecast_impact"],
        "parameters": params,
    }


async def process_closed_loop_for_org(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    limit: int = 10,
) -> dict:
    """
    Scan all unresolved high-severity anomalies for the org and execute closed loop pipeline.
    """
    res = await db.execute(
        text("""
            SELECT id FROM anomalies
            WHERE org_id = :org_id AND is_dismissed = FALSE AND severity_score >= 0.5
            ORDER BY severity_score DESC, created_at DESC
            LIMIT :limit
        """),
        {"org_id": str(org_id), "limit": limit},
    )
    anomaly_ids = [row[0] for row in res.fetchall()]

    generated = []
    for aid in anomaly_ids:
        rec = await generate_recommendation_for_anomaly(db, org_id=org_id, anomaly_id=aid)
        if rec:
            generated.append(rec)

    return {
        "anomalies_evaluated": len(anomaly_ids),
        "recommendations_created": len(generated),
        "items": generated,
    }
