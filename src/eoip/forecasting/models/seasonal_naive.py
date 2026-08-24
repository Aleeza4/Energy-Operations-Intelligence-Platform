"""Seasonal naive baseline forecasting model for EOIP."""

from __future__ import annotations

import pandas as pd

from eoip.forecasting.models.base import ForecastResult


class SeasonalNaiveForecastModel:
    """Forecast future values by repeating the previous seasonal cycle."""

    def __init__(
        self,
        *,
        seasonal_periods: int,
    ) -> None:
        """Initialize the seasonal naive forecasting model."""
        if seasonal_periods < 1:
            raise ValueError("seasonal_periods must be greater than zero.")

        self.seasonal_periods = seasonal_periods
        self._history: list[float] | None = None
        self._last_timestamp: pd.Timestamp | None = None
        self._target_column: str | None = None

    @property
    def name(self) -> str:
        """Return model name."""
        return "Seasonal Naive"

    def fit(
        self,
        *,
        frame: pd.DataFrame,
        timestamp_column: str,
        target_column: str,
    ) -> None:
        """Fit the model using the most recent complete seasonal cycle."""
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

        if len(ordered) < self.seasonal_periods:
            raise ValueError(
                "Training frame must contain at least seasonal_periods " "observations."
            )

        self._history = ordered["target"].iloc[-self.seasonal_periods :].tolist()

        self._last_timestamp = ordered["timestamp"].iloc[-1]
        self._target_column = target_column

    def predict(
        self,
        *,
        horizon: int,
        frequency: str,
    ) -> ForecastResult:
        """Generate seasonal naive forecasts."""
        if self._history is None:
            raise RuntimeError("Model must be fitted before prediction.")

        if self._last_timestamp is None:
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

        predictions = [
            self._history[index % self.seasonal_periods] for index in range(horizon)
        ]

        prediction_frame = pd.DataFrame(
            {
                "timestamp": timestamps,
                "prediction": predictions,
            }
        )

        return ForecastResult(
            model_name=self.name,
            target_column=self._target_column,
            predictions=prediction_frame,
        )
