"""Unit tests for EOIP Prophet forecasting model."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from eoip.forecasting.models.prophet_model import ProphetForecastModel
from eoip.forecasting.models.seasonal_naive import SeasonalNaiveForecastModel


def _training_frame() -> pd.DataFrame:
    """Return a small deterministic solar-style training dataset."""
    timestamps = pd.date_range(
        start="2026-08-10T00:00:00Z",
        periods=96,
        freq="15min",
    )

    values = [
        max(
            0.0,
            800.0 * (1.0 - abs(((index % 96) - 48) / 48)),
        )
        for index in range(96)
    ]

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "active_power_kw": values,
        }
    )


class TestProphetForecastModelConstruction:
    """Tests for Prophet model construction."""

    def test_name(self) -> None:
        model = ProphetForecastModel()

        assert model.name == "Prophet"

    def test_stores_seasonality_configuration(self) -> None:
        model = ProphetForecastModel(
            daily_seasonality=False,
            weekly_seasonality=False,
            yearly_seasonality=True,
        )

        assert model.daily_seasonality is False
        assert model.weekly_seasonality is False
        assert model.yearly_seasonality is True


class TestProphetForecastModelFit:
    """Tests for Prophet model fitting."""

    def test_fits_valid_training_frame(self) -> None:
        model = ProphetForecastModel(
            weekly_seasonality=False,
            yearly_seasonality=False,
        )

        model.fit(
            frame=_training_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        result = model.predict(
            horizon=2,
            frequency="15min",
        )

        assert len(result.predictions) == 2

    def test_supports_timestamp_strings(self) -> None:
        frame = _training_frame()
        frame["timestamp"] = frame["timestamp"].astype(str)

        model = ProphetForecastModel(
            weekly_seasonality=False,
            yearly_seasonality=False,
        )

        model.fit(
            frame=frame,
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        result = model.predict(
            horizon=1,
            frequency="15min",
        )

        assert len(result.predictions) == 1

    def test_rejects_empty_training_frame(self) -> None:
        model = ProphetForecastModel()

        with pytest.raises(
            ValueError,
            match="Training frame must not be empty.",
        ):
            model.fit(
                frame=pd.DataFrame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )

    def test_rejects_missing_timestamp_column(self) -> None:
        model = ProphetForecastModel()

        with pytest.raises(
            ValueError,
            match="Missing timestamp column: missing_timestamp",
        ):
            model.fit(
                frame=_training_frame(),
                timestamp_column="missing_timestamp",
                target_column="active_power_kw",
            )

    def test_rejects_missing_target_column(self) -> None:
        model = ProphetForecastModel()

        with pytest.raises(
            ValueError,
            match="Missing target column: missing_target",
        ):
            model.fit(
                frame=_training_frame(),
                timestamp_column="timestamp",
                target_column="missing_target",
            )

    def test_rejects_non_numeric_target(self) -> None:
        frame = _training_frame()
        frame["active_power_kw"] = ["invalid" for _ in range(len(frame))]

        model = ProphetForecastModel()

        with pytest.raises(
            TypeError,
            match="Training target column must contain numeric values.",
        ):
            model.fit(
                frame=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )

    def test_rejects_missing_timestamp(self) -> None:
        frame = _training_frame()
        frame.loc[1, "timestamp"] = pd.NaT

        model = ProphetForecastModel()

        with pytest.raises(
            ValueError,
            match="Training timestamps must not contain missing values.",
        ):
            model.fit(
                frame=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )

    def test_rejects_missing_target(self) -> None:
        frame = _training_frame()
        frame.loc[1, "active_power_kw"] = float("nan")

        model = ProphetForecastModel()

        with pytest.raises(
            ValueError,
            match=("Training target values must not contain missing values."),
        ):
            model.fit(
                frame=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )

    def test_rejects_duplicate_timestamps(self) -> None:
        frame = _training_frame()
        frame.loc[1, "timestamp"] = frame.loc[0, "timestamp"]

        model = ProphetForecastModel()

        with pytest.raises(
            ValueError,
            match="Training timestamps must not contain duplicates.",
        ):
            model.fit(
                frame=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )


class TestProphetForecastModelPredict:
    """Tests for Prophet prediction."""

    def test_returns_expected_metadata(self) -> None:
        model = ProphetForecastModel(
            weekly_seasonality=False,
            yearly_seasonality=False,
        )

        model.fit(
            frame=_training_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        result = model.predict(
            horizon=3,
            frequency="15min",
        )

        assert result.model_name == "Prophet"
        assert result.target_column == "active_power_kw"
        assert len(result.predictions) == 3

    def test_prediction_timestamps_follow_training_data(self) -> None:
        model = ProphetForecastModel(
            weekly_seasonality=False,
            yearly_seasonality=False,
        )

        model.fit(
            frame=_training_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        result = model.predict(
            horizon=2,
            frequency="15min",
        )

        expected = pd.to_datetime(
            [
                "2026-08-11T00:00:00Z",
                "2026-08-11T00:15:00Z",
            ],
            utc=True,
        )

        assert result.predictions["timestamp"].tolist() == list(expected)

    def test_prediction_values_are_numeric(self) -> None:
        model = ProphetForecastModel(
            weekly_seasonality=False,
            yearly_seasonality=False,
        )

        model.fit(
            frame=_training_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        result = model.predict(
            horizon=4,
            frequency="15min",
        )

        assert pd.api.types.is_numeric_dtype(result.predictions["prediction"])
        assert pd.api.types.is_numeric_dtype(result.predictions["lower_bound"])
        assert pd.api.types.is_numeric_dtype(result.predictions["upper_bound"])
        assert (
            result.predictions["lower_bound"] <= result.predictions["upper_bound"]
        ).all()

    def test_outperforms_seasonal_naive_on_periodic_solar_signal(self) -> None:
        n = 576
        timestamps = pd.date_range("2026-01-01", periods=n, freq="15min", tz="UTC")
        signal = 350 + 180 * np.sin(2 * np.pi * np.arange(n) / 96)
        frame = pd.DataFrame(
            {
                "timestamp": timestamps,
                "active_power_kw": signal,
            }
        )

        train = frame.iloc[:384].copy()
        test = frame.iloc[384:].copy()

        prophet_model = ProphetForecastModel(
            weekly_seasonality=False,
            yearly_seasonality=False,
        )
        prophet_model.fit(
            frame=train,
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )
        prophet_forecast = prophet_model.predict(
            horizon=len(test),
            frequency="15min",
        )

        seasonal_model = SeasonalNaiveForecastModel(seasonal_periods=96)
        seasonal_model.fit(
            frame=train,
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )
        seasonal_forecast = seasonal_model.predict(
            horizon=len(test),
            frequency="15min",
        )

        prophet_error = np.mean(
            np.abs(
                test["active_power_kw"].to_numpy()
                - prophet_forecast.predictions["prediction"].to_numpy()
            )
        )
        seasonal_error = np.mean(
            np.abs(
                test["active_power_kw"].to_numpy()
                - seasonal_forecast.predictions["prediction"].to_numpy()
            )
        )

        assert prophet_error < seasonal_error

    def test_predict_requires_fitted_model(self) -> None:
        model = ProphetForecastModel()

        with pytest.raises(
            RuntimeError,
            match="Model must be fitted before prediction.",
        ):
            model.predict(
                horizon=1,
                frequency="15min",
            )

    @pytest.mark.parametrize(
        "horizon",
        [
            0,
            -1,
            -10,
        ],
    )
    def test_rejects_non_positive_horizon(
        self,
        horizon: int,
    ) -> None:
        model = ProphetForecastModel(
            weekly_seasonality=False,
            yearly_seasonality=False,
        )

        model.fit(
            frame=_training_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        with pytest.raises(
            ValueError,
            match="horizon must be greater than zero.",
        ):
            model.predict(
                horizon=horizon,
                frequency="15min",
            )

    def test_rejects_empty_frequency(self) -> None:
        model = ProphetForecastModel(
            weekly_seasonality=False,
            yearly_seasonality=False,
        )

        model.fit(
            frame=_training_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        with pytest.raises(
            ValueError,
            match="frequency must not be empty.",
        ):
            model.predict(
                horizon=1,
                frequency=" ",
            )

    def test_rejects_invalid_frequency(self) -> None:
        model = ProphetForecastModel(
            weekly_seasonality=False,
            yearly_seasonality=False,
        )

        model.fit(
            frame=_training_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        with pytest.raises(
            ValueError,
            match="Invalid forecast frequency",
        ):
            model.predict(
                horizon=1,
                frequency="not-a-frequency",
            )
