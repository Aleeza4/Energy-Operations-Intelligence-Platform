"""Unit tests for EOIP downtime analytics."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eoip.analytics.kpi.base import KPIStatus, KPIWindow
from eoip.analytics.kpi.downtime import (
    calculate_downtime_percentage,
    calculate_total_downtime,
)


def _window() -> KPIWindow:
    """Return a valid 24-hour KPI window."""
    return KPIWindow(
        start_at=datetime(
            2026,
            8,
            17,
            0,
            0,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            18,
            0,
            0,
            tzinfo=UTC,
        ),
    )


class TestTotalDowntime:
    """Tests for total downtime calculation."""

    def test_calculates_single_downtime_interval(self) -> None:
        result = calculate_total_downtime(
            downtime_intervals=[
                (
                    datetime(
                        2026,
                        8,
                        17,
                        2,
                        0,
                        tzinfo=UTC,
                    ),
                    datetime(
                        2026,
                        8,
                        17,
                        5,
                        0,
                        tzinfo=UTC,
                    ),
                )
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(3.0)
        assert result.name == "Total Downtime"
        assert result.unit == "hours"
        assert result.sample_count == 1

    def test_sums_multiple_downtime_intervals(self) -> None:
        result = calculate_total_downtime(
            downtime_intervals=[
                (
                    datetime(
                        2026,
                        8,
                        17,
                        1,
                        0,
                        tzinfo=UTC,
                    ),
                    datetime(
                        2026,
                        8,
                        17,
                        3,
                        0,
                        tzinfo=UTC,
                    ),
                ),
                (
                    datetime(
                        2026,
                        8,
                        17,
                        6,
                        0,
                        tzinfo=UTC,
                    ),
                    datetime(
                        2026,
                        8,
                        17,
                        9,
                        0,
                        tzinfo=UTC,
                    ),
                ),
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(5.0)
        assert result.sample_count == 2

    def test_returns_insufficient_data_for_empty_input(self) -> None:
        result = calculate_total_downtime(
            downtime_intervals=[],
            window=_window(),
        )

        assert result.status is KPIStatus.INSUFFICIENT_DATA
        assert result.value is None
        assert result.sample_count == 0
        assert result.message == ("At least one downtime interval is required.")

    def test_rejects_naive_start_timestamp(self) -> None:
        result = calculate_total_downtime(
            downtime_intervals=[
                (
                    datetime(
                        2026,
                        8,
                        17,
                        2,
                        0,
                    ),
                    datetime(
                        2026,
                        8,
                        17,
                        5,
                        0,
                        tzinfo=UTC,
                    ),
                )
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Downtime timestamps must be timezone-aware.")

    def test_rejects_naive_end_timestamp(self) -> None:
        result = calculate_total_downtime(
            downtime_intervals=[
                (
                    datetime(
                        2026,
                        8,
                        17,
                        2,
                        0,
                        tzinfo=UTC,
                    ),
                    datetime(
                        2026,
                        8,
                        17,
                        5,
                        0,
                    ),
                )
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None

    def test_rejects_start_before_window(self) -> None:
        result = calculate_total_downtime(
            downtime_intervals=[
                (
                    datetime(
                        2026,
                        8,
                        16,
                        23,
                        0,
                        tzinfo=UTC,
                    ),
                    datetime(
                        2026,
                        8,
                        17,
                        2,
                        0,
                        tzinfo=UTC,
                    ),
                )
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == (
            "Downtime start timestamps must fall within " "the KPI window."
        )

    def test_rejects_start_at_window_end(self) -> None:
        result = calculate_total_downtime(
            downtime_intervals=[
                (
                    datetime(
                        2026,
                        8,
                        18,
                        0,
                        0,
                        tzinfo=UTC,
                    ),
                    datetime(
                        2026,
                        8,
                        18,
                        1,
                        0,
                        tzinfo=UTC,
                    ),
                )
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None

    def test_rejects_end_equal_to_start(self) -> None:
        timestamp = datetime(
            2026,
            8,
            17,
            5,
            0,
            tzinfo=UTC,
        )

        result = calculate_total_downtime(
            downtime_intervals=[
                (
                    timestamp,
                    timestamp,
                )
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == (
            "Downtime end timestamp must be later than " "downtime start timestamp."
        )

    def test_rejects_end_before_start(self) -> None:
        result = calculate_total_downtime(
            downtime_intervals=[
                (
                    datetime(
                        2026,
                        8,
                        17,
                        5,
                        0,
                        tzinfo=UTC,
                    ),
                    datetime(
                        2026,
                        8,
                        17,
                        4,
                        0,
                        tzinfo=UTC,
                    ),
                )
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None


class TestDowntimePercentage:
    """Tests for downtime percentage calculation."""

    def test_calculates_downtime_percentage(self) -> None:
        result = calculate_downtime_percentage(
            downtime_hours=6.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(25.0)
        assert result.name == "Downtime Percentage"
        assert result.unit == "%"
        assert result.sample_count == 1

    def test_allows_zero_downtime(self) -> None:
        result = calculate_downtime_percentage(
            downtime_hours=0.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_allows_full_window_downtime(self) -> None:
        result = calculate_downtime_percentage(
            downtime_hours=24.0,
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(100.0)

    def test_rejects_negative_downtime(self) -> None:
        result = calculate_downtime_percentage(
            downtime_hours=-1.0,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Downtime hours must not be negative.")

    def test_rejects_downtime_above_window_duration(self) -> None:
        result = calculate_downtime_percentage(
            downtime_hours=25.0,
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == (
            "Downtime hours must not exceed the KPI window duration."
        )

    def test_preserves_window(self) -> None:
        window = _window()

        result = calculate_downtime_percentage(
            downtime_hours=2.0,
            window=window,
        )

        assert result.window is window
