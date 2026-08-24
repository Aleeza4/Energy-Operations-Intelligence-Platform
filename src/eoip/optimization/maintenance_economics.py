"""Maintenance cost-benefit analysis for EOIP optimization."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class MaintenanceCostBenefitResult:
    """Economic evaluation of one preventive-maintenance action."""

    equipment_id: str
    maintenance_cost: float
    failure_probability: float
    failure_cost: float
    prevention_effectiveness: float
    expected_failure_cost: float
    expected_avoided_cost: float
    net_benefit: float
    roi_percentage: float
    economically_justified: bool

    def __post_init__(self) -> None:
        """Validate maintenance cost-benefit result."""
        if not self.equipment_id.strip():
            raise ValueError("equipment_id must not be empty.")

        values = {
            "maintenance_cost": self.maintenance_cost,
            "failure_probability": self.failure_probability,
            "failure_cost": self.failure_cost,
            "prevention_effectiveness": self.prevention_effectiveness,
            "expected_failure_cost": self.expected_failure_cost,
            "expected_avoided_cost": self.expected_avoided_cost,
            "net_benefit": self.net_benefit,
            "roi_percentage": self.roi_percentage,
        }

        for name, value in values.items():
            if not np.isfinite(value):
                raise ValueError(f"{name} must be finite.")

        if self.maintenance_cost < 0.0:
            raise ValueError("maintenance_cost must not be negative.")

        if not 0.0 <= self.failure_probability <= 1.0:
            raise ValueError("failure_probability must be between 0 and 1.")

        if self.failure_cost < 0.0:
            raise ValueError("failure_cost must not be negative.")

        if not 0.0 <= self.prevention_effectiveness <= 1.0:
            raise ValueError("prevention_effectiveness must be between 0 and 1.")

        if self.expected_failure_cost < 0.0:
            raise ValueError("expected_failure_cost must not be negative.")

        if self.expected_avoided_cost < 0.0:
            raise ValueError("expected_avoided_cost must not be negative.")


def evaluate_maintenance_cost_benefit(
    *,
    equipment_id: str,
    maintenance_cost: float,
    failure_probability: float,
    failure_cost: float,
    prevention_effectiveness: float = 1.0,
) -> MaintenanceCostBenefitResult:
    """Evaluate the economics of a preventive-maintenance action."""
    if not equipment_id.strip():
        raise ValueError("equipment_id must not be empty.")

    values = {
        "maintenance_cost": maintenance_cost,
        "failure_probability": failure_probability,
        "failure_cost": failure_cost,
        "prevention_effectiveness": prevention_effectiveness,
    }

    for name, value in values.items():
        if not np.isfinite(value):
            raise ValueError(f"{name} must be finite.")

    if maintenance_cost < 0.0:
        raise ValueError("maintenance_cost must not be negative.")

    if not 0.0 <= failure_probability <= 1.0:
        raise ValueError("failure_probability must be between 0 and 1.")

    if failure_cost < 0.0:
        raise ValueError("failure_cost must not be negative.")

    if not 0.0 <= prevention_effectiveness <= 1.0:
        raise ValueError("prevention_effectiveness must be between 0 and 1.")

    expected_failure_cost = failure_probability * failure_cost

    expected_avoided_cost = expected_failure_cost * prevention_effectiveness

    net_benefit = expected_avoided_cost - maintenance_cost

    if maintenance_cost == 0.0:
        # A zero-cost action cannot have a conventional percentage ROI.
        # Use 0.0 as a deterministic finite convention while retaining
        # the economic decision through net_benefit.
        roi_percentage = 0.0
    else:
        roi_percentage = net_benefit / maintenance_cost * 100.0

    economically_justified = net_benefit > 0.0

    return MaintenanceCostBenefitResult(
        equipment_id=equipment_id,
        maintenance_cost=float(maintenance_cost),
        failure_probability=float(failure_probability),
        failure_cost=float(failure_cost),
        prevention_effectiveness=float(prevention_effectiveness),
        expected_failure_cost=float(expected_failure_cost),
        expected_avoided_cost=float(expected_avoided_cost),
        net_benefit=float(net_benefit),
        roi_percentage=float(roi_percentage),
        economically_justified=(economically_justified),
    )


def analyze_maintenance_cost_benefits(
    *,
    frame: pd.DataFrame,
    equipment_id_column: str = "equipment_id",
    maintenance_cost_column: str = "maintenance_cost",
    failure_probability_column: str = "failure_probability",
    failure_cost_column: str = "failure_cost",
    prevention_effectiveness_column: str | None = None,
) -> pd.DataFrame:
    """Evaluate maintenance economics for multiple equipment assets."""
    if frame.empty:
        raise ValueError("Maintenance cost-benefit frame must not be empty.")

    column_names = {
        "equipment_id_column": equipment_id_column,
        "maintenance_cost_column": maintenance_cost_column,
        "failure_probability_column": failure_probability_column,
        "failure_cost_column": failure_cost_column,
    }

    if prevention_effectiveness_column is not None:
        column_names["prevention_effectiveness_column"] = (
            prevention_effectiveness_column
        )

    for name, value in column_names.items():
        if not value.strip():
            raise ValueError(f"{name} must not be empty.")

    required_columns = {
        equipment_id_column,
        maintenance_cost_column,
        failure_probability_column,
        failure_cost_column,
    }

    if prevention_effectiveness_column is not None:
        required_columns.add(prevention_effectiveness_column)

    missing_columns = sorted(required_columns - set(frame.columns))

    if missing_columns:
        raise ValueError(
            "Maintenance cost-benefit frame is missing required columns: "
            f"{missing_columns}"
        )

    numeric_columns = [
        maintenance_cost_column,
        failure_probability_column,
        failure_cost_column,
    ]

    if prevention_effectiveness_column is not None:
        numeric_columns.append(prevention_effectiveness_column)

    for column in numeric_columns:
        series = frame[column]

        if not pd.api.types.is_numeric_dtype(series):
            raise TypeError(f"Column '{column}' must be numeric.")

        if series.isna().any():
            raise ValueError(f"Column '{column}' must not contain missing values.")

        values = series.to_numpy(dtype=float)

        if not np.isfinite(values).all():
            raise ValueError(f"Column '{column}' must contain only finite values.")

    equipment_ids = frame[equipment_id_column].astype(str)

    if equipment_ids.str.strip().eq("").any():
        raise ValueError("Equipment identifiers must not be empty.")

    result = frame.copy(deep=True)

    expected_failure_costs: list[float] = []
    expected_avoided_costs: list[float] = []
    net_benefits: list[float] = []
    roi_percentages: list[float] = []
    justified_flags: list[bool] = []

    for index in result.index:
        effectiveness = 1.0

        if prevention_effectiveness_column is not None:
            effectiveness = float(
                result.at[
                    index,
                    prevention_effectiveness_column,
                ]
            )

        evaluation = evaluate_maintenance_cost_benefit(
            equipment_id=str(
                result.at[
                    index,
                    equipment_id_column,
                ]
            ),
            maintenance_cost=float(
                result.at[
                    index,
                    maintenance_cost_column,
                ]
            ),
            failure_probability=float(
                result.at[
                    index,
                    failure_probability_column,
                ]
            ),
            failure_cost=float(
                result.at[
                    index,
                    failure_cost_column,
                ]
            ),
            prevention_effectiveness=effectiveness,
        )

        expected_failure_costs.append(evaluation.expected_failure_cost)
        expected_avoided_costs.append(evaluation.expected_avoided_cost)
        net_benefits.append(evaluation.net_benefit)
        roi_percentages.append(evaluation.roi_percentage)
        justified_flags.append(evaluation.economically_justified)

    result["expected_failure_cost"] = expected_failure_costs

    result["expected_avoided_cost"] = expected_avoided_costs

    result["net_benefit"] = net_benefits
    result["roi_percentage"] = roi_percentages

    result["economically_justified"] = justified_flags

    return result
