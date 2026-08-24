"""Stored SQL analytics endpoints."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from eoip.api.dependencies import Provider
from eoip.api.schemas import AnalyticsSummaryResponse, Identifier, TimeRange
from eoip.api.security import AuthenticatedUser, reader_access

router = APIRouter(prefix="/analytics", tags=["Analytics"])
Reader = Annotated[AuthenticatedUser, Depends(reader_access)]
MetricGroup = Literal[
    "plant_operations",
    "scada_hourly",
    "open_alarms",
    "open_incidents",
]


@router.get(
    "/summary",
    response_model=AnalyticsSummaryResponse,
    summary="Get operational analytics summary",
)
def analytics_summary(
    provider: Provider,
    time_range: TimeRange,
    _: Reader,
    plant_id: Identifier | None = None,
    metrics: Annotated[list[MetricGroup] | None, Query()] = None,
) -> AnalyticsSummaryResponse:
    """Delegate stored operational analytics to the Phase 4/5 service layer."""
    result = provider.analytics_summary(
        plant_id=plant_id,
        start_time=time_range.start_time,
        end_time=time_range.end_time,
    )
    selected = set(metrics or result)
    return AnalyticsSummaryResponse(
        plant_id=plant_id,
        start_time=time_range.start_time,
        end_time=time_range.end_time,
        units={
            "avg_active_power_kw": "kW",
            "total_energy_kwh": "kWh",
            "alarm_count": "count",
            "incident_count": "count",
        },
        plant_operations=(
            result["plant_operations"] if "plant_operations" in selected else []
        ),
        scada_hourly=result["scada_hourly"] if "scada_hourly" in selected else [],
        open_alarms=result["open_alarms"] if "open_alarms" in selected else [],
        open_incidents=(
            result["open_incidents"] if "open_incidents" in selected else []
        ),
    )


@router.get(
    "/plants/{plant_id}",
    response_model=AnalyticsSummaryResponse,
    summary="Get plant analytics",
)
def plant_analytics(
    plant_id: Identifier,
    provider: Provider,
    time_range: TimeRange,
    user: Reader,
) -> AnalyticsSummaryResponse:
    """Return analytics constrained to one plant."""
    return analytics_summary(
        provider=provider,
        time_range=time_range,
        _=user,
        plant_id=plant_id,
        metrics=None,
    )
