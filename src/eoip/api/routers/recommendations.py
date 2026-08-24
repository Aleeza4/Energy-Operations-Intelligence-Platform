"""Optimization recommendation read endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from eoip.api.dependencies import Provider
from eoip.api.errors import APIError, ErrorResponse
from eoip.api.pagination import Pagination
from eoip.api.schemas import (
    Identifier,
    Page,
    RecommendationResponse,
    RecommendationType,
)
from eoip.api.security import AuthenticatedUser, reader_access

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])
Reader = Annotated[AuthenticatedUser, Depends(reader_access)]


@router.get(
    "",
    response_model=Page[RecommendationResponse],
    summary="List persisted optimization recommendations",
)
def list_recommendations(
    provider: Provider,
    pagination: Pagination,
    _: Reader,
    plant_id: Identifier | None = None,
    equipment_id: Identifier | None = None,
    recommendation_type: RecommendationType | None = None,
    minimum_priority: Annotated[float | None, Query(ge=0, le=1)] = None,
    economically_justified: bool | None = None,
) -> Page[RecommendationResponse]:
    items, total = provider.list_recommendations(
        plant_id=plant_id,
        equipment_id=equipment_id,
        recommendation_type=(
            recommendation_type.value if recommendation_type is not None else None
        ),
        minimum_priority=minimum_priority,
        economically_justified=economically_justified,
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
    "/{recommendation_id}",
    response_model=RecommendationResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get a recommendation",
)
def get_recommendation(
    recommendation_id: Identifier,
    provider: Provider,
    _: Reader,
) -> object:
    recommendation = provider.get_recommendation(recommendation_id)
    if recommendation is None:
        raise APIError(
            status_code=404,
            code="recommendation_not_found",
            message=f"Recommendation '{recommendation_id}' was not found.",
        )
    return recommendation
