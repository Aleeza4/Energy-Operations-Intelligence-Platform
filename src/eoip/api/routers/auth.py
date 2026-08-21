"""OAuth2-compatible token and identity endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from eoip.api.errors import APIError
from eoip.api.schemas import TokenResponse, UserResponse
from eoip.api.security import (
    AuthenticatedUser,
    AuthService,
    get_auth_service,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/token", response_model=TokenResponse, summary="Create access token")
def create_token(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Authenticate a bootstrap/API user and issue an expiring signed token."""
    user = auth_service.authenticate(form.username, form.password)
    if user is None:
        raise APIError(
            status_code=401,
            code="invalid_credentials",
            message="The username or password is incorrect.",
        )
    return TokenResponse(
        access_token=auth_service.create_token(user),
        expires_in=auth_service.expires_in_seconds,
    )


@router.get("/me", response_model=UserResponse, summary="Get current user")
def current_user(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> UserResponse:
    """Return the validated bearer principal."""
    return UserResponse(username=user.username, role=user.role)
