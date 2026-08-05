"""
Application bootstrap for the Energy Operations Intelligence Platform.

This module provides the single approved startup routine for preparing the EOIP
runtime environment. It validates configuration, initializes project
directories, and confirms that centralized logging is operational.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from eoip.config.settings import settings
from eoip.core.directories import initialize_project_directories
from eoip.core.exceptions import ConfigurationError, EOIPError
from eoip.core.logging import get_logger

logger = get_logger(__name__)

_SUPPORTED_LOG_LEVELS: frozenset[str] = frozenset(
    {
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    }
)


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    """Summary of a successful EOIP application bootstrap."""

    project_name: str
    database_host: str
    database_port: int
    database_name: str
    log_level: str
    initialized_directories: tuple[Path, ...]


def _validate_settings() -> None:
    """
    Validate configuration required to initialize the EOIP application.

    Raises
    ------
    ConfigurationError
        If a mandatory configuration value is invalid.
    """
    if not settings.project_name.strip():
        raise ConfigurationError(
            "EOIP_PROJECT_NAME is empty. Restore the default project name or "
            "provide a non-empty project name in the configuration."
        )

    if not settings.database_host.strip():
        raise ConfigurationError(
            "EOIP_DATABASE_HOST is empty. Set it to a valid hostname such as "
            "'localhost'."
        )

    if not 1 <= settings.database_port <= 65535:
        raise ConfigurationError(
            f"EOIP_DATABASE_PORT '{settings.database_port}' is invalid. "
            "Use an integer between 1 and 65535."
        )

    if not settings.database_name.strip():
        raise ConfigurationError(
            "EOIP_DATABASE_NAME is empty. Set a valid PostgreSQL database name."
        )

    if not settings.database_user.strip():
        raise ConfigurationError(
            "EOIP_DATABASE_USER is empty. Set a valid PostgreSQL username."
        )

    normalized_log_level = settings.log_level.strip().upper()

    if normalized_log_level not in _SUPPORTED_LOG_LEVELS:
        supported_levels = ", ".join(sorted(_SUPPORTED_LOG_LEVELS))
        raise ConfigurationError(
            f"EOIP_LOG_LEVEL '{settings.log_level}' is invalid. "
            f"Use one of: {supported_levels}."
        )


def bootstrap_application() -> BootstrapResult:
    """
    Prepare the EOIP runtime environment.

    Returns
    -------
    BootstrapResult
        Immutable summary of the initialized runtime environment.

    Raises
    ------
    EOIPError
        If EOIP configuration or directory initialization fails.
    OSError
        If required files or directories cannot be accessed.
    """
    logger.info("Starting EOIP application bootstrap.")

    try:
        _validate_settings()
        initialized_directories = initialize_project_directories()
    except (EOIPError, OSError):
        logger.exception(
            "EOIP application bootstrap failed. Review the error details and "
            "correct the configuration or file-system issue before retrying."
        )
        raise

    result = BootstrapResult(
        project_name=settings.project_name,
        database_host=settings.database_host,
        database_port=settings.database_port,
        database_name=settings.database_name,
        log_level=settings.log_level.strip().upper(),
        initialized_directories=initialized_directories,
    )

    logger.info(
        "EOIP application bootstrap completed successfully for project '%s'.",
        result.project_name,
    )

    return result
