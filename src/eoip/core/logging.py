"""
Centralized logging configuration for the Energy Operations Intelligence Platform.

Every EOIP production module must obtain its logger through `get_logger`.
This module owns console logging, file logging, formatting, log-level
validation, and logging initialization.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from eoip.config.settings import settings
from eoip.core.constants import (
    DEFAULT_LOG_FILE_NAME,
    DEFAULT_LOG_FORMAT,
    LOGS_DIR,
)
from eoip.core.exceptions import ConfigurationError

_CONFIGURED_LOGGER_NAMES: set[str] = set()


def _resolve_log_level(level_name: str) -> int:
    """
    Convert a configured log-level name into its numeric logging value.

    Parameters
    ----------
    level_name:
        Log-level name such as DEBUG, INFO, WARNING, ERROR, or CRITICAL.

    Returns
    -------
    int
        Numeric logging level.

    Raises
    ------
    ConfigurationError
        If the configured log level is unsupported.
    """
    normalized_level = level_name.strip().upper()
    resolved_level = logging.getLevelNamesMapping().get(normalized_level)

    if not isinstance(resolved_level, int):
        supported_levels = "DEBUG, INFO, WARNING, ERROR, CRITICAL"
        raise ConfigurationError(
            f"Invalid EOIP log level '{level_name}'. "
            f"Set EOIP_LOG_LEVEL to one of: {supported_levels}."
        )

    return resolved_level


def _create_log_file_path() -> Path:
    """
    Create the log directory and return the application log-file path.

    Returns
    -------
    pathlib.Path
        Absolute path to the EOIP log file.

    Raises
    ------
    OSError
        If the log directory cannot be created or accessed.
    """
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OSError(
            f"EOIP could not create or access the log directory '{LOGS_DIR}'. "
            "Check that the project folder exists and that your Windows user "
            "has permission to write to it."
        ) from exc

    return LOGS_DIR / DEFAULT_LOG_FILE_NAME


def configure_logging(logger_name: str = "eoip") -> logging.Logger:
    """
    Configure and return an EOIP logger.

    Configuration is idempotent for each logger name, preventing duplicate
    console and file messages when this function is called repeatedly.

    Parameters
    ----------
    logger_name:
        Name of the logger to configure.

    Returns
    -------
    logging.Logger
        Configured EOIP logger.

    Raises
    ------
    ConfigurationError
        If the configured log level is invalid.
    OSError
        If the log directory or log file cannot be created.
    ValueError
        If `logger_name` is empty.
    """
    normalized_name = logger_name.strip()

    if not normalized_name:
        raise ValueError(
            "Logger name cannot be empty. Pass a module name such as __name__."
        )

    logger = logging.getLogger(normalized_name)

    if normalized_name in _CONFIGURED_LOGGER_NAMES:
        return logger

    log_level = _resolve_log_level(settings.log_level)
    log_file_path = _create_log_file_path()
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    try:
        file_handler = logging.FileHandler(
            filename=log_file_path,
            encoding="utf-8",
        )
    except OSError as exc:
        raise OSError(
            f"EOIP could not open the log file '{log_file_path}'. "
            "Check that the file is not locked and that you have write permission."
        ) from exc

    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    logger.setLevel(log_level)
    logger.propagate = False
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    _CONFIGURED_LOGGER_NAMES.add(normalized_name)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Return a configured EOIP logger for a module.

    Parameters
    ----------
    name:
        Logger name, normally the calling module's `__name__`.

    Returns
    -------
    logging.Logger
        Configured logger instance.
    """
    return configure_logging(name)
