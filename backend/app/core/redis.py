"""
Redis connection pool and FastAPI dependency.
Used for KPI caching and (later) job queues.
"""

from redis.asyncio import Redis, from_url

from app.core.config import settings

# Module-level pool — initialised on first import
redis_pool: Redis = from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=20,
)


async def get_redis() -> Redis:
    """FastAPI dependency — returns the shared Redis client."""
    return redis_pool
