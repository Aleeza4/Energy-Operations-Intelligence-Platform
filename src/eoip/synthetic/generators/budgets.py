"""
Monthly operating-budget generator for EOIP synthetic data generation.

This module implements the Phase 2 budget contract from
PHASE_2_IMPLEMENTATION_PLAN.md. It creates exactly one plant-month budget row
for each generated calendar month. Energy budgets are based on expected
weather-normal energy, target performance ratio, degradation, and planning
assumptions rather than realized unplanned downtime. Revenue budgets use
plant-level tariff reference rates.

The public generator returns a pandas DataFrame and performs no file I/O.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

import numpy as np
import pandas as pd


class _RandomContextProtocol(Protocol):
    """Minimal random-context interface required by this generator."""

    def generator(
        self,
        name: str,
        entity_id: str | None = None,
    ) -> np.random.Generator:
        """Return a deterministic NumPy generator for a named stream."""


@dataclass(frozen=True, slots=True)
class BudgetGeneratorConfig:
    """Configuration for deterministic monthly plant budgets."""

    random_seed: int = 20250201
    default_currency: str = "PKR"
    default_target_performance_ratio: float = 0.82
    default_target_availability_ratio: float = 0.985
    minimum_capacity_factor: float = 0.17
    maximum_capacity_factor: float = 0.27
    annual_opex_per_mw: float = 2_400_000.0
    annual_planned_maintenance_per_mw: float = 450_000.0
    age_opex_escalation_per_year: float = 0.015
    monthly_energy_uncertainty_ratio: float = 0.03
    monthly_cost_uncertainty_ratio: float = 0.04
    basis_version: str = "EOIP-BUDGET-BASIS-1.0"
    schema_version: str = "1.0.0"

    def __post_init__(self) -> None:
        """Validate budget-generator configuration."""
        normalized_currency = self.default_currency.strip().upper()
        normalized_basis_version = self.basis_version.strip()
        normalized_schema_version = self.schema_version.strip()

        object.__setattr__(
            self,
            "default_currency",
            normalized_currency,
        )
        object.__setattr__(
            self,
            "basis_version",
            normalized_basis_version,
        )
        object.__setattr__(
            self,
            "schema_version",
            normalized_schema_version,
        )

        if isinstance(self.random_seed, bool) or not isinstance(
            self.random_seed,
            int,
        ):
            raise TypeError("random_seed must be an integer.")

        if self.random_seed < 0:
            raise ValueError("random_seed must be non-negative.")

        if len(normalized_currency) != 3 or not normalized_currency.isalpha():
            raise ValueError("default_currency must be a three-letter alphabetic code.")

        if not normalized_basis_version:
            raise ValueError("basis_version cannot be empty.")

        if not normalized_schema_version:
            raise ValueError("schema_version cannot be empty.")

        ratio_fields = (
            "default_target_performance_ratio",
            "default_target_availability_ratio",
            "minimum_capacity_factor",
            "maximum_capacity_factor",
            "age_opex_escalation_per_year",
            "monthly_energy_uncertainty_ratio",
            "monthly_cost_uncertainty_ratio",
        )

        for field_name in ratio_fields:
            self._validate_finite_number(
                field_name=field_name,
                value=getattr(self, field_name),
            )

        if not 0.0 < self.default_target_performance_ratio <= 1.0:
            raise ValueError(
                "default_target_performance_ratio must be greater than "
                "zero and no greater than one."
            )

        if not 0.0 < self.default_target_availability_ratio <= 1.0:
            raise ValueError(
                "default_target_availability_ratio must be greater than "
                "zero and no greater than one."
            )

        if not 0.0 <= self.minimum_capacity_factor <= 1.0:
            raise ValueError("minimum_capacity_factor must be between zero and one.")

        if not 0.0 <= self.maximum_capacity_factor <= 1.0:
            raise ValueError("maximum_capacity_factor must be between zero and one.")

        if self.maximum_capacity_factor < self.minimum_capacity_factor:
            raise ValueError(
                "maximum_capacity_factor must be greater than or equal to "
                "minimum_capacity_factor."
            )

        if not 0.0 <= self.age_opex_escalation_per_year <= 1.0:
            raise ValueError(
                "age_opex_escalation_per_year must be between zero and one."
            )

        for field_name in (
            "monthly_energy_uncertainty_ratio",
            "monthly_cost_uncertainty_ratio",
        ):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between zero and one.")

        cost_fields = (
            "annual_opex_per_mw",
            "annual_planned_maintenance_per_mw",
        )

        for field_name in cost_fields:
            self._validate_finite_number(
                field_name=field_name,
                value=getattr(self, field_name),
            )
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} must be non-negative.")

    @staticmethod
    def _validate_finite_number(
        *,
        field_name: str,
        value: float,
    ) -> None:
        """Validate a finite numeric configuration value."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{field_name} must be numeric.")

        if not math.isfinite(value):
            raise ValueError(f"{field_name} must be finite.")


