"""Recommendation prioritization for EOIP optimization."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from eoip.optimization.recommendations import RecommendationType


@dataclass(frozen=True, slots=True)
class RecommendationPriorityWeights:
    """Weights used to rank optimization recommendations."""

    risk_score: float = 0.40
    expected_benefit: float = 0.30
    recoverable_energy: float = 0.20
    recommendation_type: float = 0.10

    def __post_init__(self) -> None:
        """Validate recommendation-priority weights."""
        values = (
            self.risk_score,
            self.expected_benefit,
            self.recoverable_energy,
            self.recommendation_type,
        )

        if any(not np.isfinite(value) for value in values):
            raise ValueError("Recommendation priority weights must be finite.")

        if any(value < 0.0 for value in values):
            raise ValueError("Recommendation priority weights must not be negative.")

        if not np.isclose(sum(values), 1.0):
            raise ValueError("Recommendation priority weights must sum to 1.")


def _recommendation_type_score(
    recommendation_type: str,
) -> float:
    """Return normalized urgency score for a recommendation type."""
    mapping = {
        RecommendationType.MAINTENANCE.value: 1.0,
        RecommendationType.PERFORMANCE_RECOVERY.value: 0.75,
        RecommendationType.MONITOR.value: 0.40,
        RecommendationType.NO_ACTION.value: 0.0,
    }

    try:
        return mapping[recommendation_type]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported recommendation type: {recommendation_type}"
        ) from exc


def prioritize_recommendations(
    *,
    frame: pd.DataFrame,
    equipment_id_column: str = "equipment_id",
    recommendation_type_column: str = "recommendation_type",
    risk_score_column: str = "risk_score",
    expected_benefit_column: str = "expected_benefit",
    recoverable_energy_column: str = "recoverable_energy_kwh",
    weights: RecommendationPriorityWeights | None = None,
) -> pd.DataFrame:
    """Rank optimization recommendations by operational priority."""
    if frame.empty:
        raise ValueError("Recommendation priority frame must not be empty.")

    required_columns = {
        equipment_id_column,
        recommendation_type_column,
        risk_score_column,
        expected_benefit_column,
        recoverable_energy_column,
    }

    missing_columns = sorted(required_columns - set(frame.columns))

    if missing_columns:
        raise ValueError(
            "Recommendation priority frame is missing required columns: "
            f"{missing_columns}"
        )

    active_weights = weights if weights is not None else RecommendationPriorityWeights()

    result = frame.copy(deep=True)

    risk_values = result[risk_score_column]

    expected_benefit_values = result[expected_benefit_column]

    recoverable_values = result[recoverable_energy_column]

    numeric_columns = {
        risk_score_column: risk_values,
        expected_benefit_column: expected_benefit_values,
        recoverable_energy_column: recoverable_values,
    }

    for column, series in numeric_columns.items():
        if not pd.api.types.is_numeric_dtype(series):
            raise TypeError(f"Column '{column}' must be numeric.")

        if series.isna().any():
            raise ValueError(f"Column '{column}' must not contain missing values.")

        values = series.to_numpy(dtype=float)

        if not np.isfinite(values).all():
            raise ValueError(f"Column '{column}' must contain only finite values.")

    if ((risk_values < 0.0) | (risk_values > 1.0)).any():
        raise ValueError("Risk scores must be between 0 and 1.")

    if (expected_benefit_values < 0.0).any():
        raise ValueError("Expected benefits must not be negative.")

    if (recoverable_values < 0.0).any():
        raise ValueError("Recoverable energy values must not be negative.")

    equipment_ids = result[equipment_id_column].astype(str).str.strip()

    if equipment_ids.eq("").any():
        raise ValueError("Equipment identifiers must not be empty.")

    type_scores = (
        result[recommendation_type_column].astype(str).map(_recommendation_type_score)
    )

    max_benefit = float(expected_benefit_values.max())

    max_recoverable = float(recoverable_values.max())

    if max_benefit == 0.0:
        normalized_benefit = pd.Series(
            np.zeros(len(result)),
            index=result.index,
            dtype=float,
        )
    else:
        normalized_benefit = expected_benefit_values / max_benefit

    if max_recoverable == 0.0:
        normalized_recoverable = pd.Series(
            np.zeros(len(result)),
            index=result.index,
            dtype=float,
        )
    else:
        normalized_recoverable = recoverable_values / max_recoverable

    priority_score = (
        risk_values * active_weights.risk_score
        + normalized_benefit * active_weights.expected_benefit
        + normalized_recoverable * active_weights.recoverable_energy
        + type_scores * active_weights.recommendation_type
    )

    result["recommendation_priority_score"] = priority_score.astype(float)

    result = result.sort_values(
        by=[
            "recommendation_priority_score",
            equipment_id_column,
        ],
        ascending=[
            False,
            True,
        ],
        kind="stable",
    ).reset_index(drop=True)

    result["recommendation_priority_rank"] = result.index + 1

    return result
