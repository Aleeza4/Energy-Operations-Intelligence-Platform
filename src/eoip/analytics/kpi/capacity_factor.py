"""Capacity Factor KPI calculation for EOIP."""

from __future__ import annotations

from eoip.analytics.kpi.base import (
    KPIResult,
    KPIWindow,
    invalid_input_result,
    valid_result,
)


def calculate_capacity_factor(
    *,
    actual_energy_kwh: float,
    rated_capacity_kw: float,
    window: KPIWindow,
) -> KPIResult:
    """Calculate capacity factor as a percentage.

    Capacity Factor is calculated as:

        actual energy
        ------------------------------- * 100
        rated capacity * window hours
    """
    if actual_energy_kwh < 0:
        return invalid_input_result(
            name="Capacity Factor",
            unit="%",
            window=window,
            message="Actual energy must not be negative.",
        )

    if rated_capacity_kw <= 0:
        return invalid_input_result(
            name="Capacity Factor",
            unit="%",
            window=window,
            message="Rated capacity must be greater than zero.",
        )

    maximum_possible_energy_kwh = rated_capacity_kw * window.duration_hours

    if maximum_possible_energy_kwh <= 0:
        return invalid_input_result(
            name="Capacity Factor",
            unit="%",
            window=window,
            message="Maximum possible energy must be greater than zero.",
        )

    capacity_factor_pct = (actual_energy_kwh / maximum_possible_energy_kwh) * 100.0

    return valid_result(
        name="Capacity Factor",
        value=capacity_factor_pct,
        unit="%",
        window=window,
        sample_count=1,
    )
