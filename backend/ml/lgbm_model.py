"""
LightGBM demand forecasting model with SHAP explanations.

Interface: train() / evaluate() / predict() following project conventions.
Uses the feature matrix from ml.features.build_features().

Walk-forward validation:
  - Splits the series into N folds (default 3)
  - Each fold trains on [0:t] and validates on [t:t+horizon]
  - Reports mean MAPE and RMSE across folds

Conformal prediction intervals:
  - Residuals from validation folds are used to compute empirical quantiles
  - Lower/upper bounds set at the 10th/90th percentile of calibration residuals
  - This gives ~80% coverage without parametric assumptions

SHAP:
  - TreeExplainer is used (fast, exact for tree models)
  - Top-5 feature importances are stored in model metadata
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml.features import FEATURE_COLS, build_features

log = logging.getLogger(__name__)

_SAVED_MODELS_DIR = Path(__file__).parent / "saved_models"
_SAVED_MODELS_DIR.mkdir(exist_ok=True)


def _mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    mask = actual != 0
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


def _rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


class LightGBMForecaster:
    """
    Multi-step LightGBM regressor using a recursive strategy:
    predictions for horizon h > 1 feed back as lag features.

    Attributes:
        model_key: Unique identifier (e.g. product_id or category slug).
        horizon: Default prediction horizon in days.
    """

    name = "lightgbm"

    def __init__(self, model_key: str, horizon: int = 30) -> None:
        self.model_key = model_key
        self.horizon = horizon
        self._model: Any = None
        self._calibration_residuals: np.ndarray = np.array([])
        self._last_known: pd.Series = pd.Series(dtype=float)
        self._feature_importance: dict[str, float] = {}

    # ── Train ─────────────────────────────────────────────────────────────────

    def train(self, series: pd.Series) -> None:
        """Fit LightGBM on the full series after feature engineering."""
        import lightgbm as lgb

        df = build_features(series)
        if len(df) < 30:
            log.warning("Series too short for LightGBM (key=%s, n=%d)", self.model_key, len(df))
            return

        X = df[FEATURE_COLS].values
        y = df["y"].values

        params = {
            "objective": "regression_l1",  # MAE loss — more robust to outliers
            "n_estimators": 300,
            "learning_rate": 0.05,
            "num_leaves": 31,
            "min_child_samples": 5,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.1,
            "reg_lambda": 0.1,
            "n_jobs": -1,
            "verbose": -1,
        }

        self._model = lgb.LGBMRegressor(**params)
        self._model.fit(X, y)
        self._last_known = series.copy()

        # Feature importance
        importance = self._model.feature_importances_
        self._feature_importance = dict(
            sorted(
                zip(FEATURE_COLS, importance.tolist()),
                key=lambda x: x[1],
                reverse=True,
            )[:5]
        )
        log.info("LightGBM trained: key=%s top_features=%s", self.model_key, list(self._feature_importance.keys())[:3])

    # ── Evaluate ──────────────────────────────────────────────────────────────

    def evaluate(self, series: pd.Series, n_folds: int = 3, horizon: int | None = None) -> dict[str, float]:
        """
        Walk-forward cross-validation.
        Returns mean MAPE and RMSE across folds.
        Also populates calibration residuals for conformal intervals.
        """
        horizon = horizon or self.horizon
        min_train = 60  # need at least 60 days of history to train meaningfully

        if len(series) < min_train + horizon * n_folds:
            log.warning("Insufficient data for CV (key=%s, n=%d)", self.model_key, len(series))
            return {"mape": float("nan"), "rmse": float("nan"), "n_folds": 0}

        mapes, rmses, all_residuals = [], [], []

        fold_size = max((len(series) - min_train) // n_folds, horizon)

        for i in range(n_folds):
            cutoff = min_train + i * fold_size
            if cutoff + horizon > len(series):
                break

            train_series = series.iloc[:cutoff]
            test_series = series.iloc[cutoff: cutoff + horizon]

            # Temporarily train on fold subset
            tmp = LightGBMForecaster(self.model_key, horizon=horizon)
            tmp.train(train_series)

            if tmp._model is None:
                continue

            preds = tmp._predict_recursive(horizon)
            actual = test_series.values.astype(float)

            mapes.append(_mape(actual, preds))
            rmses.append(_rmse(actual, preds))
            all_residuals.extend((actual - preds).tolist())

        if not mapes:
            return {"mape": float("nan"), "rmse": float("nan"), "n_folds": 0}

        self._calibration_residuals = np.array(all_residuals)

        return {
            "mape": float(np.nanmean(mapes)),
            "rmse": float(np.nanmean(rmses)),
            "n_folds": len(mapes),
        }

    # ── Predict ───────────────────────────────────────────────────────────────

    def predict(self, horizon: int | None = None) -> dict[str, np.ndarray]:
        """
        Produce point forecasts and conformal prediction intervals.

        Returns:
            dict with keys: ``point``, ``lower``, ``upper`` — all np.ndarray of length `horizon`.
        """
        horizon = horizon or self.horizon
        if self._model is None:
            log.warning("predict() called before train() (key=%s)", self.model_key)
            return {
                "point": np.zeros(horizon),
                "lower": np.zeros(horizon),
                "upper": np.zeros(horizon),
            }

        point = self._predict_recursive(horizon)
        point = np.clip(point, 0, None)

        # Conformal intervals from calibration residuals
        if len(self._calibration_residuals) >= 10:
            q_low = float(np.percentile(self._calibration_residuals, 10))
            q_high = float(np.percentile(self._calibration_residuals, 90))
        else:
            # Fallback: ±20% of point forecast
            q_low = -0.20
            q_high = 0.20

        lower = np.clip(point + q_low, 0, None)
        upper = point + q_high

        return {"point": point, "lower": lower, "upper": upper}

    def _predict_recursive(self, horizon: int) -> np.ndarray:
        """Recursive multi-step prediction — feeds predictions back as lags."""
        extended = self._last_known.copy()
        predictions = []

        for _ in range(horizon):
            df = build_features(extended)
            if len(df) == 0:
                predictions.append(0.0)
                continue

            last_row = df[FEATURE_COLS].iloc[[-1]].values
            pred = float(self._model.predict(last_row)[0])
            pred = max(pred, 0)
            predictions.append(pred)

            # Append prediction to extend the series for next step
            next_date = extended.index[-1] + pd.Timedelta(days=1)
            extended.loc[next_date] = pred

        return np.array(predictions)

    # ── SHAP ─────────────────────────────────────────────────────────────────

    def explain(self, series: pd.Series) -> dict[str, float]:
        """
        Compute SHAP values for the last observation.
        Returns a dict of {feature: mean_abs_shap_value}.
        Only top-5 features are returned.
        """
        if self._model is None:
            return {}
        try:
            import shap

            df = build_features(series)
            if len(df) == 0:
                return {}

            X = df[FEATURE_COLS].values
            explainer = shap.TreeExplainer(self._model)
            shap_values = explainer.shap_values(X[-1:])
            mean_abs = np.abs(shap_values).mean(axis=0)
            result = dict(sorted(zip(FEATURE_COLS, mean_abs.tolist()), key=lambda x: x[1], reverse=True)[:5])
            return result
        except Exception:
            log.warning("SHAP explanation failed for key=%s", self.model_key, exc_info=True)
            return self._feature_importance

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self) -> Path:
        """Pickle the fitted model to saved_models/."""
        path = _SAVED_MODELS_DIR / f"lgbm_{self.model_key}.pkl"
        with open(path, "wb") as f:
            pickle.dump(self, f)
        log.info("Model saved: %s", path)
        return path

    @classmethod
    def load(cls, model_key: str) -> "LightGBMForecaster | None":
        path = _SAVED_MODELS_DIR / f"lgbm_{model_key}.pkl"
        if not path.exists():
            return None
        with open(path, "rb") as f:
            return pickle.load(f)
