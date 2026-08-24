"""Validation utilities for EOIP optimization outputs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class OptimizationValidationResult:
    """Summary of optimization validation checks."""

    row_count: int
    recommendation_count: int
    positive_net_impact_count: int
    negative_net_impact_count: int
    zero_net_impact_count: int
    intervention_count: int
    total_recoverable_energy_kwh: float
    total_net_financial_impact: float
    validation_passed: bool

    def __post_init__(self) -> None:
        """Validate optimization validation summary."""
        count_values = {
            "row_count": self.row_count,
            "recommendation_count": self.recommendation_count,
            "positive_net_impact_count": (self.positive_net_impact_count),
            "negative_net_impact_count": (self.negative_net_impact_count),
            "zero_net_impact_count": (self.zero_net_impact_count),
            "intervention_count": self.intervention_count,
        }

        for name, value in count_values.items():
            if value < 0:
                raise ValueError(f"{name} must not be negative.")

        numeric_values = {
            "total_recoverable_energy_kwh": (self.total_recoverable_energy_kwh),
            "total_net_financial_impact": (self.total_net_financial_impact),
        }

        for name, value in numeric_values.items():
            if not np.isfinite(value):
                raise ValueError(f"{name} must be finite.")

        if self.total_recoverable_energy_kwh < 0.0:
            raise ValueError("total_recoverable_energy_kwh must not be negative.")

        impact_count = (
            self.positive_net_impact_count
            + self.negative_net_impact_count
            + self.zero_net_impact_count
        )

        if impact_count != self.row_count:
            raise ValueError("Financial-impact counts must equal row_count.")

        if self.recommendation_count > self.row_count:
            raise ValueError("recommendation_count must not exceed row_count.")

        if self.intervention_count > self.row_count:
            raise ValueError("intervention_count must not exceed row_count.")


def validate_optimization_outputs(
    *,
    frame: pd.DataFrame,
    recoverable_energy_column: str = "recoverable_energy_kwh",
    net_financial_impact_column: str = "net_financial_impact",
    recommendation_type_column: str = "recommendation_type",
    intervention_column: str = "economically_justified",
) -> OptimizationValidationResult:
    """Validate optimization outputs and return portfolio summary."""
    if frame.empty:
        raise ValueError("Optimization validation frame must not be empty.")

    required_columns = {
        recoverable_energy_column,
        net_financial_impact_column,
        recommendation_type_column,
        intervention_column,
    }

    missing_columns = sorted(required_columns - set(frame.columns))

    if missing_columns:
        raise ValueError(
            "Optimization validation frame is missing required columns: "
            f"{missing_columns}"
        )

    recoverable_energy = frame[recoverable_energy_column]

    net_financial_impact = frame[net_financial_impact_column]

    if not pd.api.types.is_numeric_dtype(recoverable_energy):
        raise TypeError("Recoverable energy column must be numeric.")

    if not pd.api.types.is_numeric_dtype(net_financial_impact):
        raise TypeError("Net financial impact column must be numeric.")

    if recoverable_energy.isna().any():
        raise ValueError("Recoverable energy column must not contain missing values.")

    if net_financial_impact.isna().any():
        raise ValueError("Net financial impact column must not contain missing values.")

    recoverable_values = recoverable_energy.to_numpy(dtype=float)

    financial_values = net_financial_impact.to_numpy(dtype=float)

    if not np.isfinite(recoverable_values).all():
        raise ValueError("Recoverable energy values must contain only finite values.")

    if not np.isfinite(financial_values).all():
        raise ValueError("Net financial impact values must contain only finite values.")

    if (recoverable_values < 0.0).any():
        raise ValueError("Recoverable energy values must not be negative.")

    recommendation_values = frame[recommendation_type_column]

    if recommendation_values.isna().any():
        raise ValueError("Recommendation type column must not contain missing values.")

    normalized_recommendations = recommendation_values.astype(str).str.strip()

    if normalized_recommendations.eq("").any():
        raise ValueError("Recommendation types must not be empty.")

    intervention_values = frame[intervention_column]

    if intervention_values.isna().any():
        raise ValueError("Intervention column must not contain missing values.")

    allowed_recommendations = {
        "maintenance",
        "performance_recovery",
        "monitor",
        "no_action",
    }

    unsupported_recommendations = sorted(
        set(normalized_recommendations) - allowed_recommendations
    )

    if unsupported_recommendations:
        raise ValueError(
            "Unsupported recommendation types: " f"{unsupported_recommendations}"
        )

    row_count = len(frame)

    recommendation_count = int(normalized_recommendations.ne("no_action").sum())

    positive_net_impact_count = int((financial_values > 0.0).sum())

    negative_net_impact_count = int((financial_values < 0.0).sum())

    zero_net_impact_count = int(
        np.isclose(
            financial_values,
            0.0,
        ).sum()
    )

    intervention_count = int(intervention_values.astype(bool).sum())

    total_recoverable_energy_kwh = float(recoverable_values.sum())

    total_net_financial_impact = float(financial_values.sum())

    validation_passed = (
        row_count > 0
        and np.isfinite(total_recoverable_energy_kwh)
        and np.isfinite(total_net_financial_impact)
    )

    return OptimizationValidationResult(
        row_count=row_count,
        recommendation_count=recommendation_count,
        positive_net_impact_count=(positive_net_impact_count),
        negative_net_impact_count=(negative_net_impact_count),
        zero_net_impact_count=(zero_net_impact_count),
        intervention_count=intervention_count,
        total_recoverable_energy_kwh=(total_recoverable_energy_kwh),
        total_net_financial_impact=(total_net_financial_impact),
        validation_passed=bool(validation_passed),
    )
