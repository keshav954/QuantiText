"""
Weekly forecast retrain job.

Retrains LightGBM models for all active products in all orgs.
Designed to be run as a scheduled task (cron, APScheduler, or celery beat).

Run manually:
    python -m app.jobs.retrain

Production schedule: every Sunday at 02:00 UTC (configured in infra/cron).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

log = logging.getLogger(__name__)


async def retrain_all_products() -> dict[str, int]:
    """
    Iterate over all orgs and products with sufficient sales history,
    retrain the LightGBM model, and persist to DB.

    Returns a summary dict: {"trained": N, "skipped": N, "errors": N}
    """
    from sqlalchemy import text

    from app.core.database import engine
    from app.core.redis import redis_pool
    from app.services.forecasting_service import get_forecast

    stats = {"trained": 0, "skipped": 0, "errors": 0}
    start = datetime.now(UTC)

    log.info("Forecast retrain job starting at %s", start.isoformat())

    async with engine.begin() as raw_conn:
        # Fetch all org+product pairs that have >= 60 days of sales history
        result = await raw_conn.execute(
            text("""
                SELECT DISTINCT org_id::text, product_id::text
                FROM daily_sales
                GROUP BY org_id, product_id
                HAVING COUNT(DISTINCT sale_date) >= 60
                ORDER BY org_id, product_id
            """)
        )
        pairs = result.fetchall()

    log.info("Found %d product series to retrain", len(pairs))

    # Use a fresh session per product to avoid long-running transactions
    from app.core.database import AsyncSessionLocal

    for org_id_str, product_id_str in pairs:
        try:
            async with AsyncSessionLocal() as db:
                await get_forecast(
                    db,
                    redis_pool,
                    org_id=uuid.UUID(org_id_str),
                    product_id=uuid.UUID(product_id_str),
                    horizon=30,
                    force_retrain=True,
                )
            stats["trained"] += 1
            log.debug("Retrained: product=%s", product_id_str[:8])

        except Exception:
            stats["errors"] += 1
            log.exception("Retrain failed for product=%s", product_id_str[:8])

    elapsed = (datetime.now(UTC) - start).total_seconds()
    log.info(
        "Retrain job complete in %.1fs — trained=%d skipped=%d errors=%d",
        elapsed,
        stats["trained"],
        stats["skipped"],
        stats["errors"],
    )
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    results = asyncio.run(retrain_all_products())
    print(results)
