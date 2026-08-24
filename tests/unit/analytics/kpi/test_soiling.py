"""Unit tests for EOIP soiling loss KPIs."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eoip.analytics.kpi.base import KPIStatus, KPIWindow
from eoip.analytics.kpi.soiling import (
    calculate_soiling_loss_energy,
    calculate_soiling_loss_percentage,
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


class TestSoilingLossEnergy:
    """Tests for soiling loss energy."""

    def test_calculates_soiling_loss_energy(self) -> None:
        result = calculate_soiling_loss_energy(
            clean_reference_energy_kwh=1000.0,
            soiled_energy_kwh=900.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(100.0)
        assert result.name == "Soiling Loss Energy"
        assert result.unit == "kWh"
        assert result.sample_count == 1

    def test_returns_zero_when_soiled_equals_reference(self) -> None:
        result = calculate_soiling_loss_energy(
            clean_reference_energy_kwh=1000.0,
            soiled_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_does_not_return_negative_loss(self) -> None:
        result = calculate_soiling_loss_energy(
            clean_reference_energy_kwh=1000.0,
            soiled_energy_kwh=1050.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_allows_zero_clean_reference_energy(self) -> None:
        result = calculate_soiling_loss_energy(
            clean_reference_energy_kwh=0.0,
            soiled_energy_kwh=0.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_rejects_negative_clean_reference_energy(self) -> None:
        result = calculate_soiling_loss_energy(
            clean_reference_energy_kwh=-1.0,
            soiled_energy_kwh=0.0,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Clean reference energy must not be negative.")

    def test_rejects_negative_soiled_energy(self) -> None:
        result = calculate_soiling_loss_energy(
            clean_reference_energy_kwh=1000.0,
            soiled_energy_kwh=-1.0,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == "Soiled energy must not be negative."

    def test_preserves_window(self) -> None:
        window = _window()

        result = calculate_soiling_loss_energy(
            clean_reference_energy_kwh=1000.0,
            soiled_energy_kwh=900.0,
            window=window,
        )

        assert result.window is window


class TestSoilingLossPercentage:
    """Tests for soiling loss percentage."""

    def test_calculates_soiling_loss_percentage(self) -> None:
        result = calculate_soiling_loss_percentage(
            clean_reference_energy_kwh=1000.0,
            soiled_energy_kwh=900.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(10.0)
        assert result.name == "Soiling Loss Percentage"
        assert result.unit == "%"
        assert result.sample_count == 1

    def test_returns_zero_when_soiled_equals_reference(self) -> None:
        result = calculate_soiling_loss_percentage(
            clean_reference_energy_kwh=1000.0,
            soiled_energy_kwh=1000.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_does_not_return_negative_percentage(self) -> None:
        result = calculate_soiling_loss_percentage(
            clean_reference_energy_kwh=1000.0,
            soiled_energy_kwh=1050.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    @pytest.mark.parametrize(
        "clean_reference_energy_kwh",
        [
            0.0,
            -1.0,
        ],
    )
    def test_rejects_non_positive_clean_reference_energy(
        self,
        clean_reference_energy_kwh: float,
    ) -> None:
        result = calculate_soiling_loss_percentage(
            clean_reference_energy_kwh=clean_reference_energy_kwh,
            soiled_energy_kwh=0.0,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Clean reference energy must be greater than zero.")

    def test_rejects_negative_soiled_energy(self) -> None:
        result = calculate_soiling_loss_percentage(
            clean_reference_energy_kwh=1000.0,
            soiled_energy_kwh=-1.0,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == "Soiled energy must not be negative."

    def test_preserves_window(self) -> None:
        window = _window()

        result = calculate_soiling_loss_percentage(
            clean_reference_energy_kwh=1000.0,
            soiled_energy_kwh=950.0,
            window=window,
        )

        assert result.window is window
