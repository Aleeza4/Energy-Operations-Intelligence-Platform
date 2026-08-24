"""Unit tests for EOIP forecasting feature engineering."""

from __future__ import annotations

import pandas as pd
import pytest

from eoip.forecasting.features import (
    add_lag_features,
    add_rolling_features,
    add_time_features,
    select_forecast_features,
)


def _frame() -> pd.DataFrame:
    """Return a valid forecasting feature frame."""
    return pd.DataFrame(
        {
            "timestamp": pd.date_range(
                start="2026-08-17T00:00:00Z",
                periods=8,
                freq="15min",
            ),
            "active_power_kw": [
                0.0,
                100.0,
                200.0,
                300.0,
                400.0,
                500.0,
                600.0,
                700.0,
            ],
            "ghi_wm2": [
                0.0,
                100.0,
                200.0,
                300.0,
                400.0,
                500.0,
                600.0,
                700.0,
            ],
        }
    )


class TestAddTimeFeatures:
    """Tests for deterministic time features."""

    def test_adds_expected_time_columns(self) -> None:
        result = add_time_features(
            _frame(),
            timestamp_column="timestamp",
        )

        expected = {
            "hour",
            "minute",
            "day_of_week",
            "day_of_month",
            "month",
            "day_of_year",
            "is_weekend",
        }

        assert expected.issubset(result.columns)

    def test_computes_hour_and_minute(self) -> None:
        result = add_time_features(
            _frame(),
            timestamp_column="timestamp",
        )

        assert result["hour"].tolist()[:4] == [
            0,
            0,
            0,
            0,
        ]

        assert result["minute"].tolist()[:4] == [
            0,
            15,
            30,
            45,
        ]

    def test_computes_calendar_features(self) -> None:
        result = add_time_features(
            _frame(),
            timestamp_column="timestamp",
        )

        first = result.iloc[0]

        assert first["day_of_month"] == 17
        assert first["month"] == 8
        assert first["day_of_year"] == 229

    def test_computes_weekend_flag(self) -> None:
        result = add_time_features(
            _frame(),
            timestamp_column="timestamp",
        )

        assert set(result["is_weekend"].unique()).issubset({0, 1})

    def test_converts_timestamp_strings(self) -> None:
        frame = _frame()
        frame["timestamp"] = frame["timestamp"].astype(str)

        result = add_time_features(
            frame,
            timestamp_column="timestamp",
        )

        assert pd.api.types.is_datetime64_any_dtype(result["timestamp"])

    def test_rejects_missing_timestamp_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Missing timestamp column: missing_timestamp",
        ):
            add_time_features(
                _frame(),
                timestamp_column="missing_timestamp",
            )

    def test_returns_independent_dataframe(self) -> None:
        frame = _frame()

        result = add_time_features(
            frame,
            timestamp_column="timestamp",
        )

        result.loc[0, "active_power_kw"] = 9999.0

        assert frame.loc[0, "active_power_kw"] == 0.0


class TestAddLagFeatures:
    """Tests for target lag features."""

    def test_adds_single_lag(self) -> None:
        result = add_lag_features(
            _frame(),
            target_column="active_power_kw",
            lags=[1],
        )

        assert "active_power_kw_lag_1" in result.columns
        assert pd.isna(result.loc[0, "active_power_kw_lag_1"])
        assert result.loc[1, "active_power_kw_lag_1"] == 0.0

    def test_adds_multiple_lags(self) -> None:
        result = add_lag_features(
            _frame(),
            target_column="active_power_kw",
            lags=[1, 2, 4],
        )

        assert "active_power_kw_lag_1" in result.columns
        assert "active_power_kw_lag_2" in result.columns
        assert "active_power_kw_lag_4" in result.columns

    def test_lag_values_are_shifted_correctly(self) -> None:
        result = add_lag_features(
            _frame(),
            target_column="active_power_kw",
            lags=[2],
        )

        assert result.loc[2, "active_power_kw_lag_2"] == 0.0
        assert result.loc[3, "active_power_kw_lag_2"] == 100.0

    def test_rejects_missing_target_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Missing target column: missing_target",
        ):
            add_lag_features(
                _frame(),
                target_column="missing_target",
                lags=[1],
            )

    def test_rejects_empty_lag_list(self) -> None:
        with pytest.raises(
            ValueError,
            match="At least one lag must be provided.",
        ):
            add_lag_features(
                _frame(),
                target_column="active_power_kw",
                lags=[],
            )

    @pytest.mark.parametrize(
        "lag",
        [
            0,
            -1,
            -10,
        ],
    )
    def test_rejects_non_positive_lag(
        self,
        lag: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="Lag values must be greater than zero.",
        ):
            add_lag_features(
                _frame(),
                target_column="active_power_kw",
                lags=[lag],
            )


