"""Equipment health scoring for EOIP predictive maintenance."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class HealthScoreWeights:
    """Weights used to calculate equipment health."""

    failure_probability: float = 0.35
    anomaly_rate: float = 0.20
    alarm_burden: float = 0.15
    temperature_stress: float = 0.15
    performance_loss: float = 0.15

    def __post_init__(self) -> None:
        """Validate scoring weights."""
        values = (
            self.failure_probability,
            self.anomaly_rate,
            self.alarm_burden,
            self.temperature_stress,
            self.performance_loss,
        )

        if any(not np.isfinite(value) for value in values):
            raise ValueError("Health score weights must be finite.")

        if any(value < 0 for value in values):
            raise ValueError("Health score weights must not be negative.")

        if not np.isclose(
            sum(values),
            1.0,
        ):
            raise ValueError("Health score weights must sum to 1.")


@dataclass(frozen=True, slots=True)
class EquipmentHealthResult:
    """Calculated equipment health result."""

    equipment_id: str
    health_score: float
    degradation_score: float

    def __post_init__(self) -> None:
        """Validate equipment health result."""
        if not self.equipment_id.strip():
            raise ValueError("equipment_id must not be empty.")

        if not 0.0 <= self.health_score <= 100.0:
            raise ValueError("health_score must be between 0 and 100.")

        if not 0.0 <= self.degradation_score <= 1.0:
            raise ValueError("degradation_score must be between 0 and 1.")


def calculate_equipment_health_score(
    *,
    equipment_id: str,
    failure_probability: float,
    anomaly_rate: float,
    alarm_burden: float,
    temperature_stress: float,
    performance_loss: float,
    weights: HealthScoreWeights | None = None,
) -> EquipmentHealthResult:
    """Calculate a normalized 0-100 equipment health score.

    Each degradation input must be normalized between 0 and 1.

    A degradation score of 0 represents no detected degradation.
    A degradation score of 1 represents maximum modeled degradation.

    Health score is calculated as:

        health = 100 * (1 - degradation_score)
    """
    if not equipment_id.strip():
        raise ValueError("equipment_id must not be empty.")

    inputs = {
        "failure_probability": failure_probability,
        "anomaly_rate": anomaly_rate,
        "alarm_burden": alarm_burden,
        "temperature_stress": temperature_stress,
        "performance_loss": performance_loss,
    }

    for name, value in inputs.items():
        if not np.isfinite(value):
            raise ValueError(f"{name} must be finite.")

        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be between 0 and 1.")

    active_weights = weights if weights is not None else HealthScoreWeights()

    degradation_score = (
        failure_probability * active_weights.failure_probability
        + anomaly_rate * active_weights.anomaly_rate
        + alarm_burden * active_weights.alarm_burden
        + temperature_stress * active_weights.temperature_stress
        + performance_loss * active_weights.performance_loss
    )

    degradation_score = float(
        np.clip(
            degradation_score,
            0.0,
            1.0,
        )
    )

    health_score = float(
        np.clip(
            100.0 * (1.0 - degradation_score),
            0.0,
            100.0,
        )
    )

    return EquipmentHealthResult(
        equipment_id=equipment_id,
        health_score=health_score,
        degradation_score=degradation_score,
    )


def calculate_health_scores(
    *,
    frame: pd.DataFrame,
    equipment_id_column: str = "equipment_id",
    failure_probability_column: str = "failure_probability",
    anomaly_rate_column: str = "anomaly_rate",
    alarm_burden_column: str = "alarm_burden",
    temperature_stress_column: str = "temperature_stress",
    performance_loss_column: str = "performance_loss",
    weights: HealthScoreWeights | None = None,
) -> pd.DataFrame:
    """Calculate health scores for multiple equipment assets."""
    if frame.empty:
        raise ValueError("Equipment health frame must not be empty.")

    required_columns = {
        equipment_id_column,
        failure_probability_column,
        anomaly_rate_column,
        alarm_burden_column,
        temperature_stress_column,
        performance_loss_column,
    }

    missing_columns = sorted(required_columns - set(frame.columns))

    if missing_columns:
        raise ValueError(
            "Equipment health frame is missing required columns: " f"{missing_columns}"
        )

    result = frame.copy(deep=True)

    health_scores: list[float] = []
    degradation_scores: list[float] = []

    for row in result.itertuples(
        index=False,
    ):
        health = calculate_equipment_health_score(
            equipment_id=str(
                getattr(
                    row,
                    equipment_id_column,
                )
            ),
            failure_probability=float(
                getattr(
                    row,
                    failure_probability_column,
                )
            ),
            anomaly_rate=float(
                getattr(
                    row,
                    anomaly_rate_column,
                )
            ),
            alarm_burden=float(
                getattr(
                    row,
                    alarm_burden_column,
                )
            ),
            temperature_stress=float(
                getattr(
                    row,
                    temperature_stress_column,
                )
            ),
            performance_loss=float(
                getattr(
                    row,
                    performance_loss_column,
                )
            ),
            weights=weights,
        )

        health_scores.append(health.health_score)

        degradation_scores.append(health.degradation_score)

    result["health_score"] = health_scores
    result["degradation_score"] = degradation_scores

    return result
