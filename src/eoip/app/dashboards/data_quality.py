"""Data quality dashboard for the EOIP Streamlit application."""

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
def _quality_summary_data() -> pd.DataFrame:
    """Return temporary data-quality summary."""
    return pd.DataFrame(
        {
            "Dataset": [
                "SCADA",
                "Weather",
                "Alarms",
                "Incidents",
                "Forecasts",
                "Maintenance",
            ],
            "Completeness (%)": [
                99.4,
                98.8,
                99.7,
                100.0,
                99.1,
                98.6,
            ],
            "Validity (%)": [
                99.8,
                99.2,
                99.5,
                100.0,
                98.9,
                99.0,
            ],
            "Freshness (%)": [
                99.9,
                99.4,
                99.8,
                100.0,
                98.7,
                98.9,
            ],
            "Failed Checks": [
                3,
                5,
                2,
                0,
                4,
                6,
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _quality_trend_data() -> pd.DataFrame:
    """Return temporary data-quality trend."""
    return pd.DataFrame(
        {
            "Date": pd.date_range(
                start="2026-08-14",
                periods=8,
                freq="D",
            ),
            "Quality Score (%)": [
                97.8,
                98.1,
                98.5,
                98.2,
                98.9,
                99.0,
                98.7,
                99.1,
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _failed_checks_data() -> pd.DataFrame:
    """Return temporary failed data-quality checks."""
    return pd.DataFrame(
        {
            "Check": [
                "SCADA timestamp continuity",
                "Weather null-value check",
                "Maintenance feature completeness",
                "Forecast timestamp alignment",
                "Equipment identifier integrity",
            ],
            "Dataset": [
                "SCADA",
                "Weather",
                "Maintenance",
                "Forecasts",
                "SCADA",
            ],
            "Severity": [
                "Medium",
                "Low",
                "High",
                "Medium",
                "High",
            ],
            "Affected Rows": [
                24,
                12,
                41,
                18,
                9,
            ],
            "Status": [
                "Investigating",
                "Open",
                "Open",
                "Monitoring",
                "Investigating",
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _pipeline_health_data() -> pd.DataFrame:
    """Return temporary ETL pipeline-health data."""
    return pd.DataFrame(
        {
            "Pipeline": [
                "SCADA Ingestion",
                "Weather Ingestion",
                "Operations Transform",
                "Analytics Refresh",
                "Forecast Refresh",
            ],
            "Status": [
                "Healthy",
                "Healthy",
                "Healthy",
                "Healthy",
                "Watch",
            ],
            "Last Run": [
                "09:25",
                "09:20",
                "09:18",
                "09:15",
                "08:45",
            ],
            "Duration (sec)": [
                42,
                18,
                31,
                27,
                64,
            ],
        }
    )


def render() -> None:
    """Render the EOIP Data Quality Dashboard."""
    render_page_intro(
        title="Data Quality",
        icon="✅",
        description=(
            "Completeness, validity, freshness, pipeline health, "
            "and data-validation intelligence."
        ),
    )
    filters = render_global_filters()
    st.caption(format_filter_caption(filters, show_equipment=False))

    render_status(
        "Data-quality monitoring is operational.",
        level="success",
    )

    render_section_header(
        "Quality Overview",
        description=(
            "Current platform-wide data quality and pipeline-health indicators."
        ),
    )

    render_metric_row(
        (
            MetricCard(
                label="Overall Quality Score",
                value="99.1%",
                delta="+0.4%",
            ),
            MetricCard(
                label="Completeness",
                value="99.3%",
                delta="+0.2%",
            ),
            MetricCard(
                label="Failed Checks",
                value="20",
                delta="-5",
            ),
            MetricCard(
                label="Healthy Pipelines",
                value="4 / 5",
                delta="80%",
            ),
        )
    )

    st.write("")

    quality_summary = _quality_summary_data()

    render_section_header(
        "Dataset Quality",
        description=(
            "Completeness, validity, freshness, and failed checks by dataset."
        ),
    )

    render_dataframe(
        quality_summary,
        column_config={
            "Completeness (%)": st.column_config.ProgressColumn(
                "Completeness (%)",
                min_value=0.0,
                max_value=100.0,
                format="%.1f%%",
            ),
            "Validity (%)": st.column_config.ProgressColumn(
                "Validity (%)",
                min_value=0.0,
                max_value=100.0,
                format="%.1f%%",
            ),
            "Freshness (%)": st.column_config.ProgressColumn(
                "Freshness (%)",
                min_value=0.0,
                max_value=100.0,
                format="%.1f%%",
            ),
        },
    )

    left_column, right_column = st.columns((3, 2))

    with left_column:
        render_section_header(
            "Quality Trend",
            description=("Platform-wide data-quality score over time."),
        )

        quality_trend = apply_dataframe_filters(_quality_trend_data(), filters)

        trend_figure = px.line(
            quality_trend,
            x="Date",
            y="Quality Score (%)",
            markers=True,
        )

        trend_figure.update_layout(
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20,
            ),
            yaxis_range=[
                90,
                100,
            ],
        )

        render_plotly_chart(
            trend_figure,
            data=quality_trend,
            time_series=True,
        )

    with right_column:
        render_section_header(
            "Failed Checks by Dataset",
            description=("Current validation failures requiring attention."),
        )

        failures = quality_summary[
            [
                "Dataset",
                "Failed Checks",
            ]
        ].sort_values(
            "Failed Checks",
            ascending=True,
        )

        failure_figure = px.bar(
            failures,
            x="Failed Checks",
            y="Dataset",
            orientation="h",
        )

        failure_figure.update_layout(
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20,
            )
        )

        render_plotly_chart(
            failure_figure,
            data=failures,
        )

    render_section_header(
        "Failed Validation Checks",
        description=("Current data-quality exceptions requiring investigation."),
    )

    failed_checks = _failed_checks_data()
    render_dataframe(failed_checks)
    render_csv_download(
        quality_summary,
        label="Download quality summary CSV",
        report_name="data-quality-summary",
        filters=filters,
        key="quality_summary_download",
    )
    render_csv_download(
        failed_checks,
        label="Download validation failures CSV",
        report_name="validation-failures",
        filters=filters,
        key="quality_failures_download",
    )

    render_section_header(
        "ETL Pipeline Health",
        description=("Latest execution status for major data pipelines."),
    )

    render_dataframe(_pipeline_health_data())
