"""Core forecasting dataset contracts for EOIP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import pandas as pd


class ForecastTarget(StrEnum):
    """Supported EOIP forecasting targets."""

    ACTIVE_POWER_KW = "active_power_kw"
    INTERVAL_ENERGY_KWH = "interval_energy_kwh"
    GHI_WM2 = "ghi_wm2"


@dataclass(frozen=True, slots=True)
class ForecastDataset:
    """Validated forecasting dataset used by EOIP models."""

    data: pd.DataFrame
    timestamp_column: str
    target_column: str
    frequency: str

    def __post_init__(self) -> None:
        """Validate forecasting dataset structure."""
        if self.data.empty:
            raise ValueError("Forecast dataset must not be empty.")

        if not self.timestamp_column.strip():
            raise ValueError("timestamp_column must not be empty.")

        if not self.target_column.strip():
            raise ValueError("target_column must not be empty.")

        if not self.frequency.strip():
            raise ValueError("frequency must not be empty.")

        if self.timestamp_column not in self.data.columns:
            raise ValueError(f"Missing timestamp column: {self.timestamp_column}")

        if self.target_column not in self.data.columns:
            raise ValueError(f"Missing target column: {self.target_column}")

        timestamps = self.data[self.timestamp_column]

        if not pd.api.types.is_datetime64_any_dtype(timestamps):
            raise TypeError("Forecast timestamp column must contain datetime values.")

        if timestamps.isna().any():
            raise ValueError(
                "Forecast timestamp column must not contain missing values."
            )

        if timestamps.duplicated().any():
            raise ValueError("Forecast timestamp column must not contain duplicates.")

        target = self.data[self.target_column]

        if not pd.api.types.is_numeric_dtype(target):
            raise TypeError("Forecast target column must contain numeric values.")

        if target.isna().any():
            raise ValueError("Forecast target column must not contain missing values.")

        if not timestamps.is_monotonic_increasing:
            raise ValueError("Forecast timestamps must be sorted in ascending order.")

    @property
    def start_at(self) -> datetime:
        """Return the first timestamp in the dataset."""
        return self.data[self.timestamp_column].iloc[0].to_pydatetime()

    @property
    def end_at(self) -> datetime:
        """Return the last timestamp in the dataset."""
        return self.data[self.timestamp_column].iloc[-1].to_pydatetime()

    @property
    def row_count(self) -> int:
        """Return number of dataset rows."""
        return len(self.data)

    def copy_frame(self) -> pd.DataFrame:
        """Return an independent copy of the underlying DataFrame."""
        return self.data.copy(deep=True)
