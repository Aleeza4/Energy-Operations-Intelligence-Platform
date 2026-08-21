"""Model evaluation utilities for EOIP predictive maintenance."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


@dataclass(frozen=True, slots=True)
class MaintenanceEvaluationResult:
    """Evaluation metrics for a failure-prediction model."""

    accuracy: float
    precision: float
    recall: float
    specificity: float
    f1_score: float
    roc_auc: float
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    sample_count: int

    def __post_init__(self) -> None:
        """Validate evaluation result."""
        metric_values = {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "specificity": self.specificity,
            "f1_score": self.f1_score,
            "roc_auc": self.roc_auc,
        }

        for name, value in metric_values.items():
            if not np.isfinite(value):
                raise ValueError(f"{name} must be finite.")

            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1.")

        count_values = {
            "true_positives": self.true_positives,
            "true_negatives": self.true_negatives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "sample_count": self.sample_count,
        }

        for name, value in count_values.items():
            if value < 0:
                raise ValueError(f"{name} must not be negative.")

        confusion_total = (
            self.true_positives
            + self.true_negatives
            + self.false_positives
            + self.false_negatives
        )

        if confusion_total != self.sample_count:
            raise ValueError("Confusion-matrix counts must equal sample_count.")


def evaluate_failure_predictions(
    *,
    actual: pd.Series,
    predicted: pd.Series,
    probabilities: pd.Series,
) -> MaintenanceEvaluationResult:
    """Evaluate binary failure predictions."""
    if actual.empty:
        raise ValueError("Actual failure labels must not be empty.")

    if predicted.empty:
        raise ValueError("Predicted failure labels must not be empty.")

    if probabilities.empty:
        raise ValueError("Failure probabilities must not be empty.")

    if not (len(actual) == len(predicted) == len(probabilities)):
        raise ValueError(
            "Actual labels, predictions, and probabilities "
            "must contain the same number of rows."
        )

    if actual.isna().any():
        raise ValueError("Actual failure labels must not contain missing values.")

    if predicted.isna().any():
        raise ValueError("Predicted failure labels must not contain missing values.")

    if probabilities.isna().any():
        raise ValueError("Failure probabilities must not contain missing values.")

    actual_binary = actual.astype(int)
    predicted_binary = predicted.astype(int)

    actual_classes = set(actual_binary.unique().tolist())

    predicted_classes = set(predicted_binary.unique().tolist())

    if not actual_classes.issubset({0, 1}):
        raise ValueError("Actual failure labels must contain only binary values.")

    if not predicted_classes.issubset({0, 1}):
        raise ValueError("Predicted failure labels must contain only binary values.")

    if len(actual_classes) < 2:
        raise ValueError("Actual failure labels must contain both classes.")

    if not pd.api.types.is_numeric_dtype(probabilities):
        raise TypeError("Failure probabilities must be numeric.")

    probability_values = probabilities.to_numpy(dtype=float)

    if not np.isfinite(probability_values).all():
        raise ValueError("Failure probabilities must contain only finite values.")

    if ((probability_values < 0.0) | (probability_values > 1.0)).any():
        raise ValueError("Failure probabilities must be between 0 and 1.")

    tn, fp, fn, tp = confusion_matrix(
        actual_binary,
        predicted_binary,
        labels=[
            0,
            1,
        ],
    ).ravel()

    specificity_denominator = int(tn) + int(fp)

    specificity = (
        int(tn) / specificity_denominator if specificity_denominator > 0 else 0.0
    )

    return MaintenanceEvaluationResult(
        accuracy=float(
            accuracy_score(
                actual_binary,
                predicted_binary,
            )
        ),
        precision=float(
            precision_score(
                actual_binary,
                predicted_binary,
                zero_division=0,
            )
        ),
        recall=float(
            recall_score(
                actual_binary,
                predicted_binary,
                zero_division=0,
            )
        ),
        specificity=float(specificity),
        f1_score=float(
            f1_score(
                actual_binary,
                predicted_binary,
                zero_division=0,
            )
        ),
        roc_auc=float(
            roc_auc_score(
                actual_binary,
                probability_values,
            )
        ),
        true_positives=int(tp),
        true_negatives=int(tn),
        false_positives=int(fp),
        false_negatives=int(fn),
        sample_count=len(actual_binary),
    )
