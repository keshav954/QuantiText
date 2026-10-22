"""
Tests for inventory service — unit tests using mock DB sessions.
"""

from __future__ import annotations

import pytest

from app.services.inventory_service import _classify_abc, _eoq, _safety_stock, _stock_status

# ── Unit tests for pure calculation functions ───────────────────────────────────


def test_eoq_basic():
    """EOQ = sqrt(2 * D * S / H)."""
    # 1000 units/year, $50 ordering cost, $10 holding cost → EOQ = sqrt(10000) = 100
    result = _eoq(annual_demand=1000, ordering_cost=50, holding_cost_per_unit=10)
    assert result == 100


def test_eoq_zero_demand():
    """Zero demand should return EOQ = 0."""
    assert _eoq(annual_demand=0, ordering_cost=50, holding_cost_per_unit=10) == 0


def test_eoq_zero_holding():
    """Zero holding cost → undefined, return 0."""
    assert _eoq(annual_demand=1000, ordering_cost=50, holding_cost_per_unit=0) == 0


def test_eoq_minimum_1():
    """EOQ should always be at least 1 when demand > 0."""
    result = _eoq(annual_demand=1, ordering_cost=0.01, holding_cost_per_unit=1000)
    assert result >= 1


def test_safety_stock_basic():
    """SS = z * std * sqrt(lead_time) = 1.65 * 5 * sqrt(4) = 16.5 → 17."""
    result = _safety_stock(avg_daily_demand=10.0, std_daily_demand=5.0, lead_time_days=4)
    assert result == round(1.65 * 5.0 * 2.0)


def test_safety_stock_zero_variability():
    """Zero std → zero safety stock."""
    assert _safety_stock(avg_daily_demand=10.0, std_daily_demand=0.0, lead_time_days=7) == 0


def test_safety_stock_minimum_zero():
    """Safety stock never negative."""
    assert _safety_stock(avg_daily_demand=5.0, std_daily_demand=-1.0, lead_time_days=7) == 0


def test_classify_abc_ordering():
    """A items should be highest revenue products."""
    items = [
        {"annual_revenue": 1000, "sku": "A"},
        {"annual_revenue": 200, "sku": "B"},
        {"annual_revenue": 50, "sku": "C"},
        {"annual_revenue": 10, "sku": "D"},
    ]
    _classify_abc(items)
    # Total = 1260; A cutoff @ 70% = 882 → first item alone (1000 > 882) → class A
    abc_map = {i["sku"]: i["abc_class"] for i in items}
    assert abc_map["A"] == "A"
    # Cumulative with B = 1200 → 95% → B class
    assert abc_map["B"] == "B"
    # C and D are C class
    assert abc_map["C"] == "C"
    assert abc_map["D"] == "C"


def test_classify_abc_zero_revenue():
    """All zero revenue → all class C."""
    items = [{"annual_revenue": 0, "sku": "X"}, {"annual_revenue": 0, "sku": "Y"}]
    _classify_abc(items)
    for item in items:
        assert item["abc_class"] == "C"


def test_stock_status_critical_zero():
    """Zero stock → critical."""
    assert _stock_status(0, 10, 5, 0.0) == "critical"


def test_stock_status_critical_below_safety():
    """Stock below safety stock → critical."""
    assert _stock_status(3, 10, 5, 0.5) == "critical"


def test_stock_status_low():
    """Stock above safety but below reorder point → low."""
    assert _stock_status(8, 10, 3, 5.0) == "low"


def test_stock_status_ok():
    """Healthy stock level → ok."""
    assert _stock_status(50, 10, 5, 30.0) == "ok"


def test_stock_status_overstock():
    """More than 180 days of stock → overstock."""
    assert _stock_status(500, 10, 5, 181.0) == "overstock"


def test_what_if_shock_calculations():
    """Test safety stock & ROP increase under demand and lead time shocks."""
    base_avg = 10.0
    base_std = 2.0
    base_lt = 4
    base_ss = _safety_stock(base_avg, base_std, base_lt)
    base_rop = round(base_avg * base_lt + base_ss)

    # 50% demand shock, +3 days lead time delay
    demand_multiplier = 1.5
    sim_avg = base_avg * demand_multiplier
    sim_std = base_std * (demand_multiplier**0.5)
    sim_lt = base_lt + 3
    sim_ss = _safety_stock(sim_avg, sim_std, sim_lt)
    sim_rop = round(sim_avg * sim_lt + sim_ss)

    assert sim_ss > base_ss
    assert sim_rop > base_rop
    assert sim_rop > 100


@pytest.mark.asyncio
async def test_what_if_endpoint_requires_auth(async_client):
    """POST /api/v1/inventory/what-if requires authentication."""
    response = await async_client.post(
        "/api/v1/inventory/what-if",
        json={"demand_change_pct": 20.0, "lead_time_delay_days": 5},
    )
    assert response.status_code in (401, 403)
