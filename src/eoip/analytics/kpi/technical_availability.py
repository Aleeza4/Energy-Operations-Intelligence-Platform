"""Technical Availability KPI calculation for EOIP."""

from __future__ import annotations

from collections.abc import Iterable

from eoip.analytics.kpi.base import (
    KPIResult,
    KPIWindow,
    insufficient_data_result,
    invalid_input_result,
    valid_result,
)


def calculate_technical_availability(
    *,
    equipment_available: Iterable[bool | None],
    window: KPIWindow,
) -> KPIResult:
    """Calculate technical availability as a percentage.

    Technical availability is calculated as:

        available observations / valid observations * 100
    """
    values = [value for value in equipment_available if value is not None]

    if not values:
        return insufficient_data_result(
            name="Technical Availability",
            unit="%",
            window=window,
            message=("No valid equipment availability observations " "are available."),
        )

    if any(not isinstance(value, bool) for value in values):
        return invalid_input_result(
            name="Technical Availability",
            unit="%",
            window=window,
            message=("Equipment availability observations must be boolean."),
        )

    available_count = sum(1 for value in values if value)

    availability_pct = (available_count / len(values)) * 100.0

    return valid_result(
        name="Technical Availability",
        value=availability_pct,
        unit="%",
        window=window,
        sample_count=len(values),
    )
