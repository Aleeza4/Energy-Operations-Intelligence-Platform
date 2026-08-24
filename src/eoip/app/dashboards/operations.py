"""Operations dashboard for the EOIP Streamlit application."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from eoip.app.components import (
    MetricCard,
    format_filter_caption,
    render_csv_download,
    render_dataframe,
    render_global_filters,
    render_metric_row,
    render_page_intro,
    render_plotly_chart,
    render_section_header,
    render_status,
)
from eoip.app.data_filters import apply_dataframe_filters
from eoip.app.navigation import navigate_to


@st.cache_data(show_spinner=False)
def _operations_status_data() -> pd.DataFrame:
    """Return temporary operational-status data."""
    return pd.DataFrame(
        {
            "Plant": [
                "Solar Plant A",
                "Solar Plant B",
                "Solar Plant C",
                "Solar Plant D",
            ],
            "Status": [
                "Normal",
                "Watch",
                "Normal",
                "Critical",
            ],
            "Active Alarms": [
                2,
                7,
                1,
                14,
            ],
            "Open Incidents": [
                0,
                2,
                0,
                4,
            ],
            "Availability (%)": [
                98.8,
                95.9,
                99.2,
                91.6,
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _alarm_trend_data() -> pd.DataFrame:
    """Return temporary alarm-trend data."""
    return pd.DataFrame(
        {
            "Hour": [
                "00:00",
                "03:00",
                "06:00",
                "09:00",
                "12:00",
                "15:00",
                "18:00",
                "21:00",
            ],
            "Active Alarms": [
                4,
                3,
                5,
                8,
                13,
                11,
                7,
                5,
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _incident_data() -> pd.DataFrame:
    """Return temporary incident data."""
    return pd.DataFrame(
        {
            "Incident": [
                "INC-1042",
                "INC-1041",
                "INC-1038",
                "INC-1034",
            ],
            "Plant": [
                "Solar Plant D",
                "Solar Plant B",
                "Solar Plant D",
                "Solar Plant A",
            ],
            "Severity": [
                "Critical",
                "High",
                "High",
                "Medium",
            ],
            "Status": [
                "Open",
                "Investigating",
                "Open",
                "Resolved",
            ],
            "Downtime (min)": [
                86,
                42,
                31,
                18,
            ],
        }
    )


def render() -> None:
    """Render the EOIP Operations Dashboard."""
    render_page_intro(
        title="Operations Dashboard",
        icon="⚙️",
        description=(
            "Operational status, alarms, incidents, availability, "
            "and response intelligence."
        ),
    )
    filters = render_global_filters()
    st.caption(format_filter_caption(filters, show_equipment=False))

    render_status(
        "Operations monitoring is active.",
        level="success",
    )

    render_section_header(
        "Operational Overview",
        description=("Current portfolio-level operating condition."),
    )

    render_metric_row(
        (
            MetricCard(
                label="Plants Online",
                value="4 / 4",
                delta="100%",
            ),
            MetricCard(
                label="Active Alarms",
                value="24",
                delta="+5",
            ),
            MetricCard(
                label="Open Incidents",
                value="6",
                delta="+2",
            ),
            MetricCard(
                label="Technical Availability",
                value="96.4%",
                delta="-0.8%",
            ),
        )
    )

    st.write("")

    operations = apply_dataframe_filters(_operations_status_data(), filters)

    left_column, right_column = st.columns((3, 2))

    with left_column:
        render_section_header(
            "Plant Operating Status",
            description=("Availability, alarms, and incidents by plant."),
        )

        render_dataframe(
            operations,
            column_config={
                "Availability (%)": st.column_config.ProgressColumn(
                    "Availability (%)",
                    min_value=0.0,
                    max_value=100.0,
                    format="%.1f%%",
                )
            },
        )

    with right_column:
        render_section_header(
            "Availability by Plant",
            description=("Current plant-level technical availability."),
        )

        availability_figure = px.bar(
            operations,
            x="Plant",
            y="Availability (%)",
            text_auto=".1f",
        )

        availability_figure.update_layout(
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20,
            ),
            yaxis_range=[
                0,
                100,
            ],
        )

        render_plotly_chart(
            availability_figure,
            data=operations,
        )

    render_section_header(
        "Alarm Activity",
        description=("Recent active-alarm volume across the portfolio."),
    )

    alarm_trend = _alarm_trend_data()

    alarm_figure = px.line(
        alarm_trend,
        x="Hour",
        y="Active Alarms",
        markers=True,
    )

    alarm_figure.update_layout(
        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20,
        )
    )

    render_plotly_chart(
        alarm_figure,
        data=alarm_trend,
    )

    render_section_header(
        "Recent Incidents",
        description=("Current and recently resolved operational incidents."),
    )

    incidents = apply_dataframe_filters(_incident_data(), filters)

    render_dataframe(
        incidents,
    )
    render_csv_download(
        operations,
        label="Download plant status CSV",
        report_name="operations-plant-status",
        filters=filters,
        key="operations_status_download",
    )
    render_csv_download(
        incidents,
        label="Download incidents CSV",
        report_name="operations-incidents",
        filters=filters,
        key="operations_incidents_download",
    )

    if not incidents.empty:
        selected_incident = st.selectbox(
            "Incident drill-down",
            options=incidents["Incident"].tolist(),
            key="operations_drilldown_incident",
        )
        incident = incidents.loc[incidents["Incident"].eq(selected_incident)].iloc[0]
        if st.button("Investigate incident", key="operations_investigate_incident"):
            navigate_to("alarms_incidents", plant=str(incident["Plant"]))
