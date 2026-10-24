"""
Tests for anomaly detection service — unit tests for pure detector functions.
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.services.anomaly_service import _detect_data_quality, _detect_zscore


def _make_df(product_id: str, revenues: list[float], qtys: list[int | None] = None):
    """Build a minimal daily_sales DataFrame."""

    dates = pd.date_range("2024-01-01", periods=len(revenues), freq="D").date
    if qtys is None:
        qtys = [max(0, int(r / 10)) for r in revenues]
    return pd.DataFrame(
        {
            "product_id": [product_id] * len(revenues),
            "sale_date": dates,
            "revenue": revenues,
            "quantity_sold": qtys,
        }
    )


def test_zscore_detects_spike():
    """A revenue spike beyond 2.5 SD should be flagged."""
    pid = "prod-001"
    # 20 normal days + 1 huge spike
    revenues = [100.0] * 20 + [5000.0]
    df = _make_df(pid, revenues)
    anomalies = _detect_zscore(df, existing=set())
    assert len(anomalies) >= 1
    spike = anomalies[0]
    assert spike["anomaly_type"] == "revenue_spike"
    assert spike["detector"] == "zscore"
    assert spike["severity_score"] > 0


def test_zscore_detects_drop():
    """A revenue drop beyond -2.5 SD should be flagged."""
    pid = "prod-002"
    revenues = [500.0] * 20 + [0.0]
    df = _make_df(pid, revenues)
    anomalies = _detect_zscore(df, existing=set())
    drops = [a for a in anomalies if a["anomaly_type"] == "revenue_drop"]
    assert len(drops) >= 1


def test_zscore_no_false_positives_on_flat():
    """Flat revenue → no anomalies."""
    pid = "prod-003"
    revenues = [200.0] * 25
    df = _make_df(pid, revenues)
    anomalies = _detect_zscore(df, existing=set())
    assert len(anomalies) == 0


def test_zscore_skips_short_history():
    """Fewer than _MIN_HISTORY_DAYS points → no anomalies generated."""
    pid = "prod-004"
    revenues = [100.0, 5000.0]  # only 2 rows
    df = _make_df(pid, revenues)
    anomalies = _detect_zscore(df, existing=set())
    assert len(anomalies) == 0


def test_zscore_deduplication():
    """Already-existing keys should not produce duplicate anomalies."""
    pid = "prod-005"
    revenues = [100.0] * 20 + [5000.0]
    df = _make_df(pid, revenues)
    existing = set()
    anomalies = _detect_zscore(df, existing=existing)
    assert len(anomalies) >= 1

    # Mark all found keys as existing
    for a in anomalies:
        existing.add(a["_key"])

    anomalies2 = _detect_zscore(df, existing=existing)
    assert len(anomalies2) == 0


def test_data_quality_detects_zero_streak():
    """3+ consecutive zero-sales days should be flagged."""
    pid = "prod-006"
    qtys = [10, 12, 0, 0, 0, 8, 9]
    revenues = [float(q * 100) for q in qtys]
    df = _make_df(pid, revenues, qtys)
    anomalies = _detect_data_quality(df, existing=set())
    zero_anoms = [a for a in anomalies if a["anomaly_type"] == "zero_sales"]
    assert len(zero_anoms) >= 1
    assert zero_anoms[0]["details"]["consecutive_zero_days"] >= 3


def test_data_quality_no_flag_two_zeros():
    """Only 2 consecutive zeros → should not be flagged."""
    pid = "prod-007"
    qtys = [10, 0, 0, 8, 9, 10, 11]
    revenues = [float(q * 100) for q in qtys]
    df = _make_df(pid, revenues, qtys)
    anomalies = _detect_data_quality(df, existing=set())
    assert len(anomalies) == 0


def test_data_quality_severity_scales():
    """Longer zero streaks should have higher severity."""
    qtys_short = [10, 0, 0, 0, 8]
    qtys_long = [10, 0, 0, 0, 0, 0, 0, 0, 8]
    df_short = _make_df("prod-008a", [float(q * 100) for q in qtys_short], qtys_short)
    df_long = _make_df("prod-008b", [float(q * 100) for q in qtys_long], qtys_long)

    a_short = _detect_data_quality(df_short, set())
    a_long = _detect_data_quality(df_long, set())

    if a_short and a_long:
        max_short = max(a["severity_score"] for a in a_short)
        max_long = max(a["severity_score"] for a in a_long)
        assert max_long >= max_short


def test_closed_loop_diagnose_root_cause():
    """Verify root cause diagnosis across anomaly types."""
    from app.services.closed_loop_service import diagnose_root_cause

    rc_drop = diagnose_root_cause("revenue_drop", "zscore", 0.9, {"pct_change": "-85%"})
    assert "-85%" in rc_drop or "contraction" in rc_drop.lower()

    rc_zero = diagnose_root_cause("zero_sales", "data_quality", 0.7, {"streak_days": 5})
    assert "5" in rc_zero

    rc_custom = diagnose_root_cause(
        "inventory_critical", "zscore", 0.85, {"cause": "Supplier component halt"}
    )
    assert rc_custom == "Supplier component halt"


@pytest.mark.asyncio
async def test_closed_loop_pipeline_mocked():
    """Test full closed-loop generation: anomaly -> root cause -> forecast impact -> recommendation."""
    import uuid
    from unittest.mock import AsyncMock, MagicMock

    from app.services.closed_loop_service import generate_recommendation_for_anomaly

    db = AsyncMock()
    org_id = uuid.uuid4()
    anom_id = uuid.uuid4()
    prod_id = uuid.uuid4()

    mock_anom = {
        "id": anom_id,
        "product_id": prod_id,
        "anomaly_type": "inventory_critical",
        "detector": "zscore",
        "severity_score": 0.85,
        "estimated_impact": -1500.0,
        "details": {"cause": "Rapid stock depletion"},
    }

    anom_result = MagicMock()
    anom_result.mappings = MagicMock(
        return_value=MagicMock(first=MagicMock(return_value=mock_anom))
    )

    existing_result = MagicMock()
    existing_result.scalar = MagicMock(return_value=None)

    prod_inv = {
        "id": prod_id,
        "sku": "SKU-999",
        "name": "High Velocity Widget",
        "unit_price": 45.0,
        "stock_on_hand": 8,
        "reorder_point": 50,
        "safety_stock": 20,
        "lead_time_days": 7,
    }
    prod_result = MagicMock()
    prod_result.mappings = MagicMock(return_value=MagicMock(first=MagicMock(return_value=prod_inv)))

    forecast_result = MagicMock()
    forecast_result.mappings = MagicMock(
        return_value=MagicMock(
            first=MagicMock(
                return_value={"forecast_count": 14, "avg_pred_daily": 12.0, "total_pred_qty": 168.0}
            )
        )
    )

    db.execute.side_effect = [
        anom_result,
        existing_result,
        prod_result,
        forecast_result,
        MagicMock(),  # INSERT recommendation
    ]

    rec = await generate_recommendation_for_anomaly(db, org_id=org_id, anomaly_id=anom_id)
    assert rec is not None
    assert rec["action_type"] == "reorder"
    assert "Rapid stock depletion" in rec["root_cause"]
    assert "stockout" in rec["forecast_impact"].lower()
    assert rec["parameters"]["suggested_qty"] > 0
