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


@pytest.mark.asyncio
async def test_recommendation_po_export_requires_auth(async_client):
    """GET /api/v1/reports/recommendations/{id}/po should require auth."""
    fake_id = str(uuid.uuid4())
    response = await async_client.get(f"/api/v1/reports/recommendations/{fake_id}/po")
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


@pytest.mark.asyncio
async def test_export_po_pdf_endpoint(async_client):
    """GET /api/v1/reports/recommendations/{id}/po.pdf returns PDF bytes."""
    from unittest.mock import AsyncMock, patch

    from app.api.deps import get_current_user
    from tests.conftest import _test_app
    from tests.test_auth import _make_fake_user

    fake_user = _make_fake_user(role="viewer")
    _test_app.dependency_overrides[get_current_user] = lambda: fake_user
    fake_rec_id = uuid.uuid4()

    try:
        with patch(
            "app.services.report_service.generate_purchase_order_pdf", new_callable=AsyncMock
        ) as mock_pdf:
            mock_pdf.return_value = b"%PDF-1.4 mock pdf content"
            with patch("app.api.report.log_audit", new_callable=AsyncMock):
                response = await async_client.get(
                    f"/api/v1/reports/recommendations/{fake_rec_id}/po.pdf"
                )
                assert response.status_code == 200
                assert response.headers["content-type"] == "application/pdf"
                assert response.content.startswith(b"%PDF")
    finally:
        _test_app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_export_report_pdf_endpoint(async_client):
    """GET /api/v1/reports/{id}/export.pdf returns PDF bytes."""
    from unittest.mock import AsyncMock, patch

    from app.api.deps import get_current_user
    from tests.conftest import _test_app
    from tests.test_auth import _make_fake_user

    fake_user = _make_fake_user(role="viewer")
    _test_app.dependency_overrides[get_current_user] = lambda: fake_user
    fake_rep_id = uuid.uuid4()

    try:
        with patch(
            "app.services.report_service.export_report_pdf_by_id", new_callable=AsyncMock
        ) as mock_pdf:
            mock_pdf.return_value = b"%PDF-1.4 mock report pdf content"
            with patch("app.api.report.log_audit", new_callable=AsyncMock):
                response = await async_client.get(f"/api/v1/reports/{fake_rep_id}/export.pdf")
                assert response.status_code == 200
                assert response.headers["content-type"] == "application/pdf"
                assert response.content.startswith(b"%PDF")
    finally:
        _test_app.dependency_overrides.pop(get_current_user, None)
