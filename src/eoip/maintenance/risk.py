"""Risk classification for EOIP predictive maintenance."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np
import pandas as pd


class MaintenanceRiskLevel(StrEnum):
    """Supported predictive-maintenance risk levels."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class MaintenanceRiskResult:
    """Risk classification result for one equipment asset."""

    equipment_id: str
    health_score: float
    failure_probability: float
    risk_score: float
    risk_level: MaintenanceRiskLevel

    def __post_init__(self) -> None:
        """Validate maintenance risk result."""
        if not self.equipment_id.strip():
            raise ValueError("equipment_id must not be empty.")

        if not 0.0 <= self.health_score <= 100.0:
            raise ValueError("health_score must be between 0 and 100.")

        if not 0.0 <= self.failure_probability <= 1.0:
            raise ValueError("failure_probability must be between 0 and 1.")

        if not 0.0 <= self.risk_score <= 1.0:
            raise ValueError("risk_score must be between 0 and 1.")


def classify_risk_score(
    risk_score: float,
) -> MaintenanceRiskLevel:
    """Convert normalized risk score into an operational risk level."""
    if not np.isfinite(risk_score):
        raise ValueError("risk_score must be finite.")

    if not 0.0 <= risk_score <= 1.0:
        raise ValueError("risk_score must be between 0 and 1.")

    if risk_score >= 0.75:
        return MaintenanceRiskLevel.CRITICAL

    if risk_score >= 0.50:
        return MaintenanceRiskLevel.HIGH

    if risk_score >= 0.25:
        return MaintenanceRiskLevel.MODERATE

    return MaintenanceRiskLevel.LOW


def classify_equipment_risk(
    *,
    equipment_id: str,
    health_score: float,
    failure_probability: float,
    health_weight: float = 0.40,
    failure_probability_weight: float = 0.60,
) -> MaintenanceRiskResult:
    """Classify predictive-maintenance risk for one equipment asset."""
    if not equipment_id.strip():
        raise ValueError("equipment_id must not be empty.")

    values = {
        "health_score": health_score,
        "failure_probability": failure_probability,
        "health_weight": health_weight,
        "failure_probability_weight": failure_probability_weight,
    }

    for name, value in values.items():
        if not np.isfinite(value):
            raise ValueError(f"{name} must be finite.")

    if not 0.0 <= health_score <= 100.0:
        raise ValueError("health_score must be between 0 and 100.")

    if not 0.0 <= failure_probability <= 1.0:
        raise ValueError("failure_probability must be between 0 and 1.")

    if health_weight < 0:
        raise ValueError("health_weight must not be negative.")

    if failure_probability_weight < 0:
        raise ValueError("failure_probability_weight must not be negative.")

    if not np.isclose(
        health_weight + failure_probability_weight,
        1.0,
    ):
        raise ValueError("Risk classification weights must sum to 1.")

    health_risk = 1.0 - (health_score / 100.0)

    risk_score = (
        health_risk * health_weight + failure_probability * failure_probability_weight
    )

    risk_score = float(
        np.clip(
            risk_score,
            0.0,
            1.0,
        )
    )

    return MaintenanceRiskResult(
        equipment_id=equipment_id,
        health_score=float(health_score),
        failure_probability=float(failure_probability),
        risk_score=risk_score,
        risk_level=classify_risk_score(risk_score),
    )


def classify_equipment_risks(
    *,
    frame: pd.DataFrame,
    equipment_id_column: str = "equipment_id",
    health_score_column: str = "health_score",
    failure_probability_column: str = "failure_probability",
    health_weight: float = 0.40,
    failure_probability_weight: float = 0.60,
) -> pd.DataFrame:
    """Classify predictive-maintenance risk for multiple assets."""
    if frame.empty:
        raise ValueError("Maintenance risk frame must not be empty.")

    required_columns = {
        equipment_id_column,
        health_score_column,
        failure_probability_column,
    }

    missing_columns = sorted(required_columns - set(frame.columns))

    if missing_columns:
        raise ValueError(
            "Maintenance risk frame is missing required columns: " f"{missing_columns}"
        )

    result = frame.copy(deep=True)

    risk_scores: list[float] = []
    risk_levels: list[str] = []

    for row in result.itertuples(
        index=False,
    ):
        classification = classify_equipment_risk(
            equipment_id=str(
                getattr(
                    row,
                    equipment_id_column,
                )
            ),
            health_score=float(
                getattr(
                    row,
                    health_score_column,
                )
            ),
            failure_probability=float(
                getattr(
                    row,
                    failure_probability_column,
                )
            ),
            health_weight=health_weight,
            failure_probability_weight=(failure_probability_weight),
        )

        risk_scores.append(classification.risk_score)

        risk_levels.append(classification.risk_level.value)

    result["risk_score"] = risk_scores
    result["risk_level"] = risk_levels

    return result
