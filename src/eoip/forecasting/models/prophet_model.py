"""Prophet forecasting model for EOIP."""

from __future__ import annotations

import pandas as pd
from prophet import Prophet

from eoip.forecasting.models.base import ForecastResult


class ProphetForecastModel:
    """Forecast EOIP time-series data using Prophet."""

    def __init__(
        self,
        *,
        daily_seasonality: bool = True,
        weekly_seasonality: bool = True,
        yearly_seasonality: bool = False,
    ) -> None:
        """Initialize the Prophet forecasting model."""
        self.daily_seasonality = daily_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.yearly_seasonality = yearly_seasonality

        self._model: Prophet | None = None
        self._last_timestamp: pd.Timestamp | None = None
        self._target_column: str | None = None

    @property
    def name(self) -> str:
        """Return model name."""
        return "Prophet"

    def fit(
        self,
        *,
        frame: pd.DataFrame,
        timestamp_column: str,
        target_column: str,
    ) -> None:
        """Fit Prophet using EOIP time-series observations."""
        if frame.empty:
            raise ValueError("Training frame must not be empty.")

        if timestamp_column not in frame.columns:
            raise ValueError(f"Missing timestamp column: {timestamp_column}")

        if target_column not in frame.columns:
            raise ValueError(f"Missing target column: {target_column}")

        timestamps = pd.to_datetime(
            frame[timestamp_column],
            errors="raise",
            utc=True,
        )

        targets = frame[target_column]

        if not pd.api.types.is_numeric_dtype(targets):
            raise TypeError("Training target column must contain numeric values.")

        if timestamps.isna().any():
            raise ValueError("Training timestamps must not contain missing values.")

        if targets.isna().any():
            raise ValueError("Training target values must not contain missing values.")

        if timestamps.duplicated().any():
            raise ValueError("Training timestamps must not contain duplicates.")

        ordered = pd.DataFrame(
            {
                "ds": timestamps,
                "y": targets.astype(float),
            }
        ).sort_values("ds")

        # Prophet expects timezone-naive timestamps.
        ordered["ds"] = ordered["ds"].dt.tz_convert("UTC").dt.tz_localize(None)

        model = Prophet(
            daily_seasonality=self.daily_seasonality,
            weekly_seasonality=self.weekly_seasonality,
            yearly_seasonality=self.yearly_seasonality,
        )

        model.fit(ordered)

        self._model = model
        self._last_timestamp = timestamps.max()
        self._target_column = target_column

    def predict(
        self,
        *,
        horizon: int,
        frequency: str,
    ) -> ForecastResult:
        """Generate future Prophet forecasts."""
        if self._model is None:
            raise RuntimeError("Model must be fitted before prediction.")

        if self._last_timestamp is None:
            raise RuntimeError("Model must be fitted before prediction.")

        if self._target_column is None:
            raise RuntimeError("Model must be fitted before prediction.")

        if horizon < 1:
            raise ValueError("horizon must be greater than zero.")

        if not frequency.strip():
            raise ValueError("frequency must not be empty.")

        try:
            offset = pd.tseries.frequencies.to_offset(frequency)
        except ValueError as exc:
            raise ValueError(f"Invalid forecast frequency: {frequency}") from exc

        future_timestamps = pd.date_range(
            start=self._last_timestamp + offset,
            periods=horizon,
            freq=frequency,
        )

        prophet_future = pd.DataFrame(
            {"ds": future_timestamps.tz_convert("UTC").tz_localize(None)}
        )

        forecast = self._model.predict(prophet_future)

        predictions = pd.DataFrame(
            {
                "timestamp": future_timestamps,
                "prediction": forecast["yhat"].astype(float),
            }
        )

        return ForecastResult(
            model_name=self.name,
            target_column=self._target_column,
            predictions=predictions,
        )
