"""Unit tests for EOIP naive forecasting model."""

from __future__ import annotations

import pandas as pd
import pytest

from eoip.forecasting.models.naive import NaiveForecastModel


def _training_frame() -> pd.DataFrame:
    """Return a valid training DataFrame."""
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-08-17T10:00:00Z",
                    "2026-08-17T10:15:00Z",
                    "2026-08-17T10:30:00Z",
                ],
                utc=True,
            ),
            "active_power_kw": [
                400.0,
                500.0,
                600.0,
            ],
        }
    )


class TestNaiveForecastModel:
    """Tests for NaiveForecastModel."""

    def test_name(self) -> None:
        model = NaiveForecastModel()

        assert model.name == "Naive"

    def test_fit_and_predict(self) -> None:
        model = NaiveForecastModel()

        model.fit(
            frame=_training_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        result = model.predict(
            horizon=3,
            frequency="15min",
        )

        assert result.model_name == "Naive"
        assert result.target_column == "active_power_kw"
        assert len(result.predictions) == 3

        assert result.predictions["prediction"].tolist() == [
            600.0,
            600.0,
            600.0,
        ]

    def test_prediction_starts_after_last_training_timestamp(
        self,
    ) -> None:
        model = NaiveForecastModel()

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
                "2026-08-17T10:45:00Z",
                "2026-08-17T11:00:00Z",
            ],
            utc=True,
        )

        assert result.predictions["timestamp"].tolist() == list(expected)

    def test_fit_sorts_training_frame_before_using_last_value(
        self,
    ) -> None:
        frame = (
            _training_frame()
            .iloc[
                [
                    2,
                    0,
                    1,
                ]
            ]
            .reset_index(drop=True)
        )

        model = NaiveForecastModel()

        model.fit(
            frame=frame,
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        result = model.predict(
            horizon=1,
            frequency="15min",
        )

        assert result.predictions["prediction"].iloc[0] == pytest.approx(600.0)

    def test_supports_timestamp_strings(self) -> None:
        frame = _training_frame()
        frame["timestamp"] = frame["timestamp"].astype(str)

        model = NaiveForecastModel()

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
        assert result.predictions["prediction"].iloc[0] == pytest.approx(600.0)

    def test_rejects_empty_training_frame(self) -> None:
        model = NaiveForecastModel()

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
        model = NaiveForecastModel()

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
        model = NaiveForecastModel()

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
        frame["active_power_kw"] = [
            "low",
            "medium",
            "high",
        ]

        model = NaiveForecastModel()

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

        model = NaiveForecastModel()

        with pytest.raises(
            ValueError,
            match=("Training timestamps must not contain missing values."),
        ):
            model.fit(
                frame=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )

    def test_rejects_missing_target(self) -> None:
        frame = _training_frame()
        frame.loc[1, "active_power_kw"] = float("nan")

        model = NaiveForecastModel()

        with pytest.raises(
            ValueError,
            match=("Training target values must not contain missing values."),
        ):
            model.fit(
                frame=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )

    def test_predict_requires_fitted_model(self) -> None:
        model = NaiveForecastModel()

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
        model = NaiveForecastModel()

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
        model = NaiveForecastModel()

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

    def test_supports_hourly_forecast_frequency(self) -> None:
        model = NaiveForecastModel()

        model.fit(
            frame=_training_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        result = model.predict(
            horizon=2,
            frequency="1h",
        )

        expected = pd.to_datetime(
            [
                "2026-08-17T11:30:00Z",
                "2026-08-17T12:30:00Z",
            ],
            utc=True,
        )

        assert result.predictions["timestamp"].tolist() == list(expected)

        assert result.predictions["prediction"].tolist() == [
            600.0,
            600.0,
        ]
