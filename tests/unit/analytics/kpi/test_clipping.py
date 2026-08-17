"""Unit tests for EOIP clipping loss KPIs."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eoip.analytics.kpi.base import KPIStatus, KPIWindow
from eoip.analytics.kpi.clipping import (
    calculate_clipping_loss_energy,
    calculate_clipping_loss_percentage,
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


class TestClippingLossEnergy:
    """Tests for clipping loss energy."""

    def test_calculates_clipping_loss_energy(self) -> None:
        result = calculate_clipping_loss_energy(
            unconstrained_energy_kwh=[
                100.0,
                120.0,
                150.0,
            ],
            delivered_energy_kwh=[
                90.0,
                100.0,
                130.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(50.0)
        assert result.name == "Clipping Loss Energy"
        assert result.unit == "kWh"
        assert result.sample_count == 3

    def test_returns_zero_when_delivered_equals_unconstrained(self) -> None:
        result = calculate_clipping_loss_energy(
            unconstrained_energy_kwh=[
                100.0,
                120.0,
            ],
            delivered_energy_kwh=[
                100.0,
                120.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_does_not_create_negative_clipping_loss(self) -> None:
        result = calculate_clipping_loss_energy(
            unconstrained_energy_kwh=[
                100.0,
                120.0,
            ],
            delivered_energy_kwh=[
                110.0,
                130.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_ignores_pairs_containing_none(self) -> None:
        result = calculate_clipping_loss_energy(
            unconstrained_energy_kwh=[
                100.0,
                None,
                150.0,
            ],
            delivered_energy_kwh=[
                80.0,
                100.0,
                120.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(50.0)
        assert result.sample_count == 2

    def test_returns_insufficient_data_when_no_valid_pairs(
        self,
    ) -> None:
        result = calculate_clipping_loss_energy(
            unconstrained_energy_kwh=[
                None,
                None,
            ],
            delivered_energy_kwh=[
                None,
                None,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INSUFFICIENT_DATA
        assert result.value is None
        assert result.sample_count == 0
        assert result.message == (
            "No valid unconstrained and delivered energy " "observations are available."
        )

    def test_rejects_different_series_lengths(self) -> None:
        result = calculate_clipping_loss_energy(
            unconstrained_energy_kwh=[
                100.0,
                120.0,
            ],
            delivered_energy_kwh=[
                90.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == (
            "Unconstrained and delivered energy series must have "
            "the same number of observations."
        )

    def test_rejects_negative_unconstrained_energy(self) -> None:
        result = calculate_clipping_loss_energy(
            unconstrained_energy_kwh=[
                100.0,
                -1.0,
            ],
            delivered_energy_kwh=[
                90.0,
                0.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Energy observations must not be negative.")

    def test_rejects_negative_delivered_energy(self) -> None:
        result = calculate_clipping_loss_energy(
            unconstrained_energy_kwh=[
                100.0,
                120.0,
            ],
            delivered_energy_kwh=[
                90.0,
                -1.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None


class TestClippingLossPercentage:
    """Tests for clipping loss percentage."""

    def test_calculates_clipping_loss_percentage(self) -> None:
        result = calculate_clipping_loss_percentage(
            clipping_loss_kwh=50.0,
            unconstrained_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(5.0)
        assert result.name == "Clipping Loss Percentage"
        assert result.unit == "%"
        assert result.sample_count == 1

    def test_allows_zero_clipping_loss(self) -> None:
        result = calculate_clipping_loss_percentage(
            clipping_loss_kwh=0.0,
            unconstrained_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_allows_full_clipping_loss(self) -> None:
        result = calculate_clipping_loss_percentage(
            clipping_loss_kwh=1000.0,
            unconstrained_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(100.0)

    def test_rejects_negative_clipping_loss(self) -> None:
        result = calculate_clipping_loss_percentage(
            clipping_loss_kwh=-1.0,
            unconstrained_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Clipping loss energy must not be negative.")

    @pytest.mark.parametrize(
        "unconstrained_energy_kwh",
        [
            0.0,
            -1.0,
        ],
    )
    def test_rejects_non_positive_unconstrained_energy(
        self,
        unconstrained_energy_kwh: float,
    ) -> None:
        result = calculate_clipping_loss_percentage(
            clipping_loss_kwh=0.0,
            unconstrained_energy_kwh=unconstrained_energy_kwh,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Unconstrained energy must be greater than zero.")

    def test_rejects_clipping_loss_above_unconstrained_energy(
        self,
    ) -> None:
        result = calculate_clipping_loss_percentage(
            clipping_loss_kwh=1100.0,
            unconstrained_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == (
            "Clipping loss energy must not exceed " "unconstrained energy."
        )

    def test_preserves_window(self) -> None:
        window = _window()

        result = calculate_clipping_loss_percentage(
            clipping_loss_kwh=50.0,
            unconstrained_energy_kwh=1000.0,
            window=window,
        )

        assert result.window is window
