"""Integration tests for the EOIP PostgreSQL database layer."""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

import eoip.database.models  # noqa: F401
from eoip.database.base import Base
from eoip.database.config import DatabaseConfig
from eoip.database.engine import create_database_engine
from eoip.database.session import create_session_factory, session_scope

EXPECTED_DOMAIN_TABLES = {
    "alarms",
    "budgets",
    "equipment",
    "ground_truth_events",
    "incidents",
    "plants",
    "scada_observations",
    "tariffs",
    "weather_observations",
    "work_orders",
}

EXPECTED_DATABASE_TABLES = EXPECTED_DOMAIN_TABLES | {
    "alembic_version",
}

EXPECTED_ALEMBIC_REVISION = "a70cc2551e1b"


def _database_config_from_url(
    database_url: str,
) -> DatabaseConfig:
    """Build a DatabaseConfig from a SQLAlchemy database URL."""
    url = make_url(database_url)

    if url.host is None:
        raise ValueError("Database URL must contain a host.")

    if url.database is None:
        raise ValueError("Database URL must contain a database name.")

    if url.username is None:
        raise ValueError("Database URL must contain a username.")

    return DatabaseConfig(
        host=url.host,
        port=url.port or 5432,
        database=url.database,
        username=url.username,
        password=url.password or "",
    )


@pytest.fixture(scope="module")
def database_url() -> str:
    """Return the PostgreSQL URL used by integration tests."""
    url = os.getenv("EOIP_DATABASE_URL")

    if not url:
        pytest.skip(
            "EOIP_DATABASE_URL is not configured; "
            "database integration tests require PostgreSQL."
        )

    return url


@pytest.fixture(scope="module")
def engine(
    database_url: str,
) -> Generator[Engine, None, None]:
    """Create and dispose the integration-test database engine."""
    config = _database_config_from_url(database_url)
    database_engine = create_database_engine(config)

    try:
        yield database_engine
    finally:
        database_engine.dispose()


@pytest.fixture(scope="module")
def session_factory(
    engine: Engine,
) -> sessionmaker[Session]:
    """Create a session factory bound to the integration database."""
    return create_session_factory(engine)


class TestDatabaseConfiguration:
    """Verify integration database configuration."""

    def test_database_url_can_build_configuration(
        self,
        database_url: str,
    ) -> None:
        config = _database_config_from_url(database_url)

        assert config.host == "127.0.0.1"
        assert config.port == 5432
        assert config.database == "eoip_db"
        assert config.username == "eoip_user"

    def test_configuration_uses_psycopg2_url(
        self,
        database_url: str,
    ) -> None:
        config = _database_config_from_url(database_url)

        assert config.connection_url.startswith("postgresql+psycopg2://")


class TestDatabaseConnection:
    """Verify connectivity to the real PostgreSQL database."""

    def test_database_connection_succeeds(
        self,
        engine: Engine,
    ) -> None:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar_one()

        assert result == 1

    def test_expected_database_identity(
        self,
        engine: Engine,
    ) -> None:
        with engine.connect() as connection:
            current_user = connection.execute(text("SELECT current_user")).scalar_one()

            current_database = connection.execute(
                text("SELECT current_database()")
            ).scalar_one()

        assert current_user == "eoip_user"
        assert current_database == "eoip_db"

    def test_postgresql_dialect_is_used(
        self,
        engine: Engine,
    ) -> None:
        assert engine.dialect.name == "postgresql"

    def test_postgresql_server_version_is_available(
        self,
        engine: Engine,
    ) -> None:
        with engine.connect() as connection:
            version = connection.execute(text("SHOW server_version")).scalar_one()

        assert version


class TestDatabaseSchema:
    """Verify the migrated PostgreSQL schema."""

    def test_expected_tables_exist(
        self,
        engine: Engine,
    ) -> None:
        inspector = inspect(engine)

        actual_tables = set(inspector.get_table_names(schema="public"))

        assert actual_tables >= EXPECTED_DATABASE_TABLES

    def test_all_domain_tables_exist(
        self,
        engine: Engine,
    ) -> None:
        inspector = inspect(engine)

        actual_tables = set(inspector.get_table_names(schema="public"))

        missing_tables = EXPECTED_DOMAIN_TABLES - actual_tables

        assert not missing_tables, (
            "Missing EOIP database tables: " f"{sorted(missing_tables)}"
        )

    def test_alembic_version_table_exists(
        self,
        engine: Engine,
    ) -> None:
        inspector = inspect(engine)

        assert inspector.has_table(
            "alembic_version",
            schema="public",
        )

    def test_database_is_at_expected_alembic_revision(
        self,
        engine: Engine,
    ) -> None:
        with engine.connect() as connection:
            revision = connection.execute(text("""
                    SELECT version_num
                    FROM alembic_version
                    """)).scalar_one()

        assert revision == EXPECTED_ALEMBIC_REVISION


