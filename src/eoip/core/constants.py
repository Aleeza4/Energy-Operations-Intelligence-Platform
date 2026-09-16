"""
Immutable project-wide constants for the Energy Operations Intelligence Platform.

This module is the single source of truth for project metadata, directory paths,
database defaults, time-series settings, and logging defaults.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------
# Project metadata
# ---------------------------------------------------------------------

PROJECT_NAME: str = "Energy Operations Intelligence Platform"
PROJECT_SHORT_NAME: str = "EOIP"
PROJECT_VERSION: str = "0.1.0"

# ---------------------------------------------------------------------
# Repository directories
# ---------------------------------------------------------------------

PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]

SRC_DIR: Path = PROJECT_ROOT / "src"
CONFIG_DIR: Path = PROJECT_ROOT / "config"
DATA_DIR: Path = PROJECT_ROOT / "data"
DOCS_DIR: Path = PROJECT_ROOT / "docs"
LOGS_DIR: Path = PROJECT_ROOT / "logs"
NOTEBOOKS_DIR: Path = PROJECT_ROOT / "notebooks"
SCRIPTS_DIR: Path = PROJECT_ROOT / "scripts"
SQL_DIR: Path = PROJECT_ROOT / "sql"
TESTS_DIR: Path = PROJECT_ROOT / "tests"
DOCKER_DIR: Path = PROJECT_ROOT / "docker"

# ---------------------------------------------------------------------
# Data zones
# ---------------------------------------------------------------------

RAW_DATA_DIR: Path = DATA_DIR / "raw"
INTERIM_DATA_DIR: Path = DATA_DIR / "interim"
PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
EXTERNAL_DATA_DIR: Path = DATA_DIR / "external"
SYNTHETIC_DATA_DIR: Path = DATA_DIR / "synthetic"
QUARANTINE_DATA_DIR: Path = DATA_DIR / "quarantine"

# ---------------------------------------------------------------------
# SQL directories
# ---------------------------------------------------------------------

SQL_DDL_DIR: Path = SQL_DIR / "ddl"
SQL_DML_DIR: Path = SQL_DIR / "dml"
SQL_VIEWS_DIR: Path = SQL_DIR / "views"
SQL_ANALYTICS_DIR: Path = SQL_DIR / "analytics"

# ---------------------------------------------------------------------
# Database configuration
# ---------------------------------------------------------------------
# EOIP uses the single required environment variable EOIP_DATABASE_URL.
# Local hardcoded host/user/password defaults are intentionally not kept here.

# ---------------------------------------------------------------------
# Time-series standards
# ---------------------------------------------------------------------

SCADA_SAMPLE_INTERVAL_MINUTES: int = 15
MINUTES_PER_HOUR: int = 60
HOURS_PER_DAY: int = 24
UTC_TIMEZONE_NAME: str = "UTC"

# ---------------------------------------------------------------------
# Logging defaults
# ---------------------------------------------------------------------

DEFAULT_LOG_LEVEL: str = "INFO"
DEFAULT_LOG_FILE_NAME: str = "eoip.log"
DEFAULT_LOG_FORMAT: str = (
    "%(asctime)s | %(levelname)-8s | %(name)s | "
    "%(filename)s:%(lineno)d | %(message)s"
)
