"""Unit tests for the EOIP KPI engine foundation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eoip.analytics.kpi.base import (
    KPIResult,
    KPIStatus,
    KPIWindow,
    insufficient_data_result,
    invalid_input_result,
    valid_result,
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


class TestKPIWindow:
    """Tests for KPI calculation windows."""

    def test_valid_window(self) -> None:
        window = _window()

        assert window.duration_seconds == 3600.0
        assert window.duration_hours == 1.0

    def test_rejects_naive_start_time(self) -> None:
        with pytest.raises(
            ValueError,
            match="start_at must be timezone-aware",
        ):
            KPIWindow(
                start_at=datetime(2026, 8, 17, 10, 0),
                end_at=datetime(
                    2026,
                    8,
                    17,
                    11,
                    0,
                    tzinfo=UTC,
                ),
            )

    def test_rejects_naive_end_time(self) -> None:
        with pytest.raises(
            ValueError,
            match="end_at must be timezone-aware",
        ):
            KPIWindow(
                start_at=datetime(
                    2026,
                    8,
                    17,
                    10,
                    0,
                    tzinfo=UTC,
                ),
                end_at=datetime(2026, 8, 17, 11, 0),
            )

    def test_rejects_equal_boundaries(self) -> None:
        timestamp = datetime(
            2026,
            8,
            17,
            10,
            0,
            tzinfo=UTC,
        )

        with pytest.raises(
            ValueError,
            match="end_at must be later than start_at",
        ):
            KPIWindow(
                start_at=timestamp,
                end_at=timestamp,
            )

    def test_rejects_end_before_start(self) -> None:
        with pytest.raises(
            ValueError,
            match="end_at must be later than start_at",
        ):
            KPIWindow(
                start_at=datetime(
                    2026,
                    8,
                    17,
                    11,
                    0,
                    tzinfo=UTC,
                ),
                end_at=datetime(
                    2026,
                    8,
                    17,
                    10,
                    0,
                    tzinfo=UTC,
                ),
            )


class TestKPIResult:
    """Tests for standard KPI results."""

    def test_valid_result_accepts_value(self) -> None:
        result = KPIResult(
            name="Performance Ratio",
            value=0.82,
            unit="ratio",
            status=KPIStatus.VALID,
            window=_window(),
            sample_count=4,
        )

        assert result.value == 0.82
        assert result.status is KPIStatus.VALID
        assert result.sample_count == 4

    def test_rejects_empty_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="name must not be empty",
        ):
            KPIResult(
                name=" ",
                value=1.0,
                unit="ratio",
                status=KPIStatus.VALID,
                window=_window(),
            )

    def test_rejects_empty_unit(self) -> None:
        with pytest.raises(
            ValueError,
            match="unit must not be empty",
        ):
            KPIResult(
                name="Test KPI",
                value=1.0,
                unit=" ",
                status=KPIStatus.VALID,
                window=_window(),
            )

    def test_rejects_negative_sample_count(self) -> None:
        with pytest.raises(
            ValueError,
            match="sample_count must not be negative",
        ):
            KPIResult(
                name="Test KPI",
                value=1.0,
                unit="ratio",
                status=KPIStatus.VALID,
                window=_window(),
                sample_count=-1,
            )

    def test_valid_status_requires_value(self) -> None:
        with pytest.raises(
            ValueError,
            match="value must be provided when KPI status is valid",
        ):
            KPIResult(
                name="Test KPI",
                value=None,
                unit="ratio",
                status=KPIStatus.VALID,
                window=_window(),
            )

    def test_non_valid_status_requires_none_value(self) -> None:
        with pytest.raises(
            ValueError,
            match="value must be None when KPI status is not valid",
        ):
            KPIResult(
                name="Test KPI",
                value=1.0,
                unit="ratio",
                status=KPIStatus.INSUFFICIENT_DATA,
                window=_window(),
            )


class TestKPIResultFactories:
    """Tests for KPI result helper functions."""

    def test_valid_result_factory(self) -> None:
        result = valid_result(
            name="Actual Energy",
            value=1250.0,
            unit="kWh",
            window=_window(),
            sample_count=4,
        )

        assert result.name == "Actual Energy"
        assert result.value == 1250.0
        assert result.unit == "kWh"
        assert result.status is KPIStatus.VALID
        assert result.sample_count == 4
        assert result.message is None

    def test_insufficient_data_result_factory(self) -> None:
        result = insufficient_data_result(
            name="Performance Ratio",
            unit="ratio",
            window=_window(),
            sample_count=1,
        )

        assert result.value is None
        assert result.status is KPIStatus.INSUFFICIENT_DATA
        assert result.sample_count == 1
        assert result.message == ("Insufficient data for KPI calculation.")

    def test_invalid_input_result_factory(self) -> None:
        result = invalid_input_result(
            name="Capacity Factor",
            unit="%",
            window=_window(),
            message="Installed capacity must be positive.",
        )

        assert result.value is None
        assert result.status is KPIStatus.INVALID_INPUT
        assert result.sample_count == 0
        assert result.message == ("Installed capacity must be positive.")
