"""Unit tests for EOIP Capacity Factor KPI."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eoip.analytics.kpi.base import KPIStatus, KPIWindow
from eoip.analytics.kpi.capacity_factor import calculate_capacity_factor


def _window(
    *,
    hours: int = 1,
) -> KPIWindow:
    """Return a valid KPI window."""
    start_at = datetime(
        2026,
        8,
        17,
        10,
        0,
        tzinfo=UTC,
    )

    return KPIWindow(
        start_at=start_at,
        end_at=datetime(
            2026,
            8,
            17,
            10 + hours,
            0,
            tzinfo=UTC,
        ),
    )


class TestCapacityFactor:
    """Tests for Capacity Factor calculation."""

    def test_calculates_capacity_factor(self) -> None:
        result = calculate_capacity_factor(
            actual_energy_kwh=800.0,
            rated_capacity_kw=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(80.0)
        assert result.name == "Capacity Factor"
        assert result.unit == "%"
        assert result.sample_count == 1

    def test_uses_window_duration(self) -> None:
        result = calculate_capacity_factor(
            actual_energy_kwh=1000.0,
            rated_capacity_kw=1000.0,
            window=_window(hours=2),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(50.0)

    def test_calculates_full_capacity_factor(self) -> None:
        result = calculate_capacity_factor(
            actual_energy_kwh=1000.0,
            rated_capacity_kw=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(100.0)

    def test_allows_zero_actual_energy(self) -> None:
        result = calculate_capacity_factor(
            actual_energy_kwh=0.0,
            rated_capacity_kw=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_allows_capacity_factor_above_one_hundred_percent(
        self,
    ) -> None:
        result = calculate_capacity_factor(
            actual_energy_kwh=1100.0,
            rated_capacity_kw=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(110.0)

    def test_rejects_negative_actual_energy(self) -> None:
        result = calculate_capacity_factor(
            actual_energy_kwh=-1.0,
            rated_capacity_kw=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == "Actual energy must not be negative."

    @pytest.mark.parametrize(
        "rated_capacity_kw",
        [
            0.0,
            -1.0,
        ],
    )
    def test_rejects_non_positive_rated_capacity(
        self,
        rated_capacity_kw: float,
    ) -> None:
        result = calculate_capacity_factor(
            actual_energy_kwh=500.0,
            rated_capacity_kw=rated_capacity_kw,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Rated capacity must be greater than zero.")

    def test_preserves_window(self) -> None:
        window = _window()

        result = calculate_capacity_factor(
            actual_energy_kwh=500.0,
            rated_capacity_kw=1000.0,
            window=window,
        )

        assert result.window is window
