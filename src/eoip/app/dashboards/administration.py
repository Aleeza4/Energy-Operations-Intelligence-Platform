"""Read-only platform administration and governance workspace."""

from __future__ import annotations

from dataclasses import fields

import pandas as pd
import streamlit as st

import eoip.database.models  # noqa: F401
from eoip import __version__
from eoip.api.app import create_app
from eoip.api.schemas import Role
from eoip.app.components import (
    PageContext,
    render_dataframe,
    render_empty_state,
    render_page_context,
    render_page_intro,
    render_section_header,
)
from eoip.config.settings import Settings, settings
from eoip.database.base import Base

SAFE_ADMIN_FIELDS: tuple[str, ...] = (
    "project_name",
    "api_environment",
    "api_prefix",
    "api_version",
    "database_host",
    "database_port",
    "database_name",
    "log_level",
)
SENSITIVE_FIELD_MARKERS: tuple[str, ...] = (
    "password",
    "secret",
    "token",
    "api_key",
    "private_key",
    "database_url",
)


def safe_configuration(active_settings: Settings) -> pd.DataFrame:
    """Return explicitly allow-listed non-secret configuration values."""
    available_fields = {field.name for field in fields(active_settings)}
    rows = []
    for name in SAFE_ADMIN_FIELDS:
        if name not in available_fields:
            continue
        rows.append(
            {
                "Configuration": name.replace("_", " ").title(),
                "Value": str(getattr(active_settings, name)),
                "State": "Configured",
            }
        )
    return pd.DataFrame(rows)


def contains_sensitive_configuration(dataframe: pd.DataFrame) -> bool:
    """Return whether rendered configuration names contain sensitive markers."""
    if dataframe.empty:
        return False
    names = " ".join(dataframe["Configuration"].astype(str)).casefold()
    return any(marker in names for marker in SENSITIVE_FIELD_MARKERS)


def database_metadata() -> pd.DataFrame:
    """Return static database architecture without making a runtime connection."""
    return pd.DataFrame(
        {
            "Capability": [
                "Database dialect",
                "Configured database",
                "Registered ORM tables",
                "TimescaleDB extension",
                "Hypertables",
                "Continuous aggregates",
                "Schema revision",
                "Runtime database readiness",
            ],
            "Value": [
                "PostgreSQL",
                settings.database_name,
                str(len(Base.metadata.tables)),
                "Supported by architecture; not verified",
                "Not verified in this runtime",
                "Not verified in this runtime",
                "Not available",
                "Not verified",
            ],
            "Evidence Type": [
                "Static configuration",
                "Static configuration",
                "Application metadata",
                "Repository capability",
                "Runtime metadata unavailable",
                "Runtime metadata unavailable",
                "Migration metadata unavailable",
                "No connection check performed",
            ],
        }
    )


def api_capabilities() -> pd.DataFrame:
    """Derive API capability categories from the configured FastAPI routes."""
    try:
        application = create_app()
        capabilities: dict[str, int] = {}
        for path_item in application.openapi()["paths"].values():
            for operation in path_item.values():
                for tag in operation.get("tags", ()):
                    capabilities[str(tag)] = capabilities.get(str(tag), 0) + 1
    except Exception:  # pragma: no cover - defensive runtime boundary
        return pd.DataFrame(columns=("Capability", "Routes", "State"))
    return pd.DataFrame(
        [
            {"Capability": name, "Routes": count, "State": "Configured"}
            for name, count in sorted(capabilities.items())
        ]
    )


def security_capabilities() -> pd.DataFrame:
    """Describe configured security capabilities without activity claims."""
    return pd.DataFrame(
        {
            "Capability": [
                "Authentication",
                "Token signing",
                "Configured roles",
                "Administration protection",
            ],
            "Configuration": [
                "OAuth2 bearer",
                "HMAC signed expiring token",
                ", ".join(role.value for role in Role),
                "Administrator role required",
            ],
            "Runtime State": [
                "Configured; not health-checked",
                "Configured; secret hidden",
                "Configured",
                "Configured",
            ],
        }
    )


def render() -> None:
    """Render the EOIP Platform Administration workspace."""
    render_page_intro(
        title="Platform Administration",
        icon="administration",
        description="Read-only platform identity, configuration, and capabilities.",
    )
    render_page_context(PageContext(scope="Platform"))

    render_section_header(
        "Platform Identity",
        description=(
            "Versioned application identity from package and API configuration."
        ),
    )
    identity = pd.DataFrame(
        {
            "Property": [
                "Application",
                "Package Version",
                "API Version",
                "Environment",
            ],
            "Value": [
                settings.project_name,
                __version__,
                settings.api_version,
                settings.api_environment,
            ],
        }
    )
    render_dataframe(identity)

    render_section_header(
        "Configuration Summary",
        description="Explicitly allow-listed non-secret configuration.",
    )
    configuration = safe_configuration(settings)
    render_dataframe(configuration)

    render_section_header(
        "Data Platform",
        description="Configured architecture separated from unverified runtime state.",
    )
    render_dataframe(database_metadata())

    render_section_header(
        "API & Application Capabilities",
        description="Capability categories derived from registered FastAPI routes.",
    )
    capabilities = api_capabilities()
    if capabilities.empty:
        render_empty_state(
            title="API metadata unavailable",
            message="API route introspection was not available in this runtime.",
        )
    else:
        render_dataframe(capabilities)

    render_section_header(
        "Security & Access",
        description="Configured authentication and authorization capabilities only.",
    )
    render_dataframe(security_capabilities())

    render_section_header(
        "Runtime Readiness",
        description="No database or service health checks run on dashboard rerenders.",
    )
    render_empty_state(
        title="Runtime readiness not verified",
        message=(
            "This governance page reports configuration and detected capabilities; "
            "it does not operate as a service monitor."
        ),
    )

    with st.expander("Technical detail"):
        render_dataframe(
            pd.DataFrame(
                {
                    "Registered ORM Table": sorted(Base.metadata.tables.keys()),
                }
            )
        )