def generate_budgets(
    plants: pd.DataFrame | Iterable[Any],
    weather_or_expected_energy: pd.DataFrame | None,
    tariffs: pd.DataFrame,
    month_windows: Any,
    config: BudgetGeneratorConfig | None = None,
    random_context: _RandomContextProtocol | None = None,
    *,
    generation_run_id: str = "RUN-UNPUBLISHED",
) -> pd.DataFrame:
    """
    Generate one monthly budget row per plant and generated month.

    Parameters
    ----------
    plants:
        Plant master data. Each record must expose plant_id and AC capacity.
        Optional planning fields include currency, commissioning_date,
        target_performance_ratio, and annual_degradation_rate.
    weather_or_expected_energy:
        Optional expected-energy frame. If present, it must provide plant_id,
        a month identifier, and expected energy in MWh. If absent, expected
        energy is estimated from capacity, month length, seasonality, and a
        deterministic capacity-factor assumption.
    tariffs:
        Tariff DataFrame generated by ``generate_tariffs``.
    month_windows:
        Iterable/DataFrame containing month starts or objects with ``start``.
    config:
        Optional budget-generator configuration.
    random_context:
        Optional EOIP RandomContext-compatible object.
    generation_run_id:
        Audit run identifier included in every output row.

    Returns
    -------
    pandas.DataFrame
        Stable monthly budget rows ordered by plant, year, and month.
    """
    resolved_config = config or BudgetGeneratorConfig()
    plant_records = _normalize_plants(
        plants,
        default_currency=resolved_config.default_currency,
        default_target_pr=(resolved_config.default_target_performance_ratio),
    )
    months = _normalize_month_windows(month_windows)
    tariff_rates = _build_tariff_reference_rates(tariffs)
    expected_energy_lookup = _build_expected_energy_lookup(weather_or_expected_energy)

    if not plant_records:
        raise ValueError("plants must contain at least one plant.")

    if not months:
        raise ValueError("month_windows must contain at least one month.")

    if not generation_run_id.strip():
        raise ValueError("generation_run_id cannot be empty.")

    rows: list[dict[str, object]] = []

    for plant in plant_records:
        plant_id = plant["plant_id"]
        plant_rng = _plant_rng(
            config=resolved_config,
            random_context=random_context,
            plant_id=plant_id,
        )

        for month_start in months:
            hours_in_month = (
                pd.Timestamp(month_start)
                + pd.offsets.MonthBegin(1)
                - pd.Timestamp(month_start)
            ).total_seconds() / 3_600.0

            expected_energy_mwh = expected_energy_lookup.get((plant_id, month_start))

            if expected_energy_mwh is None:
                expected_energy_mwh = _estimate_monthly_expected_energy(
                    ac_capacity_mw=plant["ac_capacity_mw"],
                    target_performance_ratio=plant["target_performance_ratio"],
                    annual_degradation_rate=plant["annual_degradation_rate"],
                    commissioning_date=plant["commissioning_date"],
                    month_start=month_start,
                    hours_in_month=hours_in_month,
                    config=resolved_config,
                    rng=plant_rng,
                )

            tariff_key = (plant_id, month_start)
            energy_rate_per_mwh = tariff_rates.get(tariff_key)
            if energy_rate_per_mwh is None:
                raise ValueError(
                    f"No tariff coverage found for plant {plant_id} "
                    f"during {month_start:%Y-%m}."
                )

            age_years = _asset_age_years(
                commissioning_date=plant["commissioning_date"],
                reference_date=month_start,
            )
            age_cost_factor = 1.0 + (
                age_years * resolved_config.age_opex_escalation_per_year
            )

            monthly_opex = (
                plant["ac_capacity_mw"]
                * resolved_config.annual_opex_per_mw
                / 12.0
                * age_cost_factor
                * _bounded_uncertainty(
                    rng=plant_rng,
                    uncertainty_ratio=(resolved_config.monthly_cost_uncertainty_ratio),
                )
            )
            planned_maintenance = (
                plant["ac_capacity_mw"]
                * resolved_config.annual_planned_maintenance_per_mw
                / 12.0
                * age_cost_factor
                * _bounded_uncertainty(
                    rng=plant_rng,
                    uncertainty_ratio=(resolved_config.monthly_cost_uncertainty_ratio),
                )
            )
            budget_revenue = expected_energy_mwh * energy_rate_per_mwh

            rows.append(
                {
                    "budget_id": (
                        f"{plant_id}-{month_start.year:04d}-" f"{month_start.month:02d}"
                    ),
                    "plant_id": plant_id,
                    "budget_year": month_start.year,
                    "budget_month": month_start.month,
                    "budget_energy_mwh": round(
                        max(expected_energy_mwh, 0.0),
                        3,
                    ),
                    "budget_revenue": round(
                        max(budget_revenue, 0.0),
                        2,
                    ),
                    "target_performance_ratio": round(
                        plant["target_performance_ratio"],
                        6,
                    ),
                    "target_technical_availability_ratio": round(
                        resolved_config.default_target_availability_ratio,
                        6,
                    ),
                    "budget_opex": round(max(monthly_opex, 0.0), 2),
                    "budget_planned_maintenance": round(
                        max(planned_maintenance, 0.0),
                        2,
                    ),
                    "currency": plant["currency"],
                    "basis_version": resolved_config.basis_version,
                    "generation_run_id": generation_run_id.strip(),
                    "schema_version": resolved_config.schema_version,
                }
            )

    frame = pd.DataFrame.from_records(
        rows,
        columns=_output_columns(),
    )
    frame = frame.sort_values(
        ["plant_id", "budget_year", "budget_month"],
        kind="stable",
    ).reset_index(drop=True)

    _validate_generated_budgets(
        frame=frame,
        expected_plant_ids={record["plant_id"] for record in plant_records},
        months=months,
    )

    return frame


