"""Maintenance prioritization for EOIP predictive maintenance."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class MaintenancePriorityWeights:
    """Weights used to calculate maintenance priority."""

    risk_score: float = 0.40
    failure_probability: float = 0.30
    health_degradation: float = 0.20
    criticality: float = 0.10

    def __post_init__(self) -> None:
        """Validate maintenance priority weights."""
        values = (
            self.risk_score,
            self.failure_probability,
            self.health_degradation,
            self.criticality,
        )

        if any(not np.isfinite(value) for value in values):
            raise ValueError("Maintenance priority weights must be finite.")

        if any(value < 0.0 for value in values):
            raise ValueError("Maintenance priority weights must not be negative.")

        if not np.isclose(sum(values), 1.0):
            raise ValueError("Maintenance priority weights must sum to 1.")


@dataclass(frozen=True, slots=True)
class MaintenancePriorityResult:
    """Priority result for a single equipment asset."""

    equipment_id: str
    priority_score: float
    priority_rank: int

    def __post_init__(self) -> None:
        """Validate maintenance priority result."""
        if not self.equipment_id.strip():
            raise ValueError("equipment_id must not be empty.")

        if not 0.0 <= self.priority_score <= 1.0:
            raise ValueError("priority_score must be between 0 and 1.")

        if self.priority_rank < 1:
            raise ValueError("priority_rank must be greater than zero.")


def calculate_priority_score(
    *,
    risk_score: float,
    failure_probability: float,
    health_score: float,
    criticality: float,
    weights: MaintenancePriorityWeights | None = None,
) -> float:
    """Calculate normalized maintenance priority score."""
    inputs = {
        "risk_score": risk_score,
        "failure_probability": failure_probability,
        "health_score": health_score,
        "criticality": criticality,
    }

    for name, value in inputs.items():
        if not np.isfinite(value):
            raise ValueError(f"{name} must be finite.")

    if not 0.0 <= risk_score <= 1.0:
        raise ValueError("risk_score must be between 0 and 1.")

    if not 0.0 <= failure_probability <= 1.0:
        raise ValueError("failure_probability must be between 0 and 1.")

    if not 0.0 <= health_score <= 100.0:
        raise ValueError("health_score must be between 0 and 100.")

    if not 0.0 <= criticality <= 1.0:
        raise ValueError("criticality must be between 0 and 1.")

    active_weights = weights if weights is not None else MaintenancePriorityWeights()

    health_degradation = 1.0 - (health_score / 100.0)

    score = (
        risk_score * active_weights.risk_score
        + failure_probability * active_weights.failure_probability
        + health_degradation * active_weights.health_degradation
        + criticality * active_weights.criticality
    )

    return float(
        np.clip(
            score,
            0.0,
            1.0,
        )
    )


def prioritize_maintenance(
    *,
    frame: pd.DataFrame,
    equipment_id_column: str = "equipment_id",
    risk_score_column: str = "risk_score",
    failure_probability_column: str = "failure_probability",
    health_score_column: str = "health_score",
    criticality_column: str = "criticality",
    weights: MaintenancePriorityWeights | None = None,
) -> pd.DataFrame:
    """Rank equipment assets by maintenance priority."""
    if frame.empty:
        raise ValueError("Maintenance priority frame must not be empty.")

    required_columns = {
        equipment_id_column,
        risk_score_column,
        failure_probability_column,
        health_score_column,
        criticality_column,
    }

    missing_columns = sorted(required_columns - set(frame.columns))

    if missing_columns:
        raise ValueError(
            "Maintenance priority frame is missing required columns: "
            f"{missing_columns}"
        )

    result = frame.copy(deep=True)

    priority_scores: list[float] = []

    for row in result.itertuples(
        index=False,
    ):
        equipment_id = str(
            getattr(
                row,
                equipment_id_column,
            )
        ).strip()

        if not equipment_id:
            raise ValueError("equipment_id must not be empty.")

        score = calculate_priority_score(
            risk_score=float(
                getattr(
                    row,
                    risk_score_column,
                )
            ),
            failure_probability=float(
                getattr(
                    row,
                    failure_probability_column,
                )
            ),
            health_score=float(
                getattr(
                    row,
                    health_score_column,
                )
            ),
            criticality=float(
                getattr(
                    row,
                    criticality_column,
                )
            ),
            weights=weights,
        )

        priority_scores.append(score)

    result["priority_score"] = priority_scores

    result = result.sort_values(
        by=[
            "priority_score",
            equipment_id_column,
        ],
        ascending=[
            False,
            True,
        ],
        kind="stable",
    ).reset_index(drop=True)

    result["priority_rank"] = result.index + 1

    return result
