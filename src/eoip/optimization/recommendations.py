"""Recommendation engine for EOIP optimization."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np
import pandas as pd


class RecommendationType(StrEnum):
    """Supported EOIP optimization recommendation types."""

    MAINTENANCE = "maintenance"
    PERFORMANCE_RECOVERY = "performance_recovery"
    MONITOR = "monitor"
    NO_ACTION = "no_action"


@dataclass(frozen=True, slots=True)
class OptimizationRecommendation:
    """Action recommendation for one equipment asset."""

    equipment_id: str
    recommendation_type: RecommendationType
    action: str
    rationale: str
    expected_benefit: float

    def __post_init__(self) -> None:
        """Validate optimization recommendation."""
        if not self.equipment_id.strip():
            raise ValueError("equipment_id must not be empty.")

        if not self.action.strip():
            raise ValueError("action must not be empty.")

        if not self.rationale.strip():
            raise ValueError("rationale must not be empty.")

        if not np.isfinite(self.expected_benefit):
            raise ValueError("expected_benefit must be finite.")

        if self.expected_benefit < 0.0:
            raise ValueError("expected_benefit must not be negative.")


def generate_recommendation(
    *,
    equipment_id: str,
    risk_score: float,
    recoverable_energy_kwh: float,
    economically_justified: bool,
    expected_benefit: float,
) -> OptimizationRecommendation:
    """Generate an operational recommendation for one asset."""
    if not equipment_id.strip():
        raise ValueError("equipment_id must not be empty.")

    numeric_values = {
        "risk_score": risk_score,
        "recoverable_energy_kwh": recoverable_energy_kwh,
        "expected_benefit": expected_benefit,
    }

    for name, value in numeric_values.items():
        if not np.isfinite(value):
            raise ValueError(f"{name} must be finite.")

    if not 0.0 <= risk_score <= 1.0:
        raise ValueError("risk_score must be between 0 and 1.")

    if recoverable_energy_kwh < 0.0:
        raise ValueError("recoverable_energy_kwh must not be negative.")

    if expected_benefit < 0.0:
        raise ValueError("expected_benefit must not be negative.")

    if economically_justified and risk_score >= 0.50:
        return OptimizationRecommendation(
            equipment_id=equipment_id,
            recommendation_type=RecommendationType.MAINTENANCE,
            action="Schedule preventive maintenance.",
            rationale=(
                "The asset has elevated predictive-maintenance risk "
                "and the intervention is economically justified."
            ),
            expected_benefit=float(expected_benefit),
        )

    if recoverable_energy_kwh > 0.0:
        return OptimizationRecommendation(
            equipment_id=equipment_id,
            recommendation_type=(RecommendationType.PERFORMANCE_RECOVERY),
            action=("Investigate and recover identified energy losses."),
            rationale=("The asset has technically recoverable energy loss."),
            expected_benefit=float(expected_benefit),
        )

    if risk_score >= 0.25:
        return OptimizationRecommendation(
            equipment_id=equipment_id,
            recommendation_type=RecommendationType.MONITOR,
            action=("Increase monitoring frequency and review trends."),
            rationale=(
                "The asset shows elevated risk but does not currently "
                "justify direct intervention."
            ),
            expected_benefit=float(expected_benefit),
        )

    return OptimizationRecommendation(
        equipment_id=equipment_id,
        recommendation_type=RecommendationType.NO_ACTION,
        action="Continue normal operation.",
        rationale=(
            "No material recoverable opportunity or elevated risk " "was identified."
        ),
        expected_benefit=float(expected_benefit),
    )


def generate_recommendations(
    *,
    frame: pd.DataFrame,
    equipment_id_column: str = "equipment_id",
    risk_score_column: str = "risk_score",
    recoverable_energy_column: str = "recoverable_energy_kwh",
    economically_justified_column: str = "economically_justified",
    expected_benefit_column: str = "expected_benefit",
) -> pd.DataFrame:
    """Generate optimization recommendations for multiple assets."""
    if frame.empty:
        raise ValueError("Recommendation frame must not be empty.")

    required_columns = {
        equipment_id_column,
        risk_score_column,
        recoverable_energy_column,
        economically_justified_column,
        expected_benefit_column,
    }

    missing_columns = sorted(required_columns - set(frame.columns))

    if missing_columns:
        raise ValueError(
            "Recommendation frame is missing required columns: " f"{missing_columns}"
        )

    result = frame.copy(deep=True)

    recommendation_types: list[str] = []
    actions: list[str] = []
    rationales: list[str] = []

    for index in result.index:
        recommendation = generate_recommendation(
            equipment_id=str(
                result.at[
                    index,
                    equipment_id_column,
                ]
            ),
            risk_score=float(
                result.at[
                    index,
                    risk_score_column,
                ]
            ),
            recoverable_energy_kwh=float(
                result.at[
                    index,
                    recoverable_energy_column,
                ]
            ),
            economically_justified=bool(
                result.at[
                    index,
                    economically_justified_column,
                ]
            ),
            expected_benefit=float(
                result.at[
                    index,
                    expected_benefit_column,
                ]
            ),
        )

        recommendation_types.append(recommendation.recommendation_type.value)
        actions.append(recommendation.action)
        rationales.append(recommendation.rationale)

    result["recommendation_type"] = recommendation_types
    result["recommended_action"] = actions
    result["recommendation_rationale"] = rationales

    return result