class TestAddRollingFeatures:
    """Tests for rolling statistical features."""

    def test_adds_rolling_mean_and_std(self) -> None:
        result = add_rolling_features(
            _frame(),
            target_column="active_power_kw",
            windows=[2],
        )

        assert "active_power_kw_rolling_mean_2" in result.columns
        assert "active_power_kw_rolling_std_2" in result.columns

    def test_rolling_mean_uses_only_previous_values(self) -> None:
        result = add_rolling_features(
            _frame(),
            target_column="active_power_kw",
            windows=[2],
        )

        assert pd.isna(
            result.loc[
                0,
                "active_power_kw_rolling_mean_2",
            ]
        )
        assert pd.isna(
            result.loc[
                1,
                "active_power_kw_rolling_mean_2",
            ]
        )

        assert result.loc[
            2,
            "active_power_kw_rolling_mean_2",
        ] == pytest.approx(50.0)

    def test_rolling_std_uses_previous_values(self) -> None:
        result = add_rolling_features(
            _frame(),
            target_column="active_power_kw",
            windows=[2],
        )

        assert result.loc[
            2,
            "active_power_kw_rolling_std_2",
        ] == pytest.approx(70.710678, rel=1e-5)

    def test_supports_multiple_windows(self) -> None:
        result = add_rolling_features(
            _frame(),
            target_column="active_power_kw",
            windows=[2, 4],
        )

        assert "active_power_kw_rolling_mean_2" in result.columns
        assert "active_power_kw_rolling_mean_4" in result.columns

    def test_rejects_missing_target_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Missing target column: missing_target",
        ):
            add_rolling_features(
                _frame(),
                target_column="missing_target",
                windows=[2],
            )

    def test_rejects_empty_window_list(self) -> None:
        with pytest.raises(
            ValueError,
            match=("At least one rolling window must be provided."),
        ):
            add_rolling_features(
                _frame(),
                target_column="active_power_kw",
                windows=[],
            )

    @pytest.mark.parametrize(
        "window",
        [
            0,
            -1,
            -10,
        ],
    )
    def test_rejects_non_positive_window(
        self,
        window: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match=("Rolling windows must be greater than zero."),
        ):
            add_rolling_features(
                _frame(),
                target_column="active_power_kw",
                windows=[window],
            )


class TestSelectForecastFeatures:
    """Tests for final feature-frame selection."""

    def test_selects_requested_columns(self) -> None:
        frame = add_time_features(
            _frame(),
            timestamp_column="timestamp",
        )

        result = select_forecast_features(
            frame,
            timestamp_column="timestamp",
            target_column="active_power_kw",
            feature_columns=[
                "ghi_wm2",
                "hour",
            ],
        )

        assert list(result.columns) == [
            "timestamp",
            "active_power_kw",
            "ghi_wm2",
            "hour",
        ]

    def test_drops_missing_rows_by_default(self) -> None:
        frame = add_lag_features(
            _frame(),
            target_column="active_power_kw",
            lags=[1],
        )

        result = select_forecast_features(
            frame,
            timestamp_column="timestamp",
            target_column="active_power_kw",
            feature_columns=[
                "active_power_kw_lag_1",
            ],
        )

        assert len(result) == len(frame) - 1
        assert not result.isna().any().any()

    def test_can_preserve_missing_rows(self) -> None:
        frame = add_lag_features(
            _frame(),
            target_column="active_power_kw",
            lags=[1],
        )

        result = select_forecast_features(
            frame,
            timestamp_column="timestamp",
            target_column="active_power_kw",
            feature_columns=[
                "active_power_kw_lag_1",
            ],
            drop_missing=False,
        )

        assert len(result) == len(frame)
        assert result.isna().any().any()

    def test_rejects_missing_feature_column(self) -> None:
        with pytest.raises(
            ValueError,
            match=("Forecast feature frame is missing required columns"),
        ):
            select_forecast_features(
                _frame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
                feature_columns=[
                    "missing_feature",
                ],
            )

    def test_returns_independent_dataframe(self) -> None:
        frame = _frame()

        result = select_forecast_features(
            frame,
            timestamp_column="timestamp",
            target_column="active_power_kw",
            feature_columns=[
                "ghi_wm2",
            ],
        )

        result.loc[0, "ghi_wm2"] = 9999.0

        assert frame.loc[0, "ghi_wm2"] == 0.0
