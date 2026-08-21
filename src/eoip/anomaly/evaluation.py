"""Ground-truth evaluation utilities for EOIP anomaly detection."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class GroundTruthEvaluation:
    """Confusion-matrix result for anomaly detection."""

    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int

    @property
    def total(self) -> int:
        """Return total number of evaluated observations."""
        return (
            self.true_positives
            + self.true_negatives
            + self.false_positives
            + self.false_negatives
        )

    @property
    def actual_anomalies(self) -> int:
        """Return number of ground-truth anomalies."""
        return self.true_positives + self.false_negatives

    @property
    def predicted_anomalies(self) -> int:
        """Return number of predicted anomalies."""
        return self.true_positives + self.false_positives

    @property
    def correct_predictions(self) -> int:
        """Return number of correctly classified observations."""
        return self.true_positives + self.true_negatives

    @property
    def accuracy(self) -> float:
        """Return classification accuracy."""
        if self.total == 0:
            return 0.0

        return self.correct_predictions / self.total


def evaluate_ground_truth(
    *,
    frame: pd.DataFrame,
    predicted_column: str = "is_anomaly",
    ground_truth_column: str = "is_anomaly_ground_truth",
) -> GroundTruthEvaluation:
    """Evaluate predicted anomaly flags against ground truth."""
    if frame.empty:
        raise ValueError("Evaluation frame must not be empty.")

    if not predicted_column.strip():
        raise ValueError("predicted_column must not be empty.")

    if not ground_truth_column.strip():
        raise ValueError("ground_truth_column must not be empty.")

    if predicted_column not in frame.columns:
        raise ValueError(f"Missing predicted column: {predicted_column}")

    if ground_truth_column not in frame.columns:
        raise ValueError(f"Missing ground truth column: {ground_truth_column}")

    predicted = frame[predicted_column]
    ground_truth = frame[ground_truth_column]

    if predicted.isna().any():
        raise ValueError("Predicted anomaly column must not contain missing values.")

    if ground_truth.isna().any():
        raise ValueError("Ground truth anomaly column must not contain missing values.")

    if not pd.api.types.is_bool_dtype(predicted):
        raise TypeError("Predicted anomaly column must be boolean.")

    if not pd.api.types.is_bool_dtype(ground_truth):
        raise TypeError("Ground truth anomaly column must be boolean.")

    true_positives = int((predicted & ground_truth).sum())

    true_negatives = int((~predicted & ~ground_truth).sum())

    false_positives = int((predicted & ~ground_truth).sum())

    false_negatives = int((~predicted & ground_truth).sum())

    return GroundTruthEvaluation(
        true_positives=true_positives,
        true_negatives=true_negatives,
        false_positives=false_positives,
        false_negatives=false_negatives,
    )
