"""Unit tests for EOIP seasonal naive forecasting model."""

from __future__ import annotations

import pandas as pd
import pytest

from eoip.forecasting.models.seasonal_naive import (
    SeasonalNaiveForecastModel,
)


def _training_frame() -> pd.DataFrame:
    """Return a valid training DataFrame with two seasonal cycles."""
    return pd.DataFrame(
        {
            "timestamp": pd.date_range(
                start="2026-08-17T08:00:00Z",
                periods=8,
                freq="15min",
            ),
            "active_power_kw": [
                100.0,
                200.0,
                300.0,
                400.0,
                110.0,
                210.0,
                310.0,
                410.0,
            ],
        }
    )


class TestSeasonalNaiveForecastModelConstruction:
    """Tests for seasonal naive model construction."""

    def test_name(self) -> None:
        model = SeasonalNaiveForecastModel(
            seasonal_periods=4,
        )

        assert model.name == "Seasonal Naive"

    def test_stores_seasonal_periods(self) -> None:
        model = SeasonalNaiveForecastModel(
            seasonal_periods=4,
        )

        assert model.seasonal_periods == 4

    @pytest.mark.parametrize(
        "seasonal_periods",
        [
            0,
            -1,
            -10,
        ],
    )
    def test_rejects_non_positive_seasonal_periods(
        self,
        seasonal_periods: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="seasonal_periods must be greater than zero.",
        ):
            SeasonalNaiveForecastModel(
                seasonal_periods=seasonal_periods,
            )


class TestSeasonalNaiveForecastModelFit:
    """Tests for fitting the seasonal naive model."""

    def test_fits_valid_training_frame(self) -> None:
        model = SeasonalNaiveForecastModel(
            seasonal_periods=4,
        )

        model.fit(
            frame=_training_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        result = model.predict(
            horizon=1,
            frequency="15min",
        )

        assert len(result.predictions) == 1

    def test_fit_sorts_training_frame(self) -> None:
        frame = (
            _training_frame()
            .iloc[
                [
                    7,
                    0,
                    5,
                    2,
                    6,
                    1,
                    4,
                    3,
                ]
            ]
            .reset_index(drop=True)
        )

        model = SeasonalNaiveForecastModel(
            seasonal_periods=4,
        )

        model.fit(
            frame=frame,
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        result = model.predict(
            horizon=4,
            frequency="15min",
        )

        assert result.predictions["prediction"].tolist() == [
            110.0,
            210.0,
            310.0,
            410.0,
        ]

    def test_supports_timestamp_strings(self) -> None:
        frame = _training_frame()
        frame["timestamp"] = frame["timestamp"].astype(str)

        model = SeasonalNaiveForecastModel(
            seasonal_periods=4,
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

        assert result.predictions["prediction"].iloc[0] == pytest.approx(110.0)

    def test_rejects_empty_training_frame(self) -> None:
        model = SeasonalNaiveForecastModel(
            seasonal_periods=4,
        )

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
        model = SeasonalNaiveForecastModel(
            seasonal_periods=4,
        )

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
        model = SeasonalNaiveForecastModel(
            seasonal_periods=4,
        )

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
            "a",
            "b",
            "c",
            "d",
            "e",
            "f",
            "g",
            "h",
        ]

        model = SeasonalNaiveForecastModel(
            seasonal_periods=4,
        )

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

        model = SeasonalNaiveForecastModel(
            seasonal_periods=4,
        )

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

        model = SeasonalNaiveForecastModel(
            seasonal_periods=4,
        )

        with pytest.raises(
            ValueError,
            match=("Training target values must not contain missing values."),
        ):
            model.fit(
                frame=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )

    def test_rejects_insufficient_training_history(self) -> None:
        frame = _training_frame().iloc[:3].copy()

        model = SeasonalNaiveForecastModel(
            seasonal_periods=4,
        )

        with pytest.raises(
            ValueError,
            match=(
                "Training frame must contain at least seasonal_periods " "observations."
            ),
        ):
            model.fit(
                frame=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )


class TestSeasonalNaiveForecastModelPredict:
    """Tests for seasonal naive prediction."""

    def test_repeats_latest_seasonal_cycle(self) -> None:
        model = SeasonalNaiveForecastModel(
            seasonal_periods=4,
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

        assert result.predictions["prediction"].tolist() == [
            110.0,
            210.0,
            310.0,
            410.0,
        ]

    def test_repeats_cycle_for_horizon_longer_than_season(
        self,
    ) -> None:
        model = SeasonalNaiveForecastModel(
            seasonal_periods=4,
        )

        model.fit(
            frame=_training_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        result = model.predict(
            horizon=6,
            frequency="15min",
        )

        assert result.predictions["prediction"].tolist() == [
            110.0,
            210.0,
            310.0,
            410.0,
            110.0,
            210.0,
        ]

    def test_prediction_timestamps_follow_training_data(
        self,
    ) -> None:
        model = SeasonalNaiveForecastModel(
            seasonal_periods=4,
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

        expected = pd.to_datetime(
            [
                "2026-08-17T10:00:00Z",
                "2026-08-17T10:15:00Z",
                "2026-08-17T10:30:00Z",
            ],
            utc=True,
        )

        assert result.predictions["timestamp"].tolist() == list(expected)

    def test_result_metadata(self) -> None:
        model = SeasonalNaiveForecastModel(
            seasonal_periods=4,
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

        assert result.model_name == "Seasonal Naive"
        assert result.target_column == "active_power_kw"

    def test_predict_requires_fitted_model(self) -> None:
        model = SeasonalNaiveForecastModel(
            seasonal_periods=4,
        )

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
        model = SeasonalNaiveForecastModel(
            seasonal_periods=4,
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
        model = SeasonalNaiveForecastModel(
            seasonal_periods=4,
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
