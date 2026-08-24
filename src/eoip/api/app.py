"""FastAPI application factory for EOIP."""

from __future__ import annotations

from copy import deepcopy

from fastapi import FastAPI

from eoip.api.errors import register_exception_handlers
from eoip.api.routers import (
    admin,
    analytics,
    anomalies,
    auth,
    equipment,
    forecasts,
    health,
    operations,
    plants,
    recommendations,
    scada,
)
from eoip.config.settings import settings

OPENAPI_TAGS = [
    {"name": "Health", "description": "Process liveness and dependency readiness."},
    {"name": "Plants", "description": "Solar plant master data."},
    {"name": "Equipment", "description": "Operational equipment master data."},
    {"name": "SCADA", "description": "Bounded time-series telemetry reads."},
    {"name": "Operations", "description": "Alarm and incident intelligence."},
    {"name": "Analytics", "description": "Stored Phase 5 operational analytics."},
    {"name": "Forecasts", "description": "Persisted Phase 6 forecast outputs."},
    {"name": "Anomalies", "description": "Persisted Phase 7 anomaly outputs."},
    {
        "name": "Recommendations",
        "description": "Persisted Phase 9 optimization recommendations.",
    },
    {"name": "Authentication", "description": "OAuth2 bearer authentication."},
    {"name": "Administration", "description": "Role-protected API status."},
]


def create_app() -> FastAPI:
    """Create a fully configured EOIP FastAPI application."""
    application = FastAPI(
        title="Energy Operations Intelligence Platform API",
        summary="EOIP API",
        description=(
            "Versioned, typed access to EOIP operational data and persisted "
            "analytics, forecast, anomaly, and optimization outputs."
        ),
        version=settings.api_version,
        contact={"name": "EOIP Engineering"},
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    register_exception_handlers(application)

    prefix = settings.api_prefix
    for router in (
        health.router,
        auth.router,
        plants.router,
        equipment.router,
        scada.router,
        operations.alarms_router,
        operations.incidents_router,
        analytics.router,
        forecasts.router,
        anomalies.router,
        recommendations.router,
        admin.router,
    ):
        # FastAPI 0.141 transfers route ownership when including a router. A
        # copy keeps this application factory repeatable for tests and workers.
        application.include_router(deepcopy(router), prefix=prefix)

    return application


app = create_app()
