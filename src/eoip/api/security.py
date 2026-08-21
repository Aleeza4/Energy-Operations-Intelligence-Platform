"""Password hashing, signed bearer tokens, and role authorization."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from eoip.api.errors import APIError
from eoip.api.schemas import Role
from eoip.config.settings import settings

PBKDF2_ITERATIONS = 310_000
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Hash a password using salted PBKDF2-HMAC-SHA256."""
    if not password:
        raise ValueError("password must not be empty")
    active_salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        active_salt,
        PBKDF2_ITERATIONS,
    )
    return (
        f"pbkdf2_sha256${PBKDF2_ITERATIONS}$"
        f"{_b64encode(active_salt)}${_b64encode(digest)}"
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a password without timing-sensitive equality checks."""
    try:
        algorithm, iterations, salt, expected = encoded_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            _b64decode(salt),
            int(iterations),
        )
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(_b64encode(digest), expected)


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Internal authenticated principal without password material."""

    username: str
    role: Role


@dataclass(frozen=True, slots=True)
class UserRecord:
    """Internal bootstrap user record."""

    username: str
    password_hash: str
    role: Role
    disabled: bool = False


class AuthService:
    """Authenticate users and issue validated expiring signed tokens."""

    def __init__(
        self,
        *,
        secret: str,
        expiry_minutes: int,
        users: tuple[UserRecord, ...],
    ) -> None:
        if len(secret) < 32:
            raise ValueError("token secret must contain at least 32 characters")
        if expiry_minutes <= 0:
            raise ValueError("expiry_minutes must be positive")
        self._secret = secret.encode("utf-8")
        self._expiry = timedelta(minutes=expiry_minutes)
        self._users = {user.username: user for user in users}

    @property
    def expires_in_seconds(self) -> int:
        return int(self._expiry.total_seconds())

    def authenticate(self, username: str, password: str) -> AuthenticatedUser | None:
        record = self._users.get(username)
        if (
            record is None
            or record.disabled
            or not verify_password(password, record.password_hash)
        ):
            return None
        return AuthenticatedUser(username=record.username, role=record.role)

    def create_token(
        self,
        user: AuthenticatedUser,
        *,
        now: datetime | None = None,
    ) -> str:
        issued_at = now or datetime.now(UTC)
        payload = {
            "sub": user.username,
            "role": user.role.value,
            "iat": int(issued_at.timestamp()),
            "exp": int((issued_at + self._expiry).timestamp()),
        }
        encoded_payload = _b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        signature = hmac.new(
            self._secret,
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return f"{encoded_payload}.{_b64encode(signature)}"

    def validate_token(
        self,
        token: str,
        *,
        now: datetime | None = None,
    ) -> AuthenticatedUser:
        try:
            encoded_payload, encoded_signature = token.split(".", 1)
            expected_signature = hmac.new(
                self._secret,
                encoded_payload.encode("ascii"),
                hashlib.sha256,
            ).digest()
            if not hmac.compare_digest(
                expected_signature,
                _b64decode(encoded_signature),
            ):
                raise ValueError("invalid signature")
            payload = json.loads(_b64decode(encoded_payload))
            username = str(payload["sub"])
            expires_at = int(payload["exp"])
            claimed_role = Role(str(payload["role"]))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise APIError(
                status_code=401,
                code="invalid_token",
                message="The access token is invalid.",
            ) from error

        current_time = now or datetime.now(UTC)
        if current_time.timestamp() >= expires_at:
            raise APIError(
                status_code=401,
                code="expired_token",
                message="The access token has expired.",
            )

        record = self._users.get(username)
        if record is None or record.disabled or record.role != claimed_role:
            raise APIError(
                status_code=401,
                code="invalid_user",
                message="The token user is unavailable.",
            )
        return AuthenticatedUser(username=record.username, role=record.role)


_DEFAULT_USERS = (
    UserRecord(
        username="viewer",
        password_hash=(
            "pbkdf2_sha256$310000$dmlld2VyLXBoYXNlMTE$"
            "Vg46mkWAp8lwE6eqMOdBSx5PEsL12IkBuCALFjDkGLo"
        ),
        role=Role.VIEWER,
    ),
    UserRecord(
        username="operator",
        password_hash=(
            "pbkdf2_sha256$310000$b3BlcmF0b3ItcGhhc2UxMQ$"
            "AjcKNJjgNYrwYiq-ZAFED-_kUo5UXI1ywz9vUSsTHb4"
        ),
        role=Role.OPERATOR,
    ),
    UserRecord(
        username="admin",
        password_hash=(
            "pbkdf2_sha256$310000$YWRtaW4tcGhhc2UxMQ$"
            "N70YZePm8MfFdc-tTAWTfy8cmjfxNhLTyvPM4yhjyec"
        ),
        role=Role.ADMIN,
    ),
)


def get_auth_service() -> AuthService:
    """Return the configured authentication service."""
    return AuthService(
        secret=settings.api_token_secret,
        expiry_minutes=settings.api_token_expiry_minutes,
        users=_DEFAULT_USERS,
    )


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthenticatedUser:
    """Resolve the authenticated principal from a bearer token."""
    return auth_service.validate_token(token)


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]


def require_roles(*allowed_roles: Role) -> Callable[..., AuthenticatedUser]:
    """Create a reusable role authorization dependency."""
    allowed = frozenset(allowed_roles)

    def authorize(user: CurrentUser) -> AuthenticatedUser:
        if user.role not in allowed:
            raise APIError(
                status_code=403,
                code="insufficient_permissions",
                message="The authenticated user lacks the required role.",
            )
        return user

    return authorize


reader_access = require_roles(Role.VIEWER, Role.OPERATOR, Role.ADMIN)
admin_access = require_roles(Role.ADMIN)
