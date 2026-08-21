"""Anomaly dashboard for the EOIP Streamlit application."""

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
def _anomaly_trend_data() -> pd.DataFrame:
    """Return temporary anomaly trend data."""
    return pd.DataFrame(
        {
            "Time": pd.date_range(
                start="2026-08-20 00:00",
                periods=16,
                freq="90min",
            ),
            "Anomaly Score": [
                0.10,
                0.12,
                0.15,
                0.11,
                0.18,
                0.22,
                0.65,
                0.31,
                0.27,
                0.74,
                0.44,
                0.29,
                0.82,
                0.38,
                0.24,
                0.19,
            ],
            "Threshold": [0.50] * 16,
        }
    )


@st.cache_data(show_spinner=False)
def _active_anomalies_data() -> pd.DataFrame:
    """Return temporary active-anomaly data."""
    return pd.DataFrame(
        {
            "Anomaly ID": [
                "ANM-2031",
                "ANM-2028",
                "ANM-2026",
                "ANM-2022",
            ],
            "Plant": [
                "Solar Plant D",
                "Solar Plant B",
                "Solar Plant C",
                "Solar Plant D",
            ],
            "Equipment": [
                "INV-005",
                "INV-003",
                "TRF-002",
                "INV-006",
            ],
            "Severity": [
                "Critical",
                "High",
                "High",
                "Medium",
            ],
            "Method": [
                "Isolation Forest",
                "Residual Analysis",
                "Statistical Baseline",
                "Isolation Forest",
            ],
            "Anomaly Score": [
                0.92,
                0.84,
                0.76,
                0.61,
            ],
            "Status": [
                "Investigating",
                "Open",
                "Monitoring",
                "Open",
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _method_performance_data() -> pd.DataFrame:
    """Return temporary anomaly-model evaluation data."""
    return pd.DataFrame(
        {
            "Method": [
                "Statistical Baseline",
                "Isolation Forest",
                "Residual Analysis",
            ],
            "Precision (%)": [
                74.0,
                88.0,
                84.0,
            ],
            "Recall (%)": [
                69.0,
                83.0,
                87.0,
            ],
            "F1 Score (%)": [
                71.4,
                85.4,
                85.5,
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _severity_data() -> pd.DataFrame:
    """Return temporary anomaly-severity distribution."""
    return pd.DataFrame(
        {
            "Severity": [
                "Critical",
                "High",
                "Medium",
                "Low",
            ],
            "Count": [
                2,
                5,
                8,
                14,
            ],
        }
    )


def render() -> None:
    """Render the EOIP Anomaly Dashboard."""
    render_page_intro(
        title="Anomaly Dashboard",
        icon="🔍",
        description=(
            "Abnormal operating behavior, anomaly scores, "
            "detection performance, and investigation intelligence."
        ),
    )
    filters = render_global_filters(show_equipment=True)
    st.caption(format_filter_caption(filters))

    render_status(
        "Anomaly detection is operational.",
        level="success",
    )

    render_section_header(
        "Anomaly Overview",
        description=("Current anomaly volume and detection-quality indicators."),
    )

    render_metric_row(
        (
            MetricCard(
                label="Active Anomalies",
                value="15",
                delta="+3",
            ),
            MetricCard(
                label="Critical Anomalies",
                value="2",
                delta="+1",
            ),
            MetricCard(
                label="Detection Precision",
                value="88.0%",
                delta="+2.1%",
            ),
            MetricCard(
                label="Detection Recall",
                value="87.0%",
                delta="+1.6%",
            ),
        )
    )

    st.write("")

    render_section_header(
        "Anomaly Score Trend",
        description=("Recent anomaly scores against the active detection threshold."),
    )

    trend = apply_dataframe_filters(_anomaly_trend_data(), filters)

    trend_long = trend.melt(
        id_vars="Time",
        value_vars=[
            "Anomaly Score",
            "Threshold",
        ],
        var_name="Series",
        value_name="Score",
    )

    trend_figure = px.line(
        trend_long,
        x="Time",
        y="Score",
        color="Series",
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
            0,
            1,
        ],
        legend_title_text="",
    )

    render_plotly_chart(
        trend_figure,
        data=trend_long,
        time_series=True,
    )

    left_column, right_column = st.columns((3, 2))

    with left_column:
        render_section_header(
            "Detection Performance",
            description=("Precision, recall, and F1 score by anomaly method."),
        )

        performance = _method_performance_data()

        performance_long = performance.melt(
            id_vars="Method",
            value_vars=[
                "Precision (%)",
                "Recall (%)",
                "F1 Score (%)",
            ],
            var_name="Metric",
            value_name="Score (%)",
        )

        performance_figure = px.bar(
            performance_long,
            x="Method",
            y="Score (%)",
            color="Metric",
            barmode="group",
        )

        performance_figure.update_layout(
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
            legend_title_text="",
        )

        render_plotly_chart(
            performance_figure,
            data=performance_long,
        )

    with right_column:
        render_section_header(
            "Severity Distribution",
            description=("Current anomaly distribution by severity."),
        )

        severity = _severity_data()

        severity_figure = px.pie(
            severity,
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
            data=severity,
        )

    render_section_header(
        "Active Anomaly Investigations",
        description=("Current abnormal events requiring operational review."),
    )

    anomalies = apply_dataframe_filters(_active_anomalies_data(), filters)

    render_dataframe(
        anomalies,
        column_config={
            "Anomaly Score": st.column_config.ProgressColumn(
                "Anomaly Score",
                min_value=0.0,
                max_value=1.0,
                format="%.2f",
            )
        },
    )
    render_csv_download(
        anomalies,
        label="Download active anomalies CSV",
        report_name="active-anomalies",
        filters=filters,
        key="anomalies_download",
    )

    if not anomalies.empty:
        selected_id = st.selectbox(
            "Anomaly drill-down",
            options=anomalies["Anomaly ID"].tolist(),
            key="anomaly_drilldown_id",
        )
        anomaly = anomalies.loc[anomalies["Anomaly ID"].eq(selected_id)].iloc[0]
        if st.button("Investigate asset", key="anomaly_investigate_asset"):
            navigate_to(
                "assets",
                plant=str(anomaly["Plant"]),
                equipment_id=str(anomaly["Equipment"]),
            )
