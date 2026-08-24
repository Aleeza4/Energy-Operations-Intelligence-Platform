"""
SQLAlchemy session management for EOIP.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker


def create_session_factory(
    engine: Engine,
) -> sessionmaker[Session]:
    """Create a configured SQLAlchemy session factory."""
    return sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )


@contextmanager
def session_scope(
    session_factory: sessionmaker[Session],
) -> Generator[Session, None, None]:
    """
    Provide a transactional session scope.

    The transaction is committed on success and rolled back when an
    exception occurs.
    """
    session = session_factory()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


__all__ = [
    "create_session_factory",
    "session_scope",
]
