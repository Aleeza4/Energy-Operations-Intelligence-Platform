"""Unit tests for EOIP forecast model comparison utilities."""

from __future__ import annotations

import pandas as pd
import pytest

from eoip.forecasting.backtesting import expanding_window_backtest
from eoip.forecasting.comparison import (
    ModelEvaluationSummary,
    aggregate_backtest_metrics,
    evaluate_backtest_fold,
    rank_model_summaries,
)
from eoip.forecasting.models.naive import NaiveForecastModel


def _frame() -> pd.DataFrame:
    """Return deterministic time-series data for comparison tests."""
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


def _folds():
    """Return deterministic Naive-model backtest folds."""
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


class TestModelEvaluationSummary:
    """Tests for model evaluation summary validation."""

    def test_accepts_valid_summary(self) -> None:
        summary = ModelEvaluationSummary(
            model_name="Naive",
            mae=10.0,
            rmse=12.0,
            mape=5.0,
            smape=6.0,
            fold_count=3,
            sample_count=6,
        )

        assert summary.model_name == "Naive"
        assert summary.mae == 10.0
        assert summary.rmse == 12.0
        assert summary.mape == 5.0
        assert summary.smape == 6.0
        assert summary.fold_count == 3
        assert summary.sample_count == 6

    def test_allows_none_mape(self) -> None:
        summary = ModelEvaluationSummary(
            model_name="Naive",
            mae=0.0,
            rmse=0.0,
            mape=None,
            smape=0.0,
            fold_count=1,
            sample_count=1,
        )

        assert summary.mape is None

    def test_rejects_empty_model_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="model_name must not be empty.",
        ):
            ModelEvaluationSummary(
                model_name=" ",
                mae=1.0,
                rmse=1.0,
                mape=1.0,
                smape=1.0,
                fold_count=1,
                sample_count=1,
            )

    @pytest.mark.parametrize(
        ("field_name", "value", "message"),
        [
            ("mae", -1.0, "mae must not be negative."),
            ("rmse", -1.0, "rmse must not be negative."),
            ("mape", -1.0, "mape must not be negative."),
            ("smape", -1.0, "smape must not be negative."),
        ],
    )
    def test_rejects_negative_metric(
        self,
        field_name: str,
        value: float,
        message: str,
    ) -> None:
        kwargs = {
            "model_name": "Naive",
            "mae": 1.0,
            "rmse": 1.0,
            "mape": 1.0,
            "smape": 1.0,
            "fold_count": 1,
            "sample_count": 1,
        }

        kwargs[field_name] = value

        with pytest.raises(
            ValueError,
            match=message,
        ):
            ModelEvaluationSummary(**kwargs)

    @pytest.mark.parametrize(
        "fold_count",
        [
            0,
            -1,
        ],
    )
    def test_rejects_non_positive_fold_count(
        self,
        fold_count: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="fold_count must be greater than zero.",
        ):
            ModelEvaluationSummary(
                model_name="Naive",
                mae=1.0,
                rmse=1.0,
                mape=1.0,
                smape=1.0,
                fold_count=fold_count,
                sample_count=1,
            )

    @pytest.mark.parametrize(
        "sample_count",
        [
            0,
            -1,
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
            ModelEvaluationSummary(
                model_name="Naive",
                mae=1.0,
                rmse=1.0,
                mape=1.0,
                smape=1.0,
                fold_count=1,
                sample_count=sample_count,
            )


class TestEvaluateBacktestFold:
    """Tests for evaluation of individual backtest folds."""

    def test_evaluates_fold(self) -> None:
        fold = _folds()[0]

        metrics = evaluate_backtest_fold(fold)

        assert metrics.sample_count == 2
        assert metrics.mae > 0.0
        assert metrics.rmse >= metrics.mae
        assert metrics.smape >= 0.0


class TestAggregateBacktestMetrics:
    """Tests for aggregation of backtest metrics."""

    def test_aggregates_backtest_metrics(self) -> None:
        folds = _folds()

        summary = aggregate_backtest_metrics(
            folds=folds,
        )

        assert summary.model_name == "Naive"
        assert summary.fold_count == 3
        assert summary.sample_count == 6
        assert summary.mae > 0.0
        assert summary.rmse >= summary.mae
        assert summary.smape >= 0.0

    def test_rejects_empty_fold_list(self) -> None:
        with pytest.raises(
            ValueError,
            match="At least one backtest fold is required.",
        ):
            aggregate_backtest_metrics(
                folds=[],
            )

    def test_rejects_mixed_model_names(self) -> None:
        folds = _folds()

        first = folds[0]

        altered_forecast = type(first.forecast)(
            model_name="Different Model",
            target_column=first.forecast.target_column,
            predictions=first.forecast.predictions.copy(),
        )

        altered_fold = type(first)(
            fold=first.fold,
            train_start=first.train_start,
            train_end=first.train_end,
            test_start=first.test_start,
            test_end=first.test_end,
            forecast=altered_forecast,
            actuals=first.actuals.copy(),
        )

        with pytest.raises(
            ValueError,
            match=("All backtest folds must belong to the same model."),
        ):
            aggregate_backtest_metrics(
                folds=[
                    altered_fold,
                    *folds[1:],
                ],
            )


class TestRankModelSummaries:
    """Tests for forecast-model ranking."""

    def _summaries(self) -> list[ModelEvaluationSummary]:
        return [
            ModelEvaluationSummary(
                model_name="Model A",
                mae=20.0,
                rmse=25.0,
                mape=12.0,
                smape=11.0,
                fold_count=3,
                sample_count=10,
            ),
            ModelEvaluationSummary(
                model_name="Model B",
                mae=10.0,
                rmse=15.0,
                mape=8.0,
                smape=9.0,
                fold_count=3,
                sample_count=10,
            ),
            ModelEvaluationSummary(
                model_name="Model C",
                mae=30.0,
                rmse=35.0,
                mape=18.0,
                smape=16.0,
                fold_count=3,
                sample_count=10,
            ),
        ]

    def test_ranks_by_mae_by_default(self) -> None:
        ranked = rank_model_summaries(self._summaries())

        assert [summary.model_name for summary in ranked] == [
            "Model B",
            "Model A",
            "Model C",
        ]

    @pytest.mark.parametrize(
        "metric",
        [
            "mae",
            "rmse",
            "mape",
            "smape",
        ],
    )
    def test_ranks_supported_metrics(
        self,
        metric: str,
    ) -> None:
        ranked = rank_model_summaries(
            self._summaries(),
            metric=metric,
        )

        assert ranked[0].model_name == "Model B"

    def test_rejects_empty_summary_list(self) -> None:
        with pytest.raises(
            ValueError,
            match=("At least one model evaluation summary is required."),
        ):
            rank_model_summaries([])

    def test_rejects_unsupported_metric(self) -> None:
        with pytest.raises(
            ValueError,
            match="Unsupported ranking metric: accuracy",
        ):
            rank_model_summaries(
                self._summaries(),
                metric="accuracy",
            )

    def test_rejects_mape_ranking_when_mape_is_undefined(
        self,
    ) -> None:
        summaries = self._summaries()

        summaries[0] = ModelEvaluationSummary(
            model_name="Model A",
            mae=20.0,
            rmse=25.0,
            mape=None,
            smape=11.0,
            fold_count=3,
            sample_count=10,
        )

        with pytest.raises(
            ValueError,
            match=("Cannot rank by MAPE when a model has undefined MAPE."),
        ):
            rank_model_summaries(
                summaries,
                metric="mape",
            )
