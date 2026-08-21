"""Unit tests for EOIP forecasting backtesting."""

from __future__ import annotations

import pandas as pd
import pytest

from eoip.forecasting.backtesting import (
    BacktestFoldResult,
    expanding_window_backtest,
)
from eoip.forecasting.models.naive import NaiveForecastModel


def _frame() -> pd.DataFrame:
    """Return deterministic time-series data for backtesting."""
    return pd.DataFrame(
        {
            "timestamp": pd.date_range(
                start="2026-08-17T00:00:00Z",
                periods=12,
                freq="15min",
            ),
            "active_power_kw": [
                100.0,
                110.0,
                120.0,
                130.0,
                140.0,
                150.0,
                160.0,
                170.0,
                180.0,
                190.0,
                200.0,
                210.0,
            ],
        }
    )


def _run_backtest() -> list[BacktestFoldResult]:
    """Run the standard test backtest."""
    return expanding_window_backtest(
        model_factory=NaiveForecastModel,
        frame=_frame(),
        timestamp_column="timestamp",
        target_column="active_power_kw",
        initial_train_size=6,
        horizon=2,
        step_size=2,
        frequency="15min",
    )


class TestBacktestFoldResult:
    """Tests for individual backtest fold results."""

    def test_accepts_valid_fold_result(self) -> None:
        results = _run_backtest()

        result = results[0]

        assert result.fold == 1
        assert len(result.actuals) == 2
        assert len(result.forecast.predictions) == 2

    def test_rejects_non_positive_fold(self) -> None:
        valid = _run_backtest()[0]

        with pytest.raises(
            ValueError,
            match="fold must be greater than zero.",
        ):
            BacktestFoldResult(
                fold=0,
                train_start=valid.train_start,
                train_end=valid.train_end,
                test_start=valid.test_start,
                test_end=valid.test_end,
                forecast=valid.forecast,
                actuals=valid.actuals,
            )

    def test_rejects_empty_actuals(self) -> None:
        valid = _run_backtest()[0]

        with pytest.raises(
            ValueError,
            match="Backtest actuals must not be empty.",
        ):
            BacktestFoldResult(
                fold=1,
                train_start=valid.train_start,
                train_end=valid.train_end,
                test_start=valid.test_start,
                test_end=valid.test_end,
                forecast=valid.forecast,
                actuals=pd.DataFrame(),
            )

    @pytest.mark.parametrize(
        "missing_column",
        [
            "timestamp",
            "actual",
        ],
    )
    def test_rejects_missing_actual_column(
        self,
        missing_column: str,
    ) -> None:
        valid = _run_backtest()[0]

        actuals = valid.actuals.drop(
            columns=[missing_column],
        )

        with pytest.raises(
            ValueError,
            match="Backtest actuals are missing required columns",
        ):
            BacktestFoldResult(
                fold=1,
                train_start=valid.train_start,
                train_end=valid.train_end,
                test_start=valid.test_start,
                test_end=valid.test_end,
                forecast=valid.forecast,
                actuals=actuals,
            )


