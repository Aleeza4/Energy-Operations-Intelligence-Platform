"""
Tests for EOIP database configuration.
"""

from __future__ import annotations

import pytest

from eoip.database.config import DatabaseConfig


def test_database_url_is_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the config resolves a full URL from EOIP_DATABASE_URL."""
    monkeypatch.setenv(
        "EOIP_DATABASE_URL",
        "postgresql+psycopg2://eoip_user:secret@db.example.com:6543/energy_db?sslmode=require",
    )

    config = DatabaseConfig()

    assert config.database_url == (
        "postgresql+psycopg2://eoip_user:secret@db.example.com:6543/energy_db?sslmode=require"
    )
    assert config.connection_url == config.database_url
    assert config.echo_sql is False
    assert config.pool_size == 10
    assert config.max_overflow == 20
    assert config.pool_timeout == 30
    assert config.pool_recycle == 1800


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the app raises instead of falling back to local defaults."""
    monkeypatch.delenv("EOIP_DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="EOIP_DATABASE_URL"):
        DatabaseConfig()


def test_custom_configuration_accepts_explicit_database_url() -> None:
    """Verify explicit URLs can be passed to the configuration."""
    config = DatabaseConfig(
        database_url="postgresql+psycopg2://admin:secret@db.example.com:6543/energy_db?sslmode=require",
        echo_sql=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=15,
        pool_recycle=600,
    )

    assert config.database_url == (
        "postgresql+psycopg2://admin:secret@db.example.com:6543/energy_db?sslmode=require"
    )
    assert config.connection_url == config.database_url
    assert config.echo_sql is True
    assert config.pool_size == 5
    assert config.max_overflow == 10
    assert config.pool_timeout == 15
    assert config.pool_recycle == 600
