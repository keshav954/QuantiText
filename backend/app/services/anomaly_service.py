"""
Anomaly detection service — Z-score, Isolation Forest, data quality checks.

Detectors:
  zscore      — flags product-days where |z| > threshold (revenue or qty)
  iforest     — Isolation Forest on multi-variate daily features
  data_quality — missing/zero sales stretches

All detected anomalies are persisted to the `anomalies` table.
Matching `alerts` are created for severity_score > 0.5.

Data is SYNTHETIC unless stated otherwise.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

# Thresholds
_ZSCORE_THRESHOLD = 2.5
_MIN_HISTORY_DAYS = 14
_ALERT_SEVERITY_THRESHOLD = 0.5


# ── Public API ─────────────────────────────────────────────────────────────────

async def run_detection(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    lookback_days: int = 30,
) -> dict:
    """
    Run all detectors over the past `lookback_days` of data.
    Returns counts of new anomalies and alerts created.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=lookback_days)

    # Load daily sales
    sales_df = await _load_sales_df(db, org_id, start_date, end_date)

    if sales_df.empty:
        return {"new_anomalies": 0, "new_alerts": 0, "period_checked": f"{start_date} to {end_date}"}

    # Existing anomaly keys to avoid duplicates
    existing = await _load_existing_anomaly_keys(db, org_id, start_date, end_date)

    anomalies: list[dict] = []
    anomalies.extend(_detect_zscore(sales_df, existing))
    anomalies.extend(_detect_data_quality(sales_df, existing))

    # Try Isolation Forest (needs sklearn)
    try:
        anomalies.extend(_detect_iforest(sales_df, existing))
    except Exception:
        log.debug("IForest detector skipped", exc_info=True)

    # Persist anomalies and create alerts
    new_anomaly_count = 0
    new_alert_count = 0
    for a in anomalies:
        aid = await _persist_anomaly(db, org_id, a)
        if aid and a["severity_score"] >= _ALERT_SEVERITY_THRESHOLD:
            await _create_alert(db, org_id, aid, a)
            new_alert_count += 1
        if aid:
            new_anomaly_count += 1

    await db.commit()

    return {
        "new_anomalies": new_anomaly_count,
        "new_alerts": new_alert_count,
        "period_checked": f"{start_date} to {end_date}",
    }


