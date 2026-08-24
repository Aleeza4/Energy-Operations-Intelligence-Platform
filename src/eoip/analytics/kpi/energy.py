"""Energy KPI calculations for EOIP."""

from __future__ import annotations

from collections.abc import Iterable

from eoip.analytics.kpi.base import (
    KPIResult,
    KPIWindow,
    insufficient_data_result,
    invalid_input_result,
    valid_result,
)


def calculate_actual_energy(
    *,
    interval_energy_kwh: Iterable[float | None],
    window: KPIWindow,
) -> KPIResult:
    """Calculate actual energy from interval energy observations."""
    values = [float(value) for value in interval_energy_kwh if value is not None]

    if not values:
        return insufficient_data_result(
            name="Actual Energy",
            unit="kWh",
            window=window,
            message="No valid interval energy observations are available.",
        )

    if any(value < 0 for value in values):
        return invalid_input_result(
            name="Actual Energy",
            unit="kWh",
            window=window,
            message="Interval energy values must not be negative.",
        )

    return valid_result(
        name="Actual Energy",
        value=sum(values),
        unit="kWh",
        window=window,
        sample_count=len(values),
    )


def calculate_expected_energy(
    *,
    expected_energy_kwh: Iterable[float | None],
    window: KPIWindow,
) -> KPIResult:
    """Calculate expected energy from expected interval energy values."""
    values = [float(value) for value in expected_energy_kwh if value is not None]

    if not values:
        return insufficient_data_result(
            name="Expected Energy",
            unit="kWh",
            window=window,
            message="No valid expected energy observations are available.",
        )

    if any(value < 0 for value in values):
        return invalid_input_result(
            name="Expected Energy",
            unit="kWh",
            window=window,
            message="Expected energy values must not be negative.",
        )

    return valid_result(
        name="Expected Energy",
        value=sum(values),
        unit="kWh",
        window=window,
        sample_count=len(values),
    )


def calculate_energy_variance(
    *,
    actual_energy_kwh: float,
    expected_energy_kwh: float,
    window: KPIWindow,
) -> KPIResult:
    """Calculate actual-minus-expected energy variance."""
    if actual_energy_kwh < 0:
        return invalid_input_result(
            name="Energy Variance",
            unit="kWh",
            window=window,
            message="Actual energy must not be negative.",
        )

    if expected_energy_kwh < 0:
        return invalid_input_result(
            name="Energy Variance",
            unit="kWh",
            window=window,
            message="Expected energy must not be negative.",
        )

    return valid_result(
        name="Energy Variance",
        value=actual_energy_kwh - expected_energy_kwh,
        unit="kWh",
        window=window,
        sample_count=1,
    )


def calculate_energy_achievement(
    *,
    actual_energy_kwh: float,
    expected_energy_kwh: float,
    window: KPIWindow,
) -> KPIResult:
    """Calculate actual energy as a percentage of expected energy."""
    if actual_energy_kwh < 0:
        return invalid_input_result(
            name="Energy Achievement",
            unit="%",
            window=window,
            message="Actual energy must not be negative.",
        )

    if expected_energy_kwh <= 0:
        return invalid_input_result(
            name="Energy Achievement",
            unit="%",
            window=window,
            message="Expected energy must be greater than zero.",
        )

    achievement_pct = (actual_energy_kwh / expected_energy_kwh) * 100.0

    return valid_result(
        name="Energy Achievement",
        value=achievement_pct,
        unit="%",
        window=window,
        sample_count=1,
    )
