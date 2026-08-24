"""Equipment read endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from eoip.api.dependencies import Provider
from eoip.api.errors import APIError, ErrorResponse
from eoip.api.pagination import Pagination
from eoip.api.schemas import EquipmentResponse, Identifier, Page
from eoip.api.security import AuthenticatedUser, reader_access

router = APIRouter(prefix="/equipment", tags=["Equipment"])
Reader = Annotated[AuthenticatedUser, Depends(reader_access)]


@router.get("", response_model=Page[EquipmentResponse], summary="List equipment")
def list_equipment(
    provider: Provider,
    pagination: Pagination,
    _: Reader,
    plant_id: Identifier | None = None,
    equipment_type: Annotated[str | None, Query(max_length=40)] = None,
    status: Annotated[str | None, Query(max_length=30)] = None,
) -> Page[EquipmentResponse]:
    items, total = provider.list_equipment(
        plant_id=plant_id,
        equipment_type=equipment_type,
        status=status,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return Page(
        items=items,
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.get(
    "/{equipment_id}",
    response_model=EquipmentResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get equipment",
)
def get_equipment(equipment_id: Identifier, provider: Provider, _: Reader) -> object:
    equipment = provider.get_equipment(equipment_id)
    if equipment is None:
        raise APIError(
            status_code=404,
            code="equipment_not_found",
            message=f"Equipment '{equipment_id}' was not found.",
        )
    return equipment
