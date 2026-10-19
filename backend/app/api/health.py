"""
Health-check router — no authentication required.
Used by Docker healthcheck, load balancers, and the frontend to confirm the backend is alive.
"""

from datetime import datetime, timezone

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
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
        status["status"] = "degraded"

    return status
