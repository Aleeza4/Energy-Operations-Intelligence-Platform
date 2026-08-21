"""Alarms and incidents dashboard for the EOIP Streamlit application."""

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


@st.cache_data(show_spinner=False)
def _alarm_summary_data() -> pd.DataFrame:
    """Return temporary alarm summary data."""
    return pd.DataFrame(
        {
            "Severity": [
                "Critical",
                "High",
                "Medium",
                "Low",
            ],
            "Count": [
                3,
                8,
                11,
                18,
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _alarm_trend_data() -> pd.DataFrame:
    """Return temporary alarm trend data."""
    return pd.DataFrame(
        {
            "Time": pd.date_range(
                start="2026-08-20 00:00",
                periods=12,
                freq="2h",
            ),
            "Critical": [
                0,
                1,
                0,
                1,
                1,
                2,
                1,
                2,
                1,
                1,
                0,
                1,
            ],
            "High": [
                1,
                2,
                2,
                3,
                4,
                5,
                4,
                3,
                5,
                4,
                3,
                2,
            ],
            "Medium": [
                3,
                4,
                5,
                4,
                6,
                7,
                5,
                6,
                7,
                5,
                4,
                4,
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _incident_data() -> pd.DataFrame:
    """Return temporary incident data."""
    return pd.DataFrame(
        {
            "Incident ID": [
                "INC-1042",
                "INC-1041",
                "INC-1039",
                "INC-1038",
                "INC-1034",
            ],
            "Plant": [
                "Solar Plant D",
                "Solar Plant B",
                "Solar Plant C",
                "Solar Plant D",
                "Solar Plant A",
            ],
            "Equipment": [
                "INV-005",
                "INV-003",
                "TRF-002",
                "INV-006",
                "INV-001",
            ],
            "Severity": [
                "Critical",
                "High",
                "Medium",
                "High",
                "Medium",
            ],
            "Status": [
                "Open",
                "Investigating",
                "Monitoring",
                "Open",
                "Resolved",
            ],
            "MTTA (min)": [
                4,
                7,
                12,
                6,
                9,
            ],
            "Downtime (min)": [
                86,
                42,
                21,
                31,
                18,
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _response_metrics_data() -> pd.DataFrame:
    """Return temporary incident-response data."""
    return pd.DataFrame(
        {
            "Plant": [
                "Solar Plant A",
                "Solar Plant B",
                "Solar Plant C",
                "Solar Plant D",
            ],
            "MTTA (min)": [
                7.2,
                8.5,
                6.8,
                5.4,
            ],
            "MTTR (min)": [
                31.0,
                45.0,
                27.0,
                58.0,
            ],
        }
    )


def render() -> None:
    """Render the EOIP Alarms and Incidents Dashboard."""
    render_page_intro(
        title="Alarms & Incidents",
        icon="🚨",
        description=(
            "Alarm severity, incident response, downtime, MTTA, "
            "and MTTR intelligence."
        ),
    )
    filters = render_global_filters(show_equipment=True)
    st.caption(format_filter_caption(filters))

    render_status(
        "Alarm and incident monitoring is operational.",
        level="success",
    )

    render_section_header(
        "Alarm & Incident Overview",
        description=("Current event volume and operational-response indicators."),
    )

    render_metric_row(
        (
            MetricCard(
                label="Active Alarms",
                value="40",
                delta="+6",
            ),
            MetricCard(
                label="Critical Alarms",
                value="3",
                delta="+1",
            ),
            MetricCard(
                label="Open Incidents",
                value="4",
                delta="+1",
            ),
            MetricCard(
                label="Average MTTA",
                value="6.8 min",
                delta="-0.9 min",
            ),
        )
    )

    st.write("")

    left_column, right_column = st.columns((2, 3))

    with left_column:
        render_section_header(
            "Alarm Severity",
            description="Current alarm distribution by severity.",
        )

        alarm_summary = _alarm_summary_data()

        severity_figure = px.pie(
            alarm_summary,
            names="Severity",
            values="Count",
            hole=0.55,
        )

        severity_figure.update_layout(
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20,
            ),
            legend_title_text="",
        )

        render_plotly_chart(
            severity_figure,
            data=alarm_summary,
        )

    with right_column:
        render_section_header(
            "Alarm Trend",
            description=("Recent alarm activity by operational severity."),
        )

        alarm_trend = apply_dataframe_filters(_alarm_trend_data(), filters)

        alarm_long = alarm_trend.melt(
            id_vars="Time",
            value_vars=[
                "Critical",
                "High",
                "Medium",
            ],
            var_name="Severity",
            value_name="Alarm Count",
        )

        trend_figure = px.line(
            alarm_long,
            x="Time",
            y="Alarm Count",
            color="Severity",
            markers=True,
        )

        trend_figure.update_layout(
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20,
            ),
            legend_title_text="",
        )

        render_plotly_chart(
            trend_figure,
            data=alarm_long,
            time_series=True,
        )

    render_section_header(
        "Incident Register",
        description=("Current and recently resolved operational incidents."),
    )

    incidents = apply_dataframe_filters(_incident_data(), filters)

    render_dataframe(
        incidents,
    )
    render_csv_download(
        incidents,
        label="Download incident register CSV",
        report_name="incident-register",
        filters=filters,
        key="incidents_download",
    )

    render_section_header(
        "Response Performance",
        description=("Plant-level acknowledgement and repair performance."),
    )

    response = apply_dataframe_filters(_response_metrics_data(), filters)

    response_long = response.melt(
        id_vars="Plant",
        value_vars=[
            "MTTA (min)",
            "MTTR (min)",
        ],
        var_name="Metric",
        value_name="Minutes",
    )

    response_figure = px.bar(
        response_long,
        x="Plant",
        y="Minutes",
        color="Metric",
        barmode="group",
    )

    response_figure.update_layout(
        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20,
        ),
        legend_title_text="",
    )

    render_plotly_chart(
        response_figure,
        data=response_long,
    )
