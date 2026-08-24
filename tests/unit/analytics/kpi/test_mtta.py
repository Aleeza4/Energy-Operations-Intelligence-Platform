"""Unit tests for EOIP MTTA KPI."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eoip.analytics.kpi.base import KPIStatus, KPIWindow
from eoip.analytics.kpi.mtta import calculate_mtta


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


class TestMTTA:
    """Tests for Mean Time To Acknowledge."""

    def test_calculates_mtta_for_single_alarm(self) -> None:
        result = calculate_mtta(
            acknowledgement_intervals=[
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
                        2,
                        15,
                        tzinfo=UTC,
                    ),
                )
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(15.0)
        assert result.name == "MTTA"
        assert result.unit == "minutes"
        assert result.sample_count == 1

    def test_calculates_average_acknowledgement_time(self) -> None:
        result = calculate_mtta(
            acknowledgement_intervals=[
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
                        1,
                        10,
                        tzinfo=UTC,
                    ),
                ),
                (
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
                        4,
                        20,
                        tzinfo=UTC,
                    ),
                ),
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(15.0)
        assert result.sample_count == 2

    def test_allows_immediate_acknowledgement(self) -> None:
        timestamp = datetime(
            2026,
            8,
            17,
            5,
            0,
            tzinfo=UTC,
        )

        result = calculate_mtta(
            acknowledgement_intervals=[
                (
                    timestamp,
                    timestamp,
                )
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.VALID
        assert result.value == pytest.approx(0.0)

    def test_returns_insufficient_data_for_empty_input(self) -> None:
        result = calculate_mtta(
            acknowledgement_intervals=[],
            window=_window(),
        )

        assert result.status is KPIStatus.INSUFFICIENT_DATA
        assert result.value is None
        assert result.sample_count == 0
        assert result.message == (
            "At least one acknowledgement interval is required " "for MTTA."
        )

    def test_rejects_naive_raised_timestamp(self) -> None:
        result = calculate_mtta(
            acknowledgement_intervals=[
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
                        2,
                        15,
                        tzinfo=UTC,
                    ),
                )
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == ("Acknowledgement timestamps must be timezone-aware.")

    def test_rejects_naive_acknowledged_timestamp(self) -> None:
        result = calculate_mtta(
            acknowledgement_intervals=[
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
                        2,
                        15,
                    ),
                )
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None

    def test_rejects_raised_time_before_window(self) -> None:
        result = calculate_mtta(
            acknowledgement_intervals=[
                (
                    datetime(
                        2026,
                        8,
                        16,
                        23,
                        59,
                        tzinfo=UTC,
                    ),
                    datetime(
                        2026,
                        8,
                        17,
                        0,
                        10,
                        tzinfo=UTC,
                    ),
                )
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == (
            "Alarm raised timestamps must fall within " "the KPI window."
        )

    def test_rejects_raised_time_at_window_end(self) -> None:
        result = calculate_mtta(
            acknowledgement_intervals=[
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
                        0,
                        10,
                        tzinfo=UTC,
                    ),
                )
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None

    def test_rejects_acknowledgement_before_alarm(self) -> None:
        result = calculate_mtta(
            acknowledgement_intervals=[
                (
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
                        3,
                        59,
                        tzinfo=UTC,
                    ),
                )
            ],
            window=_window(),
        )

        assert result.status is KPIStatus.INVALID_INPUT
        assert result.value is None
        assert result.message == (
            "Acknowledgement timestamp must not be earlier "
            "than alarm raised timestamp."
        )

    def test_preserves_window(self) -> None:
        window = _window()

        result = calculate_mtta(
            acknowledgement_intervals=[
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
                        2,
                        10,
                        tzinfo=UTC,
                    ),
                )
            ],
            window=window,
        )

        assert result.window is window
