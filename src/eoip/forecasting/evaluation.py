"""Forecast evaluation metrics for EOIP."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class ForecastMetrics:
    """Standard forecast evaluation metrics."""

    mae: float
    rmse: float
    mape: float | None
    smape: float
    sample_count: int
    wape: float | None = None
    bias: float | None = None
    prediction_interval_coverage: float | None = None

    def __post_init__(self) -> None:
        """Validate forecast metrics."""
        if self.mae < 0:
            raise ValueError("mae must not be negative.")

        if self.rmse < 0:
            raise ValueError("rmse must not be negative.")

        if self.mape is not None and self.mape < 0:
            raise ValueError("mape must not be negative.")

        if self.smape < 0:
            raise ValueError("smape must not be negative.")

        if self.sample_count < 1:
            raise ValueError("sample_count must be greater than zero.")

        if self.wape is not None and self.wape < 0:
            raise ValueError("wape must not be negative.")

        if self.prediction_interval_coverage is not None and not (
            0.0 <= self.prediction_interval_coverage <= 100.0
        ):
            raise ValueError("prediction_interval_coverage must be between 0 and 100.")


def calculate_mae(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> float:
    """Calculate mean absolute error."""
    return float(np.mean(np.abs(actual - predicted)))


def calculate_rmse(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> float:
    """Calculate root mean squared error."""
    return float(np.sqrt(np.mean(np.square(actual - predicted))))


def calculate_mape(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> float | None:
    """Calculate mean absolute percentage error.

    MAPE is undefined when every actual value is zero. Zero-valued
    actual observations are excluded from the calculation.
    """
    non_zero_mask = actual != 0

    if not np.any(non_zero_mask):
        return None

    percentage_errors = np.abs(
        (actual[non_zero_mask] - predicted[non_zero_mask]) / actual[non_zero_mask]
    )

    return float(np.mean(percentage_errors) * 100.0)


def calculate_smape(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> float:
    """Calculate symmetric mean absolute percentage error."""
    denominator = np.abs(actual) + np.abs(predicted)

    valid_mask = denominator != 0

    if not np.any(valid_mask):
        return 0.0

    errors = (
        2.0
        * np.abs(actual[valid_mask] - predicted[valid_mask])
        / denominator[valid_mask]
    )

    return float(np.mean(errors) * 100.0)


def calculate_wape(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    """Return weighted absolute percentage error as a percentage.

    WAPE is undefined when the sum of absolute actual values is zero.
    """
    denominator = float(np.sum(np.abs(actual)))
    if denominator == 0.0:
        return None
    return float(np.sum(np.abs(actual - predicted)) / denominator * 100.0)


def calculate_forecast_bias(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> float | None:
    """Return signed aggregate forecast bias as a percentage.

    Positive values mean over-forecasting and negative values mean
    under-forecasting. Bias is undefined when aggregate actual generation is
    zero.
    """
    denominator = float(np.sum(actual))
    if denominator == 0.0:
        return None
    return float(np.sum(predicted - actual) / denominator * 100.0)


def calculate_prediction_interval_coverage(
    *,
    actual: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
) -> float:
    """Return the percentage of observations inside inclusive intervals."""
    if not (len(actual) == len(lower) == len(upper)):
        raise ValueError("Actual, lower, and upper arrays must have the same length.")
    if len(actual) == 0:
        raise ValueError("Prediction interval coverage requires observations.")
    if not (
        np.isfinite(actual).all()
        and np.isfinite(lower).all()
        and np.isfinite(upper).all()
    ):
        raise ValueError("Prediction interval values must be finite.")
    if np.any(lower > upper):
        raise ValueError(
            "Prediction interval lower values must not exceed upper values."
        )
    return float(np.mean((actual >= lower) & (actual <= upper)) * 100.0)


def evaluate_forecast(
    *,
    actual: pd.Series,
    predicted: pd.Series,
    lower: pd.Series | None = None,
    upper: pd.Series | None = None,
) -> ForecastMetrics:
    """Evaluate predicted values against actual observations."""
    if len(actual) != len(predicted):
        raise ValueError("Actual and predicted series must have the same length.")

    if len(actual) < 1:
        raise ValueError("Forecast evaluation requires at least one observation.")

    if not pd.api.types.is_numeric_dtype(actual):
        raise TypeError("Actual values must be numeric.")

    if not pd.api.types.is_numeric_dtype(predicted):
        raise TypeError("Predicted values must be numeric.")

    if actual.isna().any():
        raise ValueError("Actual values must not contain missing values.")

    if predicted.isna().any():
        raise ValueError("Predicted values must not contain missing values.")

    actual_values = actual.to_numpy(dtype=float)
    predicted_values = predicted.to_numpy(dtype=float)

    if (lower is None) != (upper is None):
        raise ValueError("Both lower and upper prediction intervals are required.")

    interval_coverage = None
    if lower is not None and upper is not None:
        interval_coverage = calculate_prediction_interval_coverage(
            actual=actual_values,
            lower=lower.to_numpy(dtype=float),
            upper=upper.to_numpy(dtype=float),
        )

    return ForecastMetrics(
        mae=calculate_mae(
            actual_values,
            predicted_values,
        ),
        rmse=calculate_rmse(
            actual_values,
            predicted_values,
        ),
        mape=calculate_mape(
            actual_values,
            predicted_values,
        ),
        smape=calculate_smape(
            actual_values,
            predicted_values,
        ),
        sample_count=len(actual_values),
        wape=calculate_wape(actual_values, predicted_values),
        bias=calculate_forecast_bias(actual_values, predicted_values),
        prediction_interval_coverage=interval_coverage,
    )
