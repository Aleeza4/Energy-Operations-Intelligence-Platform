"""
Unit tests for the EOIP application bootstrap process.

These tests verify successful runtime initialization, required directory
creation, and rejection of invalid configuration values.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import eoip.core.bootstrap as bootstrap_module
from eoip.core.bootstrap import BootstrapResult, bootstrap_application
from eoip.core.exceptions import ConfigurationError


def test_bootstrap_application_returns_expected_result() -> None:
    """Bootstrap should return a valid immutable runtime summary."""
    result = bootstrap_application()

    assert isinstance(result, BootstrapResult)
    assert result.project_name == "Energy Operations Intelligence Platform"
    assert result.database_host == "localhost"
    assert result.database_port == 5432
    assert result.database_name == "eoip"
    assert result.log_level == "INFO"
    assert len(result.initialized_directories) == 23


def test_bootstrap_application_initializes_required_directories() -> None:
    """Every directory reported by bootstrap should exist and be a directory."""
    result = bootstrap_application()

    assert result.initialized_directories
    assert all(
        directory.exists() and directory.is_dir()
        for directory in result.initialized_directories
    )


def test_bootstrap_rejects_invalid_database_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bootstrap should raise a clear error for an invalid database port."""
    invalid_settings = SimpleNamespace(
        project_name="Energy Operations Intelligence Platform",
        database_host="localhost",
        database_port=70000,
        database_name="eoip",
        database_user="postgres",
        log_level="INFO",
    )

    monkeypatch.setattr(
        bootstrap_module,
        "settings",
        invalid_settings,
    )

    with pytest.raises(
        ConfigurationError,
        match="EOIP_DATABASE_PORT '70000' is invalid",
    ):
        bootstrap_application()
