"""Recoverable Energy Opportunity KPI calculations for EOIP."""

from __future__ import annotations

from eoip.analytics.kpi.base import (
    KPIResult,
    KPIWindow,
    invalid_input_result,
    valid_result,
)


def calculate_recoverable_energy_opportunity(
    *,
    curtailment_loss_kwh: float,
    soiling_loss_kwh: float,
    clipping_loss_kwh: float,
    downtime_loss_kwh: float,
    window: KPIWindow,
) -> KPIResult:
    """Calculate total recoverable energy opportunity.

    Recoverable Energy Opportunity is the sum of identified
    recoverable energy losses:

        curtailment
        + soiling
        + clipping
        + downtime-related losses
    """
    losses = {
        "Curtailment loss": curtailment_loss_kwh,
        "Soiling loss": soiling_loss_kwh,
        "Clipping loss": clipping_loss_kwh,
        "Downtime loss": downtime_loss_kwh,
    }

    for label, value in losses.items():
        if value < 0:
            return invalid_input_result(
                name="Recoverable Energy Opportunity",
                unit="kWh",
                window=window,
                message=f"{label} must not be negative.",
            )

    recoverable_energy_kwh = sum(losses.values())

    return valid_result(
        name="Recoverable Energy Opportunity",
        value=recoverable_energy_kwh,
        unit="kWh",
        window=window,
        sample_count=len(losses),
    )


def calculate_recoverable_energy_percentage(
    *,
    recoverable_energy_kwh: float,
    expected_energy_kwh: float,
    window: KPIWindow,
) -> KPIResult:
    """Calculate recoverable opportunity as percentage of expected energy."""
    if recoverable_energy_kwh < 0:
        return invalid_input_result(
            name="Recoverable Energy Opportunity Percentage",
            unit="%",
            window=window,
            message="Recoverable energy must not be negative.",
        )

    if expected_energy_kwh <= 0:
        return invalid_input_result(
            name="Recoverable Energy Opportunity Percentage",
            unit="%",
            window=window,
            message="Expected energy must be greater than zero.",
        )

    if recoverable_energy_kwh > expected_energy_kwh:
        return invalid_input_result(
            name="Recoverable Energy Opportunity Percentage",
            unit="%",
            window=window,
            message=("Recoverable energy must not exceed expected energy."),
        )

    opportunity_pct = (recoverable_energy_kwh / expected_energy_kwh) * 100.0

    return valid_result(
        name="Recoverable Energy Opportunity Percentage",
        value=opportunity_pct,
        unit="%",
        window=window,
        sample_count=1,
    )