def _normalize_plants(
    plants: pd.DataFrame | Iterable[Any],
    *,
    default_currency: str,
    default_target_pr: float,
) -> list[dict[str, Any]]:
    """Normalize supported plant inputs to planning records."""
    if isinstance(plants, pd.DataFrame):
        records = plants.to_dict(orient="records")
    else:
        records = []
        for item in plants:
            if isinstance(item, dict):
                records.append(item)
            else:
                records.append(
                    {
                        "plant_id": getattr(item, "plant_id", None),
                        "ac_capacity_mw": getattr(
                            item,
                            "ac_capacity_mw",
                            None,
                        ),
                        "currency": getattr(item, "currency", None),
                        "commissioning_date": getattr(
                            item,
                            "commissioning_date",
                            None,
                        ),
                        "target_performance_ratio": getattr(
                            item,
                            "target_performance_ratio",
                            None,
                        ),
                        "annual_degradation_rate": getattr(
                            item,
                            "annual_degradation_rate",
                            None,
                        ),
                    }
                )

    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for record in records:
        plant_id = _required_text(record, "plant_id").upper()

        if plant_id in seen_ids:
            raise ValueError(f"Duplicate plant_id '{plant_id}'.")
        seen_ids.add(plant_id)

        ac_capacity_mw = _required_non_negative_number(
            record,
            "ac_capacity_mw",
        )
        if ac_capacity_mw <= 0:
            raise ValueError(
                f"ac_capacity_mw must be greater than zero for {plant_id}."
            )

        currency_value = record.get("currency")
        currency = (
            currency_value.strip().upper()
            if isinstance(currency_value, str) and currency_value.strip()
            else default_currency
        )
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError(f"Invalid currency '{currency}' for plant {plant_id}.")

        commissioning_value = record.get("commissioning_date")
        commissioning_date = (
            pd.Timestamp(commissioning_value).date()
            if commissioning_value is not None
            else date(2020, 1, 1)
        )

        target_pr_value = record.get("target_performance_ratio")
        target_pr = (
            float(target_pr_value) if target_pr_value is not None else default_target_pr
        )
        if not 0.0 < target_pr <= 1.0:
            raise ValueError(f"Invalid target_performance_ratio for {plant_id}.")

        degradation_value = record.get("annual_degradation_rate")
        degradation_rate = (
            float(degradation_value) if degradation_value is not None else 0.005
        )
        if not 0.0 <= degradation_rate <= 1.0:
            raise ValueError(f"Invalid annual_degradation_rate for {plant_id}.")

        normalized.append(
            {
                "plant_id": plant_id,
                "ac_capacity_mw": ac_capacity_mw,
                "currency": currency,
                "commissioning_date": commissioning_date,
                "target_performance_ratio": target_pr,
                "annual_degradation_rate": degradation_rate,
            }
        )

    return sorted(normalized, key=lambda item: item["plant_id"])


