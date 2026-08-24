"""API liveness and readiness routes."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from eoip.api.dependencies import get_session_factory
from eoip.api.schemas import HealthResponse, ReadinessResponse
from eoip.config.settings import settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse, summary="API liveness")
def health() -> HealthResponse:
    """Return process liveness without touching external dependencies."""
    return HealthResponse(
        status="healthy",
        service="eoip-api",
        version=settings.api_version,
        environment=settings.api_environment,
    )


@router.get("/ready", response_model=ReadinessResponse, summary="API readiness")
def readiness() -> ReadinessResponse:
    """Report dependency readiness without converting liveness into an outage."""
    database_status = "available"
    try:
        with get_session_factory()() as session:
            session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        database_status = "unavailable"
    return ReadinessResponse(
        status="ready" if database_status == "available" else "degraded",
        service="eoip-api",
        version=settings.api_version,
        environment=settings.api_environment,
        dependencies={"database": database_status},
    )
