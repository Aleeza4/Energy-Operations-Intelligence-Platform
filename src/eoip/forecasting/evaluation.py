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


def evaluate_forecast(
    *,
    actual: pd.Series,
    predicted: pd.Series,
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
    )

    @property
    def precision(self) -> float:
        """Return anomaly detection precision."""
        denominator = self.true_positives + self.false_positives

        if denominator == 0:
            return 0.0

        return self.true_positives / denominator

    @property
    def recall(self) -> float:
        """Return anomaly detection recall."""
        denominator = self.true_positives + self.false_negatives

        if denominator == 0:
            return 0.0

        return self.true_positives / denominator

    @property
    def specificity(self) -> float:
        """Return true-negative rate."""
        denominator = self.true_negatives + self.false_positives

        if denominator == 0:
            return 0.0

        return self.true_negatives / denominator

    @property
    def f1_score(self) -> float:
        """Return harmonic mean of precision and recall."""
        denominator = (
            2 * self.true_positives + self.false_positives + self.false_negatives
        )

        if denominator == 0:
            return 0.0

        return 2 * self.true_positives / denominator