def _normalize_month_windows(month_windows: Any) -> list[date]:
    """Normalize month-window inputs to unique month-start dates."""
    raw_values: list[Any]

    if isinstance(month_windows, pd.DataFrame):
        if "month_start" in month_windows.columns:
            raw_values = month_windows["month_start"].tolist()
        elif "start" in month_windows.columns:
            raw_values = month_windows["start"].tolist()
        else:
            raise ValueError(
                "month_windows DataFrame must contain month_start or start."
            )
    else:
        raw_values = list(month_windows)

    months: set[date] = set()

    for value in raw_values:
        if hasattr(value, "start"):
            value = value.start

        timestamp = pd.Timestamp(value)
        month_start = date(timestamp.year, timestamp.month, 1)
        months.add(month_start)

    return sorted(months)


def _build_tariff_reference_rates(
    tariffs: pd.DataFrame,
) -> dict[tuple[str, date], float]:
    """Build monthly plant-level reference rates from tariff rows."""
    required_columns = {
        "plant_id",
        "effective_start_date",
        "effective_end_date",
        "energy_rate_per_mwh",
    }
    missing_columns = required_columns.difference(tariffs.columns)
    if missing_columns:
        raise ValueError(
            "tariffs is missing required columns: " f"{sorted(missing_columns)}."
        )

    if tariffs.empty:
        raise ValueError("tariffs must not be empty.")

    normalized = tariffs.copy()
    normalized["plant_id"] = normalized["plant_id"].astype(str).str.strip().str.upper()
    normalized["effective_start_date"] = pd.to_datetime(
        normalized["effective_start_date"]
    ).dt.date
    normalized["effective_end_date"] = pd.to_datetime(
        normalized["effective_end_date"]
    ).dt.date
    normalized["energy_rate_per_mwh"] = pd.to_numeric(
        normalized["energy_rate_per_mwh"],
        errors="raise",
    )

    if (normalized["energy_rate_per_mwh"] < 0).any():
        raise ValueError("Tariff rates must be non-negative.")

    lookup: dict[tuple[str, date], float] = {}

    for plant_id, group in normalized.groupby("plant_id", sort=True):
        coverage_start = min(group["effective_start_date"])
        coverage_end = max(group["effective_end_date"])

        for month_start in pd.date_range(
            coverage_start,
            coverage_end,
            freq="MS",
        ):
            month_date = month_start.date()
            applicable = group[
                (group["effective_start_date"] <= month_date)
                & (group["effective_end_date"] >= month_date)
            ]

            if applicable.empty:
                continue

            lookup[(plant_id, month_date)] = float(
                applicable["energy_rate_per_mwh"].mean()
            )

    return lookup


