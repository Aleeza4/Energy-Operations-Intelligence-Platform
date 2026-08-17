"""Soiling loss KPI calculations for EOIP."""

from __future__ import annotations

from eoip.analytics.kpi.base import (
    KPIResult,
    KPIWindow,
    invalid_input_result,
    valid_result,
)


def calculate_soiling_loss_energy(
    *,
    clean_reference_energy_kwh: float,
    soiled_energy_kwh: float,
    window: KPIWindow,
) -> KPIResult:
    """Calculate estimated energy lost due to soiling.

    Soiling loss energy is calculated as:

        max(clean reference energy - soiled energy, 0)
    """
    if clean_reference_energy_kwh < 0:
        return invalid_input_result(
            name="Soiling Loss Energy",
            unit="kWh",
            window=window,
            message="Clean reference energy must not be negative.",
        )

    if soiled_energy_kwh < 0:
        return invalid_input_result(
            name="Soiling Loss Energy",
            unit="kWh",
            window=window,
            message="Soiled energy must not be negative.",
        )

    soiling_loss_kwh = max(
        clean_reference_energy_kwh - soiled_energy_kwh,
        0.0,
    )

    return valid_result(
        name="Soiling Loss Energy",
        value=soiling_loss_kwh,
        unit="kWh",
        window=window,
        sample_count=1,
    )


def calculate_soiling_loss_percentage(
    *,
    clean_reference_energy_kwh: float,
    soiled_energy_kwh: float,
    window: KPIWindow,
) -> KPIResult:
    """Calculate soiling loss as a percentage of clean reference energy."""
    if clean_reference_energy_kwh <= 0:
        return invalid_input_result(
            name="Soiling Loss Percentage",
            unit="%",
            window=window,
            message="Clean reference energy must be greater than zero.",
        )

    if soiled_energy_kwh < 0:
        return invalid_input_result(
            name="Soiling Loss Percentage",
            unit="%",
            window=window,
            message="Soiled energy must not be negative.",
        )

    loss_kwh = max(
        clean_reference_energy_kwh - soiled_energy_kwh,
        0.0,
    )

    loss_pct = (loss_kwh / clean_reference_energy_kwh) * 100.0

    return valid_result(
        name="Soiling Loss Percentage",
        value=loss_pct,
        unit="%",
        window=window,
        sample_count=1,
    )
