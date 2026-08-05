"""
Directory initialization for the Energy Operations Intelligence Platform.

This module owns the creation and validation of EOIP's permanent repository
directories. Other modules must use the directory paths defined in
`eoip.core.constants` rather than recreating directory paths independently.
"""

from __future__ import annotations

from pathlib import Path

from eoip.core.constants import (
    CONFIG_DIR,
    DATA_DIR,
    DOCKER_DIR,
    DOCS_DIR,
    EXTERNAL_DATA_DIR,
    INTERIM_DATA_DIR,
    LOGS_DIR,
    NOTEBOOKS_DIR,
    PROCESSED_DATA_DIR,
    QUARANTINE_DATA_DIR,
    RAW_DATA_DIR,
    SCRIPTS_DIR,
    SQL_ANALYTICS_DIR,
    SQL_DDL_DIR,
    SQL_DIR,
    SQL_DML_DIR,
    SQL_VIEWS_DIR,
    SYNTHETIC_DATA_DIR,
    TESTS_DIR,
)
from eoip.core.exceptions import DirectoryInitializationError
from eoip.core.logging import get_logger

logger = get_logger(__name__)

_REQUIRED_DIRECTORIES: tuple[Path, ...] = (
    CONFIG_DIR,
    DATA_DIR,
    RAW_DATA_DIR,
    INTERIM_DATA_DIR,
    PROCESSED_DATA_DIR,
    EXTERNAL_DATA_DIR,
    SYNTHETIC_DATA_DIR,
    QUARANTINE_DATA_DIR,
    DOCKER_DIR,
    DOCS_DIR,
    LOGS_DIR,
    NOTEBOOKS_DIR,
    SCRIPTS_DIR,
    SQL_DIR,
    SQL_DDL_DIR,
    SQL_DML_DIR,
    SQL_VIEWS_DIR,
    SQL_ANALYTICS_DIR,
    TESTS_DIR,
    TESTS_DIR / "unit",
    TESTS_DIR / "integration",
    TESTS_DIR / "performance",
    TESTS_DIR / "acceptance",
)


def initialize_project_directories() -> tuple[Path, ...]:
    """
    Create and validate every required EOIP project directory.

    Existing directories are preserved. The function returns all validated
    directory paths so callers can inspect or report the initialized structure.

    Returns
    -------
    tuple[pathlib.Path, ...]
        All required project directory paths.

    Raises
    ------
    DirectoryInitializationError
        If a required path cannot be created, is not a directory, or is not
        writable.
    """
    initialized_directories: list[Path] = []

    for directory in _REQUIRED_DIRECTORIES:
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DirectoryInitializationError(
                f"EOIP could not create the required directory '{directory}'. "
                "Check that the project location exists and that your Windows "
                "user has permission to create folders there."
            ) from exc

        if not directory.is_dir():
            raise DirectoryInitializationError(
                f"The required EOIP path '{directory}' exists but is not a "
                "directory. Rename or remove the conflicting file, then run "
                "directory initialization again."
            )

        try:
            write_test_path = directory / ".eoip_write_test"
            write_test_path.touch(exist_ok=True)
            write_test_path.unlink()
        except OSError as exc:
            raise DirectoryInitializationError(
                f"EOIP cannot write to the required directory '{directory}'. "
                "Check folder permissions and ensure the directory is not "
                "read-only."
            ) from exc

        initialized_directories.append(directory)
        logger.debug("Validated EOIP directory: %s", directory)

    logger.info(
        "EOIP directory initialization completed successfully for %d directories.",
        len(initialized_directories),
    )

    return tuple(initialized_directories)


def get_required_directories() -> tuple[Path, ...]:
    """
    Return the permanent EOIP directory collection.

    Returns
    -------
    tuple[pathlib.Path, ...]
        Required directory paths in initialization order.
    """
    return _REQUIRED_DIRECTORIES
