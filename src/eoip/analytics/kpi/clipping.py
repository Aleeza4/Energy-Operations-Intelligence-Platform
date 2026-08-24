"""Clipping loss KPI calculations for EOIP."""

from __future__ import annotations

from collections.abc import Iterable

from eoip.analytics.kpi.base import (
    KPIResult,
    KPIWindow,
    insufficient_data_result,
    invalid_input_result,
    valid_result,
)


def calculate_clipping_loss_energy(
    *,
    unconstrained_energy_kwh: Iterable[float | None],
    delivered_energy_kwh: Iterable[float | None],
    window: KPIWindow,
) -> KPIResult:
    """Calculate estimated energy lost due to inverter clipping.

    Interval clipping loss is calculated as:

        max(unconstrained energy - delivered energy, 0)

    Both input series must contain the same number of observations.
    """
    unconstrained_values = list(unconstrained_energy_kwh)
    delivered_values = list(delivered_energy_kwh)

    if len(unconstrained_values) != len(delivered_values):
        return invalid_input_result(
            name="Clipping Loss Energy",
            unit="kWh",
            window=window,
            message=(
                "Unconstrained and delivered energy series must have "
                "the same number of observations."
            ),
        )

    valid_pairs = [
        (
            float(unconstrained),
            float(delivered),
        )
        for unconstrained, delivered in zip(
            unconstrained_values,
            delivered_values,
            strict=True,
        )
        if unconstrained is not None and delivered is not None
    ]

    if not valid_pairs:
        return insufficient_data_result(
            name="Clipping Loss Energy",
            unit="kWh",
            window=window,
            message=(
                "No valid unconstrained and delivered energy "
                "observations are available."
            ),
        )

    if any(
        unconstrained < 0 or delivered < 0 for unconstrained, delivered in valid_pairs
    ):
        return invalid_input_result(
            name="Clipping Loss Energy",
            unit="kWh",
            window=window,
            message="Energy observations must not be negative.",
        )

    clipping_loss_kwh = sum(
        max(
            unconstrained - delivered,
            0.0,
        )
        for unconstrained, delivered in valid_pairs
    )

    return valid_result(
        name="Clipping Loss Energy",
        value=clipping_loss_kwh,
        unit="kWh",
        window=window,
        sample_count=len(valid_pairs),
    )


def calculate_clipping_loss_percentage(
    *,
    clipping_loss_kwh: float,
    unconstrained_energy_kwh: float,
    window: KPIWindow,
) -> KPIResult:
    """Calculate clipping loss as a percentage of unconstrained energy."""
    if clipping_loss_kwh < 0:
        return invalid_input_result(
            name="Clipping Loss Percentage",
            unit="%",
            window=window,
            message="Clipping loss energy must not be negative.",
        )

    if unconstrained_energy_kwh <= 0:
        return invalid_input_result(
            name="Clipping Loss Percentage",
            unit="%",
            window=window,
            message="Unconstrained energy must be greater than zero.",
        )

    if clipping_loss_kwh > unconstrained_energy_kwh:
        return invalid_input_result(
            name="Clipping Loss Percentage",
            unit="%",
            window=window,
            message=("Clipping loss energy must not exceed " "unconstrained energy."),
        )

    clipping_loss_pct = (clipping_loss_kwh / unconstrained_energy_kwh) * 100.0

    return valid_result(
        name="Clipping Loss Percentage",
        value=clipping_loss_pct,
        unit="%",
        window=window,
        sample_count=1,
    )
