"""Mean Time To Acknowledge KPI calculation for EOIP."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from eoip.analytics.kpi.base import (
    KPIResult,
    KPIWindow,
    insufficient_data_result,
    invalid_input_result,
    valid_result,
)


def calculate_mtta(
    *,
    acknowledgement_intervals: Iterable[tuple[datetime, datetime]],
    window: KPIWindow,
) -> KPIResult:
    """Calculate mean time to acknowledge in minutes.

    Each acknowledgement interval is represented as:

        (alarm_raised_at, alarm_acknowledged_at)

    MTTA is calculated as the average acknowledgement delay across all
    valid alarm acknowledgement intervals.
    """
    intervals = list(acknowledgement_intervals)

    if not intervals:
        return insufficient_data_result(
            name="MTTA",
            unit="minutes",
            window=window,
            message=("At least one acknowledgement interval is required " "for MTTA."),
        )

    acknowledgement_durations_minutes: list[float] = []

    for raised_at, acknowledged_at in intervals:
        if raised_at.tzinfo is None or acknowledged_at.tzinfo is None:
            return invalid_input_result(
                name="MTTA",
                unit="minutes",
                window=window,
                message=("Acknowledgement timestamps must be timezone-aware."),
            )

        if not (window.start_at <= raised_at < window.end_at):
            return invalid_input_result(
                name="MTTA",
                unit="minutes",
                window=window,
                message=("Alarm raised timestamps must fall within " "the KPI window."),
            )

        if acknowledged_at < raised_at:
            return invalid_input_result(
                name="MTTA",
                unit="minutes",
                window=window,
                message=(
                    "Acknowledgement timestamp must not be earlier "
                    "than alarm raised timestamp."
                ),
            )

        acknowledgement_duration_minutes = (
            acknowledged_at - raised_at
        ).total_seconds() / 60.0

        acknowledgement_durations_minutes.append(acknowledgement_duration_minutes)

    mtta_minutes = sum(acknowledgement_durations_minutes) / len(
        acknowledgement_durations_minutes
    )

    return valid_result(
        name="MTTA",
        value=mtta_minutes,
        unit="minutes",
        window=window,
        sample_count=len(acknowledgement_durations_minutes),
    )
