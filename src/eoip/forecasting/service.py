"""Forecast application service for EOIP."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from eoip.forecasting.models.base import ForecastModel, ForecastResult
from eoip.forecasting.storage import ForecastStore, StoredForecast


class ForecastService:
    """Coordinate forecast model execution and persistence."""

    def __init__(
        self,
        *,
        store: ForecastStore | None = None,
    ) -> None:
        """Initialize forecast service."""
        self._store = store

    def generate_forecast(
        self,
        *,
        model: ForecastModel,
        training_frame: pd.DataFrame,
        timestamp_column: str,
        target_column: str,
        horizon: int,
        frequency: str,
    ) -> ForecastResult:
        """Train a model and generate a forecast."""
        if training_frame.empty:
            raise ValueError("Training frame must not be empty.")

        if timestamp_column not in training_frame.columns:
            raise ValueError(f"Missing timestamp column: {timestamp_column}")

        if target_column not in training_frame.columns:
            raise ValueError(f"Missing target column: {target_column}")

        if horizon < 1:
            raise ValueError("horizon must be greater than zero.")

        if not frequency.strip():
            raise ValueError("frequency must not be empty.")

        model.fit(
            frame=training_frame,
            timestamp_column=timestamp_column,
            target_column=target_column,
        )

        return model.predict(
            horizon=horizon,
            frequency=frequency,
        )

    def generate_and_store_forecast(
        self,
        *,
        model: ForecastModel,
        training_frame: pd.DataFrame,
        timestamp_column: str,
        target_column: str,
        horizon: int,
        frequency: str,
        generated_at: datetime,
    ) -> StoredForecast:
        """Generate a forecast and persist it."""
        if self._store is None:
            raise RuntimeError("Forecast store is not configured.")

        forecast = self.generate_forecast(
            model=model,
            training_frame=training_frame,
            timestamp_column=timestamp_column,
            target_column=target_column,
            horizon=horizon,
            frequency=frequency,
        )

        return self._store.save(
            forecast=forecast,
            generated_at=generated_at,
        )

    def load_forecast(
        self,
        *,
        forecast_id: str,
    ) -> pd.DataFrame:
        """Load stored forecast predictions."""
        if self._store is None:
            raise RuntimeError("Forecast store is not configured.")

        if not forecast_id.strip():
            raise ValueError("forecast_id must not be empty.")

        return self._store.load(
            forecast_id=forecast_id,
        )
