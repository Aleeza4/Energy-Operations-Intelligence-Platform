"""Forecast model comparison utilities for EOIP."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import pandas as pd

from eoip.forecasting.backtesting import BacktestFoldResult
from eoip.forecasting.evaluation import ForecastMetrics, evaluate_forecast


@dataclass(frozen=True, slots=True)
class ModelEvaluationSummary:
    """Aggregated evaluation summary for one forecasting model."""

    model_name: str
    mae: float
    rmse: float
    mape: float | None
    smape: float
    fold_count: int
    sample_count: int

    def __post_init__(self) -> None:
        """Validate model evaluation summary."""
        if not self.model_name.strip():
            raise ValueError("model_name must not be empty.")

        if self.mae < 0:
            raise ValueError("mae must not be negative.")

        if self.rmse < 0:
            raise ValueError("rmse must not be negative.")

        if self.mape is not None and self.mape < 0:
            raise ValueError("mape must not be negative.")

        if self.smape < 0:
            raise ValueError("smape must not be negative.")

        if self.fold_count < 1:
            raise ValueError("fold_count must be greater than zero.")

        if self.sample_count < 1:
            raise ValueError("sample_count must be greater than zero.")


def evaluate_backtest_fold(
    fold: BacktestFoldResult,
) -> ForecastMetrics:
    """Evaluate one backtest fold."""
    actual = fold.actuals["actual"].reset_index(drop=True)

    predicted = fold.forecast.predictions["prediction"].reset_index(drop=True)

    return evaluate_forecast(
        actual=actual,
        predicted=predicted,
    )


def aggregate_backtest_metrics(
    *,
    folds: Iterable[BacktestFoldResult],
) -> ModelEvaluationSummary:
    """Aggregate forecast metrics across backtest folds."""
    fold_list = list(folds)

    if not fold_list:
        raise ValueError("At least one backtest fold is required.")

    model_names = {fold.forecast.model_name for fold in fold_list}

    if len(model_names) != 1:
        raise ValueError("All backtest folds must belong to the same model.")

    actual_values: list[float] = []
    predicted_values: list[float] = []

    for fold in fold_list:
        actual_values.extend(fold.actuals["actual"].astype(float).tolist())

        predicted_values.extend(
            fold.forecast.predictions["prediction"].astype(float).tolist()
        )

    metrics = evaluate_forecast(
        actual=pd.Series(
            actual_values,
            dtype=float,
        ),
        predicted=pd.Series(
            predicted_values,
            dtype=float,
        ),
    )

    return ModelEvaluationSummary(
        model_name=next(iter(model_names)),
        mae=metrics.mae,
        rmse=metrics.rmse,
        mape=metrics.mape,
        smape=metrics.smape,
        fold_count=len(fold_list),
        sample_count=metrics.sample_count,
    )


def rank_model_summaries(
    summaries: Iterable[ModelEvaluationSummary],
    *,
    metric: str = "mae",
) -> list[ModelEvaluationSummary]:
    """Rank model summaries from best to worst.

    Supported metrics are:

    - mae
    - rmse
    - mape
    - smape
    """
    summary_list = list(summaries)

    if not summary_list:
        raise ValueError("At least one model evaluation summary is required.")

    supported_metrics = {
        "mae",
        "rmse",
        "mape",
        "smape",
    }

    if metric not in supported_metrics:
        raise ValueError(f"Unsupported ranking metric: {metric}")

    if metric == "mape" and any(summary.mape is None for summary in summary_list):
        raise ValueError("Cannot rank by MAPE when a model has undefined MAPE.")

    return sorted(
        summary_list,
        key=lambda summary: (
            float("inf")
            if getattr(summary, metric) is None
            else float(getattr(summary, metric))
        ),
    )
