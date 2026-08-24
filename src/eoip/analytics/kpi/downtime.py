"""Downtime analytics calculations for EOIP."""

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


def calculate_total_downtime(
    *,
    downtime_intervals: Iterable[tuple[datetime, datetime]],
    window: KPIWindow,
) -> KPIResult:
    """Calculate total downtime in hours.

    Each downtime interval is represented as:

        (downtime_started_at, downtime_ended_at)

    Every interval must start within the KPI window and end later than
    its corresponding start time.
    """
    intervals = list(downtime_intervals)

    if not intervals:
        return insufficient_data_result(
            name="Total Downtime",
            unit="hours",
            window=window,
            message="At least one downtime interval is required.",
        )

    total_downtime_hours = 0.0

    for started_at, ended_at in intervals:
        if started_at.tzinfo is None or ended_at.tzinfo is None:
            return invalid_input_result(
                name="Total Downtime",
                unit="hours",
                window=window,
                message="Downtime timestamps must be timezone-aware.",
            )

        if not (window.start_at <= started_at < window.end_at):
            return invalid_input_result(
                name="Total Downtime",
                unit="hours",
                window=window,
                message=(
                    "Downtime start timestamps must fall within " "the KPI window."
                ),
            )

        if ended_at <= started_at:
            return invalid_input_result(
                name="Total Downtime",
                unit="hours",
                window=window,
                message=(
                    "Downtime end timestamp must be later than "
                    "downtime start timestamp."
                ),
            )

        total_downtime_hours += (ended_at - started_at).total_seconds() / 3600.0

    return valid_result(
        name="Total Downtime",
        value=total_downtime_hours,
        unit="hours",
        window=window,
        sample_count=len(intervals),
    )


def calculate_downtime_percentage(
    *,
    downtime_hours: float,
    window: KPIWindow,
) -> KPIResult:
    """Calculate downtime as a percentage of the KPI window."""
    if downtime_hours < 0:
        return invalid_input_result(
            name="Downtime Percentage",
            unit="%",
            window=window,
            message="Downtime hours must not be negative.",
        )

    if downtime_hours > window.duration_hours:
        return invalid_input_result(
            name="Downtime Percentage",
            unit="%",
            window=window,
            message=("Downtime hours must not exceed the KPI window duration."),
        )

    downtime_pct = (downtime_hours / window.duration_hours) * 100.0

    return valid_result(
        name="Downtime Percentage",
        value=downtime_pct,
        unit="%",
        window=window,
        sample_count=1,
    )
