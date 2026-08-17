"""Unit tests for EOIP Technical Availability KPI."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eoip.analytics.kpi.base import KPIStatus, KPIWindow
from eoip.analytics.kpi.technical_availability import (
    calculate_technical_availability,
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


class TestTechnicalAvailability:
    """Tests for Technical Availability calculation."""

    def test_calculates_full_availability(self) -> None:
        result = calculate_technical_availability(
            equipment_available=[
                True,
                True,
                True,
                True,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(100.0)
        assert result.unit == "%"
        assert result.name == "Technical Availability"
        assert result.sample_count == 4

    def test_calculates_partial_availability(self) -> None:
        result = calculate_technical_availability(
            equipment_available=[
                True,
                True,
                False,
                True,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(75.0)
        assert result.sample_count == 4

    def test_calculates_zero_availability(self) -> None:
        result = calculate_technical_availability(
            equipment_available=[
                False,
                False,
                False,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)
        assert result.sample_count == 3

    def test_ignores_none_values(self) -> None:
        result = calculate_technical_availability(
            equipment_available=[
                True,
                None,
                False,
                True,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(
            66.6666666667,
        )
        assert result.sample_count == 3

    def test_returns_insufficient_data_for_empty_input(self) -> None:
        result = calculate_technical_availability(
            equipment_available=[],
            window=_window(),
        )

        assert result.status is KPIStatus.INSUFFICIENT_DATA
        assert result.value is None
        assert result.sample_count == 0
        assert result.message == (
            "No valid equipment availability observations " "are available."
        )

    def test_returns_insufficient_data_when_all_values_are_none(
        self,
    ) -> None:
        result = calculate_technical_availability(
            equipment_available=[
                None,
                None,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INSUFFICIENT_DATA
        assert result.value is None
        assert result.sample_count == 0

    @pytest.mark.parametrize(
        "invalid_value",
        [
            1,
            0,
            "true",
            "false",
            1.0,
        ],
    )
    def test_rejects_non_boolean_observations(
        self,
        invalid_value: object,
    ) -> None:
        result = calculate_technical_availability(
            equipment_available=[
                True,
                invalid_value,  # type: ignore[list-item]
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == (
            "Equipment availability observations must be boolean."
        )

    def test_preserves_window(self) -> None:
        window = _window()

        result = calculate_technical_availability(
            equipment_available=[
                True,
                False,
            ],
            window=window,
        )

        assert result.window is window
