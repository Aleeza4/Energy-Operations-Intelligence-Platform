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
    wape: float | None = None
    bias: float | None = None
    prediction_interval_coverage: float | None = None

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


def calculate_error_improvement(
    *, baseline_error: float | None, candidate_error: float | None
) -> float | None:
    """Return candidate improvement over baseline as a percentage."""
    if baseline_error is None or candidate_error is None or baseline_error == 0.0:
        return None
    if baseline_error < 0.0 or candidate_error < 0.0:
        raise ValueError("Error metrics must not be negative.")
    return (baseline_error - candidate_error) / baseline_error * 100.0


@dataclass(frozen=True, slots=True)
class ForecastBaselineComparison:
    """Like-for-like candidate and baseline backtest comparison."""

    candidate: ModelEvaluationSummary
    baseline: ModelEvaluationSummary
    mae_improvement: float | None
    rmse_improvement: float | None
    wape_improvement: float | None


def compare_model_summaries(
    *, candidate: ModelEvaluationSummary, baseline: ModelEvaluationSummary
) -> ForecastBaselineComparison:
    """Compare summaries evaluated over an identical population."""
    if (
        candidate.fold_count != baseline.fold_count
        or candidate.sample_count != baseline.sample_count
    ):
        raise ValueError("Candidate and baseline evaluation populations must match.")
    return ForecastBaselineComparison(
        candidate=candidate,
        baseline=baseline,
        mae_improvement=calculate_error_improvement(
            baseline_error=baseline.mae, candidate_error=candidate.mae
        ),
        rmse_improvement=calculate_error_improvement(
            baseline_error=baseline.rmse, candidate_error=candidate.rmse
        ),
        wape_improvement=calculate_error_improvement(
            baseline_error=baseline.wape, candidate_error=candidate.wape
        ),
    )


def evaluate_backtest_fold(
    fold: BacktestFoldResult,
) -> ForecastMetrics:
    """Evaluate one backtest fold."""
    actual = fold.actuals["actual"].reset_index(drop=True)

    predicted = fold.forecast.predictions["prediction"].reset_index(drop=True)

    predictions = fold.forecast.predictions
    lower = (
        predictions["lower_bound"].reset_index(drop=True)
        if "lower_bound" in predictions
        else None
    )
    upper = (
        predictions["upper_bound"].reset_index(drop=True)
        if "upper_bound" in predictions
        else None
    )
    return evaluate_forecast(
        actual=actual,
        predicted=predicted,
        lower=lower,
        upper=upper,
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
    lower_values: list[float] = []
    upper_values: list[float] = []
    all_folds_have_intervals = all(
        {"lower_bound", "upper_bound"}.issubset(fold.forecast.predictions.columns)
        for fold in fold_list
    )

    for fold in fold_list:
        actual_values.extend(fold.actuals["actual"].astype(float).tolist())

        predicted_values.extend(
            fold.forecast.predictions["prediction"].astype(float).tolist()
        )
        if all_folds_have_intervals:
            lower_values.extend(
                fold.forecast.predictions["lower_bound"].astype(float).tolist()
            )
            upper_values.extend(
                fold.forecast.predictions["upper_bound"].astype(float).tolist()
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
        lower=(
            pd.Series(lower_values, dtype=float) if all_folds_have_intervals else None
        ),
        upper=(
            pd.Series(upper_values, dtype=float) if all_folds_have_intervals else None
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
        wape=metrics.wape,
        bias=metrics.bias,
        prediction_interval_coverage=metrics.prediction_interval_coverage,
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
    - wape
    """
    summary_list = list(summaries)

    if not summary_list:
        raise ValueError("At least one model evaluation summary is required.")

    supported_metrics = {
        "mae",
        "rmse",
        "mape",
        "smape",
        "wape",
    }

    if metric not in supported_metrics:
        raise ValueError(f"Unsupported ranking metric: {metric}")

    if metric in {"mape", "wape"} and any(
        getattr(summary, metric) is None for summary in summary_list
    ):
        if metric == "mape":
            raise ValueError("Cannot rank by MAPE when a model has undefined MAPE.")
        raise ValueError(
            f"Cannot rank by {metric.upper()} when a model has an undefined value."
        )

    return sorted(
        summary_list,
        key=lambda summary: (
            float("inf")
            if getattr(summary, metric) is None
            else float(getattr(summary, metric))
        ),
    )
