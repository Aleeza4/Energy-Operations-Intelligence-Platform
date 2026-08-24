"""Maintenance dashboard for the EOIP Streamlit application."""

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
def _maintenance_priority_data() -> pd.DataFrame:
    """Return temporary predictive-maintenance priority data."""
    return pd.DataFrame(
        {
            "Priority Rank": [
                1,
                2,
                3,
                4,
                5,
            ],
            "Equipment ID": [
                "INV-005",
                "TRF-004",
                "INV-003",
                "INV-006",
                "TRF-002",
            ],
            "Plant": [
                "Solar Plant D",
                "Solar Plant D",
                "Solar Plant B",
                "Solar Plant C",
                "Solar Plant C",
            ],
            "Health Score": [
                42.0,
                55.0,
                68.0,
                72.0,
                78.0,
            ],
            "Failure Probability": [
                0.78,
                0.58,
                0.36,
                0.31,
                0.24,
            ],
            "Risk Level": [
                "Critical",
                "High",
                "High",
                "Moderate",
                "Moderate",
            ],
            "Priority Score": [
                0.86,
                0.72,
                0.61,
                0.53,
                0.45,
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _health_distribution_data() -> pd.DataFrame:
    """Return temporary equipment-health distribution."""
    return pd.DataFrame(
        {
            "Risk Level": [
                "Low",
                "Moderate",
                "High",
                "Critical",
            ],
            "Assets": [
                68,
                17,
                9,
                3,
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _shap_importance_data() -> pd.DataFrame:
    """Return temporary SHAP feature importance."""
    return pd.DataFrame(
        {
            "Feature": [
                "temperature_rolling_mean_24",
                "alarm_count_rolling_mean_12",
                "active_power_delta",
                "anomaly_score",
                "performance_loss",
                "temperature_delta",
            ],
            "Mean Absolute SHAP": [
                0.182,
                0.149,
                0.128,
                0.114,
                0.091,
                0.064,
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _risk_trend_data() -> pd.DataFrame:
    """Return temporary maintenance-risk trend data."""
    return pd.DataFrame(
        {
            "Date": pd.date_range(
                start="2026-08-14",
                periods=8,
                freq="D",
            ),
            "High Risk Assets": [
                8,
                9,
                9,
                10,
                11,
                11,
                12,
                12,
            ],
            "Critical Assets": [
                1,
                1,
                2,
                2,
                2,
                3,
                3,
                3,
            ],
        }
    )


def render() -> None:
    """Render the EOIP Maintenance Dashboard."""
    render_page_intro(
        title="Maintenance Dashboard",
        icon="🛠️",
        description=(
            "Predictive failure risk, equipment health, explainability, "
            "and maintenance-priority intelligence."
        ),
    )
    filters = render_global_filters(show_equipment=True)
    st.caption(format_filter_caption(filters))

    render_status(
        "Predictive-maintenance intelligence is operational.",
        level="success",
    )

    render_section_header(
        "Maintenance Overview",
        description=("Current equipment health and future-failure risk indicators."),
    )

    render_metric_row(
        (
            MetricCard(
                label="Assets Monitored",
                value="97",
                delta="+4",
            ),
            MetricCard(
                label="High-Risk Assets",
                value="12",
                delta="+3",
            ),
            MetricCard(
                label="Critical Assets",
                value="3",
                delta="+1",
            ),
            MetricCard(
                label="Avg Health Score",
                value="84.2",
                delta="-1.4",
            ),
        )
    )

    st.write("")

    left_column, right_column = st.columns((3, 2))

    with left_column:
        render_section_header(
            "Maintenance Priority",
            description=(
                "Assets ranked by failure risk, health, and operational urgency."
            ),
        )

        priority = apply_dataframe_filters(_maintenance_priority_data(), filters)

        render_dataframe(
            priority,
            column_config={
                "Health Score": st.column_config.ProgressColumn(
                    "Health Score",
                    min_value=0.0,
                    max_value=100.0,
                    format="%.0f",
                ),
                "Failure Probability": st.column_config.ProgressColumn(
                    "Failure Probability",
                    min_value=0.0,
                    max_value=1.0,
                    format="%.2f",
                ),
                "Priority Score": st.column_config.ProgressColumn(
                    "Priority Score",
                    min_value=0.0,
                    max_value=1.0,
                    format="%.2f",
                ),
            },
        )

    with right_column:
        render_section_header(
            "Risk Distribution",
            description=("Portfolio distribution of maintenance risk levels."),
        )

        health_distribution = _health_distribution_data()

        risk_figure = px.pie(
            health_distribution,
            names="Risk Level",
            values="Assets",
            hole=0.55,
        )

        risk_figure.update_layout(
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20,
            ),
            legend_title_text="",
        )

        render_plotly_chart(
            risk_figure,
            data=health_distribution,
        )

    left_column, right_column = st.columns((3, 2))

    with left_column:
        render_section_header(
            "Predictive Risk Trend",
            description=("Change in high-risk and critical equipment over time."),
        )

        risk_trend = apply_dataframe_filters(_risk_trend_data(), filters)

        risk_long = risk_trend.melt(
            id_vars="Date",
            value_vars=[
                "High Risk Assets",
                "Critical Assets",
            ],
            var_name="Risk Category",
            value_name="Asset Count",
        )

        trend_figure = px.line(
            risk_long,
            x="Date",
            y="Asset Count",
            color="Risk Category",
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
            data=risk_long,
            time_series=True,
        )

    with right_column:
        render_section_header(
            "Model Explainability",
            description=("Most influential predictive-maintenance features."),
        )

        shap_importance = _shap_importance_data().sort_values(
            "Mean Absolute SHAP",
            ascending=True,
        )

        shap_figure = px.bar(
            shap_importance,
            x="Mean Absolute SHAP",
            y="Feature",
            orientation="h",
        )

        shap_figure.update_layout(
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20,
            )
        )

        render_plotly_chart(
            shap_figure,
            data=shap_importance,
        )

    render_section_header(
        "Immediate Maintenance Actions",
        description=("Highest-priority assets requiring maintenance review."),
    )

    immediate = priority[
        priority["Risk Level"].isin(
            [
                "Critical",
                "High",
            ]
        )
    ]

    render_dataframe(
        immediate[
            [
                "Priority Rank",
                "Equipment ID",
                "Plant",
                "Risk Level",
                "Health Score",
                "Failure Probability",
            ]
        ],
    )
    render_csv_download(
        priority,
        label="Download maintenance priority CSV",
        report_name="maintenance-priority",
        filters=filters,
        key="maintenance_download",
    )
