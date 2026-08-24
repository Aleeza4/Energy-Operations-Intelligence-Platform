"""Naive baseline forecasting model for EOIP."""

from __future__ import annotations

import pandas as pd

from eoip.forecasting.models.base import ForecastResult


class NaiveForecastModel:
    """Forecast future values using the most recent observed value."""

    def __init__(self) -> None:
        """Initialize the naive forecasting model."""
        self._last_timestamp: pd.Timestamp | None = None
        self._last_value: float | None = None
        self._target_column: str | None = None

    @property
    def name(self) -> str:
        """Return model name."""
        return "Naive"

    def fit(
        self,
        *,
        frame: pd.DataFrame,
        timestamp_column: str,
        target_column: str,
    ) -> None:
        """Fit the model using the final observed target value."""
        if frame.empty:
            raise ValueError("Training frame must not be empty.")

        if timestamp_column not in frame.columns:
            raise ValueError(f"Missing timestamp column: {timestamp_column}")

        if target_column not in frame.columns:
            raise ValueError(f"Missing target column: {target_column}")

        timestamps = pd.to_datetime(
            frame[timestamp_column],
            utc=True,
            errors="raise",
        )

        targets = frame[target_column]

        if not pd.api.types.is_numeric_dtype(targets):
            raise TypeError("Training target column must contain numeric values.")

        if timestamps.isna().any():
            raise ValueError("Training timestamps must not contain missing values.")

        if targets.isna().any():
            raise ValueError("Training target values must not contain missing values.")

        ordered = pd.DataFrame(
            {
                "timestamp": timestamps,
                "target": targets.astype(float),
            }
        ).sort_values("timestamp")

        self._last_timestamp = ordered["timestamp"].iloc[-1]
        self._last_value = float(ordered["target"].iloc[-1])
        self._target_column = target_column

    def predict(
        self,
        *,
        horizon: int,
        frequency: str,
    ) -> ForecastResult:
        """Generate naive forecasts for the requested horizon."""
        if self._last_timestamp is None:
            raise RuntimeError("Model must be fitted before prediction.")

        if self._last_value is None:
            raise RuntimeError("Model must be fitted before prediction.")

        if self._target_column is None:
            raise RuntimeError("Model must be fitted before prediction.")

        if horizon < 1:
            raise ValueError("horizon must be greater than zero.")

        if not frequency.strip():
            raise ValueError("frequency must not be empty.")

        offset = pd.tseries.frequencies.to_offset(frequency)

        timestamps = pd.date_range(
            start=self._last_timestamp + offset,
            periods=horizon,
            freq=frequency,
        )

        predictions = pd.DataFrame(
            {
                "timestamp": timestamps,
                "prediction": [self._last_value] * horizon,
            }
        )

        return ForecastResult(
            model_name=self.name,
            target_column=self._target_column,
            predictions=predictions,
        )