def _build_expected_energy_lookup(
    frame: pd.DataFrame | None,
) -> dict[tuple[str, date], float]:
    """Normalize optional expected-energy input to plant-month values."""
    if frame is None:
        return {}

    if frame.empty:
        return {}

    required_plant_column = "plant_id"
    if required_plant_column not in frame.columns:
        raise ValueError("weather_or_expected_energy must contain plant_id.")

    energy_column = _first_existing_column(
        frame,
        (
            "expected_energy_mwh",
            "budget_energy_mwh",
            "energy_mwh",
        ),
    )
    if energy_column is None:
        raise ValueError(
            "weather_or_expected_energy must contain expected_energy_mwh, "
            "budget_energy_mwh, or energy_mwh."
        )

    month_column = _first_existing_column(
        frame,
        (
            "month_start",
            "timestamp_utc",
            "timestamp",
            "date",
        ),
    )
    if month_column is None:
        raise ValueError("weather_or_expected_energy must contain a month/date column.")

    normalized = frame.copy()
    normalized["plant_id"] = normalized["plant_id"].astype(str).str.strip().str.upper()
    normalized["_month_start"] = (
        pd.to_datetime(normalized[month_column])
        .dt.to_period("M")
        .dt.to_timestamp()
        .dt.date
    )
    normalized["_expected_energy_mwh"] = pd.to_numeric(
        normalized[energy_column],
        errors="raise",
    )

    if (normalized["_expected_energy_mwh"] < 0).any():
        raise ValueError("Expected energy must be non-negative.")

    grouped = normalized.groupby(
        ["plant_id", "_month_start"],
        as_index=False,
    )["_expected_energy_mwh"].sum()

    return {
        (row["plant_id"], row["_month_start"]): float(row["_expected_energy_mwh"])
        for row in grouped.to_dict(orient="records")
    }


def _estimate_monthly_expected_energy(
    *,
    ac_capacity_mw: float,
    target_performance_ratio: float,
    annual_degradation_rate: float,
    commissioning_date: date,
    month_start: date,
    hours_in_month: float,
    config: BudgetGeneratorConfig,
    rng: np.random.Generator,
) -> float:
    """Estimate weather-normal monthly energy without realized faults."""
    month_angle = 2.0 * math.pi * (month_start.month - 1) / 12.0
    seasonal_factor = 1.0 + 0.16 * math.sin(month_angle - 1.1)

    baseline_capacity_factor = float(
        rng.uniform(
            config.minimum_capacity_factor,
            config.maximum_capacity_factor,
        )
    )
    age_years = _asset_age_years(
        commissioning_date=commissioning_date,
        reference_date=month_start,
    )
    degradation_factor = max(
        0.0,
        (1.0 - annual_degradation_rate) ** age_years,
    )
    uncertainty_factor = _bounded_uncertainty(
        rng=rng,
        uncertainty_ratio=config.monthly_energy_uncertainty_ratio,
    )

    return (
        ac_capacity_mw
        * hours_in_month
        * baseline_capacity_factor
        * seasonal_factor
        * target_performance_ratio
        * degradation_factor
        * uncertainty_factor
    )


