"""Security validation tests for the EOIP API layer."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from eoip.api.app import app
from eoip.api.errors import APIError
from eoip.api.schemas import Role
from eoip.api.security import (
    AuthenticatedUser,
    AuthService,
    UserRecord,
    get_auth_service,
    hash_password,
    require_roles,
    verify_password,
)

TOKEN_SECRET = "phase12-security-test-secret-that-is-long-enough-123456"

VIEWER_PASSWORD = "viewer-secure-password"
ADMIN_PASSWORD = "admin-secure-password"
DISABLED_PASSWORD = "disabled-secure-password"


def _auth_service() -> AuthService:
    """Create an isolated authentication service for security tests."""
    return AuthService(
        secret=TOKEN_SECRET,
        expiry_minutes=30,
        users=(
            UserRecord(
                username="security_viewer",
                password_hash=hash_password(
                    VIEWER_PASSWORD,
                    salt=b"viewer-security1",
                ),
                role=Role.VIEWER,
            ),
            UserRecord(
                username="security_admin",
                password_hash=hash_password(
                    ADMIN_PASSWORD,
                    salt=b"admin-security12",
                ),
                role=Role.ADMIN,
            ),
            UserRecord(
                username="disabled_user",
                password_hash=hash_password(
                    DISABLED_PASSWORD,
                    salt=b"disabled-user-12",
                ),
                role=Role.VIEWER,
                disabled=True,
            ),
        ),
    )


def test_password_hash_does_not_store_plaintext_password() -> None:
    """Password hashes must not expose the original password."""
    password = "super-secret-password"

    encoded = hash_password(
        password,
        salt=b"phase12-test-salt",
    )

    assert password not in encoded
    assert encoded.startswith("pbkdf2_sha256$")
    assert "$310000$" in encoded


def test_password_hashes_are_salted() -> None:
    """The same password should produce different hashes with random salts."""
    password = "same-password"

    first = hash_password(password)
    second = hash_password(password)

    assert first != second

    assert verify_password(
        password,
        first,
    )
    assert verify_password(
        password,
        second,
    )


def test_empty_password_cannot_be_hashed() -> None:
    """Empty passwords must be rejected."""
    with pytest.raises(
        ValueError,
        match="password must not be empty",
    ):
        hash_password("")


def test_correct_password_is_verified() -> None:
    """A correct password should match its PBKDF2 hash."""
    encoded = hash_password(
        "correct-password",
        salt=b"fixed-test-salt1",
    )

    assert verify_password(
        "correct-password",
        encoded,
    )


def test_wrong_password_is_rejected() -> None:
    """An incorrect password must not authenticate against a stored hash."""
    encoded = hash_password(
        "correct-password",
        salt=b"fixed-test-salt2",
    )

    assert not verify_password(
        "wrong-password",
        encoded,
    )


@pytest.mark.parametrize(
    "encoded_hash",
    (
        "",
        "invalid",
        "sha256$100$salt$digest",
        "pbkdf2_sha256$not-an-int$salt$digest",
        "pbkdf2_sha256$310000$%%%$invalid",
    ),
)
def test_malformed_password_hash_is_rejected(
    encoded_hash: str,
) -> None:
    """Malformed stored hashes must fail closed instead of authenticating."""
    assert not verify_password(
        "password",
        encoded_hash,
    )


def test_auth_service_requires_strong_token_secret() -> None:
    """Token signing secrets shorter than 32 characters must be rejected."""
    with pytest.raises(
        ValueError,
        match="token secret must contain at least 32 characters",
    ):
        AuthService(
            secret="too-short",
            expiry_minutes=30,
            users=(),
        )


def test_auth_service_requires_positive_expiry() -> None:
    """Token expiry must be positive."""
    with pytest.raises(
        ValueError,
        match="expiry_minutes must be positive",
    ):
        AuthService(
            secret=TOKEN_SECRET,
            expiry_minutes=0,
            users=(),
        )


def test_valid_credentials_authenticate_user() -> None:
    """Valid credentials should resolve the expected principal."""
    service = _auth_service()

    user = service.authenticate(
        "security_viewer",
        VIEWER_PASSWORD,
    )

    assert user == AuthenticatedUser(
        username="security_viewer",
        role=Role.VIEWER,
    )


def test_wrong_password_cannot_authenticate() -> None:
    """Authentication must reject an incorrect password."""
    service = _auth_service()

    assert (
        service.authenticate(
            "security_viewer",
            "wrong-password",
        )
        is None
    )


def test_unknown_username_cannot_authenticate() -> None:
    """Authentication must reject unknown users."""
    service = _auth_service()

    assert (
        service.authenticate(
            "does-not-exist",
            VIEWER_PASSWORD,
        )
        is None
    )


def test_disabled_user_cannot_authenticate() -> None:
    """Disabled accounts must not receive authenticated principals."""
    service = _auth_service()

    assert (
        service.authenticate(
            "disabled_user",
            DISABLED_PASSWORD,
        )
        is None
    )


def test_signed_token_round_trip() -> None:
    """A valid signed token should resolve the original principal."""
    service = _auth_service()

    user = AuthenticatedUser(
        username="security_viewer",
        role=Role.VIEWER,
    )

    now = datetime(
        2026,
        8,
        22,
        8,
        0,
        tzinfo=UTC,
    )

    token = service.create_token(
        user,
        now=now,
    )

    validated = service.validate_token(
        token,
        now=now + timedelta(minutes=5),
    )

    assert validated == user


def test_tampered_token_is_rejected() -> None:
    """Changing a signed token must invalidate its signature."""
    service = _auth_service()

    token = service.create_token(
        AuthenticatedUser(
            username="security_viewer",
            role=Role.VIEWER,
        )
    )

    payload, signature = token.split(".", 1)

    tampered = f"{payload[:-1]}" f"{'A' if payload[-1] != 'A' else 'B'}" f".{signature}"

    with pytest.raises(APIError):
        service.validate_token(tampered)


@pytest.mark.parametrize(
    "token",
    (
        "",
        "not-a-token",
        "abc.",
        ".abc",
        "abc.def.ghi",
    ),
)
def test_malformed_token_is_rejected(
    token: str,
) -> None:
    """Malformed bearer tokens must fail closed."""
    service = _auth_service()

    with pytest.raises(APIError):
        service.validate_token(token)


def test_expired_token_is_rejected() -> None:
    """Expired bearer tokens must not authenticate."""
    service = _auth_service()

    issued_at = datetime(
        2026,
        8,
        22,
        8,
        0,
        tzinfo=UTC,
    )

    token = service.create_token(
        AuthenticatedUser(
            username="security_viewer",
            role=Role.VIEWER,
        ),
        now=issued_at,
    )

    with pytest.raises(APIError):
        service.validate_token(
            token,
            now=issued_at + timedelta(minutes=31),
        )


def test_token_becomes_invalid_when_user_is_disabled() -> None:
    """Previously issued tokens must fail if the account becomes disabled."""
    initial_service = _auth_service()

    user = AuthenticatedUser(
        username="security_viewer",
        role=Role.VIEWER,
    )

    token = initial_service.create_token(user)

    disabled_service = AuthService(
        secret=TOKEN_SECRET,
        expiry_minutes=30,
        users=(
            UserRecord(
                username="security_viewer",
                password_hash=hash_password(
                    VIEWER_PASSWORD,
                    salt=b"viewer-security1",
                ),
                role=Role.VIEWER,
                disabled=True,
            ),
        ),
    )

    with pytest.raises(APIError):
        disabled_service.validate_token(token)


def test_token_becomes_invalid_when_role_changes() -> None:
    """A token must not retain privileges after the user's role changes."""
    initial_service = _auth_service()

    token = initial_service.create_token(
        AuthenticatedUser(
            username="security_viewer",
            role=Role.VIEWER,
        )
    )

    changed_service = AuthService(
        secret=TOKEN_SECRET,
        expiry_minutes=30,
        users=(
            UserRecord(
                username="security_viewer",
                password_hash=hash_password(
                    VIEWER_PASSWORD,
                    salt=b"viewer-security1",
                ),
                role=Role.ADMIN,
            ),
        ),
    )

    with pytest.raises(APIError):
        changed_service.validate_token(token)


