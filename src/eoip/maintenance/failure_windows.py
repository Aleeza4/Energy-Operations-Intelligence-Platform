"""Failure-window labeling for EOIP predictive maintenance."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd


def label_failure_windows(
    observations: pd.DataFrame,
    failures: pd.DataFrame,
    *,
    timestamp_column: str = "timestamp",
    equipment_id_column: str = "equipment_id",
    failure_timestamp_column: str = "failure_timestamp",
    prediction_window: timedelta = timedelta(hours=24),
    target_column: str = "failure_within_window",
) -> pd.DataFrame:
    """Label observations when an equipment failure occurs in a future window."""
    if observations.empty:
        raise ValueError("Observations must not be empty.")

    if failures.empty:
        raise ValueError("Failures must not be empty.")

    if prediction_window <= timedelta(0):
        raise ValueError("prediction_window must be greater than zero.")

    if not timestamp_column.strip():
        raise ValueError("timestamp_column must not be empty.")

    if not equipment_id_column.strip():
        raise ValueError("equipment_id_column must not be empty.")

    if not failure_timestamp_column.strip():
        raise ValueError("failure_timestamp_column must not be empty.")

    if not target_column.strip():
        raise ValueError("target_column must not be empty.")

    required_observation_columns = {
        timestamp_column,
        equipment_id_column,
    }

    missing_observation_columns = sorted(
        required_observation_columns - set(observations.columns)
    )

    if missing_observation_columns:
        raise ValueError(
            "Observations are missing required columns: "
            f"{missing_observation_columns}"
        )

    required_failure_columns = {
        equipment_id_column,
        failure_timestamp_column,
    }

    missing_failure_columns = sorted(required_failure_columns - set(failures.columns))

    if missing_failure_columns:
        raise ValueError(
            "Failures are missing required columns: " f"{missing_failure_columns}"
        )

    result = observations.copy(deep=True)
    failure_frame = failures.copy(deep=True)

    try:
        result[timestamp_column] = pd.to_datetime(
            result[timestamp_column],
            utc=True,
            errors="raise",
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Observation timestamps contain invalid values.") from exc

    try:
        failure_frame[failure_timestamp_column] = pd.to_datetime(
            failure_frame[failure_timestamp_column],
            utc=True,
            errors="raise",
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Failure timestamps contain invalid values.") from exc

    if result[timestamp_column].isna().any():
        raise ValueError("Observation timestamps must not contain missing values.")

    if failure_frame[failure_timestamp_column].isna().any():
        raise ValueError("Failure timestamps must not contain missing values.")

    if result[equipment_id_column].isna().any():
        raise ValueError(
            "Observation equipment identifiers must not contain " "missing values."
        )

    if failure_frame[equipment_id_column].isna().any():
        raise ValueError(
            "Failure equipment identifiers must not contain " "missing values."
        )

    result[equipment_id_column] = result[equipment_id_column].astype(str).str.strip()

    failure_frame[equipment_id_column] = (
        failure_frame[equipment_id_column].astype(str).str.strip()
    )

    if result[equipment_id_column].eq("").any():
        raise ValueError("Observation equipment identifiers must not be empty.")

    if failure_frame[equipment_id_column].eq("").any():
        raise ValueError("Failure equipment identifiers must not be empty.")

    failure_lookup: dict[str, pd.DatetimeIndex] = {}

    for equipment_id, group in failure_frame.groupby(
        equipment_id_column,
        sort=False,
    ):
        failure_lookup[str(equipment_id)] = pd.DatetimeIndex(
            group[failure_timestamp_column].sort_values()
        )

    labels: list[bool] = []

    for equipment_id, timestamp in zip(
        result[equipment_id_column],
        result[timestamp_column],
        strict=True,
    ):
        equipment_failures = failure_lookup.get(str(equipment_id))

        if equipment_failures is None:
            labels.append(False)
            continue

        window_end = timestamp + prediction_window

        has_future_failure = bool(
            (
                (equipment_failures > timestamp) & (equipment_failures <= window_end)
            ).any()
        )

        labels.append(has_future_failure)

    result[target_column] = labels

    return result
