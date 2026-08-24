"""Unit tests for EOIP PostgreSQL backup and restore commands."""

from __future__ import annotations

from pathlib import Path

import pytest

from eoip.database.backup.commands import (
    BackupConfig,
    build_backup_command,
    build_restore_command,
)


class TestBackupConfig:
    """Tests for backup configuration validation."""

    def test_valid_configuration(self) -> None:
        config = BackupConfig(
            host="127.0.0.1",
            port=5432,
            database="eoip_db",
            username="eoip_user",
        )

        assert config.host == "127.0.0.1"
        assert config.port == 5432
        assert config.database == "eoip_db"
        assert config.username == "eoip_user"

    @pytest.mark.parametrize(
        "host",
        [
            "",
            "   ",
        ],
    )
    def test_rejects_empty_host(
        self,
        host: str,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="host must not be empty",
        ):
            BackupConfig(
                host=host,
                port=5432,
                database="eoip_db",
                username="eoip_user",
            )

    @pytest.mark.parametrize(
        "port",
        [
            0,
            -1,
            65536,
        ],
    )
    def test_rejects_invalid_port(
        self,
        port: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="port must be between 1 and 65535",
        ):
            BackupConfig(
                host="127.0.0.1",
                port=port,
                database="eoip_db",
                username="eoip_user",
            )

    @pytest.mark.parametrize(
        "database",
        [
            "",
            "   ",
        ],
    )
    def test_rejects_empty_database(
        self,
        database: str,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="database must not be empty",
        ):
            BackupConfig(
                host="127.0.0.1",
                port=5432,
                database=database,
                username="eoip_user",
            )

    @pytest.mark.parametrize(
        "username",
        [
            "",
            "   ",
        ],
    )
    def test_rejects_empty_username(
        self,
        username: str,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="username must not be empty",
        ):
            BackupConfig(
                host="127.0.0.1",
                port=5432,
                database="eoip_db",
                username=username,
            )


class TestBuildBackupCommand:
    """Tests for PostgreSQL backup command creation."""

    def test_builds_expected_backup_command(self) -> None:
        config = BackupConfig(
            host="127.0.0.1",
            port=5432,
            database="eoip_db",
            username="eoip_user",
        )

        result = build_backup_command(
            config,
            Path("backups/eoip.dump"),
        )

        assert result == [
            "pg_dump",
            "--host",
            "127.0.0.1",
            "--port",
            "5432",
            "--username",
            "eoip_user",
            "--dbname",
            "eoip_db",
            "--format=custom",
            "--verbose",
            "--file",
            str(Path("backups/eoip.dump")),
        ]

    def test_accepts_string_output_path(self) -> None:
        config = BackupConfig(
            host="localhost",
            port=5432,
            database="eoip_db",
            username="eoip_user",
        )

        result = build_backup_command(
            config,
            "eoip.dump",
        )

        assert result[-2:] == [
            "--file",
            "eoip.dump",
        ]


class TestBuildRestoreCommand:
    """Tests for PostgreSQL restore command creation."""

    def test_builds_restore_command_without_clean(self) -> None:
        config = BackupConfig(
            host="127.0.0.1",
            port=5432,
            database="eoip_db",
            username="eoip_user",
        )

        result = build_restore_command(
            config,
            Path("backups/eoip.dump"),
        )

        assert result == [
            "pg_restore",
            "--host",
            "127.0.0.1",
            "--port",
            "5432",
            "--username",
            "eoip_user",
            "--dbname",
            "eoip_db",
            "--verbose",
            str(Path("backups/eoip.dump")),
        ]

    def test_builds_restore_command_with_clean(self) -> None:
        config = BackupConfig(
            host="127.0.0.1",
            port=5432,
            database="eoip_db",
            username="eoip_user",
        )

        result = build_restore_command(
            config,
            "eoip.dump",
            clean=True,
        )

        assert "--clean" in result
        assert "--if-exists" in result
        assert result[-1] == "eoip.dump"

    def test_clean_options_are_omitted_by_default(self) -> None:
        config = BackupConfig(
            host="127.0.0.1",
            port=5432,
            database="eoip_db",
            username="eoip_user",
        )

        result = build_restore_command(
            config,
            "eoip.dump",
        )

        assert "--clean" not in result
        assert "--if-exists" not in result
