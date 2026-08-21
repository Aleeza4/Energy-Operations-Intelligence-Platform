"""Core anomaly detection dataset contracts for EOIP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import pandas as pd


class AnomalyTarget(StrEnum):
    """Supported anomaly detection targets."""

    ACTIVE_POWER_KW = "active_power_kw"
    INTERVAL_ENERGY_KWH = "interval_energy_kwh"
    PERFORMANCE_RATIO = "performance_ratio"
    RESIDUAL = "residual"


@dataclass(frozen=True, slots=True)
class AnomalyDataset:
    """Validated dataset used by EOIP anomaly detection models."""

    data: pd.DataFrame
    timestamp_column: str
    target_column: str

    def __post_init__(self) -> None:
        """Validate anomaly dataset structure."""
        if self.data.empty:
            raise ValueError("Anomaly dataset must not be empty.")

        if not self.timestamp_column.strip():
            raise ValueError("timestamp_column must not be empty.")

        if not self.target_column.strip():
            raise ValueError("target_column must not be empty.")

        if self.timestamp_column not in self.data.columns:
            raise ValueError(f"Missing timestamp column: {self.timestamp_column}")

        if self.target_column not in self.data.columns:
            raise ValueError(f"Missing target column: {self.target_column}")

        timestamps = self.data[self.timestamp_column]

        if not pd.api.types.is_datetime64_any_dtype(timestamps):
            raise TypeError("Anomaly timestamp column must contain datetime values.")

        if timestamps.isna().any():
            raise ValueError(
                "Anomaly timestamp column must not contain missing values."
            )

        if timestamps.duplicated().any():
            raise ValueError("Anomaly timestamp column must not contain duplicates.")

        if not timestamps.is_monotonic_increasing:
            raise ValueError("Anomaly timestamps must be sorted in ascending order.")

        target = self.data[self.target_column]

        if not pd.api.types.is_numeric_dtype(target):
            raise TypeError("Anomaly target column must contain numeric values.")

        if target.isna().any():
            raise ValueError("Anomaly target column must not contain missing values.")

    @property
    def start_at(self) -> datetime:
        """Return first timestamp in the dataset."""
        return self.data[self.timestamp_column].iloc[0].to_pydatetime()

    @property
    def end_at(self) -> datetime:
        """Return last timestamp in the dataset."""
        return self.data[self.timestamp_column].iloc[-1].to_pydatetime()

    @property
    def row_count(self) -> int:
        """Return number of anomaly observations."""
        return len(self.data)

    def copy_frame(self) -> pd.DataFrame:
        """Return an independent copy of the dataset."""
        return self.data.copy(deep=True)
