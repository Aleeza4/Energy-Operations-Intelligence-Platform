"""Feature engineering utilities for EOIP predictive maintenance."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


def _validate_feature_inputs(
    frame: pd.DataFrame,
    *,
    equipment_id_column: str,
    feature_columns: Iterable[str],
) -> list[str]:
    """Validate common feature-engineering inputs."""
    if not equipment_id_column.strip():
        raise ValueError("equipment_id_column must not be empty.")

    if equipment_id_column not in frame.columns:
        raise ValueError(f"Missing equipment identifier column: {equipment_id_column}")

    selected_features = list(feature_columns)

    if not selected_features:
        raise ValueError("At least one feature column must be provided.")

    missing_columns = sorted(set(selected_features) - set(frame.columns))

    if missing_columns:
        raise ValueError(
            "Maintenance feature columns are missing: " f"{missing_columns}"
        )

    for column in selected_features:
        if not pd.api.types.is_numeric_dtype(frame[column]):
            raise TypeError(f"Feature column must be numeric: {column}")

    return selected_features


def add_lag_features(
    frame: pd.DataFrame,
    *,
    equipment_id_column: str,
    feature_columns: Iterable[str],
    lags: Iterable[int],
) -> pd.DataFrame:
    """Add per-equipment lag features."""
    selected_features = _validate_feature_inputs(
        frame,
        equipment_id_column=equipment_id_column,
        feature_columns=feature_columns,
    )

    lag_values = list(lags)

    if not lag_values:
        raise ValueError("At least one lag must be provided.")

    if any(lag < 1 for lag in lag_values):
        raise ValueError("Lag values must be greater than zero.")

    result = frame.copy(deep=True)

    grouped = result.groupby(
        equipment_id_column,
        sort=False,
    )

    for column in selected_features:
        for lag in lag_values:
            result[f"{column}_lag_{lag}"] = grouped[column].shift(lag)

    return result


def add_rolling_features(
    frame: pd.DataFrame,
    *,
    equipment_id_column: str,
    feature_columns: Iterable[str],
    windows: Iterable[int],
) -> pd.DataFrame:
    """Add per-equipment rolling mean and standard deviation features."""
    selected_features = _validate_feature_inputs(
        frame,
        equipment_id_column=equipment_id_column,
        feature_columns=feature_columns,
    )

    window_values = list(windows)

    if not window_values:
        raise ValueError("At least one rolling window must be provided.")

    if any(window < 1 for window in window_values):
        raise ValueError("Rolling windows must be greater than zero.")

    result = frame.copy(deep=True)

    for column in selected_features:
        shifted = result.groupby(
            equipment_id_column,
            sort=False,
        )[
            column
        ].shift(1)

        for window in window_values:
            rolling = shifted.groupby(
                result[equipment_id_column],
                sort=False,
            ).rolling(
                window=window,
            )

            result[f"{column}_rolling_mean_{window}"] = (
                rolling.mean()
                .reset_index(
                    level=0,
                    drop=True,
                )
                .sort_index()
            )

            result[f"{column}_rolling_std_{window}"] = (
                rolling.std()
                .reset_index(
                    level=0,
                    drop=True,
                )
                .sort_index()
            )

    return result


def add_delta_features(
    frame: pd.DataFrame,
    *,
    equipment_id_column: str,
    feature_columns: Iterable[str],
) -> pd.DataFrame:
    """Add per-equipment first-difference features."""
    selected_features = _validate_feature_inputs(
        frame,
        equipment_id_column=equipment_id_column,
        feature_columns=feature_columns,
    )

    result = frame.copy(deep=True)

    grouped = result.groupby(
        equipment_id_column,
        sort=False,
    )

    for column in selected_features:
        result[f"{column}_delta"] = grouped[column].diff()

    return result
