"""
Unit tests for EOIP SQLAlchemy engine creation.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

from eoip.database.config import DatabaseConfig
from eoip.database.engine import create_database_engine


def test_create_engine_with_default_configuration() -> None:
    """Verify engine creation using default database settings."""
    mock_engine = Mock()

    with patch(
        "eoip.database.engine.create_engine",
        return_value=mock_engine,
    ) as mocked_create_engine:
        result = create_database_engine()

    assert result is mock_engine

    mocked_create_engine.assert_called_once_with(
        "postgresql+psycopg2://" "postgres:postgres@localhost:5432/eoip",
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
        future=True,
    )


def test_create_engine_with_custom_configuration() -> None:
    """Verify that custom settings are passed to SQLAlchemy."""
    config = DatabaseConfig(
        host="database.example.com",
        port=6543,
        database="energy_operations",
        username="eoip_user",
        password="secure-password",
        echo_sql=True,
        pool_size=5,
        max_overflow=8,
        pool_timeout=15,
        pool_recycle=900,
    )
    mock_engine = Mock()

    with patch(
        "eoip.database.engine.create_engine",
        return_value=mock_engine,
    ) as mocked_create_engine:
        result = create_database_engine(config)

    assert result is mock_engine

    mocked_create_engine.assert_called_once_with(
        "postgresql+psycopg2://"
        "eoip_user:secure-password"
        "@database.example.com:6543/energy_operations",
        echo=True,
        pool_size=5,
        max_overflow=8,
        pool_timeout=15,
        pool_recycle=900,
        pool_pre_ping=True,
        future=True,
    )


def test_create_database_engine_returns_create_engine_result() -> None:
    """Verify that the SQLAlchemy engine object is returned unchanged."""
    expected_engine = Mock(name="database_engine")

    with patch(
        "eoip.database.engine.create_engine",
        return_value=expected_engine,
    ):
        result = create_database_engine(DatabaseConfig())

    assert result is expected_engine


def test_new_default_config_is_used_for_each_call() -> None:
    """Verify repeated default calls consistently use the expected URL."""
    with patch(
        "eoip.database.engine.create_engine",
        return_value=Mock(),
    ) as mocked_create_engine:
        create_database_engine()
        create_database_engine()

    assert mocked_create_engine.call_count == 2

    first_call = mocked_create_engine.call_args_list[0]
    second_call = mocked_create_engine.call_args_list[1]

    assert first_call.args[0] == second_call.args[0]
    assert first_call.kwargs == second_call.kwargs