def _asset_age_years(
    *,
    commissioning_date: date,
    reference_date: date,
) -> float:
    """Return non-negative fractional asset age in years."""
    days = max((reference_date - commissioning_date).days, 0)
    return days / 365.25


def _bounded_uncertainty(
    *,
    rng: np.random.Generator,
    uncertainty_ratio: float,
) -> float:
    """Return a bounded multiplicative planning uncertainty factor."""
    if uncertainty_ratio == 0.0:
        return 1.0

    return float(
        rng.uniform(
            1.0 - uncertainty_ratio,
            1.0 + uncertainty_ratio,
        )
    )


def _plant_rng(
    *,
    config: BudgetGeneratorConfig,
    random_context: _RandomContextProtocol | None,
    plant_id: str,
) -> np.random.Generator:
    """Return the deterministic budget random stream for one plant."""
    if random_context is not None:
        return random_context.generator("budgets", entity_id=plant_id)

    plant_entropy = sum(
        (index + 1) * ord(character) for index, character in enumerate(plant_id)
    )
    return np.random.default_rng(config.random_seed + plant_entropy)


def _validate_generated_budgets(
    *,
    frame: pd.DataFrame,
    expected_plant_ids: set[str],
    months: list[date],
) -> None:
    """Validate mandatory budget invariants before returning."""
    if frame.empty:
        raise ValueError("Generated budget frame is empty.")

    if frame["budget_id"].duplicated().any():
        raise ValueError("Generated budgets contain duplicate budget_id.")

    actual_plant_ids = set(frame["plant_id"].astype(str))
    if actual_plant_ids != expected_plant_ids:
        raise ValueError("Generated budget plant coverage does not match input plants.")

    expected_count = len(expected_plant_ids) * len(months)
    if len(frame) != expected_count:
        raise ValueError(
            "Generated budgets do not contain exactly one row per " "plant-month."
        )

    numeric_columns = (
        "budget_energy_mwh",
        "budget_revenue",
        "target_performance_ratio",
        "target_technical_availability_ratio",
        "budget_opex",
        "budget_planned_maintenance",
    )
    for column in numeric_columns:
        if not np.isfinite(frame[column].to_numpy(dtype=float)).all():
            raise ValueError(
                f"Generated budget column '{column}' contains " "non-finite values."
            )

    non_negative_columns = (
        "budget_energy_mwh",
        "budget_revenue",
        "budget_opex",
        "budget_planned_maintenance",
    )
    for column in non_negative_columns:
        if (frame[column] < 0).any():
            raise ValueError(
                f"Generated budget column '{column}' must be non-negative."
            )


def _required_text(record: dict[str, Any], field_name: str) -> str:
    """Return a required normalized text field."""
    value = record.get(field_name)
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty.")

    return normalized


def _required_non_negative_number(
    record: dict[str, Any],
    field_name: str,
) -> float:
    """Return a required finite non-negative numeric field."""
    value = record.get(field_name)

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric.")

    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        raise ValueError(f"{field_name} must be finite.")

    if numeric_value < 0:
        raise ValueError(f"{field_name} must be non-negative.")

    return numeric_value


def _first_existing_column(
    frame: pd.DataFrame,
    candidates: tuple[str, ...],
) -> str | None:
    """Return the first candidate column present in a DataFrame."""
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate

    return None


def _output_columns() -> tuple[str, ...]:
    """Return stable budget output column order."""
    return (
        "budget_id",
        "plant_id",
        "budget_year",
        "budget_month",
        "budget_energy_mwh",
        "budget_revenue",
        "target_performance_ratio",
        "target_technical_availability_ratio",
        "budget_opex",
        "budget_planned_maintenance",
        "currency",
        "basis_version",
        "generation_run_id",
        "schema_version",
    )
