"""Forecast storage contracts for EOIP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import pandas as pd

from eoip.forecasting.models.base import ForecastResult


@dataclass(frozen=True, slots=True)
class StoredForecast:
    """Metadata describing a stored forecasting run."""

    forecast_id: str
    model_name: str
    target_column: str
    generated_at: datetime
    row_count: int

    def __post_init__(self) -> None:
        """Validate stored forecast metadata."""
        if not self.forecast_id.strip():
            raise ValueError("forecast_id must not be empty.")

        if not self.model_name.strip():
            raise ValueError("model_name must not be empty.")

        if not self.target_column.strip():
            raise ValueError("target_column must not be empty.")

        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware.")

        if self.row_count < 1:
            raise ValueError("row_count must be greater than zero.")


class ForecastStore(Protocol):
    """Protocol implemented by forecast storage backends."""

    def save(
        self,
        *,
        forecast: ForecastResult,
        generated_at: datetime,
    ) -> StoredForecast:
        """Persist a forecast and return storage metadata."""
        ...

    def load(
        self,
        *,
        forecast_id: str,
    ) -> pd.DataFrame:
        """Load stored forecast predictions."""
        ...


def validate_forecast_for_storage(
    forecast: ForecastResult,
) -> None:
    """Validate forecast output before persistence."""
    if forecast.predictions.empty:
        raise ValueError("Forecast predictions must not be empty.")

    required_columns = {
        "timestamp",
        "prediction",
    }

    missing_columns = required_columns - set(forecast.predictions.columns)

    if missing_columns:
        raise ValueError(
            "Forecast predictions are missing required columns: "
            f"{sorted(missing_columns)}"
        )

    timestamps = forecast.predictions["timestamp"]

    if not pd.api.types.is_datetime64_any_dtype(timestamps):
        raise TypeError("Forecast prediction timestamps must contain datetime values.")

    if timestamps.isna().any():
        raise ValueError(
            "Forecast prediction timestamps must not contain missing values."
        )

    predictions = forecast.predictions["prediction"]

    if not pd.api.types.is_numeric_dtype(predictions):
        raise TypeError("Forecast prediction values must be numeric.")

    if predictions.isna().any():
        raise ValueError("Forecast prediction values must not contain missing values.")
