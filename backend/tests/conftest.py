"""
Shared test fixtures.

Provides:
- async_client: httpx.AsyncClient wired to the FastAPI app (no live server needed)
- Overrides DB and Redis dependencies with mocks for test isolation.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# ── Mock dependencies ────────────────────────────────────────────────────────


def _mock_db():
    """Return a mock AsyncSession that won't hit a real DB."""
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=1)))
    session.commit = AsyncMock()
    session.close = AsyncMock()
    return session


def _mock_redis():
    """Return a mock Redis client."""
    r = AsyncMock()
    r.ping = AsyncMock(return_value=True)
    r.get = AsyncMock(return_value=None)
    r.set = AsyncMock(return_value=True)
    r.delete = AsyncMock(return_value=True)
    return r


async def _get_mock_db() -> AsyncGenerator:
    yield _mock_db()


async def _get_mock_readonly_db() -> AsyncGenerator:
    yield _mock_db()


async def _get_mock_redis():
    return _mock_redis()


# ── Build a test app with overridden deps ────────────────────────────────────


def _create_test_app() -> FastAPI:
    """
    Create the FastAPI app with a no-op lifespan and mocked DB/Redis deps.
    This avoids needing real Postgres or Redis during unit tests.
    """
    from app.core.config import settings  # noqa: F401
    from app.core.exceptions import register_exception_handlers

    @asynccontextmanager
    async def _test_lifespan(app: FastAPI):
        yield  # no startup/shutdown checks

    test_app = FastAPI(
        title="QuantiText (test)",
        version="0.1.0",
        lifespan=_test_lifespan,
    )

    register_exception_handlers(test_app)

    # Import and mount routers (same as main.py)
    from app.api.admin import router as admin_router
    from app.api.anomaly import router as anomaly_router
    from app.api.auth import router as auth_router
    from app.api.copilot import router as copilot_router
    from app.api.forecast import router as forecast_router
    from app.api.health import router as health_router
    from app.api.inventory import router as inventory_router
    from app.api.kpi import router as kpi_router
    from app.api.report import router as report_router

    test_app.include_router(health_router)

    prefix = settings.API_PREFIX
    test_app.include_router(auth_router, prefix=prefix)
    test_app.include_router(kpi_router, prefix=prefix)
    test_app.include_router(forecast_router, prefix=prefix)
    test_app.include_router(inventory_router, prefix=prefix)
    test_app.include_router(anomaly_router, prefix=prefix)
    test_app.include_router(copilot_router, prefix=prefix)
    test_app.include_router(report_router, prefix=prefix)
    test_app.include_router(admin_router, prefix=prefix)

    # Override dependencies with mocks
    from app.core.database import get_db, get_readonly_db
    from app.core.redis import get_redis

    test_app.dependency_overrides[get_db] = _get_mock_db
    test_app.dependency_overrides[get_readonly_db] = _get_mock_readonly_db
    test_app.dependency_overrides[get_redis] = _get_mock_redis

    return test_app


# Singleton so all tests share the same app instance
_test_app = _create_test_app()


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
async def async_client():
    """
    Async HTTP test client.
    Uses httpx ASGITransport so tests hit the FastAPI app in-process
    without needing a running server or real DB/Redis connections.
    """
    transport = ASGITransport(app=_test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
