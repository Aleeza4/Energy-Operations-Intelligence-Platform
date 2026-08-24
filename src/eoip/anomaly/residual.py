"""Residual-based anomaly analysis for EOIP."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class ResidualAnalysisResult:
    """Result produced by residual anomaly analysis."""

    data: pd.DataFrame
    actual_column: str
    expected_column: str
    threshold: float

    @property
    def row_count(self) -> int:
        """Return number of evaluated observations."""
        return len(self.data)

    @property
    def anomaly_count(self) -> int:
        """Return number of detected anomalies."""
        return int(self.data["is_anomaly"].sum())

    @property
    def anomaly_rate(self) -> float:
        """Return proportion of anomalous observations."""
        if self.row_count == 0:
            return 0.0

        return self.anomaly_count / self.row_count

    def anomalies(self) -> pd.DataFrame:
        """Return only anomalous observations."""
        return self.data.loc[self.data["is_anomaly"]].copy(deep=True)


def analyze_residuals(
    *,
    frame: pd.DataFrame,
    actual_column: str,
    expected_column: str,
    threshold: float,
) -> ResidualAnalysisResult:
    """Analyze actual-minus-expected residuals.

    Residuals are calculated as:

        actual - expected

    An observation is classified as anomalous when its absolute
    residual exceeds the configured threshold.
    """
    if frame.empty:
        raise ValueError("Residual analysis frame must not be empty.")

    if not actual_column.strip():
        raise ValueError("actual_column must not be empty.")

    if not expected_column.strip():
        raise ValueError("expected_column must not be empty.")

    if actual_column not in frame.columns:
        raise ValueError(f"Missing actual column: {actual_column}")

    if expected_column not in frame.columns:
        raise ValueError(f"Missing expected column: {expected_column}")

    if not np.isfinite(threshold):
        raise ValueError("threshold must be finite.")

    if threshold <= 0:
        raise ValueError("threshold must be greater than zero.")

    actual = frame[actual_column]
    expected = frame[expected_column]

    if not pd.api.types.is_numeric_dtype(actual):
        raise TypeError("Actual column must contain numeric values.")

    if not pd.api.types.is_numeric_dtype(expected):
        raise TypeError("Expected column must contain numeric values.")

    if actual.isna().any():
        raise ValueError("Actual column must not contain missing values.")

    if expected.isna().any():
        raise ValueError("Expected column must not contain missing values.")

    actual_values = actual.to_numpy(dtype=float)

    expected_values = expected.to_numpy(dtype=float)

    if not np.isfinite(actual_values).all():
        raise ValueError("Actual values must be finite.")

    if not np.isfinite(expected_values).all():
        raise ValueError("Expected values must be finite.")

    residuals = actual_values - expected_values

    absolute_residuals = np.abs(residuals)

    result = frame.copy(deep=True)

    result["residual"] = residuals
    result["absolute_residual"] = absolute_residuals
    result["is_anomaly"] = absolute_residuals > threshold

    return ResidualAnalysisResult(
        data=result,
        actual_column=actual_column,
        expected_column=expected_column,
        threshold=float(threshold),
    )
