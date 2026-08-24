"""Administration page for the EOIP Streamlit application."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from eoip.app.components import (
    MetricCard,
    render_dataframe,
    render_metric_row,
    render_page_intro,
    render_section_header,
    render_status,
)


@st.cache_data(show_spinner=False)
def _platform_modules_data() -> pd.DataFrame:
    """Return temporary EOIP platform-module status."""
    return pd.DataFrame(
        {
            "Module": [
                "Synthetic Data Engine",
                "ETL Platform",
                "Database Layer",
                "Analytics Engine",
                "Forecasting",
                "Anomaly Detection",
                "Predictive Maintenance",
                "Optimization Engine",
                "Streamlit Application",
            ],
            "Status": [
                "Operational",
                "Operational",
                "Operational",
                "Operational",
                "Operational",
                "Operational",
                "Operational",
                "Operational",
                "In Development",
            ],
            "Phase": [
                "Phase 2",
                "Phase 3",
                "Phase 4",
                "Phase 5",
                "Phase 6",
                "Phase 7",
                "Phase 8",
                "Phase 9",
                "Phase 10",
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _environment_data() -> pd.DataFrame:
    """Return temporary environment information."""
    return pd.DataFrame(
        {
            "Setting": [
                "Application",
                "Environment",
                "Database",
                "Time-Series Engine",
                "Frontend",
                "API",
                "Version",
            ],
            "Value": [
                "Energy Operations Intelligence Platform",
                "Development",
                "PostgreSQL",
                "TimescaleDB",
                "Streamlit",
                "FastAPI — Phase 11",
                "0.10.0-dev",
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _service_health_data() -> pd.DataFrame:
    """Return temporary service-health information."""
    return pd.DataFrame(
        {
            "Service": [
                "Application",
                "PostgreSQL",
                "TimescaleDB",
                "Analytics Engine",
                "Forecasting Engine",
                "Anomaly Engine",
                "Maintenance Engine",
                "Optimization Engine",
            ],
            "Status": [
                "Healthy",
                "Healthy",
                "Healthy",
                "Healthy",
                "Healthy",
                "Healthy",
                "Healthy",
                "Healthy",
            ],
        }
    )


def render() -> None:
    """Render the EOIP Administration page."""
    render_page_intro(
        title="Administration",
        icon="⚙️",
        description=(
            "Platform configuration, module status, environment "
            "information, and system-health overview."
        ),
    )

    render_status(
        "EOIP platform services are operational.",
        level="success",
    )

    render_section_header(
        "Platform Overview",
        description=("Current platform version and service-health indicators."),
    )

    render_metric_row(
        (
            MetricCard(
                label="Platform Version",
                value="0.10.0-dev",
            ),
            MetricCard(
                label="Active Modules",
                value="9",
            ),
            MetricCard(
                label="Healthy Services",
                value="8 / 8",
            ),
            MetricCard(
                label="Environment",
                value="Development",
            ),
        )
    )

    st.write("")

    left_column, right_column = st.columns((3, 2))

    with left_column:
        render_section_header(
            "Platform Modules",
            description=("Implementation status across EOIP engineering phases."),
        )

        render_dataframe(_platform_modules_data())

    with right_column:
        render_section_header(
            "Environment",
            description=("Current application and infrastructure configuration."),
        )

        render_dataframe(_environment_data())

    render_section_header(
        "Service Health",
        description=("Current health state of major EOIP services and engines."),
    )

    render_dataframe(_service_health_data())

    render_section_header(
        "Application Settings",
        description=("Development controls for the EOIP interface."),
    )

    first_column, second_column = st.columns(2)

    with first_column:
        st.selectbox(
            "Default Dashboard",
            options=[
                "Executive Dashboard",
                "Operations Dashboard",
                "Plant Performance",
                "Asset Dashboard",
            ],
            index=0,
            key="admin_default_dashboard",
        )

        st.selectbox(
            "Default Time Range",
            options=[
                "24 Hours",
                "7 Days",
                "30 Days",
                "90 Days",
            ],
            index=1,
            key="admin_default_time_range",
        )

    with second_column:
        st.toggle(
            "Enable forecast intelligence",
            value=True,
            key="admin_forecast_enabled",
        )

        st.toggle(
            "Enable anomaly alerts",
            value=True,
            key="admin_anomaly_enabled",
        )

        st.toggle(
            "Enable optimization recommendations",
            value=True,
            key="admin_optimization_enabled",
        )

    st.info(
        "Administration controls currently demonstrate the Phase 10 "
        "configuration interface. Persistent settings will be integrated "
        "with the API and authorization layers in later phases."
    )
