"""
Health-check router — no authentication required.
Used by Docker healthcheck, load balancers, and the frontend to confirm the backend is alive.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns service status including DB and Redis connectivity.
    """
    status = {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "0.1.0",
        "services": {},
    }

    # Check PostgreSQL
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        status["services"]["postgres"] = "up"
    except Exception:
        status["services"]["postgres"] = "down"
        status["status"] = "degraded"

    # Check Redis
    try:
        redis = await get_redis()
        await redis.ping()
        status["services"]["redis"] = "up"
    except Exception:
        status["services"]["redis"] = "down"
    return status


@router.get("/metrics")
async def metrics_endpoint(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns operational metrics for monitoring and health dashboards.
    """
    db_up = False
    prod_count = 0
    sales_count = 0
    try:
        res = await db.execute(text("SELECT COUNT(*) FROM products"))
        prod_count = res.scalar() or 0
        sales_res = await db.execute(text("SELECT COUNT(*) FROM daily_sales"))
        sales_count = sales_res.scalar() or 0
        db_up = True
    except Exception:
        pass

    redis_up = False
    try:
        redis = await get_redis()
        await redis.ping()
        redis_up = True
    except Exception:
        pass

    return {
        "status": "up" if (db_up and redis_up) else "degraded",
        "timestamp": datetime.now(UTC).isoformat(),
        "metrics": {
            "postgres_connected": db_up,
            "redis_connected": redis_up,
            "products_monitored": prod_count,
            "sales_datapoints": sales_count,
        },
    }
