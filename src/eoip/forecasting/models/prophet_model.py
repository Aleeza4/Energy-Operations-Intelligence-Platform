"""Prophet forecasting model for EOIP."""

from __future__ import annotations

import numpy as np
import pandas as pd
from prophet import Prophet

from eoip.forecasting.models.base import ForecastResult


class ProphetForecastModel:
    """Forecast EOIP time-series data using Prophet with a daily-cycle fallback."""

    def __init__(
        self,
        *,
        daily_seasonality: bool = True,
        weekly_seasonality: bool = True,
        yearly_seasonality: bool = False,
        changepoint_prior_scale: float = 0.05,
        seasonality_prior_scale: float = 10.0,
    ) -> None:
        """Initialize the Prophet forecasting model."""
        self.daily_seasonality = daily_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.yearly_seasonality = yearly_seasonality
        self.changepoint_prior_scale = changepoint_prior_scale
        self.seasonality_prior_scale = seasonality_prior_scale

        self._model: Prophet | None = None
        self._last_timestamp: pd.Timestamp | None = None
        self._target_column: str | None = None
        self._daily_profile: np.ndarray | None = None
        self._trend_slope: float | None = None
        self._seasonal_period: int | None = None

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
            changepoint_prior_scale=self.changepoint_prior_scale,
            seasonality_prior_scale=self.seasonality_prior_scale,
        )

        model.fit(ordered)

        ordered_index = OrderedIndex(ordered["ds"], ordered["y"])
        self._daily_profile = ordered_index.daily_profile()
        self._seasonal_period = len(self._daily_profile)
        self._trend_slope = ordered_index.trend_slope()

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
        prophet_predictions = forecast["yhat"].astype(float).to_numpy()

        if self._daily_profile is not None and self._trend_slope is not None:
            daily_index = (future_timestamps.hour * 60 + future_timestamps.minute) // 15
            daily_component = self._daily_profile[
                daily_index % len(self._daily_profile)
            ]
            trend_component = self._trend_slope * np.arange(1, horizon + 1, dtype=float)
            blended_predictions = 0.65 * prophet_predictions + 0.35 * np.maximum(
                daily_component + trend_component,
                0.0,
            )
            lower_bound = np.minimum(prophet_predictions, blended_predictions)
            upper_bound = np.maximum(prophet_predictions, blended_predictions)
        else:
            blended_predictions = prophet_predictions
            lower_bound = forecast["yhat_lower"].astype(float).to_numpy()
            upper_bound = forecast["yhat_upper"].astype(float).to_numpy()

        predictions = pd.DataFrame(
            {
                "timestamp": future_timestamps,
                "prediction": blended_predictions.astype(float),
                "lower_bound": lower_bound.astype(float),
                "upper_bound": upper_bound.astype(float),
            }
        )

        return ForecastResult(
            model_name=self.name,
            target_column=self._target_column,
            predictions=predictions,
        )


class OrderedIndex:
    """Helper for constructing robust seasonal and trend components."""

    def __init__(self, timestamps: pd.Series, values: pd.Series) -> None:
        frame = pd.DataFrame({"ds": timestamps, "y": values.astype(float)})
        frame = frame.sort_values("ds").reset_index(drop=True)
        self.timestamps = frame["ds"].to_numpy()
        self.values = frame["y"].to_numpy(dtype=float)

    def daily_profile(self) -> np.ndarray:
        """Return a 15-minute daily profile estimated from the training data."""
        if len(self.values) == 0:
            return np.array([], dtype=float)
        slots = 24 * 60 // 15
        buckets = np.empty(slots, dtype=float)
        for slot in range(slots):
            bucket_mask = (
                self.timestamps.hour * 60 + self.timestamps.minute
            ) // 15 == slot
            if np.any(bucket_mask):
                buckets[slot] = np.median(self.values[bucket_mask])
            else:
                buckets[slot] = float(np.median(self.values))
        return buckets

    def trend_slope(self) -> float:
        """Return a simple linear slope for recent trends."""
        if len(self.values) < 2:
            return 0.0
        x = np.arange(len(self.values), dtype=float)
        slope = np.polyfit(
            x[-min(len(self.values), 12) :],
            self.values[-min(len(self.values), 12) :],
            1,
        )[0]
        return float(slope)
