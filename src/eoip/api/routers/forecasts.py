"""Persisted forecast read endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from eoip.api.dependencies import Provider
from eoip.api.errors import APIError, ErrorResponse
from eoip.api.pagination import Pagination
from eoip.api.schemas import ForecastResponse, Identifier, Page
from eoip.api.security import AuthenticatedUser, reader_access

router = APIRouter(prefix="/forecasts", tags=["Forecasts"])
Reader = Annotated[AuthenticatedUser, Depends(reader_access)]


@router.get("", response_model=Page[ForecastResponse], summary="List forecasts")
def list_forecasts(
    provider: Provider,
    pagination: Pagination,
    _: Reader,
    model_name: Annotated[str | None, Query(max_length=255)] = None,
    horizon: Annotated[int, Query(ge=1, le=365)] = 30,
) -> Page[ForecastResponse]:
    """Read persisted forecasts without training a model in the request."""
    items, total = provider.list_forecasts(
        model_name=model_name,
        horizon=horizon,
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
    "/{forecast_id}",
    response_model=ForecastResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get a forecast",
)
def get_forecast(forecast_id: Identifier, provider: Provider, _: Reader) -> object:
    forecast = provider.get_forecast(forecast_id)
    if forecast is None:
        raise APIError(
            status_code=404,
            code="forecast_not_found",
            message=f"Forecast '{forecast_id}' was not found.",
        )
    return forecast
