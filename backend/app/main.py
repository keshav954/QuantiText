"""
FastAPI application factory.

Creates the app, registers routers, middleware, and lifespan events.
This is the single entry point — uvicorn loads `app.main:app`.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Startup / shutdown lifecycle.
    - Startup: verify DB and Redis connections.
    - Shutdown: dispose engine pools.
    """
    # ── Startup ──────────────────────────────────────────
    from app.core.database import engine, readonly_engine
    from app.core.redis import redis_pool

    # Verify database connectivity
    async with engine.begin() as conn:
        await conn.execute(__import__("sqlalchemy").text("SELECT 1"))

    # Verify Redis connectivity
    await redis_pool.ping()

    yield

    # ── Shutdown ─────────────────────────────────────────
    await engine.dispose()
    await readonly_engine.dispose()
    await redis_pool.aclose()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""

    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="AI-powered Business Intelligence and Decision Support System",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ───────────────────────────────
    register_exception_handlers(app)

    # ── Routers ──────────────────────────────────────────
    from app.api.admin import router as admin_router
    from app.api.anomaly import router as anomaly_router
    from app.api.auth import router as auth_router
    from app.api.copilot import router as copilot_router
    from app.api.forecast import router as forecast_router
    from app.api.health import router as health_router
    from app.api.inventory import router as inventory_router
    from app.api.kpi import router as kpi_router
    from app.api.report import router as report_router

    # Health is mounted at root (no prefix) for load balancer compatibility
    app.include_router(health_router)

    # API routers under versioned prefix
    app.include_router(auth_router, prefix=settings.API_PREFIX)
    app.include_router(kpi_router, prefix=settings.API_PREFIX)
    app.include_router(forecast_router, prefix=settings.API_PREFIX)
    app.include_router(inventory_router, prefix=settings.API_PREFIX)
    app.include_router(anomaly_router, prefix=settings.API_PREFIX)
    app.include_router(copilot_router, prefix=settings.API_PREFIX)
    app.include_router(report_router, prefix=settings.API_PREFIX)
    app.include_router(admin_router, prefix=settings.API_PREFIX)

    return app


# The app instance uvicorn loads
app = create_app()
