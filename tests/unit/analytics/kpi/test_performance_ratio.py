"""Unit tests for EOIP Performance Ratio KPI."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eoip.analytics.kpi.base import KPIStatus, KPIWindow
from eoip.analytics.kpi.performance_ratio import (
    calculate_performance_ratio,
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


class TestPerformanceRatio:
    """Tests for Performance Ratio calculation."""

    def test_calculates_performance_ratio(self) -> None:
        result = calculate_performance_ratio(
            actual_energy_kwh=800.0,
            reference_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(80.0)
        assert result.unit == "%"
        assert result.name == "Performance Ratio"
        assert result.sample_count == 1

    def test_allows_performance_ratio_above_one_hundred_percent(
        self,
    ) -> None:
        result = calculate_performance_ratio(
            actual_energy_kwh=1100.0,
            reference_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(110.0)

    def test_allows_zero_actual_energy(self) -> None:
        result = calculate_performance_ratio(
            actual_energy_kwh=0.0,
            reference_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_rejects_negative_actual_energy(self) -> None:
        result = calculate_performance_ratio(
            actual_energy_kwh=-1.0,
            reference_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Actual energy must not be negative.")

    @pytest.mark.parametrize(
        "reference_energy_kwh",
        [
            0.0,
            -1.0,
        ],
    )
    def test_rejects_non_positive_reference_energy(
        self,
        reference_energy_kwh: float,
    ) -> None:
        result = calculate_performance_ratio(
            actual_energy_kwh=800.0,
            reference_energy_kwh=reference_energy_kwh,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Reference energy must be greater than zero.")

    def test_preserves_window(self) -> None:
        window = _window()

        result = calculate_performance_ratio(
            actual_energy_kwh=750.0,
            reference_energy_kwh=1000.0,
            window=window,
        )

        assert result.window is window
