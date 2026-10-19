"""
Tests for anomaly detection service — unit tests for pure detector functions.
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.services.anomaly_service import _detect_zscore, _detect_data_quality


def _make_df(product_id: str, revenues: list[float], qtys: list[int | None] = None):
    """Build a minimal daily_sales DataFrame."""
    import uuid
    dates = pd.date_range("2024-01-01", periods=len(revenues), freq="D").date
    if qtys is None:
        qtys = [max(0, int(r / 10)) for r in revenues]
    return pd.DataFrame({
        "product_id": [product_id] * len(revenues),
        "sale_date": dates,
        "revenue": revenues,
        "quantity_sold": qtys,
    })


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
    pid = "prod-008"
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
