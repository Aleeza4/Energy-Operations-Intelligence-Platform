"""Anomaly storage contracts for EOIP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import pandas as pd


@dataclass(frozen=True, slots=True)
class StoredAnomalyRun:
    """Metadata describing a stored anomaly detection run."""

    anomaly_run_id: str
    detector_name: str
    target_column: str
    generated_at: datetime
    row_count: int
    anomaly_count: int

    def __post_init__(self) -> None:
        """Validate stored anomaly metadata."""
        if not self.anomaly_run_id.strip():
            raise ValueError("anomaly_run_id must not be empty.")

        if not self.detector_name.strip():
            raise ValueError("detector_name must not be empty.")

        if not self.target_column.strip():
            raise ValueError("target_column must not be empty.")

        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware.")

        if self.row_count < 1:
            raise ValueError("row_count must be greater than zero.")

        if self.anomaly_count < 0:
            raise ValueError("anomaly_count must not be negative.")

        if self.anomaly_count > self.row_count:
            raise ValueError("anomaly_count must not exceed row_count.")


class AnomalyStore(Protocol):
    """Protocol implemented by anomaly storage backends."""

    def save(
        self,
        *,
        detector_name: str,
        target_column: str,
        result_frame: pd.DataFrame,
        generated_at: datetime,
    ) -> StoredAnomalyRun:
        """Persist anomaly detection results."""
        ...

    def load(
        self,
        *,
        anomaly_run_id: str,
    ) -> pd.DataFrame:
        """Load anomaly detection results."""
        ...


def validate_anomaly_frame_for_storage(
    frame: pd.DataFrame,
) -> None:
    """Validate anomaly result frame before persistence."""
    if frame.empty:
        raise ValueError("Anomaly result frame must not be empty.")

    required_columns = {
        "timestamp",
        "is_anomaly",
    }

    missing_columns = required_columns - set(frame.columns)

    if missing_columns:
        raise ValueError(
            "Anomaly result frame is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    timestamps = frame["timestamp"]

    if not pd.api.types.is_datetime64_any_dtype(timestamps):
        raise TypeError("Anomaly timestamps must contain datetime values.")

    if timestamps.isna().any():
        raise ValueError("Anomaly timestamps must not contain missing values.")

    anomaly_flags = frame["is_anomaly"]

    if not pd.api.types.is_bool_dtype(anomaly_flags):
        raise TypeError("Anomaly flags must be boolean.")

    if anomaly_flags.isna().any():
        raise ValueError("Anomaly flags must not contain missing values.")