def test_admin_role_dependency_allows_admin() -> None:
    """An admin-only role dependency should accept administrators."""
    authorize = require_roles(Role.ADMIN)

    user = AuthenticatedUser(
        username="security_admin",
        role=Role.ADMIN,
    )

    assert authorize(user) == user


def test_admin_role_dependency_rejects_viewer() -> None:
    """A viewer must not pass an administrator authorization dependency."""
    authorize = require_roles(Role.ADMIN)

    user = AuthenticatedUser(
        username="security_viewer",
        role=Role.VIEWER,
    )

    with pytest.raises(APIError):
        authorize(user)


def test_public_health_endpoint_requires_no_authentication() -> None:
    """The health endpoint should remain intentionally public."""
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200


def test_protected_endpoint_rejects_missing_token() -> None:
    """Protected API resources must reject unauthenticated callers."""
    with TestClient(app) as client:
        response = client.get("/api/v1/plants")

    assert response.status_code in {
        401,
        403,
    }


def test_api_rejects_invalid_bearer_token() -> None:
    """A malformed bearer token must not access protected resources."""
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/plants",
            headers={
                "Authorization": "Bearer invalid-token",
            },
        )

    assert response.status_code == 401


def test_api_login_rejects_bad_credentials_without_password_leak() -> None:
    """Failed authentication must not expose supplied credentials."""
    service = _auth_service()

    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/token",
                data={
                    "username": "security_viewer",
                    "password": "definitely-wrong-secret",
                },
            )
    finally:
        app.dependency_overrides.pop(
            get_auth_service,
            None,
        )

    assert response.status_code == 401

    body = response.text

    assert "definitely-wrong-secret" not in body
    assert VIEWER_PASSWORD not in body
    assert TOKEN_SECRET not in body


def test_api_login_and_authenticated_identity_round_trip() -> None:
    """Valid credentials should issue a usable bearer token."""
    service = _auth_service()

    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as client:
            login_response = client.post(
                "/api/v1/auth/token",
                data={
                    "username": "security_viewer",
                    "password": VIEWER_PASSWORD,
                },
            )

            assert login_response.status_code == 200

            payload = login_response.json()

            access_token = payload["access_token"]

            identity_response = client.get(
                "/api/v1/auth/me",
                headers={
                    "Authorization": (f"Bearer {access_token}"),
                },
            )
    finally:
        app.dependency_overrides.pop(
            get_auth_service,
            None,
        )

    assert identity_response.status_code == 200

    assert identity_response.json() == {
        "username": "security_viewer",
        "role": Role.VIEWER.value,
    }


def test_api_does_not_expose_token_secret() -> None:
    """API responses must never contain the token-signing secret."""
    service = _auth_service()

    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/token",
                data={
                    "username": "security_viewer",
                    "password": VIEWER_PASSWORD,
                },
            )
    finally:
        app.dependency_overrides.pop(
            get_auth_service,
            None,
        )

    assert response.status_code == 200
    assert TOKEN_SECRET not in response.text
