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
    component_contributions: tuple[tuple[str, float], ...] = ()
    confidence_score: float = 1.0
    trend_direction: str = "stable"
    trend_score: float = 0.0

    def __post_init__(self) -> None:
        """Validate equipment health result."""
        if not self.equipment_id.strip():
            raise ValueError("equipment_id must not be empty.")

        if not 0.0 <= self.health_score <= 100.0:
            raise ValueError("health_score must be between 0 and 100.")

        if not 0.0 <= self.degradation_score <= 1.0:
            raise ValueError("degradation_score must be between 0 and 1.")

        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("confidence_score must be between 0 and 1.")

        if self.trend_direction not in {"improving", "stable", "degrading"}:
            raise ValueError(
                "trend_direction must be one of: improving, stable, degrading."
            )

        if not -1.0 <= self.trend_score <= 1.0:
            raise ValueError("trend_score must be between -1 and 1.")

        if self.component_contributions:
            contribution_total = sum(value for _, value in self.component_contributions)
            if not np.isclose(contribution_total, self.degradation_score):
                raise ValueError(
                    "component contributions must sum to degradation_score."
                )


def _calculate_health_trend(
    history: list[float] | tuple[float, ...] | None,
) -> tuple[str, float]:
    """Return a qualitative trend direction and a bounded numeric trend score."""
    if history is None or len(history) < 2:
        return "stable", 0.0

    ordered = np.asarray(history, dtype=float)

    if not np.isfinite(ordered).all():
        raise ValueError("health history values must be finite.")

    start_value = float(ordered[0])
    end_value = float(ordered[-1])
    delta = end_value - start_value
    scale = max(abs(start_value), abs(end_value), 1.0)
    trend_score = float(np.clip(delta / scale, -1.0, 1.0))

    if trend_score > 0.05:
        return "improving", trend_score

    if trend_score < -0.05:
        return "degrading", trend_score

    return "stable", 0.0


def calculate_equipment_health_score(
    *,
    equipment_id: str,
    failure_probability: float,
    anomaly_rate: float,
    alarm_burden: float,
    temperature_stress: float,
    performance_loss: float,
    weights: HealthScoreWeights | None = None,
    history: list[float] | tuple[float, ...] | None = None,
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

    component_contributions = (
        (
            "failure_probability",
            failure_probability * active_weights.failure_probability,
        ),
        ("anomaly_rate", anomaly_rate * active_weights.anomaly_rate),
        ("alarm_burden", alarm_burden * active_weights.alarm_burden),
        (
            "temperature_stress",
            temperature_stress * active_weights.temperature_stress,
        ),
        ("performance_loss", performance_loss * active_weights.performance_loss),
    )
    degradation_score = sum(value for _, value in component_contributions)

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

    confidence_score = float(np.clip(1.0 - degradation_score, 0.0, 1.0))
    trend_direction, trend_score = _calculate_health_trend(history)

    return EquipmentHealthResult(
        equipment_id=equipment_id,
        health_score=health_score,
        degradation_score=degradation_score,
        component_contributions=tuple(
            (name, float(value)) for name, value in component_contributions
        ),
        confidence_score=confidence_score,
        trend_direction=trend_direction,
        trend_score=trend_score,
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
    history_column: str | None = None,
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
    confidence_scores: list[float] = []
    trend_directions: list[str] = []
    trend_scores: list[float] = []
    component_values: dict[str, list[float]] = {
        "failure_probability_contribution": [],
        "anomaly_rate_contribution": [],
        "alarm_burden_contribution": [],
        "temperature_stress_contribution": [],
        "performance_loss_contribution": [],
    }

    for row in result.itertuples(
        index=False,
    ):
        history = None
        if history_column is not None and hasattr(row, history_column):
            raw_history = getattr(row, history_column)
            if raw_history is not None:
                history = raw_history

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
            history=history,
        )

        health_scores.append(health.health_score)
        degradation_scores.append(health.degradation_score)
        confidence_scores.append(health.confidence_score)
        trend_directions.append(health.trend_direction)
        trend_scores.append(health.trend_score)
        for name, value in health.component_contributions:
            component_values[f"{name}_contribution"].append(value)

    result["health_score"] = health_scores
    result["degradation_score"] = degradation_scores
    result["confidence_score"] = confidence_scores
    result["trend_direction"] = trend_directions
    result["trend_score"] = trend_scores
    for column, values in component_values.items():
        result[column] = values

    return result
