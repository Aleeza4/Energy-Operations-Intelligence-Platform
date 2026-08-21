"""Anomaly alert generation for EOIP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import uuid4

import pandas as pd


class AnomalySeverity(StrEnum):
    """Supported anomaly alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class AnomalyAlert:
    """Standard EOIP anomaly alert record."""

    alert_id: str
    timestamp: datetime
    source: str
    metric: str
    observed_value: float
    score: float
    severity: AnomalySeverity
    message: str

    def __post_init__(self) -> None:
        """Validate anomaly alert."""
        if not self.alert_id.strip():
            raise ValueError("alert_id must not be empty.")

        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware.")

        if not self.source.strip():
            raise ValueError("source must not be empty.")

        if not self.metric.strip():
            raise ValueError("metric must not be empty.")

        if not self.message.strip():
            raise ValueError("message must not be empty.")


def severity_from_score(
    score: float,
) -> AnomalySeverity:
    """Map absolute anomaly score to severity."""
    absolute_score = abs(score)

    if absolute_score >= 5.0:
        return AnomalySeverity.CRITICAL

    if absolute_score >= 4.0:
        return AnomalySeverity.HIGH

    if absolute_score >= 3.0:
        return AnomalySeverity.MEDIUM

    return AnomalySeverity.LOW


def generate_anomaly_alerts(
    *,
    frame: pd.DataFrame,
    timestamp_column: str,
    metric_column: str,
    score_column: str,
    anomaly_column: str = "is_anomaly",
    source: str,
) -> list[AnomalyAlert]:
    """Generate anomaly alerts from flagged observations."""
    if frame.empty:
        return []

    if not timestamp_column.strip():
        raise ValueError("timestamp_column must not be empty.")

    if not metric_column.strip():
        raise ValueError("metric_column must not be empty.")

    if not score_column.strip():
        raise ValueError("score_column must not be empty.")

    if not anomaly_column.strip():
        raise ValueError("anomaly_column must not be empty.")

    if not source.strip():
        raise ValueError("source must not be empty.")

    required_columns = {
        timestamp_column,
        metric_column,
        score_column,
        anomaly_column,
    }

    missing_columns = sorted(required_columns - set(frame.columns))

    if missing_columns:
        raise ValueError(
            "Alert source frame is missing required columns: " f"{missing_columns}"
        )

    timestamps = pd.to_datetime(
        frame[timestamp_column],
        utc=True,
        errors="raise",
    )

    metric_values = frame[metric_column]
    scores = frame[score_column]
    anomaly_flags = frame[anomaly_column]

    if not pd.api.types.is_numeric_dtype(metric_values):
        raise TypeError("Metric column must contain numeric values.")

    if not pd.api.types.is_numeric_dtype(scores):
        raise TypeError("Score column must contain numeric values.")

    if not pd.api.types.is_bool_dtype(anomaly_flags):
        raise TypeError("Anomaly column must be boolean.")

    alerts: list[AnomalyAlert] = []

    for index in frame.index:
        if not bool(anomaly_flags.loc[index]):
            continue

        timestamp = timestamps.loc[index]
        observed_value = float(metric_values.loc[index])
        score = float(scores.loc[index])

        severity = severity_from_score(score)

        alerts.append(
            AnomalyAlert(
                alert_id=str(uuid4()),
                timestamp=timestamp.to_pydatetime(),
                source=source,
                metric=metric_column,
                observed_value=observed_value,
                score=score,
                severity=severity,
                message=(
                    f"Anomaly detected for {metric_column} " f"with score {score:.3f}."
                ),
            )
        )

    return alerts
