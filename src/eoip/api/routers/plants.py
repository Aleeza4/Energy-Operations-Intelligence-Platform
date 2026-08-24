"""Plant read endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from eoip.api.dependencies import Provider
from eoip.api.errors import APIError, ErrorResponse
from eoip.api.pagination import Pagination
from eoip.api.schemas import Identifier, Page, PlantResponse
from eoip.api.security import AuthenticatedUser, reader_access

router = APIRouter(prefix="/plants", tags=["Plants"])
Reader = Annotated[AuthenticatedUser, Depends(reader_access)]


@router.get("", response_model=Page[PlantResponse], summary="List plants")
def list_plants(
    provider: Provider,
    pagination: Pagination,
    _: Reader,
    status: Annotated[str | None, Query(max_length=30)] = None,
) -> Page[PlantResponse]:
    items, total = provider.list_plants(
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
    "/{plant_id}",
    response_model=PlantResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get a plant",
)
def get_plant(plant_id: Identifier, provider: Provider, _: Reader) -> object:
    plant = provider.get_plant(plant_id)
    if plant is None:
        raise APIError(
            status_code=404,
            code="plant_not_found",
            message=f"Plant '{plant_id}' was not found.",
        )
    return plant
