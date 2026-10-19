"""
Tests for the /health endpoint.
"""

import pytest


@pytest.mark.asyncio
async def test_health_returns_200(async_client):
    """Health endpoint should return 200 with status and version fields."""
    response = await async_client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "timestamp" in data
    assert "services" in data
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_health_contains_service_checks(async_client):
    """Health response should report on postgres and redis services."""
    response = await async_client.get("/health")
    data = response.json()

    services = data["services"]
    assert "postgres" in services
    assert "redis" in services
