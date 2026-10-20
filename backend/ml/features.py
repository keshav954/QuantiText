"""
Feature engineering for demand forecasting.

Builds a feature matrix from daily_sales with:
  - Lag features: qty at t-1, t-7, t-14, t-28
  - Rolling means: 7-day, 14-day, 28-day rolling average
  - Calendar features: day-of-week, month, quarter, is_weekend
  - Indian festival flags (Diwali, Holi, Dussehra, Eid, Christmas, New Year)
  - Trend: days since series start (normalised)

All features are derived from the date index and historical sales only —
no future leakage is possible because rolling/lag windows use shift(1) before
computing, so t depends only on t-1, t-2, … .
"""

from __future__ import annotations

import pandas as pd

# ── Indian festival approximate dates (fixed or approximate) ─────────────────
# We flag ±3 days around each festival date for proximity effect.
# Dates are given as (month, day) tuples; year is filled in at runtime.
_FESTIVALS: list[tuple[int, int, str]] = [
    (1, 1, "new_year"),
    (1, 26, "republic_day"),
    (3, 25, "holi"),  # approximate (varies ±2 weeks)
    (8, 15, "independence"),
    (10, 2, "gandhi_jayanti"),
    (10, 24, "diwali"),  # approximate (varies ±2 weeks)
    (10, 15, "dussehra"),  # approximate
    (11, 14, "childrens_day"),
    (12, 25, "christmas"),
    (12, 31, "new_year_eve"),
]
_FESTIVAL_WINDOW = 3  # days before/after to flag


def _build_festival_flags(dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Return a DataFrame of binary festival-proximity flags."""
    flags = pd.DataFrame(index=dates)
    flags["is_festival"] = 0

    for month, day, _name in _FESTIVALS:
        for year in dates.year.unique():
            try:
                center = pd.Timestamp(year=year, month=month, day=day)
            except ValueError:
                continue
            mask = (dates >= center - pd.Timedelta(days=_FESTIVAL_WINDOW)) & (
                dates <= center + pd.Timedelta(days=_FESTIVAL_WINDOW)
            )
            flags.loc[mask, "is_festival"] = 1

    return flags


def build_features(series: pd.Series) -> pd.DataFrame:
    """
    Build a feature matrix from a daily quantity series.

    Args:
        series: pd.Series with DatetimeIndex, values = quantity_sold.
                Must be sorted ascending with no gaps (fill missing dates with 0).

    Returns:
        DataFrame with features and target column ``y``.
        Rows with NaN features (due to lag/rolling windows) are dropped.
    """
    series = series.sort_index().asfreq("D", fill_value=0)
    df = pd.DataFrame({"y": series})

    # ── Lag features ─────────────────────────────────────────────────────────
    for lag in [1, 7, 14, 28]:
        df[f"lag_{lag}"] = df["y"].shift(lag)

    # ── Rolling means (computed on lagged series to avoid leakage) ───────────
    lagged = df["y"].shift(1)
    for window in [7, 14, 28]:
        df[f"rolling_mean_{window}"] = lagged.rolling(window).mean()
        df[f"rolling_std_{window}"] = lagged.rolling(window).std().fillna(0)

    # ── Calendar features ─────────────────────────────────────────────────────
    df["day_of_week"] = df.index.dayofweek  # 0=Monday
    df["month"] = df.index.month
    df["quarter"] = df.index.quarter
    df["is_weekend"] = (df.index.dayofweek >= 5).astype(int)
    df["day_of_month"] = df.index.day
    df["week_of_year"] = df.index.isocalendar().week.astype(int)

    # ── Trend feature ─────────────────────────────────────────────────────────
    days_total = max((df.index[-1] - df.index[0]).days, 1)
    df["trend"] = [(d - df.index[0]).days / days_total for d in df.index]

    # ── Festival flags ────────────────────────────────────────────────────────
    festival_df = _build_festival_flags(df.index)
    df["is_festival"] = festival_df["is_festival"].values

    # Drop rows with NaN (lag/rolling warm-up period)
    df = df.dropna()
    return df


FEATURE_COLS: list[str] = [
    "lag_1",
    "lag_7",
    "lag_14",
    "lag_28",
    "rolling_mean_7",
    "rolling_mean_14",
    "rolling_mean_28",
    "rolling_std_7",
    "rolling_std_14",
    "rolling_std_28",
    "day_of_week",
    "month",
    "quarter",
    "is_weekend",
    "day_of_month",
    "week_of_year",
    "trend",
    "is_festival",
]
