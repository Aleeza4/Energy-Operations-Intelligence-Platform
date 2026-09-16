"""
Application configuration for the Energy Operations Intelligence Platform.

This module provides a single immutable configuration object that loads
environment variables and exposes project-wide settings.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv

from eoip.core.constants import DEFAULT_LOG_LEVEL, PROJECT_NAME, PROJECT_ROOT

# Load .env if it exists.
load_dotenv(PROJECT_ROOT / ".env")


def _get_env(name: str, default: str) -> str:
    """Return an environment variable or its default value."""
    return os.getenv(name, default)


def _database_url_parts() -> tuple[str, str, str, str, str]:
    """Extract host, port, database, user, and password from EOIP_DATABASE_URL."""
    database_url = _get_env("EOIP_DATABASE_URL", "")
    if not database_url:
        return ("", "", "", "", "")

    parsed = urlparse(database_url)
    host = parsed.hostname or ""
    port = str(parsed.port or 5432)
    database = parsed.path.lstrip("/") if parsed.path else ""
    username = parsed.username or ""
    password = parsed.password or ""
    return host, port, database, username, password


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable EOIP application settings."""

    project_name: str = PROJECT_NAME

    database_url: str = _get_env("EOIP_DATABASE_URL", "")

    database_host: str = _get_env(
        "EOIP_DATABASE_HOST",
        _database_url_parts()[0],
    )

    database_port: int = int(
        _get_env(
            "EOIP_DATABASE_PORT",
            _database_url_parts()[1],
        ) or 5432
    )

    database_name: str = _get_env(
        "EOIP_DATABASE_NAME",
        _database_url_parts()[2],
    )

    database_user: str = _get_env(
        "EOIP_DATABASE_USER",
        _database_url_parts()[3],
    )

    database_password: str = _get_env(
        "EOIP_DATABASE_PASSWORD",
        _database_url_parts()[4],
    )

    log_level: str = _get_env(
        "EOIP_LOG_LEVEL",
        DEFAULT_LOG_LEVEL,
    )

    api_environment: str = _get_env("EOIP_API_ENVIRONMENT", "development")
    api_prefix: str = _get_env("EOIP_API_PREFIX", "/api/v1")
    api_version: str = _get_env("EOIP_API_VERSION", "0.1.0")
    api_token_secret: str = _get_env(
        "EOIP_API_TOKEN_SECRET",
        secrets.token_urlsafe(32),
    )
    api_token_expiry_minutes: int = int(_get_env("EOIP_API_TOKEN_EXPIRY_MINUTES", "30"))
    api_base_url: str = _get_env("EOIP_API_BASE_URL", "http://127.0.0.1:8000/api/v1")
    api_access_token: str = _get_env("EOIP_API_ACCESS_TOKEN", "")
    api_request_timeout_seconds: float = float(
        _get_env("EOIP_API_REQUEST_TIMEOUT_SECONDS", "10")
    )


settings = Settings()
