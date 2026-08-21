"""Persisted anomaly read and evaluation endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from eoip.api.dependencies import Provider
from eoip.api.errors import APIError, ErrorResponse
from eoip.api.pagination import Pagination
from eoip.api.schemas import (
    AnomalyEvaluationResponse,
    AnomalyResponse,
    Identifier,
    Page,
    TimeRange,
)
from eoip.api.security import AuthenticatedUser, reader_access

router = APIRouter(prefix="/anomalies", tags=["Anomalies"])
Reader = Annotated[AuthenticatedUser, Depends(reader_access)]


@router.get("", response_model=Page[AnomalyResponse], summary="List anomalies")
def list_anomalies(
    provider: Provider,
    pagination: Pagination,
    time_range: TimeRange,
    _: Reader,
    method: Annotated[str | None, Query(max_length=255)] = None,
) -> Page[AnomalyResponse]:
    items, total = provider.list_anomalies(
        method=method,
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


@router.get(
    "/evaluation",
    response_model=list[AnomalyEvaluationResponse],
    summary="Get stored anomaly evaluation summary",
)
def anomaly_evaluation(provider: Provider, _: Reader) -> list[dict[str, object]]:
    """Expose stored run volume without inventing unavailable labels."""
    return provider.anomaly_evaluation()


@router.get(
    "/{anomaly_id}",
    response_model=AnomalyResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get an anomaly",
)
def get_anomaly(anomaly_id: Identifier, provider: Provider, _: Reader) -> object:
    anomaly = provider.get_anomaly(anomaly_id)
    if anomaly is None:
        raise APIError(
            status_code=404,
            code="anomaly_not_found",
            message=f"Anomaly '{anomaly_id}' was not found.",
        )
    return anomaly
