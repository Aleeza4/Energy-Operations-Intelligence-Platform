"""Cost optimization utilities for EOIP."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class CostOptimizationResult:
    """Optimized cost decision for one maintenance opportunity."""

    equipment_id: str
    intervention_cost: float
    expected_loss_avoided: float
    net_benefit: float
    benefit_cost_ratio: float
    should_intervene: bool

    def __post_init__(self) -> None:
        """Validate cost optimization result."""
        if not self.equipment_id.strip():
            raise ValueError("equipment_id must not be empty.")

        numeric_values = {
            "intervention_cost": self.intervention_cost,
            "expected_loss_avoided": self.expected_loss_avoided,
            "net_benefit": self.net_benefit,
            "benefit_cost_ratio": self.benefit_cost_ratio,
        }

        for name, value in numeric_values.items():
            if not np.isfinite(value):
                raise ValueError(f"{name} must be finite.")

        if self.intervention_cost < 0.0:
            raise ValueError("intervention_cost must not be negative.")

        if self.expected_loss_avoided < 0.0:
            raise ValueError("expected_loss_avoided must not be negative.")

        if self.benefit_cost_ratio < 0.0:
            raise ValueError("benefit_cost_ratio must not be negative.")


def optimize_cost(
    *,
    equipment_id: str,
    intervention_cost: float,
    failure_probability: float,
    failure_cost: float,
    prevention_effectiveness: float = 1.0,
) -> CostOptimizationResult:
    """Evaluate whether a preventive intervention is economically justified."""
    if not equipment_id.strip():
        raise ValueError("equipment_id must not be empty.")

    values = {
        "intervention_cost": intervention_cost,
        "failure_probability": failure_probability,
        "failure_cost": failure_cost,
        "prevention_effectiveness": prevention_effectiveness,
    }

    for name, value in values.items():
        if not np.isfinite(value):
            raise ValueError(f"{name} must be finite.")

    if intervention_cost < 0.0:
        raise ValueError("intervention_cost must not be negative.")

    if not 0.0 <= failure_probability <= 1.0:
        raise ValueError("failure_probability must be between 0 and 1.")

    if failure_cost < 0.0:
        raise ValueError("failure_cost must not be negative.")

    if not 0.0 <= prevention_effectiveness <= 1.0:
        raise ValueError("prevention_effectiveness must be between 0 and 1.")

    expected_failure_loss = failure_probability * failure_cost

    expected_loss_avoided = expected_failure_loss * prevention_effectiveness

    net_benefit = expected_loss_avoided - intervention_cost

    if intervention_cost == 0.0:
        benefit_cost_ratio = float("inf") if expected_loss_avoided > 0.0 else 0.0
    else:
        benefit_cost_ratio = expected_loss_avoided / intervention_cost

    should_intervene = net_benefit > 0.0

    return CostOptimizationResult(
        equipment_id=equipment_id,
        intervention_cost=float(intervention_cost),
        expected_loss_avoided=float(expected_loss_avoided),
        net_benefit=float(net_benefit),
        benefit_cost_ratio=float(benefit_cost_ratio),
        should_intervene=should_intervene,
    )


def optimize_costs(
    *,
    frame: pd.DataFrame,
    equipment_id_column: str = "equipment_id",
    intervention_cost_column: str = "intervention_cost",
    failure_probability_column: str = "failure_probability",
    failure_cost_column: str = "failure_cost",
    prevention_effectiveness_column: str | None = None,
) -> pd.DataFrame:
    """Evaluate preventive-maintenance economics for multiple assets."""
    if frame.empty:
        raise ValueError("Cost optimization frame must not be empty.")

    required_columns = {
        equipment_id_column,
        intervention_cost_column,
        failure_probability_column,
        failure_cost_column,
    }

    if prevention_effectiveness_column is not None:
        required_columns.add(prevention_effectiveness_column)

    missing_columns = sorted(required_columns - set(frame.columns))

    if missing_columns:
        raise ValueError(
            "Cost optimization frame is missing required columns: " f"{missing_columns}"
        )

    result = frame.copy(deep=True)

    expected_losses_avoided: list[float] = []
    net_benefits: list[float] = []
    benefit_cost_ratios: list[float] = []
    intervention_flags: list[bool] = []

    for row in result.itertuples(
        index=False,
    ):
        effectiveness = 1.0

        if prevention_effectiveness_column is not None:
            effectiveness = float(
                getattr(
                    row,
                    prevention_effectiveness_column,
                )
            )

        optimization = optimize_cost(
            equipment_id=str(
                getattr(
                    row,
                    equipment_id_column,
                )
            ),
            intervention_cost=float(
                getattr(
                    row,
                    intervention_cost_column,
                )
            ),
            failure_probability=float(
                getattr(
                    row,
                    failure_probability_column,
                )
            ),
            failure_cost=float(
                getattr(
                    row,
                    failure_cost_column,
                )
            ),
            prevention_effectiveness=effectiveness,
        )

        expected_losses_avoided.append(optimization.expected_loss_avoided)

        net_benefits.append(optimization.net_benefit)

        benefit_cost_ratios.append(optimization.benefit_cost_ratio)

        intervention_flags.append(optimization.should_intervene)

    result["expected_loss_avoided"] = expected_losses_avoided
    result["net_benefit"] = net_benefits
    result["benefit_cost_ratio"] = benefit_cost_ratios
    result["should_intervene"] = intervention_flags

    return result
