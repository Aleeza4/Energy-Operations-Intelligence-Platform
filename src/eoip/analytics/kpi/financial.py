"""Financial KPI calculations for EOIP."""

from __future__ import annotations

from eoip.analytics.kpi.base import (
    KPIResult,
    KPIWindow,
    invalid_input_result,
    valid_result,
)


def calculate_revenue(
    *,
    energy_kwh: float,
    tariff_per_kwh: float,
    window: KPIWindow,
) -> KPIResult:
    """Calculate energy revenue."""
    if energy_kwh < 0:
        return invalid_input_result(
            name="Revenue",
            unit="currency",
            window=window,
            message="Energy must not be negative.",
        )

    if tariff_per_kwh < 0:
        return invalid_input_result(
            name="Revenue",
            unit="currency",
            window=window,
            message="Tariff must not be negative.",
        )

    revenue = energy_kwh * tariff_per_kwh

    return valid_result(
        name="Revenue",
        value=revenue,
        unit="currency",
        window=window,
        sample_count=1,
    )


def calculate_revenue_loss(
    *,
    lost_energy_kwh: float,
    tariff_per_kwh: float,
    window: KPIWindow,
) -> KPIResult:
    """Calculate revenue lost due to energy losses."""
    if lost_energy_kwh < 0:
        return invalid_input_result(
            name="Revenue Loss",
            unit="currency",
            window=window,
            message="Lost energy must not be negative.",
        )

    if tariff_per_kwh < 0:
        return invalid_input_result(
            name="Revenue Loss",
            unit="currency",
            window=window,
            message="Tariff must not be negative.",
        )

    revenue_loss = lost_energy_kwh * tariff_per_kwh

    return valid_result(
        name="Revenue Loss",
        value=revenue_loss,
        unit="currency",
        window=window,
        sample_count=1,
    )


def calculate_recoverable_revenue_opportunity(
    *,
    recoverable_energy_kwh: float,
    tariff_per_kwh: float,
    window: KPIWindow,
) -> KPIResult:
    """Calculate revenue opportunity from recoverable energy."""
    if recoverable_energy_kwh < 0:
        return invalid_input_result(
            name="Recoverable Revenue Opportunity",
            unit="currency",
            window=window,
            message="Recoverable energy must not be negative.",
        )

    if tariff_per_kwh < 0:
        return invalid_input_result(
            name="Recoverable Revenue Opportunity",
            unit="currency",
            window=window,
            message="Tariff must not be negative.",
        )

    opportunity = recoverable_energy_kwh * tariff_per_kwh

    return valid_result(
        name="Recoverable Revenue Opportunity",
        value=opportunity,
        unit="currency",
        window=window,
        sample_count=1,
    )


def calculate_budget_variance(
    *,
    actual_cost: float,
    budgeted_cost: float,
    window: KPIWindow,
) -> KPIResult:
    """Calculate actual-minus-budget cost variance."""
    if actual_cost < 0:
        return invalid_input_result(
            name="Budget Variance",
            unit="currency",
            window=window,
            message="Actual cost must not be negative.",
        )

    if budgeted_cost < 0:
        return invalid_input_result(
            name="Budget Variance",
            unit="currency",
            window=window,
            message="Budgeted cost must not be negative.",
        )

    variance = actual_cost - budgeted_cost

    return valid_result(
        name="Budget Variance",
        value=variance,
        unit="currency",
        window=window,
        sample_count=1,
    )


def calculate_budget_utilization(
    *,
    actual_cost: float,
    budgeted_cost: float,
    window: KPIWindow,
) -> KPIResult:
    """Calculate actual cost as a percentage of budget."""
    if actual_cost < 0:
        return invalid_input_result(
            name="Budget Utilization",
            unit="%",
            window=window,
            message="Actual cost must not be negative.",
        )

    if budgeted_cost <= 0:
        return invalid_input_result(
            name="Budget Utilization",
            unit="%",
            window=window,
            message="Budgeted cost must be greater than zero.",
        )

    utilization_pct = (actual_cost / budgeted_cost) * 100.0

    return valid_result(
        name="Budget Utilization",
        value=utilization_pct,
        unit="%",
        window=window,
        sample_count=1,
    )