async def get_anomalies(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    only_active: bool = True,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Return paginated anomaly list."""
    where = "org_id = :org_id"
    if only_active:
        where += " AND is_dismissed = FALSE"

    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM anomalies WHERE {where}"),
        {"org_id": str(org_id)},
    )
    total = count_result.scalar_one()

    result = await db.execute(
        text(f"""
            SELECT
                a.id, a.product_id, p.sku, p.name AS product_name,
                a.detected_date, a.anomaly_type, a.detector,
                a.severity_score, a.estimated_impact, a.details,
                a.is_dismissed, a.created_at
            FROM anomalies a
            LEFT JOIN products p ON p.id = a.product_id
            WHERE {where}
            ORDER BY a.severity_score DESC, a.created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {"org_id": str(org_id), "limit": limit, "offset": offset},
    )
    rows = result.mappings().all()

    items = [
        {
            "id": r["id"],
            "product_id": r["product_id"],
            "sku": r["sku"],
            "product_name": r["product_name"],
            "detected_date": r["detected_date"],
            "anomaly_type": r["anomaly_type"],
            "detector": r["detector"],
            "severity_score": float(r["severity_score"]),
            "estimated_impact": float(r["estimated_impact"]) if r["estimated_impact"] else None,
            "details": r["details"],
            "is_dismissed": r["is_dismissed"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]
    return {"items": items, "total": total}


async def dismiss_anomaly(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    anomaly_id: uuid.UUID,
) -> bool:
    """Mark an anomaly as dismissed. Returns True if found and updated."""
    result = await db.execute(
        text("""
            UPDATE anomalies
            SET is_dismissed = TRUE
            WHERE id = :id AND org_id = :org_id
        """),
        {"id": str(anomaly_id), "org_id": str(org_id)},
    )
    await db.commit()
    return result.rowcount > 0


async def get_alerts(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    only_unread: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Return paginated alert list."""
    where = "org_id = :org_id"
    if only_unread:
        where += " AND is_read = FALSE"

    unread_result = await db.execute(
        text("SELECT COUNT(*) FROM alerts WHERE org_id = :org_id AND is_read = FALSE"),
        {"org_id": str(org_id)},
    )
    unread_count = unread_result.scalar_one()

    result = await db.execute(
        text(f"""
            SELECT id, anomaly_id, title, description, severity, is_read, created_at
            FROM alerts
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {"org_id": str(org_id), "limit": limit, "offset": offset},
    )
    rows = result.mappings().all()

    return {
        "items": [dict(r) for r in rows],
        "unread_count": unread_count,
    }


async def mark_alerts_read(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    alert_ids: list[uuid.UUID],
) -> int:
    """Mark given alerts as read. Returns count updated."""
    if not alert_ids:
        return 0
    id_strs = [str(a) for a in alert_ids]
    result = await db.execute(
        text("""
            UPDATE alerts
            SET is_read = TRUE
            WHERE org_id = :org_id AND id = ANY(:ids::uuid[])
        """),
        {"org_id": str(org_id), "ids": id_strs},
    )
    await db.commit()
    return result.rowcount


# ── Detectors ──────────────────────────────────────────────────────────────────

def _detect_zscore(df: pd.DataFrame, existing: set) -> list[dict]:
    """Z-score detector: flags days where revenue z-score > threshold per product."""
    anomalies = []
    for product_id, grp in df.groupby("product_id"):
        if len(grp) < _MIN_HISTORY_DAYS:
            continue
        grp = grp.sort_values("sale_date")
        rev = grp["revenue"].astype(float)
        mu, sigma = rev.mean(), rev.std()
        if sigma < 1e-6:
            continue
        z = (rev - mu) / sigma
        for i, (_, row) in enumerate(grp.iterrows()):
            z_val = float(z.iloc[i])
            if abs(z_val) <= _ZSCORE_THRESHOLD:
                continue
            key = (str(product_id), str(row["sale_date"]), "zscore")
            if key in existing:
                continue
            severity = min(1.0, (abs(z_val) - _ZSCORE_THRESHOLD) / 3.0)
            anomaly_type = "revenue_spike" if z_val > 0 else "revenue_drop"
            impact = abs(float(row["revenue"]) - mu)
            anomalies.append({
                "product_id": product_id,
                "detected_date": row["sale_date"],
                "anomaly_type": anomaly_type,
                "detector": "zscore",
                "severity_score": round(severity, 3),
                "estimated_impact": round(impact, 2),
                "details": {"z_score": round(z_val, 3), "mean_revenue": round(mu, 2)},
                "_key": key,
            })
    return anomalies


def _detect_data_quality(df: pd.DataFrame, existing: set) -> list[dict]:
    """Flag products with 3+ consecutive zero-sales days."""
    anomalies = []
    for product_id, grp in df.groupby("product_id"):
        grp = grp.sort_values("sale_date")
        consecutive_zeros = 0
        zero_start = None
        for _, row in grp.iterrows():
            if row["quantity_sold"] == 0:
                if consecutive_zeros == 0:
                    zero_start = row["sale_date"]
                consecutive_zeros += 1
                if consecutive_zeros >= 3:
                    key = (str(product_id), str(row["sale_date"]), "data_quality")
                    if key not in existing:
                        anomalies.append({
                            "product_id": product_id,
                            "detected_date": row["sale_date"],
                            "anomaly_type": "zero_sales",
                            "detector": "data_quality",
                            "severity_score": min(1.0, consecutive_zeros / 10.0),
                            "estimated_impact": None,
                            "details": {"consecutive_zero_days": consecutive_zeros, "start": str(zero_start)},
                            "_key": key,
                        })
            else:
                consecutive_zeros = 0
                zero_start = None
    return anomalies


def _detect_iforest(df: pd.DataFrame, existing: set) -> list[dict]:
    """Isolation Forest on (revenue, quantity_sold) per product per day."""
    from sklearn.ensemble import IsolationForest

    anomalies = []
    for product_id, grp in df.groupby("product_id"):
        if len(grp) < _MIN_HISTORY_DAYS:
            continue
        X = grp[["revenue", "quantity_sold"]].astype(float).values
        clf = IsolationForest(contamination=0.05, random_state=42)
        preds = clf.fit_predict(X)
        scores = clf.decision_function(X)  # higher = more normal

        for i, (_, row) in enumerate(grp.iterrows()):
            if preds[i] != -1:
                continue
            key = (str(product_id), str(row["sale_date"]), "iforest")
            if key in existing:
                continue
            # Convert decision function score to severity (lower score = more anomalous)
            severity = min(1.0, max(0.0, -scores[i] + 0.1))
            anomalies.append({
                "product_id": product_id,
                "detected_date": row["sale_date"],
                "anomaly_type": "revenue_spike" if float(row["revenue"]) > grp["revenue"].mean() else "revenue_drop",
                "detector": "iforest",
                "severity_score": round(severity, 3),
                "estimated_impact": None,
                "details": {"isolation_score": round(float(scores[i]), 4)},
                "_key": key,
            })
    return anomalies


# ── DB helpers ─────────────────────────────────────────────────────────────────

async def _load_sales_df(
    db: AsyncSession,
    org_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    result = await db.execute(
        text("""
            SELECT product_id, sale_date, quantity_sold, revenue
            FROM daily_sales
            WHERE org_id = :org_id
              AND sale_date BETWEEN :start AND :end
        """),
        {"org_id": str(org_id), "start": start_date, "end": end_date},
    )
    rows = result.fetchall()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows, columns=["product_id", "sale_date", "quantity_sold", "revenue"])


async def _load_existing_anomaly_keys(
    db: AsyncSession,
    org_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> set:
    result = await db.execute(
        text("""
            SELECT product_id::text, detected_date::text, detector
            FROM anomalies
            WHERE org_id = :org_id
              AND detected_date BETWEEN :start AND :end
        """),
        {"org_id": str(org_id), "start": start_date, "end": end_date},
    )
    return {(r[0], r[1], r[2]) for r in result.fetchall()}


async def _persist_anomaly(db: AsyncSession, org_id: uuid.UUID, a: dict) -> uuid.UUID | None:
    aid = uuid.uuid4()
    try:
        await db.execute(
            text("""
                INSERT INTO anomalies
                    (id, org_id, product_id, detected_date, anomaly_type, detector,
                     severity_score, estimated_impact, details, is_dismissed)
                VALUES
                    (:id, :org_id, :product_id, :detected_date, :anomaly_type, :detector,
                     :severity_score, :estimated_impact, :details, FALSE)
            """),
            {
                "id": str(aid),
                "org_id": str(org_id),
                "product_id": str(a["product_id"]),
                "detected_date": a["detected_date"],
                "anomaly_type": a["anomaly_type"],
                "detector": a["detector"],
                "severity_score": a["severity_score"],
                "estimated_impact": a.get("estimated_impact"),
                "details": json.dumps(a.get("details") or {}),
            },
        )
        return aid
    except Exception:
        log.warning("Failed to persist anomaly", exc_info=True)
        return None


async def _create_alert(
    db: AsyncSession,
    org_id: uuid.UUID,
    anomaly_id: uuid.UUID,
    a: dict,
) -> None:
    severity = "critical" if a["severity_score"] >= 0.75 else "warning"
    type_labels = {
        "revenue_spike": "Revenue spike detected",
        "revenue_drop": "Revenue drop detected",
        "zero_sales": "Zero sales streak",
        "inventory_critical": "Critical stock level",
    }
    title = type_labels.get(a["anomaly_type"], "Anomaly detected")
    desc = (
        f"Detected by {a['detector']} on {a['detected_date']}. "
        f"Severity: {a['severity_score']:.0%}."
    )
    try:
        await db.execute(
            text("""
                INSERT INTO alerts (id, org_id, anomaly_id, title, description, severity, is_read)
                VALUES (:id, :org_id, :anomaly_id, :title, :description, :severity, FALSE)
            """),
            {
                "id": str(uuid.uuid4()),
                "org_id": str(org_id),
                "anomaly_id": str(anomaly_id),
                "title": title,
                "description": desc,
                "severity": severity,
            },
        )
    except Exception:
        log.warning("Failed to create alert", exc_info=True)
