"""
Application configuration for the Energy Operations Intelligence Platform.

This module provides a single immutable configuration object that loads
environment variables and exposes project-wide settings.
"""

from __future__ import annotations

import os
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


settings = Settings()
