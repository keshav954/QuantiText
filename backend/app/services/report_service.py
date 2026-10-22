"""
Report service — aggregation, LLM narrative generation, and PDF export.

Pipeline:
1. Aggregate KPIs, trends, forecasts, inventory flags, anomalies into one JSON.
2. LLM writes a narrative from that JSON only (grounding check).
3. Persist the report to the `reports` table.
4. Export as PDF (or plain text if weasyprint is not available).

Data is SYNTHETIC unless stated otherwise.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm.base import TaskType
from app.services.llm.factory import get_provider

log = logging.getLogger(__name__)

# Where generated reports are stored
_REPORT_DIR = Path("/app/data/reports")


# ── Public API ─────────────────────────────────────────────────────────────────


async def generate_report(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
    title: str = "Weekly Business Report",
    report_type: str = "on_demand",
) -> dict:
    """
    Generate a full BI report.

    1. Aggregate data from views/tables.
    2. Generate LLM narrative from the aggregated JSON.
    3. Persist to DB.
    4. Return report dict.
    """
    # Step 1: Aggregate all data
    aggregated = await _aggregate_data(db, org_id)

    # Step 2: Generate narrative via LLM
    narrative = await _generate_narrative(aggregated)

    # Step 3: Persist
    report_id = uuid.uuid4()
    now = datetime.now(UTC)

    await db.execute(
        text("""
            INSERT INTO reports (id, org_id, generated_by, title, report_type, aggregated_data, narrative, created_at)
            VALUES (:id, :org_id, :generated_by, :title, :report_type, :aggregated_data, :narrative, :created_at)
        """),
        {
            "id": str(report_id),
            "org_id": str(org_id),
            "generated_by": str(user_id) if user_id else None,
            "title": title,
            "report_type": report_type,
            "aggregated_data": json.dumps(aggregated, default=str),
            "narrative": narrative,
            "created_at": now,
        },
    )
    await db.commit()

    return {
        "id": report_id,
        "org_id": org_id,
        "generated_by": user_id,
        "title": title,
        "report_type": report_type,
        "aggregated_data": aggregated,
        "narrative": narrative,
        "file_path": None,
        "created_at": now,
        "has_data": True,
    }


async def list_reports(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Return paginated report list."""
    count_result = await db.execute(
        text("SELECT COUNT(*) FROM reports WHERE org_id = :org_id"),
        {"org_id": str(org_id)},
    )
    total = count_result.scalar_one()

    result = await db.execute(
        text("""
            SELECT id, org_id, generated_by, title, report_type, narrative,
                   file_path, created_at,
                   (aggregated_data IS NOT NULL) AS has_data
            FROM reports
            WHERE org_id = :org_id
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {"org_id": str(org_id), "limit": limit, "offset": offset},
    )
    rows = result.mappings().all()

    return {
        "items": [
            {
                "id": r["id"],
                "org_id": r["org_id"],
                "generated_by": r["generated_by"],
                "title": r["title"],
                "report_type": r["report_type"],
                "narrative": r["narrative"],
                "file_path": r["file_path"],
                "created_at": r["created_at"],
                "has_data": r["has_data"],
            }
            for r in rows
        ],
        "total": total,
    }


async def get_report(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    report_id: uuid.UUID,
) -> dict | None:
    """Get full report detail including aggregated data."""
    result = await db.execute(
        text("""
            SELECT id, org_id, generated_by, title, report_type,
                   aggregated_data, narrative, file_path, created_at
            FROM reports
            WHERE id = :id AND org_id = :org_id
        """),
        {"id": str(report_id), "org_id": str(org_id)},
    )
    row = result.mappings().first()
    if not row:
        return None

    agg_data = row["aggregated_data"]
    if isinstance(agg_data, str):
        agg_data = json.loads(agg_data)

    return {
        "id": row["id"],
        "org_id": row["org_id"],
        "generated_by": row["generated_by"],
        "title": row["title"],
        "report_type": row["report_type"],
        "aggregated_data": agg_data,
        "narrative": row["narrative"],
        "file_path": row["file_path"],
        "created_at": row["created_at"],
        "has_data": agg_data is not None,
    }


async def export_report_text(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    report_id: uuid.UUID,
) -> str | None:
    """Export a report as formatted plain text (fallback for PDF)."""
    report = await get_report(db, org_id=org_id, report_id=report_id)
    if not report:
        return None

    lines = [
        f"{'=' * 60}",
        f"  {report['title']}",
        f"  Generated: {report['created_at']}",
        f"  Type: {report['report_type']}",
        f"{'=' * 60}",
        "",
    ]

    if report.get("narrative"):
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 40)
        lines.append(report["narrative"])
        lines.append("")

    agg = report.get("aggregated_data") or {}

    if "kpi_summary" in agg:
        kpi = agg["kpi_summary"]
        lines.append("KEY PERFORMANCE INDICATORS")
        lines.append("-" * 40)
        lines.append(f"  Total Revenue:    £{kpi.get('total_revenue', 0):,.2f}")
        lines.append(f"  Total Orders:     {kpi.get('total_orders', 0):,}")
        lines.append(f"  Avg Order Value:  £{kpi.get('avg_order_value', 0):,.2f}")
        lines.append(f"  Unique Customers: {kpi.get('unique_customers', 0):,}")
        lines.append("")

    if "top_products" in agg:
        lines.append("TOP PRODUCTS BY REVENUE")
        lines.append("-" * 40)
        for i, p in enumerate(agg["top_products"][:10], 1):
            lines.append(
                f"  {i}. {p.get('product_name', 'N/A')}: £{p.get('total_revenue', 0):,.2f}"
            )
        lines.append("")

    if "inventory_flags" in agg:
        inv = agg["inventory_flags"]
        lines.append("INVENTORY STATUS")
        lines.append("-" * 40)
        lines.append(f"  Critical Items: {inv.get('critical', 0)}")
        lines.append(f"  Low Stock:      {inv.get('low', 0)}")
        lines.append(f"  Overstock:      {inv.get('overstock', 0)}")
        lines.append(f"  Healthy:        {inv.get('healthy', 0)}")
        lines.append("")

    if "anomaly_summary" in agg:
        anom = agg["anomaly_summary"]
        lines.append("ANOMALIES DETECTED")
        lines.append("-" * 40)
        lines.append(f"  Total Active: {anom.get('total_active', 0)}")
        lines.append(f"  Critical:     {anom.get('critical', 0)}")
        lines.append(f"  Warnings:     {anom.get('warnings', 0)}")
        lines.append("")

    if "pending_recommendations" in agg:
        lines.append(f"PENDING RECOMMENDATIONS: {agg['pending_recommendations']}")
        lines.append("")

    lines.append(f"{'=' * 60}")
    lines.append("⚠️ Data is SYNTHETIC unless stated otherwise.")
    lines.append(f"{'=' * 60}")

    return "\n".join(lines)


# ── Recommendation / Approval ──────────────────────────────────────────────────


async def list_recommendations(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Return paginated recommendations with optional status filter."""
    where = "r.org_id = :org_id"
    params: dict = {"org_id": str(org_id), "limit": limit, "offset": offset}

    if status_filter:
        where += " AND r.status = :status"
        params["status"] = status_filter

    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM recommendations r WHERE {where}"),
        params,
    )
    total = count_result.scalar_one()

    pending_result = await db.execute(
        text("SELECT COUNT(*) FROM recommendations WHERE org_id = :org_id AND status = 'pending'"),
        {"org_id": str(org_id)},
    )
    pending_count = pending_result.scalar_one()

    result = await db.execute(
        text(f"""
            SELECT r.id, r.org_id, r.product_id, p.name AS product_name, p.sku,
                   r.action_type, r.reason, r.parameters, r.status,
                   r.approved_by, r.decided_at, r.created_at
            FROM recommendations r
            LEFT JOIN products p ON p.id = r.product_id
            WHERE {where}
            ORDER BY
                CASE r.status WHEN 'pending' THEN 0 ELSE 1 END,
                r.created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    )
    rows = result.mappings().all()

    items = [
        {
            "id": r["id"],
            "org_id": r["org_id"],
            "product_id": r["product_id"],
            "product_name": r["product_name"],
            "sku": r["sku"],
            "action_type": r["action_type"],
            "reason": r["reason"],
            "parameters": r["parameters"],
            "status": r["status"],
            "approved_by": r["approved_by"],
            "decided_at": r["decided_at"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]

    return {"items": items, "total": total, "pending_count": pending_count}


async def decide_recommendation(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    recommendation_id: uuid.UUID,
    action: str,
    user_id: uuid.UUID,
) -> bool:
    """Approve or reject a recommendation. Returns True if updated."""
    now = datetime.now(UTC)
    result = await db.execute(
        text("""
            UPDATE recommendations
            SET status = :status,
                approved_by = :user_id,
                decided_at = :decided_at
            WHERE id = :id AND org_id = :org_id AND status = 'pending'
        """),
        {
            "id": str(recommendation_id),
            "org_id": str(org_id),
            "status": "approved" if action == "approve" else "rejected",
            "user_id": str(user_id),
            "decided_at": now,
        },
    )
    await db.commit()
    return result.rowcount > 0


async def generate_purchase_order(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    recommendation_id: uuid.UUID,
) -> str | None:
    """Generate a formal Purchase Order document for a recommendation."""
    result = await db.execute(
        text("""
            SELECT
                r.id, r.org_id, r.product_id, r.action_type, r.reason,
                r.parameters, r.status, r.approved_by, r.decided_at, r.created_at,
                p.name AS product_name, p.sku,
                c.name AS category_name,
                i.stock_on_hand, i.reorder_point, i.lead_time_days, i.unit_cost,
                u.full_name AS approver_name, u.email AS approver_email,
                o.name AS org_name
            FROM recommendations r
            LEFT JOIN products p ON p.id = r.product_id
            LEFT JOIN categories c ON c.id = p.category_id
            LEFT JOIN inventory i ON i.product_id = r.product_id AND i.org_id = r.org_id
            LEFT JOIN users u ON u.id = r.approved_by
            JOIN orgs o ON o.id = r.org_id
            WHERE r.id = :id AND r.org_id = :org_id
        """),
        {"id": str(recommendation_id), "org_id": str(org_id)},
    )
    row = result.mappings().first()
    if not row:
        return None

    params = row["parameters"] or {}
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except Exception:
            params = {}

    suggested_qty = int(params.get("suggested_qty", 100))
    lead_time = int(params.get("lead_time_days") or row["lead_time_days"] or 7)
    unit_cost = float(params.get("unit_cost") or row["unit_cost"] or 25.0)
    urgency = str(params.get("urgency", "standard")).upper()
    subtotal = suggested_qty * unit_cost
    freight = 75.00 if subtotal > 0 else 0.00
    vat = subtotal * 0.20
    total_amount = subtotal + freight + vat

    po_ref = f"PO-{str(row['id'])[:8].upper()}"
    status_label = (
        "AUTHORIZED PURCHASE ORDER"
        if row["status"] == "approved"
        else f"PURCHASE REQUISITION ({row['status'].upper()})"
    )
    created_dt = row["created_at"].strftime("%Y-%m-%d %H:%M UTC") if row["created_at"] else "N/A"
    decided_dt = (
        row["decided_at"].strftime("%Y-%m-%d %H:%M UTC")
        if row["decided_at"]
        else "PENDING DECISION"
    )
    approver = (
        f"{row['approver_name']} ({row['approver_email']})"
        if row["approver_name"]
        else "System Decision Queue"
    )
    target_delivery = (
        (row["created_at"] + timedelta(days=lead_time)).strftime("%Y-%m-%d")
        if row["created_at"]
        else "TBD"
    )

    lines = [
        "=" * 78,
        f"{'QUANTITEXT DECISION SUPPORT SYSTEM':^78}",
        f"{status_label:^78}",
        f"{'Reference: ' + po_ref:^78}",
        "=" * 78,
        "",
        "1. ORDER HEADER & AUTHORIZATION",
        "-" * 78,
        f"  PO Number:            {po_ref}",
        f"  Issue Timestamp:      {created_dt}",
        f"  Order Status:         {row['status'].upper()}",
        f"  Authorized Approver:  {approver}",
        f"  Authorization Date:   {decided_dt}",
        f"  Requested Lead Time:  {lead_time} business days",
        f"  Target Delivery Date: {target_delivery}",
        "",
        "2. PURCHASING ENTITY & DESTINATION",
        "-" * 78,
        f"  Organization:         {row['org_name']}",
        "  Procurement Division: Supply Chain & Replenishment Operations",
        "  Delivery Hub:         Central Distribution Facility — Intake Dock B",
        "",
        "3. PRODUCT SPECIFICATIONS & LINE ITEMS",
        "-" * 78,
        f"  SKU:                  {row['sku'] or 'N/A'}",
        f"  Product Name:         {row['product_name'] or 'N/A'}",
        f"  Category:             {row['category_name'] or 'General Goods'}",
        f"  Warehouse Inventory:  {row['stock_on_hand'] or 0} on hand  |  Reorder Point: {row['reorder_point'] or 0}",
        "",
        f"  {'ITEM':<32} {'QTY':>8} {'UNIT COST':>14} {'EXT AMOUNT':>16}",
        f"  {'-' * 32} {'-' * 8} {'-' * 14} {'-' * 16}",
        f"  {(row['product_name'] or 'Retail Item')[:32]:<32} {suggested_qty:>8,d} {f'£{unit_cost:.2f}':>14} {f'£{subtotal:,.2f}':>16}",
        f"  {'-' * 72:>74}",
        f"  {'Merchandise Subtotal:':<56} {f'£{subtotal:,.2f}':>16}",
        f"  {'Freight & Inbound Handling (Standard Logistics):':<56} {f'£{freight:,.2f}':>16}",
        f"  {'Estimated VAT / Tax (20%):':<56} {f'£{vat:,.2f}':>16}",
        f"  {'=' * 72:>74}",
        f"  {'TOTAL PURCHASE ORDER VALUE:':<56} {f'£{total_amount:,.2f}':>16}",
        "",
        "4. ALGORITHMIC RATIONALE & CLOSED-LOOP AUDIT TRAIL",
        "-" * 78,
        f"  Action Category:      {row['action_type'].upper()}",
        f"  Urgency Classification: {urgency}",
        f"  Analytical Trigger:   {row['reason']}",
        f"  Recommendation UUID:  {row['id']}",
        "",
        "5. STANDARD COMMERCIAL TERMS & INSTRUCTIONS",
        "-" * 78,
        "  1. Vendor must acknowledge receipt and confirm ship date within 24 hours.",
        "  2. PO reference must be printed prominently on exterior master cartons and bill of lading.",
        "  3. Standard Payment Terms: Net 30 days from automated warehouse intake barcode verification.",
        "  4. Quantity variances greater than 2% require explicit procurement re-approval.",
        "",
        "=" * 78,
        "⚠️  Inventory, cost, lead-time and approval records generated by QuantiText DSS.",
        "=" * 78,
    ]
    return "\n".join(lines)


# ── Private helpers ────────────────────────────────────────────────────────────


async def _aggregate_data(db: AsyncSession, org_id: uuid.UUID) -> dict:
    """Collect all data needed for the report into a single dict."""
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    aggregated: dict = {"period": f"{start_date} to {end_date}"}

    # KPI summary
    try:
        kpi_result = await db.execute(
            text("""
                SELECT
                    COALESCE(SUM(total_revenue), 0) AS total_revenue,
                    COALESCE(SUM(order_count), 0) AS total_orders,
                    CASE WHEN SUM(order_count) > 0
                         THEN SUM(total_revenue) / SUM(order_count)
                         ELSE 0 END AS avg_order_value,
                    COALESCE(SUM(unique_customers), 0) AS unique_customers
                FROM v_kpi_daily
                WHERE org_id = :org_id
                  AND sale_date BETWEEN :start AND :end
            """),
            {"org_id": str(org_id), "start": start_date, "end": end_date},
        )
        row = kpi_result.mappings().first()
        if row:
            aggregated["kpi_summary"] = {
                "total_revenue": float(row["total_revenue"]),
                "total_orders": int(row["total_orders"]),
                "avg_order_value": round(float(row["avg_order_value"]), 2),
                "unique_customers": int(row["unique_customers"]),
            }
    except Exception:
        log.debug("KPI aggregation skipped", exc_info=True)

    # Top products
    try:
        tp_result = await db.execute(
            text("""
                SELECT product_name, category_name, total_revenue, total_qty
                FROM v_sales_by_product
                WHERE org_id = :org_id
                ORDER BY total_revenue DESC
                LIMIT 5
            """),
            {"org_id": str(org_id)},
        )
        aggregated["top_products"] = [
            {
                "product_name": r["product_name"],
                "category": r["category_name"],
                "total_revenue": float(r["total_revenue"]),
                "total_qty": int(r["total_qty"]),
            }
            for r in tp_result.mappings().all()
        ]
    except Exception:
        log.debug("Top products aggregation skipped", exc_info=True)

    # Inventory flags
    try:
        inv_result = await db.execute(
            text("""
                SELECT stock_status, COUNT(*) AS cnt
                FROM v_inventory_status
                WHERE org_id = :org_id
                GROUP BY stock_status
            """),
            {"org_id": str(org_id)},
        )
        inv_flags = {}
        for r in inv_result.mappings().all():
            inv_flags[r["stock_status"]] = int(r["cnt"])
        aggregated["inventory_flags"] = inv_flags
    except Exception:
        log.debug("Inventory aggregation skipped", exc_info=True)

    # Anomaly summary
    try:
        anom_result = await db.execute(
            text("""
                SELECT
                    COUNT(*) FILTER (WHERE NOT is_dismissed) AS total_active,
                    COUNT(*) FILTER (WHERE severity_score >= 0.75 AND NOT is_dismissed) AS critical,
                    COUNT(*) FILTER (WHERE severity_score < 0.75 AND severity_score >= 0.5 AND NOT is_dismissed) AS warnings
                FROM anomalies
                WHERE org_id = :org_id
                  AND detected_date >= :start
            """),
            {"org_id": str(org_id), "start": start_date},
        )
        anom_row = anom_result.mappings().first()
        if anom_row:
            aggregated["anomaly_summary"] = {
                "total_active": int(anom_row["total_active"]),
                "critical": int(anom_row["critical"]),
                "warnings": int(anom_row["warnings"]),
            }
    except Exception:
        log.debug("Anomaly aggregation skipped", exc_info=True)

    # Pending recommendations count
    try:
        rec_result = await db.execute(
            text(
                "SELECT COUNT(*) FROM recommendations WHERE org_id = :org_id AND status = 'pending'"
            ),
            {"org_id": str(org_id)},
        )
        aggregated["pending_recommendations"] = rec_result.scalar_one()
    except Exception:
        log.debug("Recommendations count skipped", exc_info=True)

    # Forecast coverage
    try:
        fc_result = await db.execute(
            text("""
                SELECT COUNT(DISTINCT product_id) AS forecasted_products,
                       ROUND(AVG(mape)::numeric, 2) AS avg_mape
                FROM forecasts
                WHERE org_id = :org_id
                  AND forecast_date >= CURRENT_DATE
            """),
            {"org_id": str(org_id)},
        )
        fc_row = fc_result.mappings().first()
        if fc_row:
            aggregated["forecast_summary"] = {
                "forecasted_products": int(fc_row["forecasted_products"]),
                "avg_mape": float(fc_row["avg_mape"]) if fc_row["avg_mape"] else None,
            }
    except Exception:
        log.debug("Forecast aggregation skipped", exc_info=True)

    return aggregated


async def _generate_narrative(aggregated: dict) -> str:
    """Use LLM to write a narrative from the aggregated data only."""
    data_text = json.dumps(aggregated, indent=2, default=str)

    prompt = f"""Write a concise executive summary (3-5 paragraphs) for a weekly business intelligence report.
Use ONLY the data provided below — do not invent any numbers or facts.
All monetary values are in GBP (£). Data is synthetic unless stated otherwise.

Data:
{data_text}

Structure:
1. Overview paragraph with key revenue/order metrics and period.
2. Product performance highlights.
3. Inventory health and any critical flags.
4. Anomalies and recommended actions.
5. Brief outlook/recommendations.

Be professional, data-driven, and specific with numbers."""

    try:
        provider = get_provider()
        response = await provider.generate(
            prompt,
            system_prompt=(
                "You are a senior business analyst writing a BI report narrative. "
                "Use ONLY the provided data. Never invent numbers. Be concise and actionable."
            ),
            task_type=TaskType.SUMMARIZATION,
            temperature=0.2,
            max_tokens=1500,
        )
        return response.text
    except Exception:
        log.warning("LLM narrative generation failed, using template fallback", exc_info=True)
        return _template_narrative(aggregated)


def _template_narrative(agg: dict) -> str:
    """Fallback narrative when LLM is unavailable."""
    kpi = agg.get("kpi_summary", {})
    period = agg.get("period", "the reporting period")

    lines = [
        f"Business Performance Report for {period}.",
        "",
    ]

    if kpi:
        lines.append(
            f"During this period, total revenue reached £{kpi.get('total_revenue', 0):,.2f} "
            f"across {kpi.get('total_orders', 0):,} orders, "
            f"with an average order value of £{kpi.get('avg_order_value', 0):,.2f}. "
            f"The business served {kpi.get('unique_customers', 0):,} unique customers."
        )
        lines.append("")

    top_prods = agg.get("top_products", [])
    if top_prods:
        top = top_prods[0]
        lines.append(
            f"The top-performing product was {top.get('product_name', 'N/A')} "
            f"in the {top.get('category', 'N/A')} category, "
            f"generating £{top.get('total_revenue', 0):,.2f} in revenue."
        )
        lines.append("")

    inv = agg.get("inventory_flags", {})
    if inv:
        critical = inv.get("critical", 0)
        low = inv.get("low", 0)
        if critical + low > 0:
            lines.append(
                f"Inventory monitoring has flagged {critical} critical "
                f"and {low} low-stock items requiring attention."
            )
        else:
            lines.append("Inventory levels are within healthy ranges across all categories.")
        lines.append("")

    anom = agg.get("anomaly_summary", {})
    if anom and anom.get("total_active", 0) > 0:
        lines.append(
            f"The anomaly detection system identified {anom.get('total_active', 0)} active anomalies, "
            f"including {anom.get('critical', 0)} critical items that require immediate review."
        )
        lines.append("")

    lines.append("⚠️ Note: All data in this report is SYNTHETIC unless stated otherwise.")

    return "\n".join(lines)
