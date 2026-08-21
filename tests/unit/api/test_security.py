"""Unit tests for EOIP API authentication primitives."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from eoip.api.errors import APIError
from eoip.api.schemas import Role
from eoip.api.security import (
    AuthenticatedUser,
    AuthService,
    UserRecord,
    hash_password,
    verify_password,
)


def auth_service() -> AuthService:
    """Return deterministic test authentication."""
    return AuthService(
        secret="test-secret-that-is-at-least-32-characters",
        expiry_minutes=15,
        users=(
            UserRecord(
                username="viewer",
                password_hash=hash_password("test-password", salt=b"fixed-test-salt"),
                role=Role.VIEWER,
            ),
        ),
    )


def test_password_hash_is_salted_and_verifiable() -> None:
    encoded = hash_password("sensitive", salt=b"0123456789abcdef")

    assert "sensitive" not in encoded
    assert verify_password("sensitive", encoded)
    assert not verify_password("wrong", encoded)


def test_signed_token_round_trip() -> None:
    service = auth_service()
    user = AuthenticatedUser(username="viewer", role=Role.VIEWER)

    token = service.create_token(user, now=datetime(2026, 8, 21, tzinfo=UTC))
    result = service.validate_token(token, now=datetime(2026, 8, 21, tzinfo=UTC))

    assert result == user


def test_tampered_token_is_rejected() -> None:
    service = auth_service()
    token = service.create_token(AuthenticatedUser("viewer", Role.VIEWER))

    with pytest.raises(APIError, match="invalid"):
        service.validate_token(f"{token}x")


def test_expired_token_is_rejected() -> None:
    service = auth_service()
    issued = datetime(2026, 8, 21, tzinfo=UTC)
    token = service.create_token(
        AuthenticatedUser("viewer", Role.VIEWER),
        now=issued,
    )

    with pytest.raises(APIError, match="expired"):
        service.validate_token(token, now=issued + timedelta(minutes=16))
