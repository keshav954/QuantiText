"""
Async SQLAlchemy engine, session factory, and FastAPI dependency.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Async engine for the main application
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

# Read-only engine for NL2SQL (separate pool, enforced by DB role later)
readonly_engine = create_async_engine(
    settings.DB_READONLY_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
)

# Session factories
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

AsyncReadonlySession = async_sessionmaker(
    bind=readonly_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async session and ensures cleanup."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_readonly_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — read-only session for NL2SQL queries."""
    async with AsyncReadonlySession() as session:
        try:
            yield session
        finally:
            await session.close()