class TestORMMetadata:
    """Verify ORM metadata matches PostgreSQL."""

    def test_expected_tables_are_registered_in_metadata(
        self,
    ) -> None:
        metadata_tables = set(Base.metadata.tables)

        assert metadata_tables == EXPECTED_DOMAIN_TABLES

    def test_metadata_tables_exist_in_database(
        self,
        engine: Engine,
    ) -> None:
        inspector = inspect(engine)

        database_tables = set(inspector.get_table_names(schema="public"))

        metadata_tables = set(Base.metadata.tables)

        assert database_tables >= metadata_tables

    @pytest.mark.parametrize(
        "table_name",
        sorted(EXPECTED_DOMAIN_TABLES),
    )
    def test_table_columns_match_metadata(
        self,
        engine: Engine,
        table_name: str,
    ) -> None:
        inspector = inspect(engine)

        database_columns = {
            column["name"]
            for column in inspector.get_columns(
                table_name,
                schema="public",
            )
        }

        metadata_columns = {
            column.name for column in Base.metadata.tables[table_name].columns
        }

        assert database_columns == metadata_columns

    @pytest.mark.parametrize(
        "table_name",
        sorted(EXPECTED_DOMAIN_TABLES),
    )
    def test_primary_keys_match_metadata(
        self,
        engine: Engine,
        table_name: str,
    ) -> None:
        inspector = inspect(engine)

        database_primary_key = inspector.get_pk_constraint(
            table_name,
            schema="public",
        )

        database_columns = set(
            database_primary_key.get(
                "constrained_columns",
                [],
            )
        )

        metadata_columns = {
            column.name
            for column in Base.metadata.tables[table_name].primary_key.columns
        }

        assert database_columns == metadata_columns


class TestSessionManagement:
    """Verify EOIP SQLAlchemy session management."""

    def test_session_factory_creates_session(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        session = session_factory()

        try:
            assert isinstance(
                session,
                Session,
            )
        finally:
            session.close()

    def test_session_can_execute_query(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        with session_scope(session_factory) as session:
            result = session.execute(text("SELECT 1")).scalar_one()

        assert result == 1

    def test_session_scope_commits_successful_transaction(
        self,
        engine: Engine,
    ) -> None:
        with engine.connect() as connection:
            connection.execute(text("""
                    CREATE TEMP TABLE eoip_commit_test (
                        value INTEGER NOT NULL
                    )
                    ON COMMIT PRESERVE ROWS
                    """))
            connection.commit()

            temporary_factory = sessionmaker(
                bind=connection,
                class_=Session,
                autoflush=False,
                expire_on_commit=False,
            )

            with session_scope(temporary_factory) as session:
                session.execute(text("""
                        INSERT INTO eoip_commit_test (
                            value
                        )
                        VALUES (42)
                        """))

            result = connection.execute(text("""
                    SELECT value
                    FROM eoip_commit_test
                    """)).scalar_one()

            assert result == 42

            connection.execute(text("""
                    DROP TABLE IF EXISTS eoip_commit_test
                    """))
            connection.commit()

    def test_session_scope_rolls_back_failed_transaction(
        self,
        engine: Engine,
    ) -> None:
        with engine.connect() as connection:
            connection.execute(text("""
                    CREATE TEMP TABLE eoip_rollback_test (
                        value INTEGER NOT NULL
                    )
                    ON COMMIT PRESERVE ROWS
                    """))
            connection.commit()

            temporary_factory = sessionmaker(
                bind=connection,
                class_=Session,
                autoflush=False,
                expire_on_commit=False,
            )

            with (
                pytest.raises(
                    RuntimeError,
                    match="Force transaction rollback",
                ),
                session_scope(temporary_factory) as session,
            ):
                session.execute(text("""
                        INSERT INTO eoip_rollback_test (
                            value
                        )
                        VALUES (99)
                        """))

                raise RuntimeError("Force transaction rollback")

            count = connection.execute(text("""
                    SELECT COUNT(*)
                    FROM eoip_rollback_test
                    """)).scalar_one()

            assert count == 0

            connection.execute(text("""
                    DROP TABLE IF EXISTS eoip_rollback_test
                    """))
            connection.commit()


class TestDatabaseConstraints:
    """Verify important PostgreSQL relationships and constraints."""

    def test_plant_primary_key_exists(
        self,
        engine: Engine,
    ) -> None:
        inspector = inspect(engine)

        primary_key = inspector.get_pk_constraint(
            "plants",
            schema="public",
        )

        assert primary_key["constrained_columns"] == [
            "plant_id",
        ]

    def test_equipment_foreign_keys_exist(
        self,
        engine: Engine,
    ) -> None:
        inspector = inspect(engine)

        foreign_keys = inspector.get_foreign_keys(
            "equipment",
            schema="public",
        )

        referred_tables = {
            foreign_key["referred_table"] for foreign_key in foreign_keys
        }

        assert "plants" in referred_tables
        assert "equipment" in referred_tables

    def test_incident_alarm_relationship_exists(
        self,
        engine: Engine,
    ) -> None:
        inspector = inspect(engine)

        foreign_keys = inspector.get_foreign_keys(
            "incidents",
            schema="public",
        )

        referred_tables = {
            foreign_key["referred_table"] for foreign_key in foreign_keys
        }

        assert "alarms" in referred_tables

    def test_work_order_incident_relationship_exists(
        self,
        engine: Engine,
    ) -> None:
        inspector = inspect(engine)

        foreign_keys = inspector.get_foreign_keys(
            "work_orders",
            schema="public",
        )

        referred_tables = {
            foreign_key["referred_table"] for foreign_key in foreign_keys
        }

        assert "incidents" in referred_tables
