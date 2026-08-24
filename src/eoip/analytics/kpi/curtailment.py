"""Curtailment analytics calculations for EOIP."""

from __future__ import annotations

from collections.abc import Iterable

from eoip.analytics.kpi.base import (
    KPIResult,
    KPIWindow,
    insufficient_data_result,
    invalid_input_result,
    valid_result,
)


def calculate_curtailed_energy(
    *,
    potential_energy_kwh: Iterable[float | None],
    actual_energy_kwh: Iterable[float | None],
    window: KPIWindow,
) -> KPIResult:
    """Calculate total curtailed energy in kWh.

    Curtailment for each interval is calculated as:

        max(potential_energy - actual_energy, 0)

    Both input series must contain the same number of observations.
    """
    potential_values = list(potential_energy_kwh)
    actual_values = list(actual_energy_kwh)

    if len(potential_values) != len(actual_values):
        return invalid_input_result(
            name="Curtailed Energy",
            unit="kWh",
            window=window,
            message=(
                "Potential and actual energy series must have "
                "the same number of observations."
            ),
        )

    valid_pairs = [
        (
            float(potential),
            float(actual),
        )
        for potential, actual in zip(
            potential_values,
            actual_values,
            strict=True,
        )
        if potential is not None and actual is not None
    ]

    if not valid_pairs:
        return insufficient_data_result(
            name="Curtailed Energy",
            unit="kWh",
            window=window,
            message=(
                "No valid potential and actual energy observations " "are available."
            ),
        )

    for potential, actual in valid_pairs:
        if potential < 0 or actual < 0:
            return invalid_input_result(
                name="Curtailed Energy",
                unit="kWh",
                window=window,
                message="Energy observations must not be negative.",
            )

    curtailed_energy_kwh = sum(
        max(
            potential - actual,
            0.0,
        )
        for potential, actual in valid_pairs
    )

    return valid_result(
        name="Curtailed Energy",
        value=curtailed_energy_kwh,
        unit="kWh",
        window=window,
        sample_count=len(valid_pairs),
    )


def calculate_curtailment_percentage(
    *,
    curtailed_energy_kwh: float,
    potential_energy_kwh: float,
    window: KPIWindow,
) -> KPIResult:
    """Calculate curtailed energy as a percentage of potential energy."""
    if curtailed_energy_kwh < 0:
        return invalid_input_result(
            name="Curtailment Percentage",
            unit="%",
            window=window,
            message="Curtailed energy must not be negative.",
        )

    if potential_energy_kwh <= 0:
        return invalid_input_result(
            name="Curtailment Percentage",
            unit="%",
            window=window,
            message="Potential energy must be greater than zero.",
        )

    if curtailed_energy_kwh > potential_energy_kwh:
        return invalid_input_result(
            name="Curtailment Percentage",
            unit="%",
            window=window,
            message=("Curtailed energy must not exceed potential energy."),
        )

    curtailment_pct = (curtailed_energy_kwh / potential_energy_kwh) * 100.0

    return valid_result(
        name="Curtailment Percentage",
        value=curtailment_pct,
        unit="%",
        window=window,
        sample_count=1,
    )
