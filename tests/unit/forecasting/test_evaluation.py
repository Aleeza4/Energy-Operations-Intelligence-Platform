"""Unit tests for EOIP forecast evaluation metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from eoip.forecasting.evaluation import (
    ForecastMetrics,
    calculate_mae,
    calculate_mape,
    calculate_rmse,
    calculate_smape,
    evaluate_forecast,
)


class TestForecastMetrics:
    """Tests for forecast metric result validation."""

    def test_accepts_valid_metrics(self) -> None:
        result = ForecastMetrics(
            mae=10.0,
            rmse=12.0,
            mape=5.0,
            smape=6.0,
            sample_count=4,
        )

        assert result.mae == 10.0
        assert result.rmse == 12.0
        assert result.mape == 5.0
        assert result.smape == 6.0
        assert result.sample_count == 4

    def test_allows_none_mape(self) -> None:
        result = ForecastMetrics(
            mae=0.0,
            rmse=0.0,
            mape=None,
            smape=0.0,
            sample_count=1,
        )

        assert result.mape is None

    @pytest.mark.parametrize(
        (
            "field",
            "kwargs",
            "message",
        ),
        [
            (
                "mae",
                {
                    "mae": -1.0,
                    "rmse": 1.0,
                    "mape": 1.0,
                    "smape": 1.0,
                    "sample_count": 1,
                },
                "mae must not be negative.",
            ),
            (
                "rmse",
                {
                    "mae": 1.0,
                    "rmse": -1.0,
                    "mape": 1.0,
                    "smape": 1.0,
                    "sample_count": 1,
                },
                "rmse must not be negative.",
            ),
            (
                "mape",
                {
                    "mae": 1.0,
                    "rmse": 1.0,
                    "mape": -1.0,
                    "smape": 1.0,
                    "sample_count": 1,
                },
                "mape must not be negative.",
            ),
            (
                "smape",
                {
                    "mae": 1.0,
                    "rmse": 1.0,
                    "mape": 1.0,
                    "smape": -1.0,
                    "sample_count": 1,
                },
                "smape must not be negative.",
            ),
        ],
    )
    def test_rejects_negative_metric(
        self,
        field: str,
        kwargs: dict[str, object],
        message: str,
    ) -> None:
        del field

        with pytest.raises(
            ValueError,
            match=message,
        ):
            ForecastMetrics(**kwargs)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "sample_count",
        [
            0,
            -1,
            -10,
        ],
    )
    def test_rejects_non_positive_sample_count(
        self,
        sample_count: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="sample_count must be greater than zero.",
        ):
            ForecastMetrics(
                mae=1.0,
                rmse=1.0,
                mape=1.0,
                smape=1.0,
                sample_count=sample_count,
            )


class TestMetricFunctions:
    """Tests for individual forecast metric functions."""

    def test_calculates_mae(self) -> None:
        actual = np.array(
            [
                100.0,
                200.0,
                300.0,
            ]
        )
        predicted = np.array(
            [
                90.0,
                210.0,
                330.0,
            ]
        )

        result = calculate_mae(
            actual,
            predicted,
        )

        assert result == pytest.approx(
            16.6666666667,
        )

    def test_calculates_rmse(self) -> None:
        actual = np.array(
            [
                100.0,
                200.0,
                300.0,
            ]
        )
        predicted = np.array(
            [
                90.0,
                210.0,
                330.0,
            ]
        )

        result = calculate_rmse(
            actual,
            predicted,
        )

        expected = np.sqrt((10.0**2 + 10.0**2 + 30.0**2) / 3.0)

        assert result == pytest.approx(expected)

    def test_calculates_mape(self) -> None:
        actual = np.array(
            [
                100.0,
                200.0,
            ]
        )
        predicted = np.array(
            [
                90.0,
                220.0,
            ]
        )

        result = calculate_mape(
            actual,
            predicted,
        )

        assert result == pytest.approx(10.0)

    def test_mape_ignores_zero_actual_values(self) -> None:
        actual = np.array(
            [
                0.0,
                100.0,
            ]
        )
        predicted = np.array(
            [
                50.0,
                90.0,
            ]
        )

        result = calculate_mape(
            actual,
            predicted,
        )

        assert result == pytest.approx(10.0)

    def test_mape_returns_none_when_all_actuals_are_zero(
        self,
    ) -> None:
        actual = np.array(
            [
                0.0,
                0.0,
            ]
        )
        predicted = np.array(
            [
                10.0,
                20.0,
            ]
        )

        result = calculate_mape(
            actual,
            predicted,
        )

        assert result is None

    def test_calculates_smape(self) -> None:
        actual = np.array(
            [
                100.0,
                200.0,
            ]
        )
        predicted = np.array(
            [
                90.0,
                220.0,
            ]
        )

        result = calculate_smape(
            actual,
            predicted,
        )

        expected = ((2.0 * 10.0 / 190.0 + 2.0 * 20.0 / 420.0) / 2.0) * 100.0

        assert result == pytest.approx(expected)

    def test_smape_returns_zero_when_both_series_are_zero(
        self,
    ) -> None:
        actual = np.array(
            [
                0.0,
                0.0,
            ]
        )
        predicted = np.array(
            [
                0.0,
                0.0,
            ]
        )

        result = calculate_smape(
            actual,
            predicted,
        )

        assert result == pytest.approx(0.0)


class TestEvaluateForecast:
    """Tests for complete forecast evaluation."""

    def test_evaluates_forecast(self) -> None:
        actual = pd.Series(
            [
                100.0,
                200.0,
                300.0,
            ]
        )

        predicted = pd.Series(
            [
                90.0,
                210.0,
                330.0,
            ]
        )

        result = evaluate_forecast(
            actual=actual,
            predicted=predicted,
        )

        assert result.mae == pytest.approx(16.6666666667)
        assert result.rmse > result.mae
        assert result.mape is not None
        assert result.smape >= 0.0
        assert result.sample_count == 3

    def test_perfect_forecast_returns_zero_error(self) -> None:
        actual = pd.Series(
            [
                100.0,
                200.0,
                300.0,
            ]
        )

        result = evaluate_forecast(
            actual=actual,
            predicted=actual.copy(),
        )

        assert result.mae == pytest.approx(0.0)
        assert result.rmse == pytest.approx(0.0)
        assert result.mape == pytest.approx(0.0)
        assert result.smape == pytest.approx(0.0)

    def test_handles_zero_actual_values(self) -> None:
        result = evaluate_forecast(
            actual=pd.Series(
                [
                    0.0,
                    100.0,
                ]
            ),
            predicted=pd.Series(
                [
                    20.0,
                    90.0,
                ]
            ),
        )

        assert result.mape == pytest.approx(10.0)
        assert result.smape > 0.0

    def test_rejects_different_series_lengths(self) -> None:
        with pytest.raises(
            ValueError,
            match=("Actual and predicted series must have the same length."),
        ):
            evaluate_forecast(
                actual=pd.Series(
                    [
                        1.0,
                        2.0,
                    ]
                ),
                predicted=pd.Series(
                    [
                        1.0,
                    ]
                ),
            )

    def test_rejects_empty_series(self) -> None:
        with pytest.raises(
            ValueError,
            match=("Forecast evaluation requires at least one observation."),
        ):
            evaluate_forecast(
                actual=pd.Series(
                    [],
                    dtype=float,
                ),
                predicted=pd.Series(
                    [],
                    dtype=float,
                ),
            )

    def test_rejects_non_numeric_actuals(self) -> None:
        with pytest.raises(
            TypeError,
            match="Actual values must be numeric.",
        ):
            evaluate_forecast(
                actual=pd.Series(
                    [
                        "a",
                        "b",
                    ]
                ),
                predicted=pd.Series(
                    [
                        1.0,
                        2.0,
                    ]
                ),
            )

    def test_rejects_non_numeric_predictions(self) -> None:
        with pytest.raises(
            TypeError,
            match="Predicted values must be numeric.",
        ):
            evaluate_forecast(
                actual=pd.Series(
                    [
                        1.0,
                        2.0,
                    ]
                ),
                predicted=pd.Series(
                    [
                        "a",
                        "b",
                    ]
                ),
            )

    def test_rejects_missing_actual_values(self) -> None:
        with pytest.raises(
            ValueError,
            match=("Actual values must not contain missing values."),
        ):
            evaluate_forecast(
                actual=pd.Series(
                    [
                        1.0,
                        float("nan"),
                    ]
                ),
                predicted=pd.Series(
                    [
                        1.0,
                        2.0,
                    ]
                ),
            )

    def test_rejects_missing_prediction_values(self) -> None:
        with pytest.raises(
            ValueError,
            match=("Predicted values must not contain missing values."),
        ):
            evaluate_forecast(
                actual=pd.Series(
                    [
                        1.0,
                        2.0,
                    ]
                ),
                predicted=pd.Series(
                    [
                        1.0,
                        float("nan"),
                    ]
                ),
            )
