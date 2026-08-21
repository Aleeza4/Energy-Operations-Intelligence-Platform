"""FastAPI dependency wiring for EOIP database and service boundaries."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from eoip.api.provider import DataProvider, SQLAlchemyDataProvider
from eoip.config.settings import settings
from eoip.database.config import DatabaseConfig
from eoip.database.engine import create_database_engine
from eoip.database.session import create_session_factory


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create the shared lazy SQLAlchemy engine."""
    return create_database_engine(
        DatabaseConfig(
            host=settings.database_host,
            port=settings.database_port,
            database=settings.database_name,
            username=settings.database_user,
            password=settings.database_password,
        )
    )


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Return the shared EOIP SQLAlchemy session factory."""
    return create_session_factory(get_engine())


def get_session() -> Generator[Session, None, None]:
    """Provide a request-scoped session with rollback and cleanup."""
    session = get_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_data_provider(
    session: Annotated[Session, Depends(get_session)],
) -> DataProvider:
    """Provide the database-backed API data boundary."""
    return SQLAlchemyDataProvider(session)


Provider = Annotated[DataProvider, Depends(get_data_provider)]
