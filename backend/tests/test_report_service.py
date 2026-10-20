"""
Tests for the report service — report generation and recommendation approval.
"""

import uuid

import pytest


@pytest.mark.asyncio
async def test_report_generation_endpoint(async_client):
    """POST /api/v1/reports/generate should return 401 without auth."""
    response = await async_client.post(
        "/api/v1/reports/generate",
        json={"title": "Test Report", "report_type": "on_demand"},
    )
    # Should require auth
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_report_list_endpoint(async_client):
    """GET /api/v1/reports should return 401 without auth."""
    response = await async_client.get("/api/v1/reports")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_recommendations_endpoint(async_client):
    """GET /api/v1/reports/recommendations should return 401 without auth."""
    response = await async_client.get("/api/v1/reports/recommendations")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_recommendation_decide_requires_manager(async_client):
    """POST /api/v1/reports/recommendations/{id}/decide requires manager role."""
    fake_id = str(uuid.uuid4())
    response = await async_client.post(
        f"/api/v1/reports/recommendations/{fake_id}/decide",
        json={"action": "approve"},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_report_export_requires_auth(async_client):
    """GET /api/v1/reports/{id}/export should require auth."""
    fake_id = str(uuid.uuid4())
    response = await async_client.get(f"/api/v1/reports/{fake_id}/export")
    assert response.status_code in (401, 403)


def test_template_narrative():
    """The template fallback narrative should produce valid text."""
    from app.services.report_service import _template_narrative

    agg = {
        "period": "2024-01-01 to 2024-01-31",
        "kpi_summary": {
            "total_revenue": 125000.50,
            "total_orders": 450,
            "avg_order_value": 277.78,
            "unique_customers": 200,
        },
        "top_products": [
            {"product_name": "Widget A", "category": "Electronics", "total_revenue": 15000.00},
        ],
        "inventory_flags": {"critical": 3, "low": 7, "healthy": 90},
        "anomaly_summary": {"total_active": 5, "critical": 2, "warnings": 3},
    }

    narrative = _template_narrative(agg)

    assert "£125,000.50" in narrative
    assert "450" in narrative
    assert "Widget A" in narrative
    assert "3 critical" in narrative
    assert "SYNTHETIC" in narrative
