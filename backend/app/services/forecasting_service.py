"""
Forecasting service — orchestrates the ML pipeline and DB persistence.

This is the only layer that touches both the ML code and the database.
Routers call this service; the ML modules know nothing about FastAPI or SQLAlchemy.

Responsibilities:
1. Load historical daily_sales from DB for a given product.
2. Run LightGBMForecaster.train() → evaluate() → predict().
3. Persist forecast rows to the `forecasts` table.
4. Log the MLflow run (experiment + metrics).
5. Cache the latest forecast in Redis (TTL 1 hour).
6. Return structured ForecastResult to the router.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import timedelta

import numpy as np
import pandas as pd
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

_FORECAST_CACHE_TTL = 3600  # 1 hour


# ── Cache helpers ─────────────────────────────────────────────────────────────


def _forecast_cache_key(org_id: uuid.UUID, product_id: uuid.UUID, horizon: int) -> str:
    return f"forecast:{org_id}:{product_id}:{horizon}"


async def _get_cached_forecast(redis: Redis, key: str) -> dict | None:
    try:
        raw = await redis.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        log.warning("Redis forecast cache read failed: key=%s", key)
        return None


async def _set_cached_forecast(redis: Redis, key: str, data: dict) -> None:
    try:
        await redis.setex(key, _FORECAST_CACHE_TTL, json.dumps(data, default=str))
    except Exception:
        log.warning("Redis forecast cache write failed: key=%s", key)


# ── DB helpers ────────────────────────────────────────────────────────────────


async def _load_daily_sales(
    db: AsyncSession,
    org_id: uuid.UUID,
    product_id: uuid.UUID,
) -> pd.Series:
    """Load all daily_sales for this product as a date-indexed pd.Series of quantity_sold."""
    result = await db.execute(
        text("""
            SELECT sale_date, SUM(quantity_sold) AS qty
            FROM daily_sales
            WHERE org_id = :org_id AND product_id = :product_id
            GROUP BY sale_date
            ORDER BY sale_date
        """),
        {"org_id": str(org_id), "product_id": str(product_id)},
    )
    rows = result.fetchall()
    if not rows:
        return pd.Series(dtype=float)

    dates = [r[0] for r in rows]
    qtys = [float(r[1]) for r in rows]
    s = pd.Series(qtys, index=pd.DatetimeIndex(dates), name="quantity_sold")
    return s.asfreq("D", fill_value=0).sort_index()


async def _persist_forecasts(
    db: AsyncSession,
    org_id: uuid.UUID,
    product_id: uuid.UUID,
    forecasts: list[dict],
    model_name: str,
    mape: float | None,
) -> None:
    """Delete stale forecasts for this product+model, then insert fresh rows."""
    # Delete existing forecasts for this product/model (fresh retrain)
    await db.execute(
        text("""
            DELETE FROM forecasts
            WHERE org_id = :org_id AND product_id = :product_id AND model_name = :model_name
        """),
        {"org_id": str(org_id), "product_id": str(product_id), "model_name": model_name},
    )

    for row in forecasts:
        await db.execute(
            text("""
                INSERT INTO forecasts
                    (id, org_id, product_id, forecast_date, horizon_days,
                     predicted_qty, lower_bound, upper_bound, model_name, mape)
                VALUES
                    (:id, :org_id, :product_id, :forecast_date, :horizon_days,
                     :predicted_qty, :lower_bound, :upper_bound, :model_name, :mape)
            """),
            {
                "id": str(uuid.uuid4()),
                "org_id": str(org_id),
                "product_id": str(product_id),
                "forecast_date": row["forecast_date"],
                "horizon_days": row["horizon_days"],
                "predicted_qty": round(float(row["predicted_qty"]), 2),
                "lower_bound": round(float(row["lower_bound"]), 2),
                "upper_bound": round(float(row["upper_bound"]), 2),
                "model_name": model_name,
                "mape": round(mape, 4) if mape is not None and not np.isnan(mape) else None,
            },
        )
    await db.commit()


def _log_mlflow_run(
    product_id: str,
    model_name: str,
    mape: float | None,
    rmse: float | None,
    n_obs: int,
    horizon: int,
    shap_features: dict,
) -> None:
    """Log a training run to MLflow. Gracefully skips if MLflow is unavailable."""
    try:
        import mlflow

        from app.core.config import settings

        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        mlflow.set_experiment("demand_forecasting")

        with mlflow.start_run(run_name=f"{model_name}_{product_id[:8]}"):
            mlflow.set_tags(
                {
                    "product_id": product_id,
                    "model": model_name,
                }
            )
            mlflow.log_params(
                {
                    "horizon_days": horizon,
                    "n_observations": n_obs,
                }
            )
            if mape is not None and not np.isnan(mape):
                mlflow.log_metric("mape", mape)
            if rmse is not None and not np.isnan(rmse):
                mlflow.log_metric("rmse", rmse)
            for feat, importance in shap_features.items():
                mlflow.log_metric(f"shap_{feat}", importance)

    except Exception:
        log.debug("MLflow logging skipped (not available)", exc_info=True)


# ── Public API ────────────────────────────────────────────────────────────────


async def get_forecast(
    db: AsyncSession,
    redis: Redis,
    *,
    org_id: uuid.UUID,
    product_id: uuid.UUID,
    horizon: int = 30,
    force_retrain: bool = False,
) -> dict:
    """
    Return a forecast for the given product.

    If a cached or stored forecast exists and force_retrain=False,
    return it immediately. Otherwise train a new model, persist, cache, and return.

    Returns a dict with keys:
        product_id, model_name, mape, horizon_days,
        forecasts: list of {date, predicted_qty, lower_bound, upper_bound}
        shap_features: dict of top-5 feature importances
        from_cache: bool
    """
    cache_key = _forecast_cache_key(org_id, product_id, horizon)

    if not force_retrain:
        cached = await _get_cached_forecast(redis, cache_key)
        if cached:
            cached["from_cache"] = True
            return cached

        # Try loading from DB (most recent run)
        stored = await _load_stored_forecast(db, org_id, product_id, horizon)
        if stored:
            await _set_cached_forecast(redis, cache_key, stored)
            stored["from_cache"] = True
            return stored

    # ── Train a fresh model ────────────────────────────────────────────────
    log.info("Training forecast model: product=%s horizon=%d", product_id, horizon)

    series = await _load_daily_sales(db, org_id, product_id)
    if len(series) < 30:
        return {
            "product_id": str(product_id),
            "model_name": "insufficient_data",
            "mape": None,
            "horizon_days": horizon,
            "forecasts": [],
            "shap_features": {},
            "from_cache": False,
            "error": f"Only {len(series)} days of data available (need ≥30)",
        }

    from ml.lgbm_model import LightGBMForecaster

    model = LightGBMForecaster(str(product_id), horizon=horizon)
    eval_metrics = model.evaluate(series)
    model.train(series)
    predictions = model.predict(horizon)
    shap_features = model.explain(series)

    mape = eval_metrics.get("mape")
    rmse = eval_metrics.get("rmse")

    # Build forecast rows
    start_date = (series.index[-1] + timedelta(days=1)).date()
    forecast_rows = []
    for i in range(horizon):
        fdate = start_date + timedelta(days=i)
        forecast_rows.append(
            {
                "forecast_date": fdate,
                "horizon_days": i + 1,
                "predicted_qty": float(np.clip(predictions["point"][i], 0, None)),
                "lower_bound": float(np.clip(predictions["lower"][i], 0, None)),
                "upper_bound": float(predictions["upper"][i]),
            }
        )

    # Persist to DB
    await _persist_forecasts(
        db,
        org_id,
        product_id,
        forecast_rows,
        model_name="lightgbm",
        mape=mape,
    )

    # Log to MLflow
    _log_mlflow_run(
        str(product_id),
        "lightgbm",
        mape=mape,
        rmse=rmse,
        n_obs=len(series),
        horizon=horizon,
        shap_features=shap_features,
    )

    result = {
        "product_id": str(product_id),
        "model_name": "lightgbm",
        "mape": round(mape, 2) if mape and not np.isnan(mape) else None,
        "rmse": round(rmse, 2) if rmse and not np.isnan(rmse) else None,
        "horizon_days": horizon,
        "forecasts": [
            {
                "date": str(r["forecast_date"]),
                "predicted_qty": r["predicted_qty"],
                "lower_bound": r["lower_bound"],
                "upper_bound": r["upper_bound"],
            }
            for r in forecast_rows
        ],
        "shap_features": {k: round(v, 4) for k, v in shap_features.items()},
        "from_cache": False,
    }

    await _set_cached_forecast(redis, cache_key, result)
    return result


async def _load_stored_forecast(
    db: AsyncSession,
    org_id: uuid.UUID,
    product_id: uuid.UUID,
    horizon: int,
) -> dict | None:
    """Load the most recently created forecast from DB, if it covers the full horizon."""
    result = await db.execute(
        text("""
            SELECT forecast_date, horizon_days, predicted_qty, lower_bound, upper_bound,
                   model_name, mape
            FROM forecasts
            WHERE org_id = :org_id
              AND product_id = :product_id
              AND forecast_date >= CURRENT_DATE
              AND horizon_days <= :horizon
            ORDER BY forecast_date
            LIMIT :limit
        """),
        {
            "org_id": str(org_id),
            "product_id": str(product_id),
            "horizon": horizon,
            "limit": horizon,
        },
    )
    rows = result.fetchall()
    if not rows or len(rows) < horizon // 2:
        return None

    model_name = rows[0][5]
    mape = float(rows[0][6]) if rows[0][6] is not None else None

    return {
        "product_id": str(product_id),
        "model_name": model_name,
        "mape": mape,
        "horizon_days": horizon,
        "forecasts": [
            {
                "date": str(r[0]),
                "predicted_qty": float(r[2]),
                "lower_bound": float(r[3]),
                "upper_bound": float(r[4]),
            }
            for r in rows
        ],
        "shap_features": {},
    }


async def list_product_forecasts(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    limit: int = 20,
) -> list[dict]:
    """Return a summary list of products that have stored forecasts."""
    result = await db.execute(
        text("""
            SELECT f.product_id::text, p.name AS product_name, p.sku,
                   MIN(f.forecast_date) AS from_date, MAX(f.forecast_date) AS to_date,
                   AVG(f.mape) AS avg_mape, f.model_name,
                   MAX(f.created_at) AS last_trained
            FROM forecasts f
            JOIN products p ON p.id = f.product_id
            WHERE f.org_id = :org_id AND f.forecast_date >= CURRENT_DATE
            GROUP BY f.product_id, p.name, p.sku, f.model_name
            ORDER BY last_trained DESC
            LIMIT :limit
        """),
        {"org_id": str(org_id), "limit": limit},
    )
    rows = result.mappings().all()
    return [
        {
            "product_id": r["product_id"],
            "product_name": r["product_name"],
            "sku": r["sku"],
            "from_date": str(r["from_date"]),
            "to_date": str(r["to_date"]),
            "avg_mape": round(float(r["avg_mape"]), 2) if r["avg_mape"] else None,
            "model_name": r["model_name"],
            "last_trained": str(r["last_trained"]),
        }
        for r in rows
    ]
