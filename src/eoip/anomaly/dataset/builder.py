"""Dataset builder for EOIP anomaly detection."""

from __future__ import annotations

import pandas as pd

from eoip.anomaly.dataset.base import AnomalyDataset


def build_anomaly_dataset(
    *,
    frame: pd.DataFrame,
    timestamp_column: str,
    target_column: str,
) -> AnomalyDataset:
    """Build a validated anomaly detection dataset.

    The builder creates an independent frame, normalizes timestamps to UTC,
    converts the target to numeric values, sorts observations chronologically,
    and delegates final validation to ``AnomalyDataset``.
    """
    if frame.empty:
        raise ValueError("Source frame must not be empty.")

    if not timestamp_column.strip():
        raise ValueError("timestamp_column must not be empty.")

    if not target_column.strip():
        raise ValueError("target_column must not be empty.")

    if timestamp_column not in frame.columns:
        raise ValueError(f"Missing timestamp column: {timestamp_column}")

    if target_column not in frame.columns:
        raise ValueError(f"Missing target column: {target_column}")

    data = frame.copy(deep=True)

    try:
        data[timestamp_column] = pd.to_datetime(
            data[timestamp_column],
            utc=True,
            errors="raise",
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Timestamp column contains invalid datetime values.") from exc

    try:
        data[target_column] = pd.to_numeric(
            data[target_column],
            errors="raise",
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Target column contains non-numeric values.") from exc

    if data[timestamp_column].isna().any():
        raise ValueError("Timestamp column contains missing values.")

    if data[target_column].isna().any():
        raise ValueError("Target column contains missing values.")

    if data[timestamp_column].duplicated().any():
        raise ValueError("Timestamp column contains duplicate values.")

    data = data.sort_values(
        timestamp_column,
        kind="stable",
    ).reset_index(drop=True)

    return AnomalyDataset(
        data=data,
        timestamp_column=timestamp_column,
        target_column=target_column,
    )
