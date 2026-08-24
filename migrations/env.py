"""Alembic migration environment for EOIP."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Importing this package registers all ORM tables with Base.metadata.
import eoip.database.models  # noqa: F401
from eoip.database.base import Base

DATABASE_URL_ENV_VAR = "EOIP_DATABASE_URL"

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    """Return the database URL used by Alembic."""
    database_url = os.getenv(DATABASE_URL_ENV_VAR)

    if not database_url:
        raise RuntimeError(
            f"{DATABASE_URL_ENV_VAR} is not set. "
            "Set the environment variable before running Alembic."
        )

    return database_url


def run_migrations_offline() -> None:
    """Run Alembic migrations without opening a database connection."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run Alembic migrations using a live database connection."""
    section = config.get_section(
        config.config_ini_section,
        {},
    )

    section["sqlalchemy.url"] = _database_url()

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
