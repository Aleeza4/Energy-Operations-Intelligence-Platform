"""Scenario analysis for EOIP optimization."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class ScenarioComparisonResult:
    """Comparison between baseline and intervention scenarios."""

    baseline_energy_kwh: float
    intervention_energy_kwh: float
    baseline_cost: float
    intervention_cost: float
    baseline_risk: float
    intervention_risk: float
    energy_gain_kwh: float
    cost_saving: float
    risk_reduction: float

    def __post_init__(self) -> None:
        """Validate scenario comparison result."""
        values = {
            "baseline_energy_kwh": self.baseline_energy_kwh,
            "intervention_energy_kwh": self.intervention_energy_kwh,
            "baseline_cost": self.baseline_cost,
            "intervention_cost": self.intervention_cost,
            "baseline_risk": self.baseline_risk,
            "intervention_risk": self.intervention_risk,
            "energy_gain_kwh": self.energy_gain_kwh,
            "cost_saving": self.cost_saving,
            "risk_reduction": self.risk_reduction,
        }

        for name, value in values.items():
            if not np.isfinite(value):
                raise ValueError(f"{name} must be finite.")

        if self.baseline_energy_kwh < 0.0:
            raise ValueError("baseline_energy_kwh must not be negative.")

        if self.intervention_energy_kwh < 0.0:
            raise ValueError("intervention_energy_kwh must not be negative.")

        if self.baseline_cost < 0.0:
            raise ValueError("baseline_cost must not be negative.")

        if self.intervention_cost < 0.0:
            raise ValueError("intervention_cost must not be negative.")

        if not 0.0 <= self.baseline_risk <= 1.0:
            raise ValueError("baseline_risk must be between 0 and 1.")

        if not 0.0 <= self.intervention_risk <= 1.0:
            raise ValueError("intervention_risk must be between 0 and 1.")


def compare_scenarios(
    *,
    baseline_energy_kwh: float,
    intervention_energy_kwh: float,
    baseline_cost: float,
    intervention_cost: float,
    baseline_risk: float,
    intervention_risk: float,
) -> ScenarioComparisonResult:
    """Compare baseline and intervention operating scenarios."""
    values = {
        "baseline_energy_kwh": baseline_energy_kwh,
        "intervention_energy_kwh": intervention_energy_kwh,
        "baseline_cost": baseline_cost,
        "intervention_cost": intervention_cost,
        "baseline_risk": baseline_risk,
        "intervention_risk": intervention_risk,
    }

    for name, value in values.items():
        if not np.isfinite(value):
            raise ValueError(f"{name} must be finite.")

    if baseline_energy_kwh < 0.0:
        raise ValueError("baseline_energy_kwh must not be negative.")

    if intervention_energy_kwh < 0.0:
        raise ValueError("intervention_energy_kwh must not be negative.")

    if baseline_cost < 0.0:
        raise ValueError("baseline_cost must not be negative.")

    if intervention_cost < 0.0:
        raise ValueError("intervention_cost must not be negative.")

    if not 0.0 <= baseline_risk <= 1.0:
        raise ValueError("baseline_risk must be between 0 and 1.")

    if not 0.0 <= intervention_risk <= 1.0:
        raise ValueError("intervention_risk must be between 0 and 1.")

    energy_gain_kwh = intervention_energy_kwh - baseline_energy_kwh

    cost_saving = baseline_cost - intervention_cost

    risk_reduction = baseline_risk - intervention_risk

    return ScenarioComparisonResult(
        baseline_energy_kwh=float(baseline_energy_kwh),
        intervention_energy_kwh=float(intervention_energy_kwh),
        baseline_cost=float(baseline_cost),
        intervention_cost=float(intervention_cost),
        baseline_risk=float(baseline_risk),
        intervention_risk=float(intervention_risk),
        energy_gain_kwh=float(energy_gain_kwh),
        cost_saving=float(cost_saving),
        risk_reduction=float(risk_reduction),
    )


def analyze_scenarios(
    *,
    frame: pd.DataFrame,
    baseline_energy_column: str = "baseline_energy_kwh",
    intervention_energy_column: str = "intervention_energy_kwh",
    baseline_cost_column: str = "baseline_cost",
    intervention_cost_column: str = "intervention_cost",
    baseline_risk_column: str = "baseline_risk",
    intervention_risk_column: str = "intervention_risk",
) -> pd.DataFrame:
    """Compare baseline and intervention scenarios for multiple rows."""
    if frame.empty:
        raise ValueError("Scenario analysis frame must not be empty.")

    required_columns = {
        baseline_energy_column,
        intervention_energy_column,
        baseline_cost_column,
        intervention_cost_column,
        baseline_risk_column,
        intervention_risk_column,
    }

    missing_columns = sorted(required_columns - set(frame.columns))

    if missing_columns:
        raise ValueError(
            "Scenario analysis frame is missing required columns: " f"{missing_columns}"
        )

    numeric_columns = [
        baseline_energy_column,
        intervention_energy_column,
        baseline_cost_column,
        intervention_cost_column,
        baseline_risk_column,
        intervention_risk_column,
    ]

    for column in numeric_columns:
        series = frame[column]

        if not pd.api.types.is_numeric_dtype(series):
            raise TypeError(f"Column '{column}' must be numeric.")

        if series.isna().any():
            raise ValueError(f"Column '{column}' must not contain missing values.")

        values = series.to_numpy(dtype=float)

        if not np.isfinite(values).all():
            raise ValueError(f"Column '{column}' must contain only finite values.")

    result = frame.copy(deep=True)

    energy_gains: list[float] = []
    cost_savings: list[float] = []
    risk_reductions: list[float] = []

    for index in result.index:
        comparison = compare_scenarios(
            baseline_energy_kwh=float(
                result.at[
                    index,
                    baseline_energy_column,
                ]
            ),
            intervention_energy_kwh=float(
                result.at[
                    index,
                    intervention_energy_column,
                ]
            ),
            baseline_cost=float(
                result.at[
                    index,
                    baseline_cost_column,
                ]
            ),
            intervention_cost=float(
                result.at[
                    index,
                    intervention_cost_column,
                ]
            ),
            baseline_risk=float(
                result.at[
                    index,
                    baseline_risk_column,
                ]
            ),
            intervention_risk=float(
                result.at[
                    index,
                    intervention_risk_column,
                ]
            ),
        )

        energy_gains.append(comparison.energy_gain_kwh)
        cost_savings.append(comparison.cost_saving)
        risk_reductions.append(comparison.risk_reduction)

    result["energy_gain_kwh"] = energy_gains

    result["cost_saving"] = cost_savings

    result["risk_reduction"] = risk_reductions

    return result
