"""Model evaluation utilities for EOIP predictive maintenance."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
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
    pr_auc: float | None = None
    top_five_percent_recall: float | None = None
    top_five_percent_count: int = 0
    brier_score: float | None = None
    calibration_bins: tuple[dict[str, float | int], ...] = ()

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

        if self.pr_auc is not None and not 0.0 <= self.pr_auc <= 1.0:
            raise ValueError("pr_auc must be between 0 and 1.")

        if self.top_five_percent_recall is not None and not (
            0.0 <= self.top_five_percent_recall <= 1.0
        ):
            raise ValueError("top_five_percent_recall must be between 0 and 1.")

        if self.brier_score is not None and not 0.0 <= self.brier_score <= 1.0:
            raise ValueError("brier_score must be between 0 and 1.")


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

    top_recall, top_count = calculate_top_risk_recall(
        actual=actual_binary,
        probabilities=probabilities,
        fraction=0.05,
    )
    calibration_bins = calculate_calibration_bins(
        actual=actual_binary,
        probabilities=probabilities,
    )

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
        pr_auc=float(average_precision_score(actual_binary, probability_values)),
        top_five_percent_recall=top_recall,
        top_five_percent_count=top_count,
        brier_score=float(brier_score_loss(actual_binary, probability_values)),
        calibration_bins=calibration_bins,
    )


def calculate_top_risk_recall(
    *, actual: pd.Series, probabilities: pd.Series, fraction: float = 0.05
) -> tuple[float | None, int]:
    """Return positive recall captured by the highest-risk fraction.

    The cohort size is ``ceil(n * fraction)`` with a minimum of one. Risk ties
    retain stable input order, so ties do not silently expand the cohort.
    """
    if len(actual) != len(probabilities) or actual.empty:
        raise ValueError(
            "Actual labels and probabilities require equal non-zero length."
        )
    if not 0.0 < fraction <= 1.0:
        raise ValueError("fraction must be greater than zero and at most one.")
    positive_count = int(actual.astype(int).sum())
    cohort_count = max(1, int(np.ceil(len(actual) * fraction)))
    if positive_count == 0:
        return None, cohort_count
    ranked = pd.DataFrame(
        {"actual": actual.astype(int).to_numpy(), "risk": probabilities.to_numpy()}
    ).sort_values("risk", ascending=False, kind="stable")
    captured = int(ranked.head(cohort_count)["actual"].sum())
    return captured / positive_count, cohort_count


def calculate_calibration_bins(
    *, actual: pd.Series, probabilities: pd.Series, bin_count: int = 10
) -> tuple[dict[str, float | int], ...]:
    """Return observed and predicted event rates for fixed-width bins."""
    if len(actual) != len(probabilities) or actual.empty:
        raise ValueError("Calibration inputs require equal non-zero length.")
    if bin_count < 2:
        raise ValueError("bin_count must be at least two.")
    frame = pd.DataFrame(
        {
            "actual": actual.astype(int).to_numpy(),
            "probability": probabilities.to_numpy(dtype=float),
        }
    )
    edges = np.linspace(0.0, 1.0, bin_count + 1)
    frame["bin"] = pd.cut(
        frame["probability"], bins=edges, include_lowest=True, right=True
    )
    records: list[dict[str, float | int]] = []
    for interval, group in frame.groupby("bin", observed=True):
        records.append(
            {
                "lower": float(interval.left),
                "upper": float(interval.right),
                "count": len(group),
                "mean_predicted_probability": float(group["probability"].mean()),
                "observed_event_rate": float(group["actual"].mean()),
            }
        )
    return tuple(records)
