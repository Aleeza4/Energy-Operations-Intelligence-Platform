"""Mean Time Between Failures KPI calculation for EOIP."""

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


def calculate_mtbf(
    *,
    failure_times: Iterable[datetime],
    window: KPIWindow,
) -> KPIResult:
    """Calculate mean time between failures in hours.

    MTBF is calculated from the time differences between consecutive
    failure events occurring inside the KPI window.

    At least two failure events are required.
    """
    failures = list(failure_times)

    if len(failures) < 2:
        return insufficient_data_result(
            name="MTBF",
            unit="hours",
            window=window,
            sample_count=len(failures),
            message="At least two failure events are required for MTBF.",
        )

    for failure_time in failures:
        if failure_time.tzinfo is None:
            return invalid_input_result(
                name="MTBF",
                unit="hours",
                window=window,
                message="Failure timestamps must be timezone-aware.",
            )

        if not (window.start_at <= failure_time < window.end_at):
            return invalid_input_result(
                name="MTBF",
                unit="hours",
                window=window,
                message=("Failure timestamps must fall within the KPI window."),
            )

    failures.sort()

    intervals_hours = [
        (current_failure - previous_failure).total_seconds() / 3600.0
        for previous_failure, current_failure in zip(
            failures,
            failures[1:],
            strict=False,
        )
    ]

    if any(interval <= 0 for interval in intervals_hours):
        return invalid_input_result(
            name="MTBF",
            unit="hours",
            window=window,
            message=(
                "Failure timestamps must represent distinct " "chronological events."
            ),
        )

    mtbf_hours = sum(intervals_hours) / len(intervals_hours)

    return valid_result(
        name="MTBF",
        value=mtbf_hours,
        unit="hours",
        window=window,
        sample_count=len(intervals_hours),
    )
