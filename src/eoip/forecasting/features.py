"""Feature engineering utilities for EOIP forecasting."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import pandas as pd


def add_time_features(
    frame: pd.DataFrame,
    *,
    timestamp_column: str,
) -> pd.DataFrame:
    """Add deterministic calendar and clock features."""
    if timestamp_column not in frame.columns:
        raise ValueError(f"Missing timestamp column: {timestamp_column}")

    result = frame.copy()

    timestamps = pd.to_datetime(
        result[timestamp_column],
        utc=True,
        errors="raise",
    )

    result[timestamp_column] = timestamps

    result["hour"] = timestamps.dt.hour
    result["minute"] = timestamps.dt.minute
    result["day_of_week"] = timestamps.dt.dayofweek
    result["day_of_month"] = timestamps.dt.day
    result["month"] = timestamps.dt.month
    result["day_of_year"] = timestamps.dt.dayofyear
    result["is_weekend"] = (timestamps.dt.dayofweek >= 5).astype(int)

    return result


def add_lag_features(
    frame: pd.DataFrame,
    *,
    target_column: str,
    lags: Iterable[int],
) -> pd.DataFrame:
    """Add target lag features."""
    if target_column not in frame.columns:
        raise ValueError(f"Missing target column: {target_column}")

    lag_values = list(lags)

    if not lag_values:
        raise ValueError("At least one lag must be provided.")

    if any(lag < 1 for lag in lag_values):
        raise ValueError("Lag values must be greater than zero.")

    result = frame.copy()

    for lag in lag_values:
        result[f"{target_column}_lag_{lag}"] = result[target_column].shift(lag)

    return result


def add_rolling_features(
    frame: pd.DataFrame,
    *,
    target_column: str,
    windows: Iterable[int],
) -> pd.DataFrame:
    """Add rolling mean and standard deviation features."""
    if target_column not in frame.columns:
        raise ValueError(f"Missing target column: {target_column}")

    window_values = list(windows)

    if not window_values:
        raise ValueError("At least one rolling window must be provided.")

    if any(window < 1 for window in window_values):
        raise ValueError("Rolling windows must be greater than zero.")

    result = frame.copy()

    shifted_target = result[target_column].shift(1)

    for window in window_values:
        result[f"{target_column}_rolling_mean_{window}"] = shifted_target.rolling(
            window=window
        ).mean()

        result[f"{target_column}_rolling_std_{window}"] = shifted_target.rolling(
            window=window
        ).std()

    return result


def select_forecast_features(
    frame: pd.DataFrame,
    *,
    timestamp_column: str,
    target_column: str,
    feature_columns: Sequence[str],
    drop_missing: bool = True,
) -> pd.DataFrame:
    """Return the final model-ready forecasting feature frame."""
    required_columns = {
        timestamp_column,
        target_column,
        *feature_columns,
    }

    missing_columns = sorted(required_columns - set(frame.columns))

    if missing_columns:
        raise ValueError(
            "Forecast feature frame is missing required columns: " f"{missing_columns}"
        )

    selected_columns = [
        timestamp_column,
        target_column,
        *feature_columns,
    ]

    result = frame.loc[
        :,
        selected_columns,
    ].copy()

    if drop_missing:
        result = result.dropna().reset_index(drop=True)

    return result
