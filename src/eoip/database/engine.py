"""SQLAlchemy engine creation for EOIP."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from eoip.database.config import DatabaseConfig


def create_database_engine(
    config: DatabaseConfig | None = None,
) -> Engine:
    """Create and configure the SQLAlchemy database engine."""
    cfg = config or DatabaseConfig()

    if not isinstance(cfg, DatabaseConfig):
        raise TypeError("config must be a DatabaseConfig or None.")

    return create_engine(
        cfg.connection_url,
        echo=cfg.echo_sql,
        pool_size=cfg.pool_size,
        max_overflow=cfg.max_overflow,
        pool_timeout=cfg.pool_timeout,
        pool_recycle=cfg.pool_recycle,
        pool_pre_ping=True,
        future=True,
    )


__all__ = [
    "create_database_engine",
]
