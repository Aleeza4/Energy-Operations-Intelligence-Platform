"""Unit tests for EOIP MTBF KPI."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eoip.analytics.kpi.base import KPIStatus, KPIWindow
from eoip.analytics.kpi.mtbf import calculate_mtbf


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


class TestMTBF:
    """Tests for Mean Time Between Failures."""

    def test_calculates_mtbf_from_even_intervals(self) -> None:
        result = calculate_mtbf(
            failure_times=[
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
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(4.0)
        assert result.unit == "hours"
        assert result.name == "MTBF"
        assert result.sample_count == 2

    def test_sorts_failure_times_before_calculation(self) -> None:
        result = calculate_mtbf(
            failure_times=[
                datetime(
                    2026,
                    8,
                    17,
                    10,
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
                datetime(
                    2026,
                    8,
                    17,
                    6,
                    0,
                    tzinfo=UTC,
                ),
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(4.0)

    def test_calculates_average_of_uneven_intervals(self) -> None:
        result = calculate_mtbf(
            failure_times=[
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
                    4,
                    0,
                    tzinfo=UTC,
                ),
                datetime(
                    2026,
                    8,
                    17,
                    11,
                    0,
                    tzinfo=UTC,
                ),
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(5.0)
        assert result.sample_count == 2

    def test_returns_insufficient_data_for_no_failures(self) -> None:
        result = calculate_mtbf(
            failure_times=[],
            window=_window(),
        )

        assert result.status is KPIStatus.INSUFFICIENT_DATA
        assert result.value is None
        assert result.sample_count == 0
        assert result.message == ("At least two failure events are required for MTBF.")

    def test_returns_insufficient_data_for_one_failure(self) -> None:
        result = calculate_mtbf(
            failure_times=[
                datetime(
                    2026,
                    8,
                    17,
                    3,
                    0,
                    tzinfo=UTC,
                )
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INSUFFICIENT_DATA
        assert result.value is None
        assert result.sample_count == 1

    def test_rejects_naive_failure_timestamp(self) -> None:
        result = calculate_mtbf(
            failure_times=[
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
                    6,
                    0,
                    tzinfo=UTC,
                ),
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Failure timestamps must be timezone-aware.")

    def test_rejects_failure_before_window(self) -> None:
        result = calculate_mtbf(
            failure_times=[
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
                    6,
                    0,
                    tzinfo=UTC,
                ),
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Failure timestamps must fall within the KPI window.")

    def test_rejects_failure_at_window_end(self) -> None:
        result = calculate_mtbf(
            failure_times=[
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
                    18,
                    0,
                    0,
                    tzinfo=UTC,
                ),
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None

    def test_rejects_duplicate_failure_timestamps(self) -> None:
        timestamp = datetime(
            2026,
            8,
            17,
            6,
            0,
            tzinfo=UTC,
        )

        result = calculate_mtbf(
            failure_times=[
                timestamp,
                timestamp,
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == (
            "Failure timestamps must represent distinct " "chronological events."
        )

    def test_preserves_window(self) -> None:
        window = _window()

        result = calculate_mtbf(
            failure_times=[
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
                    6,
                    0,
                    tzinfo=UTC,
                ),
            ],
            window=window,
        )

        assert result.window is window
