"""Performance Ratio KPI calculation for EOIP."""

from __future__ import annotations

from eoip.analytics.kpi.base import (
    KPIResult,
    KPIWindow,
    invalid_input_result,
    valid_result,
)


def calculate_performance_ratio(
    *,
    actual_energy_kwh: float,
    reference_energy_kwh: float,
    window: KPIWindow,
) -> KPIResult:
    """Calculate photovoltaic performance ratio.

    Performance Ratio is calculated as:

        actual_energy_kwh / reference_energy_kwh

    The result is returned as a percentage.
    """
    if actual_energy_kwh < 0:
        return invalid_input_result(
            name="Performance Ratio",
            unit="%",
            window=window,
            message="Actual energy must not be negative.",
        )

    if reference_energy_kwh <= 0:
        return invalid_input_result(
            name="Performance Ratio",
            unit="%",
            window=window,
            message="Reference energy must be greater than zero.",
        )

    performance_ratio_pct = (actual_energy_kwh / reference_energy_kwh) * 100.0

    return valid_result(
        name="Performance Ratio",
        value=performance_ratio_pct,
        unit="%",
        window=window,
        sample_count=1,
    )
