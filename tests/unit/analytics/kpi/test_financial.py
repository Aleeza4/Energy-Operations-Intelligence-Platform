"""Unit tests for EOIP financial KPIs."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eoip.analytics.kpi.base import KPIStatus, KPIWindow
from eoip.analytics.kpi.financial import (
    calculate_budget_utilization,
    calculate_budget_variance,
    calculate_recoverable_revenue_opportunity,
    calculate_revenue,
    calculate_revenue_loss,
)


def _window() -> KPIWindow:
    """Return a valid one-hour KPI window."""
    return KPIWindow(
        start_at=datetime(
            2026,
            8,
            17,
            10,
            0,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            17,
            11,
            0,
            tzinfo=UTC,
        ),
    )


class TestRevenue:
    """Tests for revenue calculation."""

    def test_calculates_revenue(self) -> None:
        result = calculate_revenue(
            energy_kwh=1000.0,
            tariff_per_kwh=0.15,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(150.0)
        assert result.name == "Revenue"
        assert result.unit == "currency"
        assert result.sample_count == 1

    def test_allows_zero_energy(self) -> None:
        result = calculate_revenue(
            energy_kwh=0.0,
            tariff_per_kwh=0.15,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_allows_zero_tariff(self) -> None:
        result = calculate_revenue(
            energy_kwh=1000.0,
            tariff_per_kwh=0.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_rejects_negative_energy(self) -> None:
        result = calculate_revenue(
            energy_kwh=-1.0,
            tariff_per_kwh=0.15,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == "Energy must not be negative."

    def test_rejects_negative_tariff(self) -> None:
        result = calculate_revenue(
            energy_kwh=1000.0,
            tariff_per_kwh=-0.01,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == "Tariff must not be negative."


class TestRevenueLoss:
    """Tests for revenue loss calculation."""

    def test_calculates_revenue_loss(self) -> None:
        result = calculate_revenue_loss(
            lost_energy_kwh=200.0,
            tariff_per_kwh=0.15,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(30.0)
        assert result.name == "Revenue Loss"
        assert result.unit == "currency"

    def test_allows_zero_lost_energy(self) -> None:
        result = calculate_revenue_loss(
            lost_energy_kwh=0.0,
            tariff_per_kwh=0.15,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_rejects_negative_lost_energy(self) -> None:
        result = calculate_revenue_loss(
            lost_energy_kwh=-1.0,
            tariff_per_kwh=0.15,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == "Lost energy must not be negative."

    def test_rejects_negative_tariff(self) -> None:
        result = calculate_revenue_loss(
            lost_energy_kwh=100.0,
            tariff_per_kwh=-0.01,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == "Tariff must not be negative."


class TestRecoverableRevenueOpportunity:
    """Tests for recoverable revenue opportunity."""

    def test_calculates_recoverable_revenue_opportunity(self) -> None:
        result = calculate_recoverable_revenue_opportunity(
            recoverable_energy_kwh=300.0,
            tariff_per_kwh=0.20,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(60.0)
        assert result.name == "Recoverable Revenue Opportunity"
        assert result.unit == "currency"

    def test_allows_zero_recoverable_energy(self) -> None:
        result = calculate_recoverable_revenue_opportunity(
            recoverable_energy_kwh=0.0,
            tariff_per_kwh=0.20,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_rejects_negative_recoverable_energy(self) -> None:
        result = calculate_recoverable_revenue_opportunity(
            recoverable_energy_kwh=-1.0,
            tariff_per_kwh=0.20,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Recoverable energy must not be negative.")

    def test_rejects_negative_tariff(self) -> None:
        result = calculate_recoverable_revenue_opportunity(
            recoverable_energy_kwh=100.0,
            tariff_per_kwh=-0.01,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == "Tariff must not be negative."


class TestBudgetVariance:
    """Tests for budget variance calculation."""

    def test_calculates_positive_variance(self) -> None:
        result = calculate_budget_variance(
            actual_cost=1200.0,
            budgeted_cost=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(200.0)
        assert result.name == "Budget Variance"
        assert result.unit == "currency"

    def test_calculates_negative_variance(self) -> None:
        result = calculate_budget_variance(
            actual_cost=800.0,
            budgeted_cost=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(-200.0)

    def test_allows_zero_costs(self) -> None:
        result = calculate_budget_variance(
            actual_cost=0.0,
            budgeted_cost=0.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_rejects_negative_actual_cost(self) -> None:
        result = calculate_budget_variance(
            actual_cost=-1.0,
            budgeted_cost=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == "Actual cost must not be negative."

    def test_rejects_negative_budgeted_cost(self) -> None:
        result = calculate_budget_variance(
            actual_cost=1000.0,
            budgeted_cost=-1.0,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == "Budgeted cost must not be negative."


class TestBudgetUtilization:
    """Tests for budget utilization calculation."""

    def test_calculates_budget_utilization(self) -> None:
        result = calculate_budget_utilization(
            actual_cost=750.0,
            budgeted_cost=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(75.0)
        assert result.name == "Budget Utilization"
        assert result.unit == "%"
        assert result.sample_count == 1

    def test_allows_zero_actual_cost(self) -> None:
        result = calculate_budget_utilization(
            actual_cost=0.0,
            budgeted_cost=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_allows_utilization_above_one_hundred_percent(self) -> None:
        result = calculate_budget_utilization(
            actual_cost=1200.0,
            budgeted_cost=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(120.0)

    def test_rejects_negative_actual_cost(self) -> None:
        result = calculate_budget_utilization(
            actual_cost=-1.0,
            budgeted_cost=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == "Actual cost must not be negative."

    @pytest.mark.parametrize(
        "budgeted_cost",
        [
            0.0,
            -1.0,
        ],
    )
    def test_rejects_non_positive_budgeted_cost(
        self,
        budgeted_cost: float,
    ) -> None:
        result = calculate_budget_utilization(
            actual_cost=500.0,
            budgeted_cost=budgeted_cost,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Budgeted cost must be greater than zero.")

    def test_preserves_window(self) -> None:
        window = _window()

        result = calculate_budget_utilization(
            actual_cost=500.0,
            budgeted_cost=1000.0,
            window=window,
        )

        assert result.window is window
