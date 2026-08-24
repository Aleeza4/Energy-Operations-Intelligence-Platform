"""Non-destructive administrative status endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from eoip.api.schemas import AdminStatusResponse
from eoip.api.security import AuthenticatedUser, admin_access
from eoip.config.settings import settings

router = APIRouter(prefix="/admin", tags=["Administration"])
Admin = Annotated[AuthenticatedUser, Depends(admin_access)]


@router.get("/status", response_model=AdminStatusResponse, summary="Get API status")
def admin_status(user: Admin) -> AdminStatusResponse:
    """Return safe configuration status for administrators."""
    return AdminStatusResponse(
        service="eoip-api",
        environment=settings.api_environment,
        authenticated_user=user.username,
        role=user.role,
        database_configured=bool(settings.database_password),
    )
