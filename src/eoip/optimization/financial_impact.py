"""Financial impact estimation for EOIP optimization."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class FinancialImpactResult:
    """Financial impact produced by an optimization intervention."""

    recovered_energy_kwh: float
    energy_value_per_kwh: float
    avoided_failure_cost: float
    operating_cost_saving: float
    intervention_cost: float
    recovered_energy_value: float
    gross_financial_benefit: float
    net_financial_impact: float
    roi_percentage: float

    def __post_init__(self) -> None:
        """Validate financial-impact result."""
        values = {
            "recovered_energy_kwh": self.recovered_energy_kwh,
            "energy_value_per_kwh": self.energy_value_per_kwh,
            "avoided_failure_cost": self.avoided_failure_cost,
            "operating_cost_saving": self.operating_cost_saving,
            "intervention_cost": self.intervention_cost,
            "recovered_energy_value": self.recovered_energy_value,
            "gross_financial_benefit": self.gross_financial_benefit,
            "net_financial_impact": self.net_financial_impact,
            "roi_percentage": self.roi_percentage,
        }

        for name, value in values.items():
            if not np.isfinite(value):
                raise ValueError(f"{name} must be finite.")

        non_negative_values = {
            "recovered_energy_kwh": self.recovered_energy_kwh,
            "energy_value_per_kwh": self.energy_value_per_kwh,
            "avoided_failure_cost": self.avoided_failure_cost,
            "operating_cost_saving": self.operating_cost_saving,
            "intervention_cost": self.intervention_cost,
            "recovered_energy_value": self.recovered_energy_value,
            "gross_financial_benefit": self.gross_financial_benefit,
        }

        for name, value in non_negative_values.items():
            if value < 0.0:
                raise ValueError(f"{name} must not be negative.")


def estimate_financial_impact(
    *,
    recovered_energy_kwh: float,
    energy_value_per_kwh: float,
    avoided_failure_cost: float = 0.0,
    operating_cost_saving: float = 0.0,
    intervention_cost: float = 0.0,
) -> FinancialImpactResult:
    """Estimate financial impact of an optimization intervention."""
    inputs = {
        "recovered_energy_kwh": recovered_energy_kwh,
        "energy_value_per_kwh": energy_value_per_kwh,
        "avoided_failure_cost": avoided_failure_cost,
        "operating_cost_saving": operating_cost_saving,
        "intervention_cost": intervention_cost,
    }

    for name, value in inputs.items():
        if not np.isfinite(value):
            raise ValueError(f"{name} must be finite.")

        if value < 0.0:
            raise ValueError(f"{name} must not be negative.")

    recovered_energy_value = recovered_energy_kwh * energy_value_per_kwh

    gross_financial_benefit = (
        recovered_energy_value + avoided_failure_cost + operating_cost_saving
    )

    net_financial_impact = gross_financial_benefit - intervention_cost

    if intervention_cost == 0.0:
        # Keep ROI finite and deterministic for downstream analytics.
        # Net financial impact still captures the economic benefit.
        roi_percentage = 0.0
    else:
        roi_percentage = net_financial_impact / intervention_cost * 100.0

    return FinancialImpactResult(
        recovered_energy_kwh=float(recovered_energy_kwh),
        energy_value_per_kwh=float(energy_value_per_kwh),
        avoided_failure_cost=float(avoided_failure_cost),
        operating_cost_saving=float(operating_cost_saving),
        intervention_cost=float(intervention_cost),
        recovered_energy_value=float(recovered_energy_value),
        gross_financial_benefit=float(gross_financial_benefit),
        net_financial_impact=float(net_financial_impact),
        roi_percentage=float(roi_percentage),
    )


def estimate_financial_impacts(
    *,
    frame: pd.DataFrame,
    recovered_energy_column: str = "recovered_energy_kwh",
    energy_value_column: str = "energy_value_per_kwh",
    avoided_failure_cost_column: str = "avoided_failure_cost",
    operating_cost_saving_column: str = "operating_cost_saving",
    intervention_cost_column: str = "intervention_cost",
) -> pd.DataFrame:
    """Estimate financial impacts for multiple interventions."""
    if frame.empty:
        raise ValueError("Financial impact frame must not be empty.")

    required_columns = {
        recovered_energy_column,
        energy_value_column,
        avoided_failure_cost_column,
        operating_cost_saving_column,
        intervention_cost_column,
    }

    missing_columns = sorted(required_columns - set(frame.columns))

    if missing_columns:
        raise ValueError(
            "Financial impact frame is missing required columns: " f"{missing_columns}"
        )

    numeric_columns = [
        recovered_energy_column,
        energy_value_column,
        avoided_failure_cost_column,
        operating_cost_saving_column,
        intervention_cost_column,
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

        if (series < 0.0).any():
            raise ValueError(f"Column '{column}' must not contain negative values.")

    result = frame.copy(deep=True)

    recovered_energy_values: list[float] = []
    gross_benefits: list[float] = []
    net_impacts: list[float] = []
    roi_percentages: list[float] = []

    for index in result.index:
        impact = estimate_financial_impact(
            recovered_energy_kwh=float(
                result.at[
                    index,
                    recovered_energy_column,
                ]
            ),
            energy_value_per_kwh=float(
                result.at[
                    index,
                    energy_value_column,
                ]
            ),
            avoided_failure_cost=float(
                result.at[
                    index,
                    avoided_failure_cost_column,
                ]
            ),
            operating_cost_saving=float(
                result.at[
                    index,
                    operating_cost_saving_column,
                ]
            ),
            intervention_cost=float(
                result.at[
                    index,
                    intervention_cost_column,
                ]
            ),
        )

        recovered_energy_values.append(impact.recovered_energy_value)
        gross_benefits.append(impact.gross_financial_benefit)
        net_impacts.append(impact.net_financial_impact)
        roi_percentages.append(impact.roi_percentage)

    result["recovered_energy_value"] = recovered_energy_values

    result["gross_financial_benefit"] = gross_benefits

    result["net_financial_impact"] = net_impacts

    result["roi_percentage"] = roi_percentages

    return result
