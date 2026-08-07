"""
SQLAlchemy engine creation for EOIP.
"""

from __future__ import annotations

from sqlalchemy import Engine, create_engine

from eoip.database.config import DatabaseConfig


def create_database_engine(
    config: DatabaseConfig | None = None,
) -> Engine:
    """
    Create and configure the SQLAlchemy engine.
    """
    cfg = config or DatabaseConfig()

    return create_engine(
        cfg.connection_url,
        echo=cfg.echo_sql,
        pool_size=cfg.pool_size,
        max_overflow=cfg.max_overflow,
        pool_timeout=cfg.pool_timeout,
        pool_recycle=cfg.pool_recycle,
        future=True,
    )


__all__ = [
    "create_database_engine",
]
