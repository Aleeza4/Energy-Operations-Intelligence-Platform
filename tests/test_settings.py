"""Smoke tests for application environment configuration."""

from eoip.config.settings import settings
from eoip.core.constants import PROJECT_NAME


def test_settings_load_from_environment() -> None:
    """The shared settings object loads with valid core value types."""
    assert settings.project_name == PROJECT_NAME
    assert settings.database_host
    assert 1 <= settings.database_port <= 65_535
    assert settings.database_name
    assert settings.database_user
    assert settings.log_level
