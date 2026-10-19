"""
Forecast router — /api/v1/forecast endpoints.

GET  /forecast/              — list products with stored forecasts
GET  /forecast/{product_id}  — get/generate forecast for a product
POST /forecast/{product_id}/retrain — force retrain (manager+ only)

All endpoints require at least viewer role.
Retrain requires manager+.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_redis, require_role
from app.models.user import User
from app.schemas.forecast import ForecastListResponse, ForecastResponse, ForecastSummary
from app.services import forecasting_service

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get(
    "/",
    response_model=ForecastListResponse,
    dependencies=[Depends(require_role("viewer"))],
)
async def list_forecasts(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ForecastListResponse:
    """
    List products that have stored forecasts, ordered by most recently trained.
    """
    items = await forecasting_service.list_product_forecasts(
        db, org_id=current_user.org_id, limit=limit
    )
    return ForecastListResponse(
        forecasts=[ForecastSummary(**item) for item in items],
        total=len(items),
    )


@router.get(
    "/{product_id}",
    response_model=ForecastResponse,
    dependencies=[Depends(require_role("viewer"))],
)
async def get_forecast(
    product_id: uuid.UUID,
    horizon: int = Query(30, ge=1, le=90, description="Forecast horizon in days (1, 7, or 30 recommended)"),
    force_retrain: bool = Query(False, description="Bypass cache and retrain the model"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
) -> ForecastResponse:
    """
    Get demand forecast for a product.

    - Returns cached forecast if available (TTL 1 hour) and force_retrain=False.
    - Otherwise trains a LightGBM model on historical daily_sales and stores results.
    - Includes conformal prediction intervals (10th–90th percentile of CV residuals).
    - Includes top-5 SHAP feature importances.
    """
    result = await forecasting_service.get_forecast(
        db,
        redis,
        org_id=current_user.org_id,
        product_id=product_id,
        horizon=horizon,
        force_retrain=force_retrain,
    )
    return ForecastResponse(**result)


@router.post(
    "/{product_id}/retrain",
    response_model=ForecastResponse,
    dependencies=[Depends(require_role("manager"))],
)
async def retrain_forecast(
    product_id: uuid.UUID,
    horizon: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
) -> ForecastResponse:
    """
    Force retrain the forecast model for a product (manager+ only).
    Invalidates cache and re-runs full training + evaluation pipeline.
    """
    result = await forecasting_service.get_forecast(
        db,
        redis,
        org_id=current_user.org_id,
        product_id=product_id,
        horizon=horizon,
        force_retrain=True,
    )
    return ForecastResponse(**result)
