"""Database configuration for EOIP."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus

from dotenv import load_dotenv

from eoip.core.constants import PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    """Configuration used to connect to PostgreSQL."""

    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None
    database_url: str | None = None
    echo_sql: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 1800

    def __post_init__(self) -> None:
        """Validate database configuration."""
        env_database_url = os.getenv("EOIP_DATABASE_URL")
        if self.database_url is None:
            self.database_url = env_database_url

        if self.database_url is not None and not self.database_url.strip():
            self.database_url = None

        if self.database_url is None:
            if not self.host or not self.database or not self.username:
                raise RuntimeError(
                    "EOIP_DATABASE_URL is not set. Set it in your environment or .env "
                    "before starting the app."
                )
            port = self.port or 5432
            password = self.password or ""
            username = quote_plus(self.username)
            password = quote_plus(password)
            self.database_url = (
                f"postgresql+psycopg2://{username}:{password}@{self.host}:{port}/"
                f"{self.database}"
            )

        if not isinstance(self.echo_sql, bool):
            raise TypeError("echo_sql must be a boolean.")

        for field_name in (
            "pool_size",
            "max_overflow",
            "pool_timeout",
            "pool_recycle",
        ):
            value = getattr(self, field_name)

            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer.")

            if value < 0:
                raise ValueError(f"{field_name} must be greater than or equal to zero.")

    @property
    def connection_url(self) -> str:
        """Return the SQLAlchemy PostgreSQL connection URL."""
        if not self.database_url or not self.database_url.strip():
            raise RuntimeError(
                "EOIP_DATABASE_URL is not set. Set it in your environment or .env "
                "before starting the app."
            )
        return self.database_url


__all__ = ["DatabaseConfig"]
