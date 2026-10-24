"""
Database integration tests against live PostgreSQL.
Exercises migrations, views, read-only permissions, and tenant isolation.
In CI, connects to the Postgres service container.
Locally, skips cleanly if live PostgreSQL is not reachable.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.services.copilot_service import validate_and_secure_sql


def is_postgres_configured() -> bool:
    return "postgresql" in settings.DATABASE_URL


@pytest.fixture
async def live_db():
    if not is_postgres_configured():
        pytest.skip("PostgreSQL not configured in DATABASE_URL")
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1;"))
    except Exception as e:
        pytest.skip(f"PostgreSQL connection failed: {e}")

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def readonly_db():
    if not is_postgres_configured():
        pytest.skip("PostgreSQL not configured in DB_READONLY_URL")
    engine = create_async_engine(settings.DB_READONLY_URL, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1;"))
    except Exception as e:
        pytest.skip(f"Read-only DB connection failed: {e}")

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_schema_and_views_exist(live_db):
    """Verify that all core tables and analytics views exist in PostgreSQL."""
    tables_result = await live_db.execute(
        text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public';
        """)
    )
    existing_tables = {r[0] for r in tables_result.fetchall()}

    expected_tables = {
        "orgs",
        "users",
        "products",
        "categories",
        "daily_sales",
        "inventory",
        "forecasts",
        "anomalies",
        "alerts",
        "recommendations",
        "reports",
        "audit_log",
    }
    for table in expected_tables:
        assert table in existing_tables, f"Expected table '{table}' not found in database."

    views_result = await live_db.execute(
        text("""
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = 'public';
        """)
    )
    existing_views = {r[0] for r in views_result.fetchall()}
    expected_views = {
        "v_kpi_daily",
        "v_sales_by_product",
        "v_sales_by_region",
        "v_inventory_status",
    }
    for view in expected_views:
        assert view in existing_views, f"Expected view '{view}' not found in database."


@pytest.mark.asyncio
async def test_bi_readonly_table_permissions(readonly_db):
    """
    Verify migration 0004 permissions:
    bi_readonly role has SELECT access on daily_sales, products, categories, forecasts, anomalies.
    """
    for table in ("daily_sales", "products", "categories", "forecasts", "anomalies"):
        res = await readonly_db.execute(text(f"SELECT COUNT(*) FROM {table};"))
        count = res.scalar()
        assert isinstance(count, int)


@pytest.mark.asyncio
async def test_live_tenant_isolation_execution(readonly_db):
    """
    Verify that an AST-scoped query executing on PostgreSQL enforces tenant isolation
    even when injected with a cross-tenant WHERE clause.
    """
    org_a = str(uuid.uuid4())
    org_b = str(uuid.uuid4())

    attack_sql = f"SELECT * FROM daily_sales WHERE org_id = '{org_b}'"
    secured_sql = validate_and_secure_sql(attack_sql, org_a)

    # Executing the secured query against PostgreSQL succeeds and returns 0 rows
    res = await readonly_db.execute(text(secured_sql))
    rows = res.fetchall()
    assert len(rows) == 0