class TestExpandingWindowBacktest:
    """Tests for expanding-window forecasting backtests."""

    def test_generates_expected_number_of_folds(self) -> None:
        results = _run_backtest()

        assert len(results) == 3

    def test_assigns_sequential_fold_numbers(self) -> None:
        results = _run_backtest()

        assert [result.fold for result in results] == [
            1,
            2,
            3,
        ]

    def test_training_window_expands(self) -> None:
        results = _run_backtest()

        assert results[0].train_start == pd.Timestamp("2026-08-17T00:00:00Z")
        assert results[0].train_end == pd.Timestamp("2026-08-17T01:15:00Z")

        assert results[1].train_start == pd.Timestamp("2026-08-17T00:00:00Z")
        assert results[1].train_end == pd.Timestamp("2026-08-17T01:45:00Z")

    def test_test_windows_follow_training_windows(self) -> None:
        results = _run_backtest()

        assert results[0].test_start == pd.Timestamp("2026-08-17T01:30:00Z")
        assert results[0].test_end == pd.Timestamp("2026-08-17T01:45:00Z")

        assert results[1].test_start == pd.Timestamp("2026-08-17T02:00:00Z")
        assert results[1].test_end == pd.Timestamp("2026-08-17T02:15:00Z")

    def test_preserves_actual_values(self) -> None:
        results = _run_backtest()

        assert results[0].actuals["actual"].tolist() == [
            160.0,
            170.0,
        ]

        assert results[1].actuals["actual"].tolist() == [
            180.0,
            190.0,
        ]

    def test_naive_forecast_uses_last_training_value(self) -> None:
        results = _run_backtest()

        assert results[0].forecast.predictions["prediction"].tolist() == [
            150.0,
            150.0,
        ]

        assert results[1].forecast.predictions["prediction"].tolist() == [
            170.0,
            170.0,
        ]

    def test_forecast_timestamps_align_with_actuals(self) -> None:
        results = _run_backtest()

        for result in results:
            forecast_timestamps = result.forecast.predictions["timestamp"].tolist()

            actual_timestamps = result.actuals["timestamp"].tolist()

            assert forecast_timestamps == actual_timestamps

    def test_sorts_input_before_backtesting(self) -> None:
        frame = _frame().sample(
            frac=1.0,
            random_state=42,
        )

        results = expanding_window_backtest(
            model_factory=NaiveForecastModel,
            frame=frame,
            timestamp_column="timestamp",
            target_column="active_power_kw",
            initial_train_size=6,
            horizon=2,
            step_size=2,
            frequency="15min",
        )

        assert results[0].train_start == pd.Timestamp("2026-08-17T00:00:00Z")

        assert results[0].actuals["actual"].tolist() == [
            160.0,
            170.0,
        ]

    def test_supports_timestamp_strings(self) -> None:
        frame = _frame()
        frame["timestamp"] = frame["timestamp"].astype(str)

        results = expanding_window_backtest(
            model_factory=NaiveForecastModel,
            frame=frame,
            timestamp_column="timestamp",
            target_column="active_power_kw",
            initial_train_size=6,
            horizon=2,
            step_size=2,
            frequency="15min",
        )

        assert len(results) == 3

    def test_rejects_empty_frame(self) -> None:
        with pytest.raises(
            ValueError,
            match="Backtest frame must not be empty.",
        ):
            expanding_window_backtest(
                model_factory=NaiveForecastModel,
                frame=pd.DataFrame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
                initial_train_size=6,
                horizon=2,
                step_size=2,
                frequency="15min",
            )

    def test_rejects_missing_timestamp_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Missing timestamp column: missing_timestamp",
        ):
            expanding_window_backtest(
                model_factory=NaiveForecastModel,
                frame=_frame(),
                timestamp_column="missing_timestamp",
                target_column="active_power_kw",
                initial_train_size=6,
                horizon=2,
                step_size=2,
                frequency="15min",
            )

    def test_rejects_missing_target_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Missing target column: missing_target",
        ):
            expanding_window_backtest(
                model_factory=NaiveForecastModel,
                frame=_frame(),
                timestamp_column="timestamp",
                target_column="missing_target",
                initial_train_size=6,
                horizon=2,
                step_size=2,
                frequency="15min",
            )

    @pytest.mark.parametrize(
        "initial_train_size",
        [
            0,
            -1,
            -10,
        ],
    )
    def test_rejects_non_positive_initial_train_size(
        self,
        initial_train_size: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="initial_train_size must be greater than zero.",
        ):
            expanding_window_backtest(
                model_factory=NaiveForecastModel,
                frame=_frame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
                initial_train_size=initial_train_size,
                horizon=2,
                step_size=2,
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
        with pytest.raises(
            ValueError,
            match="horizon must be greater than zero.",
        ):
            expanding_window_backtest(
                model_factory=NaiveForecastModel,
                frame=_frame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
                initial_train_size=6,
                horizon=horizon,
                step_size=2,
                frequency="15min",
            )

    @pytest.mark.parametrize(
        "step_size",
        [
            0,
            -1,
            -10,
        ],
    )
    def test_rejects_non_positive_step_size(
        self,
        step_size: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="step_size must be greater than zero.",
        ):
            expanding_window_backtest(
                model_factory=NaiveForecastModel,
                frame=_frame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
                initial_train_size=6,
                horizon=2,
                step_size=step_size,
                frequency="15min",
            )

    def test_rejects_empty_frequency(self) -> None:
        with pytest.raises(
            ValueError,
            match="frequency must not be empty.",
        ):
            expanding_window_backtest(
                model_factory=NaiveForecastModel,
                frame=_frame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
                initial_train_size=6,
                horizon=2,
                step_size=2,
                frequency=" ",
            )

    def test_rejects_insufficient_observations(self) -> None:
        with pytest.raises(
            ValueError,
            match=("Backtest frame does not contain enough observations"),
        ):
            expanding_window_backtest(
                model_factory=NaiveForecastModel,
                frame=_frame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
                initial_train_size=11,
                horizon=2,
                step_size=1,
                frequency="15min",
            )
