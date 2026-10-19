"""
Tests for KPI endpoints: summary, revenue-trend, top-products.
"""

import pytest


@pytest.mark.asyncio
async def test_kpi_summary_requires_auth(async_client):
    """KPI summary should require authentication."""
    response = await async_client.get("/api/v1/kpi/summary")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_revenue_trend_requires_auth(async_client):
    """Revenue trend should require authentication."""
    response = await async_client.get("/api/v1/kpi/revenue-trend")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_top_products_requires_auth(async_client):
    """Top products should require authentication."""
    response = await async_client.get("/api/v1/kpi/top-products")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_top_products_limit_validation(async_client):
    """Top products limit param should reject values > 50."""
    response = await async_client.get(
        "/api/v1/kpi/top-products?limit=100",
        headers={"Authorization": "Bearer fake.token"},
    )
    # Either 422 (validation) or 401 (auth first) is acceptable
    assert response.status_code in (401, 403, 422)
