"""Unit tests for EOIP MTTR KPI."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eoip.analytics.kpi.base import KPIStatus, KPIWindow
from eoip.analytics.kpi.mttr import calculate_mttr


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


class TestMTTR:
    """Tests for Mean Time To Repair."""

    def test_calculates_mttr_for_single_repair(self) -> None:
        result = calculate_mttr(
            repair_intervals=[
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
        assert result.name == "MTTR"
        assert result.unit == "hours"
        assert result.sample_count == 1

    def test_calculates_average_repair_duration(self) -> None:
        result = calculate_mttr(
            repair_intervals=[
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
                        10,
                        0,
                        tzinfo=UTC,
                    ),
                ),
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(3.0)
        assert result.sample_count == 2

    def test_returns_insufficient_data_for_empty_input(self) -> None:
        result = calculate_mttr(
            repair_intervals=[],
            window=_window(),
        )

        assert result.status is KPIStatus.INSUFFICIENT_DATA
        assert result.value is None
        assert result.sample_count == 0
        assert result.message == ("At least one repair interval is required for MTTR.")

    def test_rejects_naive_start_timestamp(self) -> None:
        result = calculate_mttr(
            repair_intervals=[
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
        assert result.message == ("Repair timestamps must be timezone-aware.")

    def test_rejects_naive_completion_timestamp(self) -> None:
        result = calculate_mttr(
            repair_intervals=[
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
        result = calculate_mttr(
            repair_intervals=[
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
            "Repair start timestamps must fall within " "the KPI window."
        )

    def test_rejects_start_at_window_end(self) -> None:
        result = calculate_mttr(
            repair_intervals=[
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

    def test_rejects_completion_equal_to_start(self) -> None:
        timestamp = datetime(
            2026,
            8,
            17,
            5,
            0,
            tzinfo=UTC,
        )

        result = calculate_mttr(
            repair_intervals=[
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
            "Repair completion timestamp must be later " "than repair start timestamp."
        )

    def test_rejects_completion_before_start(self) -> None:
        result = calculate_mttr(
            repair_intervals=[
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

    def test_preserves_window(self) -> None:
        window = _window()

        result = calculate_mttr(
            repair_intervals=[
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
                        4,
                        0,
                        tzinfo=UTC,
                    ),
                )
            ],
            window=window,
        )

        assert result.window is window
