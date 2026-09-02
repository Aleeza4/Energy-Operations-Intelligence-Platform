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

    @property
    def precision(self) -> float:
        """Return precision, using zero when no anomaly was predicted."""
        denominator = self.true_positives + self.false_positives
        return self.true_positives / denominator if denominator else 0.0

    @property
    def recall(self) -> float:
        """Return recall, using zero when no positive truth exists."""
        denominator = self.true_positives + self.false_negatives
        return self.true_positives / denominator if denominator else 0.0

    @property
    def f1_score(self) -> float:
        """Return the harmonic mean of precision and recall."""
        denominator = (
            2 * self.true_positives + self.false_positives + self.false_negatives
        )
        return 2 * self.true_positives / denominator if denominator else 0.0


@dataclass(frozen=True, slots=True)
class DetectionDelayEvaluation:
    """Event-level delay statistics in minutes."""

    detected_event_count: int
    eligible_event_count: int
    mean_minutes: float | None
    median_minutes: float | None
    p95_minutes: float | None


def calculate_critical_recall(
    *,
    frame: pd.DataFrame,
    severity_column: str = "severity",
    predicted_column: str = "is_anomaly",
    ground_truth_column: str = "is_anomaly_ground_truth",
) -> float | None:
    """Return recall restricted to critical ground-truth observations."""
    required = {severity_column, predicted_column, ground_truth_column}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Critical recall frame is missing columns: {missing}")
    critical_truth = frame[ground_truth_column] & frame[severity_column].astype(
        str
    ).str.casefold().eq("critical")
    denominator = int(critical_truth.sum())
    if denominator == 0:
        return None
    return float((frame[predicted_column] & critical_truth).sum() / denominator)


def calculate_asset_days(
    *,
    exposure: pd.DataFrame,
    asset_column: str = "asset_id",
    start_column: str = "exposure_start",
    end_column: str = "exposure_end",
) -> float | None:
    """Sum explicit per-asset exposure intervals in 24-hour asset-days."""
    required = {asset_column, start_column, end_column}
    missing = sorted(required - set(exposure.columns))
    if missing:
        return None
    if exposure.empty:
        return None
    starts = pd.to_datetime(exposure[start_column], utc=True, errors="raise")
    ends = pd.to_datetime(exposure[end_column], utc=True, errors="raise")
    if (ends <= starts).any() or exposure[asset_column].isna().any():
        raise ValueError(
            "Asset exposure intervals require an asset and end after start."
        )
    return float((ends - starts).dt.total_seconds().sum() / 86_400.0)


def calculate_false_alerts_per_asset_day(
    *, false_positive_count: int, evaluated_asset_days: float | None
) -> float | None:
    """Return false-positive alerts divided by explicit asset exposure."""
    if false_positive_count < 0:
        raise ValueError("false_positive_count must not be negative.")
    if evaluated_asset_days is None:
        return None
    if evaluated_asset_days <= 0.0:
        raise ValueError("evaluated_asset_days must be positive.")
    return false_positive_count / evaluated_asset_days


def evaluate_detection_delay(
    *,
    events: pd.DataFrame,
    detections: pd.DataFrame,
    event_id_column: str = "event_id",
    event_start_column: str = "started_at",
    detection_time_column: str = "detected_at",
) -> DetectionDelayEvaluation:
    """Match detections by event ID and evaluate the earliest valid detection."""
    event_required = {event_id_column, event_start_column}
    detection_required = {event_id_column, detection_time_column}
    if event_required - set(events.columns) or detection_required - set(
        detections.columns
    ):
        raise ValueError("Detection delay requires event IDs and timestamps.")
    starts = events[[event_id_column, event_start_column]].copy()
    starts[event_start_column] = pd.to_datetime(
        starts[event_start_column], utc=True, errors="raise"
    )
    observed = detections[[event_id_column, detection_time_column]].copy()
    observed[detection_time_column] = pd.to_datetime(
        observed[detection_time_column], utc=True, errors="raise"
    )
    merged = starts.merge(observed, on=event_id_column, how="left")
    merged = merged.loc[merged[detection_time_column] >= merged[event_start_column]]
    merged = merged.sort_values(detection_time_column)
    earliest = merged.groupby(event_id_column, as_index=False).first()
    delays = (
        earliest[detection_time_column] - earliest[event_start_column]
    ).dt.total_seconds() / 60.0
    if delays.empty:
        return DetectionDelayEvaluation(0, len(starts), None, None, None)
    return DetectionDelayEvaluation(
        detected_event_count=len(delays),
        eligible_event_count=len(starts),
        mean_minutes=float(delays.mean()),
        median_minutes=float(delays.median()),
        p95_minutes=float(delays.quantile(0.95, interpolation="linear")),
    )


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
