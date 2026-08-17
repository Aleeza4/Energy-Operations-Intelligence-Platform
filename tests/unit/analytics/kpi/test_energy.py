"""Unit tests for EOIP energy KPI calculations."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eoip.analytics.kpi.base import KPIStatus, KPIWindow
from eoip.analytics.kpi.energy import (
    calculate_actual_energy,
    calculate_energy_achievement,
    calculate_energy_variance,
    calculate_expected_energy,
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


class TestActualEnergy:
    """Tests for actual energy calculation."""

    def test_sums_interval_energy(self) -> None:
        result = calculate_actual_energy(
            interval_energy_kwh=[
                100.0,
                125.0,
                150.0,
                175.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == 550.0
        assert result.unit == "kWh"
        assert result.sample_count == 4

    def test_ignores_none_values(self) -> None:
        result = calculate_actual_energy(
            interval_energy_kwh=[
                100.0,
                None,
                150.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == 250.0
        assert result.sample_count == 2

    def test_returns_insufficient_data_when_empty(self) -> None:
        result = calculate_actual_energy(
            interval_energy_kwh=[],
            window=_window(),
        )

        assert result.status is KPIStatus.INSUFFICIENT_DATA
        assert result.value is None
        assert result.sample_count == 0

    def test_returns_insufficient_data_when_all_values_are_none(
        self,
    ) -> None:
        result = calculate_actual_energy(
            interval_energy_kwh=[
                None,
                None,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INSUFFICIENT_DATA
        assert result.value is None

    def test_rejects_negative_interval_energy(self) -> None:
        result = calculate_actual_energy(
            interval_energy_kwh=[
                100.0,
                -1.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Interval energy values must not be negative.")


class TestExpectedEnergy:
    """Tests for expected energy calculation."""

    def test_sums_expected_energy(self) -> None:
        result = calculate_expected_energy(
            expected_energy_kwh=[
                120.0,
                130.0,
                140.0,
                160.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == 550.0
        assert result.unit == "kWh"
        assert result.sample_count == 4

    def test_ignores_none_values(self) -> None:
        result = calculate_expected_energy(
            expected_energy_kwh=[
                120.0,
                None,
                180.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == 300.0
        assert result.sample_count == 2

    def test_returns_insufficient_data_when_empty(self) -> None:
        result = calculate_expected_energy(
            expected_energy_kwh=[],
            window=_window(),
        )

        assert result.status is KPIStatus.INSUFFICIENT_DATA
        assert result.value is None

    def test_rejects_negative_expected_energy(self) -> None:
        result = calculate_expected_energy(
            expected_energy_kwh=[
                100.0,
                -10.0,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Expected energy values must not be negative.")


class TestEnergyVariance:
    """Tests for energy variance calculation."""

    def test_calculates_positive_variance(self) -> None:
        result = calculate_energy_variance(
            actual_energy_kwh=600.0,
            expected_energy_kwh=550.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == 50.0
        assert result.unit == "kWh"

    def test_calculates_negative_variance(self) -> None:
        result = calculate_energy_variance(
            actual_energy_kwh=500.0,
            expected_energy_kwh=550.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == -50.0

    def test_rejects_negative_actual_energy(self) -> None:
        result = calculate_energy_variance(
            actual_energy_kwh=-1.0,
            expected_energy_kwh=550.0,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Actual energy must not be negative.")

    def test_rejects_negative_expected_energy(self) -> None:
        result = calculate_energy_variance(
            actual_energy_kwh=500.0,
            expected_energy_kwh=-1.0,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Expected energy must not be negative.")


class TestEnergyAchievement:
    """Tests for actual-versus-expected energy achievement."""

    def test_calculates_energy_achievement_percentage(self) -> None:
        result = calculate_energy_achievement(
            actual_energy_kwh=450.0,
            expected_energy_kwh=500.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(90.0)
        assert result.unit == "%"

    def test_allows_achievement_above_one_hundred_percent(
        self,
    ) -> None:
        result = calculate_energy_achievement(
            actual_energy_kwh=550.0,
            expected_energy_kwh=500.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(110.0)

    def test_rejects_negative_actual_energy(self) -> None:
        result = calculate_energy_achievement(
            actual_energy_kwh=-1.0,
            expected_energy_kwh=500.0,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None

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
        result = calculate_energy_achievement(
            actual_energy_kwh=500.0,
            expected_energy_kwh=expected_energy_kwh,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Expected energy must be greater than zero.")
