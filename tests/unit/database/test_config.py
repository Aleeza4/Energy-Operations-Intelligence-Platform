"""
Tests for EOIP database configuration.
"""

from __future__ import annotations

from eoip.database.config import DatabaseConfig


def test_default_database_configuration() -> None:
    """Verify default configuration values."""
    config = DatabaseConfig()

    assert config.host == "localhost"
    assert config.port == 5432
    assert config.database == "eoip"
    assert config.username == "postgres"
    assert config.password == "postgres"

    assert config.echo_sql is False
    assert config.pool_size == 10
    assert config.max_overflow == 20
    assert config.pool_timeout == 30
    assert config.pool_recycle == 1800


def test_connection_url() -> None:
    """Verify SQLAlchemy connection URL."""
    config = DatabaseConfig()

    assert (
        config.connection_url == "postgresql+psycopg2://"
        "postgres:postgres@localhost:5432/eoip"
    )


def test_custom_configuration() -> None:
    """Verify custom values."""
    config = DatabaseConfig(
        host="db.example.com",
        port=6543,
        database="energy_db",
        username="admin",
        password="secret",
        echo_sql=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=15,
        pool_recycle=600,
    )

    assert config.host == "db.example.com"
    assert config.port == 6543
    assert config.database == "energy_db"
    assert config.username == "admin"
    assert config.password == "secret"

    assert config.echo_sql is True
    assert config.pool_size == 5
    assert config.max_overflow == 10
    assert config.pool_timeout == 15
    assert config.pool_recycle == 600

    assert (
        config.connection_url == "postgresql+psycopg2://"
        "admin:secret@db.example.com:6543/energy_db"
    )
