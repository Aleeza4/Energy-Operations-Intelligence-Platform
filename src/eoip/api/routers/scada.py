"""Bounded time-series SCADA endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from eoip.api.dependencies import Provider
from eoip.api.pagination import Pagination
from eoip.api.schemas import Identifier, Page, SCADAResponse, TimeRange
from eoip.api.security import AuthenticatedUser, reader_access

router = APIRouter(prefix="/scada", tags=["SCADA"])
Reader = Annotated[AuthenticatedUser, Depends(reader_access)]


def _scada_page(
    *,
    provider: Provider,
    pagination: Pagination,
    time_range: TimeRange,
    plant_id: Identifier | None,
    equipment_id: Identifier | None,
    latest: bool,
) -> Page[SCADAResponse]:
    items, total = provider.list_scada(
        plant_id=plant_id,
        equipment_id=equipment_id,
        start_time=time_range.start_time,
        end_time=time_range.end_time,
        limit=pagination.limit,
        offset=pagination.offset,
        latest=latest,
    )
    return Page(
        items=items,
        total=total,
        limit=min(pagination.limit, 100) if latest else pagination.limit,
        offset=pagination.offset,
    )


@router.get("", response_model=Page[SCADAResponse], summary="Query SCADA telemetry")
def list_scada(
    provider: Provider,
    pagination: Pagination,
    time_range: TimeRange,
    _: Reader,
    plant_id: Identifier | None = None,
    equipment_id: Identifier | None = None,
) -> Page[SCADAResponse]:
    """Return a bounded, filtered SCADA time-series page."""
    return _scada_page(
        provider=provider,
        pagination=pagination,
        time_range=time_range,
        plant_id=plant_id,
        equipment_id=equipment_id,
        latest=False,
    )


@router.get(
    "/latest",
    response_model=Page[SCADAResponse],
    summary="Get latest SCADA telemetry",
)
def latest_scada(
    provider: Provider,
    pagination: Pagination,
    time_range: TimeRange,
    _: Reader,
    plant_id: Identifier | None = None,
    equipment_id: Identifier | None = None,
) -> Page[SCADAResponse]:
    """Return at most 100 latest telemetry observations."""
    return _scada_page(
        provider=provider,
        pagination=pagination,
        time_range=time_range,
        plant_id=plant_id,
        equipment_id=equipment_id,
        latest=True,
    )
