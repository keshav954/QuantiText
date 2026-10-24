"""
Tests for forecasting ML models and forecasting endpoints.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import numpy as np
import pandas as pd
import pytest

from ml.baselines import NaiveModel, SeasonalNaiveModel, _mape, _rmse
from ml.features import build_features
from ml.lgbm_model import LightGBMForecaster


def _make_sample_series(n_days: int = 90) -> pd.Series:
    """Generate a synthetic daily sales series."""
    dates = pd.date_range("2024-01-01", periods=n_days, freq="D")
    t = np.arange(n_days)
    weekly = 10 * np.sin(2 * np.pi * t / 7)
    values = np.maximum(20 + 0.1 * t + weekly + np.random.normal(0, 2, n_days), 1.0)
    return pd.Series(values, index=dates)


# ── Baseline model tests ───────────────────────────────────────────────────────


def test_naive_model():
    series = _make_sample_series(30)
    model = NaiveModel()
    model.train(series)
    preds = model.predict(horizon=7)

    assert len(preds) == 7
    assert np.allclose(preds, series.iloc[-1])

    eval_metrics = model.evaluate(series, horizon=7)
    assert "mape" in eval_metrics
    assert "rmse" in eval_metrics
    assert eval_metrics["rmse"] >= 0


def test_seasonal_naive_model():
    series = _make_sample_series(30)
    model = SeasonalNaiveModel()
    model.train(series)
    preds = model.predict(horizon=14)

    assert len(preds) == 14
    assert preds[7] == preds[0]

    eval_metrics = model.evaluate(series, horizon=7)
    assert eval_metrics["rmse"] >= 0


def test_metrics_empty_or_zero():
    actual = np.array([0, 0, 0])
    pred = np.array([1, 1, 1])
    assert np.isnan(_mape(actual, pred))
    assert _rmse(actual, pred) == 1.0


# ── Feature engineering tests ──────────────────────────────────────────────────


def test_build_features():
    series = _make_sample_series(45)
    df = build_features(series)

    assert "y" in df.columns
    assert "lag_1" in df.columns
    assert "lag_7" in df.columns
    assert "rolling_mean_7" in df.columns
    assert "day_of_week" in df.columns
    assert not df.isna().any().any()


# ── LightGBM model tests ───────────────────────────────────────────────────────


def test_lgbm_forecaster_fit_and_predict():
    series = _make_sample_series(60)
    model = LightGBMForecaster(model_key="test_product", horizon=7)
    model.train(series)

    preds = model.predict(horizon=7)
    assert len(preds["point"]) == 7
    assert len(preds["lower"]) == 7
    assert len(preds["upper"]) == 7
    assert (preds["lower"] <= preds["point"]).all()
    assert (preds["point"] <= preds["upper"]).all()


# ── Router endpoint tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_forecasts(async_client):
    from app.api.deps import get_current_user
    from tests.conftest import _test_app
    from tests.test_auth import _make_fake_user

    fake_user = _make_fake_user(role="viewer")
    _test_app.dependency_overrides[get_current_user] = lambda: fake_user

    try:
        with patch(
            "app.services.forecasting_service.list_product_forecasts", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = [
                {
                    "product_id": str(uuid.uuid4()),
                    "product_name": "Test SKU",
                    "sku": "SKU-001",
                    "from_date": "2024-03-01",
                    "to_date": "2024-03-30",
                    "model_name": "lightgbm",
                    "avg_mape": 12.5,
                    "last_trained": "2024-03-01",
                }
            ]
            response = await async_client.get("/api/v1/forecast/")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["forecasts"]) == 1
    finally:
        _test_app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_forecast_endpoint(async_client):
    from app.api.deps import get_current_user
    from tests.conftest import _test_app
    from tests.test_auth import _make_fake_user

    fake_user = _make_fake_user(role="viewer")
    _test_app.dependency_overrides[get_current_user] = lambda: fake_user
    prod_id = uuid.uuid4()

    try:
        with patch(
            "app.services.forecasting_service.get_forecast", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = {
                "product_id": str(prod_id),
                "model_name": "lightgbm",
                "mape": 10.2,
                "rmse": 3.4,
                "horizon_days": 30,
                "forecasts": [
                    {
                        "date": "2024-03-02",
                        "predicted_qty": 25.0,
                        "lower_bound": 20.0,
                        "upper_bound": 30.0,
                    }
                ],
                "shap_features": {"lag_7": 0.4, "rolling_mean_7": 0.3},
                "from_cache": False,
                "error": None,
            }
            response = await async_client.get(f"/api/v1/forecast/{prod_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["model_name"] == "lightgbm"
            assert data["mape"] == 10.2
            assert len(data["forecasts"]) == 1
    finally:
        _test_app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_retrain_forecast_endpoint(async_client):
    from app.api.deps import get_current_user
    from tests.conftest import _test_app
    from tests.test_auth import _make_fake_user

    fake_manager = _make_fake_user(role="manager")
    _test_app.dependency_overrides[get_current_user] = lambda: fake_manager
    prod_id = uuid.uuid4()

    try:
        with patch(
            "app.services.forecasting_service.get_forecast", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = {
                "product_id": str(prod_id),
                "model_name": "lightgbm",
                "mape": 9.8,
                "rmse": 3.1,
                "horizon_days": 30,
                "forecasts": [
                    {
                        "date": "2024-03-02",
                        "predicted_qty": 25.0,
                        "lower_bound": 20.0,
                        "upper_bound": 30.0,
                    }
                ],
                "shap_features": {"lag_7": 0.4},
                "from_cache": False,
                "error": None,
            }
            with patch("app.api.forecast.log_audit", new_callable=AsyncMock) as mock_audit:
                response = await async_client.post(f"/api/v1/forecast/{prod_id}/retrain")
                assert response.status_code == 200
                assert mock_audit.called
                assert mock_audit.call_args[1]["action"] == "retrain_forecast"
    finally:
        _test_app.dependency_overrides.pop(get_current_user, None)
