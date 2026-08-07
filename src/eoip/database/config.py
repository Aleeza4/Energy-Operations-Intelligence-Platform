"""
Database configuration for EOIP.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    """
    Configuration used to connect to PostgreSQL.
    """

    host: str = "localhost"
    port: int = 5432
    database: str = "eoip"
    username: str = "postgres"
    password: str = "postgres"

    echo_sql: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 1800

    @property
    def connection_url(self) -> str:
        """Return the SQLAlchemy PostgreSQL connection URL."""
        return (
            "postgresql+psycopg://"
            f"{self.username}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )


__all__ = ["DatabaseConfig"]
