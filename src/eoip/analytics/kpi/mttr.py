"""Mean Time To Repair KPI calculation for EOIP."""

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


def calculate_mttr(
    *,
    repair_intervals: Iterable[tuple[datetime, datetime]],
    window: KPIWindow,
) -> KPIResult:
    """Calculate mean time to repair in hours.

    Each repair interval is represented as:

        (failure_started_at, repair_completed_at)

    MTTR is calculated as the average repair duration across all
    valid repair intervals.
    """
    intervals = list(repair_intervals)

    if not intervals:
        return insufficient_data_result(
            name="MTTR",
            unit="hours",
            window=window,
            message="At least one repair interval is required for MTTR.",
        )

    repair_durations_hours: list[float] = []

    for started_at, completed_at in intervals:
        if started_at.tzinfo is None or completed_at.tzinfo is None:
            return invalid_input_result(
                name="MTTR",
                unit="hours",
                window=window,
                message="Repair timestamps must be timezone-aware.",
            )

        if not (window.start_at <= started_at < window.end_at):
            return invalid_input_result(
                name="MTTR",
                unit="hours",
                window=window,
                message=("Repair start timestamps must fall within " "the KPI window."),
            )

        if completed_at <= started_at:
            return invalid_input_result(
                name="MTTR",
                unit="hours",
                window=window,
                message=(
                    "Repair completion timestamp must be later "
                    "than repair start timestamp."
                ),
            )

        repair_duration_hours = (completed_at - started_at).total_seconds() / 3600.0

        repair_durations_hours.append(repair_duration_hours)

    mttr_hours = sum(repair_durations_hours) / len(repair_durations_hours)

    return valid_result(
        name="MTTR",
        value=mttr_hours,
        unit="hours",
        window=window,
        sample_count=len(repair_durations_hours),
    )
