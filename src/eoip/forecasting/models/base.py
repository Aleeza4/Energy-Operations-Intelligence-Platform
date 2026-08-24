"""Core forecasting model contracts for EOIP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import pandas as pd


@dataclass(frozen=True, slots=True)
class ForecastPoint:
    """Single forecasted value."""

    timestamp: datetime
    value: float


@dataclass(frozen=True, slots=True)
class ForecastResult:
    """Standard result returned by EOIP forecasting models."""

    model_name: str
    target_column: str
    predictions: pd.DataFrame

    def __post_init__(self) -> None:
        """Validate forecast result."""
        if not self.model_name.strip():
            raise ValueError("model_name must not be empty.")

        if not self.target_column.strip():
            raise ValueError("target_column must not be empty.")

        if self.predictions.empty:
            raise ValueError("Forecast predictions must not be empty.")

        required_columns = {
            "timestamp",
            "prediction",
        }

        missing_columns = required_columns - set(self.predictions.columns)

        if missing_columns:
            raise ValueError(
                "Forecast predictions are missing required columns: "
                f"{sorted(missing_columns)}"
            )

        timestamps = self.predictions["timestamp"]

        if not pd.api.types.is_datetime64_any_dtype(timestamps):
            raise TypeError(
                "Forecast prediction timestamps must contain " "datetime values."
            )

        predictions = self.predictions["prediction"]

        if not pd.api.types.is_numeric_dtype(predictions):
            raise TypeError("Forecast prediction values must be numeric.")

        if timestamps.isna().any():
            raise ValueError(
                "Forecast prediction timestamps must not contain " "missing values."
            )

        if predictions.isna().any():
            raise ValueError(
                "Forecast prediction values must not contain " "missing values."
            )


class ForecastModel(Protocol):
    """Protocol implemented by EOIP forecasting models."""

    @property
    def name(self) -> str:
        """Return model name."""
        ...

    def fit(
        self,
        *,
        frame: pd.DataFrame,
        timestamp_column: str,
        target_column: str,
    ) -> None:
        """Fit the forecasting model."""
        ...

    def predict(
        self,
        *,
        horizon: int,
        frequency: str,
    ) -> ForecastResult:
        """Generate future forecasts."""
        ...
