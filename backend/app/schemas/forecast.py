"""
Forecast schemas — request/response Pydantic models for /forecast endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ForecastPoint(BaseModel):
    """Single day forecast with confidence interval."""

    date: str  # ISO date string YYYY-MM-DD
    predicted_qty: float = Field(..., ge=0, description="Point forecast (units)")
    lower_bound: float = Field(..., ge=0, description="Lower conformal bound (~10th percentile)")
    upper_bound: float = Field(..., ge=0, description="Upper conformal bound (~90th percentile)")


class ForecastResponse(BaseModel):
    """Full forecast result for a single product."""

    product_id: str
    model_name: str
    mape: float | None = Field(None, description="Walk-forward CV MAPE (%)")
    rmse: float | None = None
    horizon_days: int
    forecasts: list[ForecastPoint]
    shap_features: dict[str, float] = Field(
        default_factory=dict,
        description="Top-5 SHAP feature importances for the last observation",
    )
    from_cache: bool = False
    error: str | None = None


class ForecastSummary(BaseModel):
    """Brief summary of a stored product forecast (list view)."""

    product_id: str
    product_name: str
    sku: str
    from_date: str
    to_date: str
    avg_mape: float | None = None
    model_name: str
    last_trained: str


class ForecastListResponse(BaseModel):
    forecasts: list[ForecastSummary]
    total: int
