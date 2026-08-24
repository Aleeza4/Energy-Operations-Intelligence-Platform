"""Forecasting dataset builders for EOIP."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from eoip.forecasting.dataset.base import ForecastDataset


def build_forecast_dataset(
    *,
    frame: pd.DataFrame,
    timestamp_column: str,
    target_column: str,
    frequency: str,
    feature_columns: Sequence[str] | None = None,
) -> ForecastDataset:
    """Build a validated EOIP forecasting dataset.

    Parameters
    ----------
    frame:
        Source DataFrame containing timestamps, target, and optional features.
    timestamp_column:
        Name of the timestamp column.
    target_column:
        Name of the forecasting target column.
    frequency:
        Expected time-series frequency, such as ``15min`` or ``1h``.
    feature_columns:
        Optional feature columns to retain.

    Returns
    -------
    ForecastDataset
        Validated forecasting dataset.

    Raises
    ------
    ValueError
        If required columns are missing or feature configuration is invalid.
    TypeError
        If the timestamp column cannot be converted to datetime.
    """
    if frame.empty:
        raise ValueError("Source forecasting frame must not be empty.")

    required_columns = {
        timestamp_column,
        target_column,
    }

    if feature_columns is not None:
        required_columns.update(feature_columns)

    missing_columns = sorted(required_columns - set(frame.columns))

    if missing_columns:
        raise ValueError(
            "Forecast source frame is missing required columns: " f"{missing_columns}"
        )

    selected_columns = [
        timestamp_column,
        target_column,
    ]

    if feature_columns is not None:
        for column in feature_columns:
            if column in selected_columns:
                continue

            selected_columns.append(column)

    dataset_frame = frame.loc[
        :,
        selected_columns,
    ].copy()

    try:
        dataset_frame[timestamp_column] = pd.to_datetime(
            dataset_frame[timestamp_column],
            utc=True,
            errors="raise",
        )
    except (TypeError, ValueError) as exc:
        raise TypeError(
            "Forecast timestamp column could not be converted " "to datetime values."
        ) from exc

    dataset_frame = dataset_frame.sort_values(timestamp_column).reset_index(drop=True)

    if dataset_frame[timestamp_column].duplicated().any():
        raise ValueError("Forecast source frame contains duplicate timestamps.")

    return ForecastDataset(
        data=dataset_frame,
        timestamp_column=timestamp_column,
        target_column=target_column,
        frequency=frequency,
    )
