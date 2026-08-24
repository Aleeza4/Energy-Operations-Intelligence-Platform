"""Alarm and incident read endpoints."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from eoip.api.dependencies import Provider
from eoip.api.errors import APIError, ErrorResponse
from eoip.api.pagination import Pagination
from eoip.api.schemas import (
    AlarmResponse,
    Identifier,
    IncidentResponse,
    Page,
    TimeRange,
)
from eoip.api.security import AuthenticatedUser, reader_access

alarms_router = APIRouter(prefix="/alarms", tags=["Operations"])
incidents_router = APIRouter(prefix="/incidents", tags=["Operations"])
Reader = Annotated[AuthenticatedUser, Depends(reader_access)]
Severity = Literal["critical", "high", "medium", "low"]


@alarms_router.get("", response_model=Page[AlarmResponse], summary="List alarms")
def list_alarms(
    provider: Provider,
    pagination: Pagination,
    time_range: TimeRange,
    _: Reader,
    plant_id: Identifier | None = None,
    equipment_id: Identifier | None = None,
    severity: Severity | None = None,
    status: Annotated[str | None, Query(max_length=30)] = None,
) -> Page[AlarmResponse]:
    items, total = provider.list_alarms(
        plant_id=plant_id,
        equipment_id=equipment_id,
        severity=severity,
        status=status,
        start_time=time_range.start_time,
        end_time=time_range.end_time,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return Page(
        items=items,
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@alarms_router.get(
    "/{alarm_id}",
    response_model=AlarmResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get an alarm",
)
def get_alarm(alarm_id: Identifier, provider: Provider, _: Reader) -> object:
    alarm = provider.get_alarm(alarm_id)
    if alarm is None:
        raise APIError(
            status_code=404,
            code="alarm_not_found",
            message=f"Alarm '{alarm_id}' was not found.",
        )
    return alarm


@incidents_router.get(
    "",
    response_model=Page[IncidentResponse],
    summary="List incidents",
)
def list_incidents(
    provider: Provider,
    pagination: Pagination,
    time_range: TimeRange,
    _: Reader,
    plant_id: Identifier | None = None,
    equipment_id: Identifier | None = None,
    severity: Severity | None = None,
    status: Annotated[str | None, Query(max_length=30)] = None,
) -> Page[IncidentResponse]:
    items, total = provider.list_incidents(
        plant_id=plant_id,
        equipment_id=equipment_id,
        severity=severity,
        status=status,
        start_time=time_range.start_time,
        end_time=time_range.end_time,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return Page(
        items=items,
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@incidents_router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get an incident",
)
def get_incident(incident_id: Identifier, provider: Provider, _: Reader) -> object:
    incident = provider.get_incident(incident_id)
    if incident is None:
        raise APIError(
            status_code=404,
            code="incident_not_found",
            message=f"Incident '{incident_id}' was not found.",
        )
    return incident
