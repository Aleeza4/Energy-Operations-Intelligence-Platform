"""Configuration-security tests for EOIP application settings."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields

import pytest

from eoip.api.security import AuthService
from eoip.config.settings import Settings, settings
from eoip.core.constants import PROJECT_NAME


def _setting_names() -> set[str]:
    """Return the declared Settings dataclass field names."""
    return {field.name for field in fields(Settings)}


def test_settings_is_slotted_dataclass() -> None:
    """Settings should not expose a mutable instance dictionary."""
    assert not hasattr(settings, "__dict__")


def test_settings_is_immutable() -> None:
    """Runtime configuration should not be mutable accidentally."""
    with pytest.raises(FrozenInstanceError):
        settings.log_level = "DEBUG"  # type: ignore[misc]


def test_project_identity_is_expected() -> None:
    """The application should expose the expected project identity."""
    assert settings.project_name == PROJECT_NAME


def test_database_port_is_valid() -> None:
    """Database port must remain inside the valid TCP port range."""
    assert isinstance(settings.database_port, int)
    assert 1 <= settings.database_port <= 65_535


def test_database_identity_fields_are_not_empty() -> None:
    """Core database connection identity must be configured."""
    assert settings.database_host.strip()
    assert settings.database_name.strip()
    assert settings.database_user.strip()


def test_api_environment_is_not_empty() -> None:
    """API environment must have an explicit non-empty value."""
    assert settings.api_environment.strip()


def test_api_version_is_not_empty() -> None:
    """API version must have an explicit non-empty value."""
    assert settings.api_version.strip()


def test_token_expiry_is_positive() -> None:
    """Access-token lifetime must be positive."""
    assert isinstance(settings.api_token_expiry_minutes, int)
    assert settings.api_token_expiry_minutes > 0


def test_token_secret_meets_auth_service_minimum_length() -> None:
    """Configured token secret must satisfy AuthService requirements."""
    assert isinstance(settings.api_token_secret, str)
    assert len(settings.api_token_secret) >= 32


def test_current_security_configuration_can_initialize_auth_service() -> None:
    """Security settings should construct a valid authentication service."""
    service = AuthService(
        secret=settings.api_token_secret,
        expiry_minutes=settings.api_token_expiry_minutes,
        users=(),
    )

    assert service.expires_in_seconds == settings.api_token_expiry_minutes * 60


def test_sensitive_configuration_fields_exist() -> None:
    """Security-sensitive configuration must remain explicitly represented."""
    names = _setting_names()

    assert "database_password" in names
    assert "api_token_secret" in names


def test_settings_repr_does_not_need_to_be_used_for_secret_logging() -> None:
    """Sensitive values should be addressable without requiring object dumping."""
    names = _setting_names()

    assert "database_password" in names
    assert "api_token_secret" in names

    assert hasattr(settings, "database_password")
    assert hasattr(settings, "api_token_secret")


def test_settings_has_no_model_dump_interface() -> None:
    """Settings is intentionally not a serialization-oriented Pydantic model."""
    assert not hasattr(settings, "model_dump")


@pytest.mark.parametrize(
    "attribute",
    (
        "database_host",
        "database_name",
        "database_user",
        "log_level",
        "api_environment",
        "api_version",
    ),
)
def test_required_text_settings_are_strings(
    attribute: str,
) -> None:
    """Required textual configuration values must remain strings."""
    value = getattr(settings, attribute)

    assert isinstance(value, str)
    assert value.strip()


def test_database_password_is_string_typed() -> None:
    """Database password configuration should have a predictable type."""
    assert isinstance(settings.database_password, str)


def test_token_secret_is_not_database_password() -> None:
    """Authentication signing material must not reuse DB credentials."""
    if settings.database_password:
        assert settings.api_token_secret != settings.database_password


def test_token_secret_is_not_project_name() -> None:
    """Public project metadata must never double as signing material."""
    assert settings.api_token_secret != settings.project_name


@pytest.mark.parametrize(
    "unsafe_secret",
    (
        "",
        "secret",
        "password",
        "development",
        "changeme",
        "default",
    ),
)
def test_auth_service_rejects_obviously_short_signing_secrets(
    unsafe_secret: str,
) -> None:
    """Obviously weak short signing secrets must fail authentication setup."""
    with pytest.raises(
        ValueError,
        match="token secret must contain at least 32 characters",
    ):
        AuthService(
            secret=unsafe_secret,
            expiry_minutes=30,
            users=(),
        )


@pytest.mark.parametrize(
    "invalid_expiry",
    (
        0,
        -1,
        -30,
    ),
)
def test_auth_service_rejects_non_positive_token_expiry(
    invalid_expiry: int,
) -> None:
    """Zero or negative access-token lifetimes must fail closed."""
    with pytest.raises(
        ValueError,
        match="expiry_minutes must be positive",
    ):
        AuthService(
            secret="configuration-security-secret-123456789",
            expiry_minutes=invalid_expiry,
            users=(),
        )
