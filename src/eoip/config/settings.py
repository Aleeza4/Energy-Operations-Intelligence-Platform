"""
Application configuration for the Energy Operations Intelligence Platform.

This module provides a single immutable configuration object that loads
environment variables and exposes project-wide settings.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass

from dotenv import load_dotenv

from eoip.core.constants import (
    DEFAULT_DATABASE_HOST,
    DEFAULT_DATABASE_NAME,
    DEFAULT_DATABASE_PORT,
    DEFAULT_DATABASE_USER,
    DEFAULT_LOG_LEVEL,
    PROJECT_NAME,
    PROJECT_ROOT,
)

# Load .env if it exists.
load_dotenv(PROJECT_ROOT / ".env")


def _get_env(name: str, default: str) -> str:
    """Return an environment variable or its default value."""
    return os.getenv(name, default)


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable EOIP application settings."""

    project_name: str = PROJECT_NAME

    database_host: str = _get_env(
        "EOIP_DATABASE_HOST",
        DEFAULT_DATABASE_HOST,
    )

    database_port: int = int(
        _get_env(
            "EOIP_DATABASE_PORT",
            str(DEFAULT_DATABASE_PORT),
        )
    )

    database_name: str = _get_env(
        "EOIP_DATABASE_NAME",
        DEFAULT_DATABASE_NAME,
    )

    database_user: str = _get_env(
        "EOIP_DATABASE_USER",
        DEFAULT_DATABASE_USER,
    )

    database_password: str = _get_env(
        "EOIP_DATABASE_PASSWORD",
        "",
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
