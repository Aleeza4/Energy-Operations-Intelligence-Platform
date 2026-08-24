"""Database configuration for EOIP."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote_plus


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    """Configuration used to connect to PostgreSQL."""

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

    def __post_init__(self) -> None:
        """Validate database configuration."""
        if not isinstance(self.host, str):
            raise TypeError("host must be a string.")

        if not self.host.strip():
            raise ValueError("host cannot be empty.")

        if isinstance(self.port, bool) or not isinstance(self.port, int):
            raise TypeError("port must be an integer.")

        if not 1 <= self.port <= 65_535:
            raise ValueError("port must be between 1 and 65535.")

        if not isinstance(self.database, str):
            raise TypeError("database must be a string.")

        if not self.database.strip():
            raise ValueError("database cannot be empty.")

        if not isinstance(self.username, str):
            raise TypeError("username must be a string.")

        if not self.username.strip():
            raise ValueError("username cannot be empty.")

        if not isinstance(self.password, str):
            raise TypeError("password must be a string.")

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
        username = quote_plus(self.username)
        password = quote_plus(self.password)

        return (
            f"postgresql+psycopg2://{username}:{password}"
            f"@{self.host}:{self.port}/{self.database}"
        )


__all__ = ["DatabaseConfig"]
