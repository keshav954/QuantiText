"""
Baseline forecasting models.

Two simple baselines used as lower-bound comparison in the benchmark:
  - NaiveModel: forecast = last observed value (random walk)
  - SeasonalNaiveModel: forecast = value from same day-of-week 1 week ago

Both expose train() / evaluate() / predict() following project conventions.
Metrics logged: MAPE, RMSE.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Mean Absolute Percentage Error — ignores zero actuals."""
    mask = actual != 0
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


def _rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


class NaiveModel:
    """
    Naive (persistence) model: ŷ_{t+h} = y_t for all horizons h.
    """

    name = "naive"
    _last_value: float = 0.0

    def train(self, series: pd.Series) -> None:
        self._last_value = float(series.iloc[-1]) if len(series) > 0 else 0.0

    def predict(self, horizon: int) -> np.ndarray:
        return np.full(horizon, max(self._last_value, 0))

    def evaluate(self, series: pd.Series, horizon: int = 7) -> dict[str, float]:
        """Walk-forward evaluation on last `horizon` steps."""
        if len(series) <= horizon:
            return {"mape": float("nan"), "rmse": float("nan")}
        train = series.iloc[:-horizon]
        test = series.iloc[-horizon:]
        self.train(train)
        preds = self.predict(horizon)
        actual = test.values.astype(float)
        return {"mape": _mape(actual, preds), "rmse": _rmse(actual, preds)}


class SeasonalNaiveModel:
    """
    Seasonal naive model: ŷ_{t+h} = y_{t+h-7} (same weekday last week).
    Falls back to NaiveModel if fewer than 7 observations.
    """

    name = "seasonal_naive"
    _season: int = 7
    _history: pd.Series = pd.Series(dtype=float)

    def train(self, series: pd.Series) -> None:
        self._history = series.copy()

    def predict(self, horizon: int) -> np.ndarray:
        if len(self._history) < self._season:
            last = float(self._history.iloc[-1]) if len(self._history) > 0 else 0.0
            return np.full(horizon, max(last, 0))
        tail = self._history.iloc[-self._season:].values.astype(float)
        preds = np.array([max(tail[i % self._season], 0) for i in range(horizon)])
        return preds

    def evaluate(self, series: pd.Series, horizon: int = 7) -> dict[str, float]:
        if len(series) <= horizon:
            return {"mape": float("nan"), "rmse": float("nan")}
        train = series.iloc[:-horizon]
        test = series.iloc[-horizon:]
        self.train(train)
        preds = self.predict(horizon)
        actual = test.values.astype(float)
        return {"mape": _mape(actual, preds), "rmse": _rmse(actual, preds)}
