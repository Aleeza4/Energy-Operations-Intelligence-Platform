"""Unit tests for EOIP recoverable energy opportunity KPIs."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eoip.analytics.kpi.base import KPIStatus, KPIWindow
from eoip.analytics.kpi.recoverable_energy import (
    calculate_recoverable_energy_opportunity,
    calculate_recoverable_energy_percentage,
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


class TestRecoverableEnergyOpportunity:
    """Tests for total recoverable energy opportunity."""

    def test_calculates_total_recoverable_energy(self) -> None:
        result = calculate_recoverable_energy_opportunity(
            curtailment_loss_kwh=100.0,
            soiling_loss_kwh=50.0,
            clipping_loss_kwh=25.0,
            downtime_loss_kwh=75.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(250.0)
        assert result.name == "Recoverable Energy Opportunity"
        assert result.unit == "kWh"
        assert result.sample_count == 4

    def test_allows_zero_losses(self) -> None:
        result = calculate_recoverable_energy_opportunity(
            curtailment_loss_kwh=0.0,
            soiling_loss_kwh=0.0,
            clipping_loss_kwh=0.0,
            downtime_loss_kwh=0.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_calculates_with_single_non_zero_loss(self) -> None:
        result = calculate_recoverable_energy_opportunity(
            curtailment_loss_kwh=0.0,
            soiling_loss_kwh=100.0,
            clipping_loss_kwh=0.0,
            downtime_loss_kwh=0.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(100.0)

    @pytest.mark.parametrize(
        (
            "curtailment_loss_kwh",
            "soiling_loss_kwh",
            "clipping_loss_kwh",
            "downtime_loss_kwh",
            "expected_message",
        ),
        [
            (
                -1.0,
                0.0,
                0.0,
                0.0,
                "Curtailment loss must not be negative.",
            ),
            (
                0.0,
                -1.0,
                0.0,
                0.0,
                "Soiling loss must not be negative.",
            ),
            (
                0.0,
                0.0,
                -1.0,
                0.0,
                "Clipping loss must not be negative.",
            ),
            (
                0.0,
                0.0,
                0.0,
                -1.0,
                "Downtime loss must not be negative.",
            ),
        ],
    )
    def test_rejects_negative_loss_components(
        self,
        curtailment_loss_kwh: float,
        soiling_loss_kwh: float,
        clipping_loss_kwh: float,
        downtime_loss_kwh: float,
        expected_message: str,
    ) -> None:
        result = calculate_recoverable_energy_opportunity(
            curtailment_loss_kwh=curtailment_loss_kwh,
            soiling_loss_kwh=soiling_loss_kwh,
            clipping_loss_kwh=clipping_loss_kwh,
            downtime_loss_kwh=downtime_loss_kwh,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == expected_message

    def test_preserves_window(self) -> None:
        window = _window()

        result = calculate_recoverable_energy_opportunity(
            curtailment_loss_kwh=10.0,
            soiling_loss_kwh=20.0,
            clipping_loss_kwh=30.0,
            downtime_loss_kwh=40.0,
            window=window,
        )

        assert result.window is window


class TestRecoverableEnergyPercentage:
    """Tests for recoverable energy opportunity percentage."""

    def test_calculates_recoverable_energy_percentage(self) -> None:
        result = calculate_recoverable_energy_percentage(
            recoverable_energy_kwh=200.0,
            expected_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(20.0)
        assert result.name == "Recoverable Energy Opportunity Percentage"
        assert result.unit == "%"
        assert result.sample_count == 1

    def test_allows_zero_recoverable_energy(self) -> None:
        result = calculate_recoverable_energy_percentage(
            recoverable_energy_kwh=0.0,
            expected_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_allows_full_expected_energy_as_recoverable(self) -> None:
        result = calculate_recoverable_energy_percentage(
            recoverable_energy_kwh=1000.0,
            expected_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(100.0)

    def test_rejects_negative_recoverable_energy(self) -> None:
        result = calculate_recoverable_energy_percentage(
            recoverable_energy_kwh=-1.0,
            expected_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Recoverable energy must not be negative.")

    @pytest.mark.parametrize(
        "expected_energy_kwh",
        [
            0.0,
            -1.0,
        ],
    )
    def test_rejects_non_positive_expected_energy(
        self,
        expected_energy_kwh: float,
    ) -> None:
        result = calculate_recoverable_energy_percentage(
            recoverable_energy_kwh=0.0,
            expected_energy_kwh=expected_energy_kwh,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Expected energy must be greater than zero.")

    def test_rejects_recoverable_energy_above_expected_energy(
        self,
    ) -> None:
        result = calculate_recoverable_energy_percentage(
            recoverable_energy_kwh=1100.0,
            expected_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Recoverable energy must not exceed expected energy.")

    def test_preserves_window(self) -> None:
        window = _window()

        result = calculate_recoverable_energy_percentage(
            recoverable_energy_kwh=100.0,
            expected_energy_kwh=1000.0,
            window=window,
        )

        assert result.window is window
