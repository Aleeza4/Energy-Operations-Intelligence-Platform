"""Unit tests for EOIP curtailment analytics."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eoip.analytics.kpi.base import KPIStatus, KPIWindow
from eoip.analytics.kpi.curtailment import (
    calculate_curtailed_energy,
    calculate_curtailment_percentage,
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


class TestCurtailedEnergy:
    """Tests for curtailed energy calculation."""

    def test_calculates_curtailed_energy(self) -> None:
        result = calculate_curtailed_energy(
            potential_energy_kwh=[
                100.0,
                120.0,
                150.0,
            ],
            actual_energy_kwh=[
                90.0,
                100.0,
                120.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(60.0)
        assert result.name == "Curtailed Energy"
        assert result.unit == "kWh"
        assert result.sample_count == 3

    def test_returns_zero_when_actual_equals_potential(self) -> None:
        result = calculate_curtailed_energy(
            potential_energy_kwh=[
                100.0,
                120.0,
            ],
            actual_energy_kwh=[
                100.0,
                120.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_does_not_create_negative_curtailment(self) -> None:
        result = calculate_curtailed_energy(
            potential_energy_kwh=[
                100.0,
                120.0,
            ],
            actual_energy_kwh=[
                110.0,
                130.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_ignores_pairs_containing_none(self) -> None:
        result = calculate_curtailed_energy(
            potential_energy_kwh=[
                100.0,
                None,
                150.0,
            ],
            actual_energy_kwh=[
                80.0,
                100.0,
                120.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(50.0)
        assert result.sample_count == 2

    def test_ignores_none_in_actual_series(self) -> None:
        result = calculate_curtailed_energy(
            potential_energy_kwh=[
                100.0,
                120.0,
                150.0,
            ],
            actual_energy_kwh=[
                80.0,
                None,
                130.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(40.0)
        assert result.sample_count == 2

    def test_returns_insufficient_data_when_no_valid_pairs(
        self,
    ) -> None:
        result = calculate_curtailed_energy(
            potential_energy_kwh=[
                None,
                None,
            ],
            actual_energy_kwh=[
                None,
                None,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INSUFFICIENT_DATA
        assert result.value is None
        assert result.sample_count == 0
        assert result.message == (
            "No valid potential and actual energy observations " "are available."
        )

    def test_rejects_different_series_lengths(self) -> None:
        result = calculate_curtailed_energy(
            potential_energy_kwh=[
                100.0,
                120.0,
            ],
            actual_energy_kwh=[
                90.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == (
            "Potential and actual energy series must have "
            "the same number of observations."
        )

    def test_rejects_negative_potential_energy(self) -> None:
        result = calculate_curtailed_energy(
            potential_energy_kwh=[
                100.0,
                -1.0,
            ],
            actual_energy_kwh=[
                90.0,
                0.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Energy observations must not be negative.")

    def test_rejects_negative_actual_energy(self) -> None:
        result = calculate_curtailed_energy(
            potential_energy_kwh=[
                100.0,
                120.0,
            ],
            actual_energy_kwh=[
                90.0,
                -1.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None


class TestCurtailmentPercentage:
    """Tests for curtailment percentage calculation."""

    def test_calculates_curtailment_percentage(self) -> None:
        result = calculate_curtailment_percentage(
            curtailed_energy_kwh=100.0,
            potential_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(10.0)
        assert result.name == "Curtailment Percentage"
        assert result.unit == "%"
        assert result.sample_count == 1

    def test_allows_zero_curtailment(self) -> None:
        result = calculate_curtailment_percentage(
            curtailed_energy_kwh=0.0,
            potential_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_allows_full_curtailment(self) -> None:
        result = calculate_curtailment_percentage(
            curtailed_energy_kwh=1000.0,
            potential_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(100.0)

    def test_rejects_negative_curtailed_energy(self) -> None:
        result = calculate_curtailment_percentage(
            curtailed_energy_kwh=-1.0,
            potential_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Curtailed energy must not be negative.")

    @pytest.mark.parametrize(
        "potential_energy_kwh",
        [
            0.0,
            -1.0,
        ],
    )
    def test_rejects_non_positive_potential_energy(
        self,
        potential_energy_kwh: float,
    ) -> None:
        result = calculate_curtailment_percentage(
            curtailed_energy_kwh=0.0,
            potential_energy_kwh=potential_energy_kwh,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Potential energy must be greater than zero.")

    def test_rejects_curtailment_above_potential_energy(
        self,
    ) -> None:
        result = calculate_curtailment_percentage(
            curtailed_energy_kwh=1100.0,
            potential_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Curtailed energy must not exceed potential energy.")

    def test_preserves_window(self) -> None:
        window = _window()

        result = calculate_curtailment_percentage(
            curtailed_energy_kwh=100.0,
            potential_energy_kwh=1000.0,
            window=window,
        )

        assert result.window is window
