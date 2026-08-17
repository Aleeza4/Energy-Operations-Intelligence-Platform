"""Backup and restore command builders for the EOIP PostgreSQL database."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BackupConfig:
    """Configuration required for PostgreSQL backup and restore commands."""

    host: str
    port: int
    database: str
    username: str

    def __post_init__(self) -> None:
        """Validate backup configuration."""
        if not self.host.strip():
            raise ValueError("host must not be empty")

        if self.port < 1 or self.port > 65535:
            raise ValueError("port must be between 1 and 65535")

        if not self.database.strip():
            raise ValueError("database must not be empty")

        if not self.username.strip():
            raise ValueError("username must not be empty")


def build_backup_command(
    config: BackupConfig,
    output_path: str | Path,
) -> list[str]:
    """Build a PostgreSQL custom-format backup command."""
    path = Path(output_path)

    return [
        "pg_dump",
        "--host",
        config.host,
        "--port",
        str(config.port),
        "--username",
        config.username,
        "--dbname",
        config.database,
        "--format=custom",
        "--verbose",
        "--file",
        str(path),
    ]


def build_restore_command(
    config: BackupConfig,
    backup_path: str | Path,
    *,
    clean: bool = False,
) -> list[str]:
    """Build a PostgreSQL restore command for a custom-format backup."""
    path = Path(backup_path)

    command = [
        "pg_restore",
        "--host",
        config.host,
        "--port",
        str(config.port),
        "--username",
        config.username,
        "--dbname",
        config.database,
        "--verbose",
    ]

    if clean:
        command.extend(
            [
                "--clean",
                "--if-exists",
            ]
        )

    command.append(str(path))

    return command
