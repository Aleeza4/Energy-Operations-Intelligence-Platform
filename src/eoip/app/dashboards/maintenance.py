"""Maintenance dashboard for the EOIP Streamlit application."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from eoip.app import data_access
from eoip.app.components import (
    MetricCard,
    get_filter_selection,
    render_csv_download,
    render_dataframe,
    render_empty_state,
    render_global_filters,
    render_metric_row,
    render_page_intro,
    render_plotly_chart,
    render_section_header,
)
from eoip.app.data_filters import (
    FilterDimensions,
    PageDataContract,
    equipment_options_for_plant,
)
from eoip.app.navigation import navigate_to
from eoip.app.theme import EOIP_DANGER, EOIP_DANGER_STRONG, EOIP_PRIMARY, RISK_COLORS


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


def build_maintenance_priority(priority: pd.DataFrame) -> pd.DataFrame:
    """Order maintenance attention by the existing priority rank."""
    if priority.empty:
        return priority.copy()
    return priority.sort_values(["Priority Rank", "Equipment ID"], kind="stable")


def related_maintenance_evidence(
    item: pd.Series,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return exact plant-and-equipment operational evidence."""
    plant = str(item["Plant"])
    equipment = str(item["Equipment ID"])
    incidents = data_access.get_incidents()
    anomalies = data_access.get_anomalies()
    recommendations = data_access.get_recommendations()
    return (
        incidents.loc[
            incidents["Plant"].eq(plant) & incidents["Equipment"].eq(equipment)
        ].copy(),
        anomalies.loc[
            anomalies["Plant"].eq(plant) & anomalies["Equipment"].eq(equipment)
        ].copy(),
        recommendations.loc[
            recommendations["Plant"].eq(plant)
            & recommendations["Equipment ID"].eq(equipment)
        ].copy(),
    )


def render() -> None:
    """Render the EOIP Maintenance Dashboard."""
    render_page_intro(
        title="Maintenance Priority Workspace",
        icon="maintenance",
        description=(
            "Predictive failure risk, equipment health, explainability, "
            "and maintenance-priority intelligence."
        ),
    )
    raw_priority = data_access.get_maintenance_priorities()
    current_scope = get_filter_selection()
    filters = render_global_filters(
        show_date=False,
        show_equipment=True,
        equipment_options=equipment_options_for_plant(
            raw_priority, current_scope.plant
        ),
    )
    contract = PageDataContract(
        filters,
        {
            "priority": raw_priority,
            "risk_trend": _risk_trend_data(),
            "shap": _shap_importance_data(),
        },
    )
    priority = contract.scoped("priority", dimensions=FilterDimensions(date=False))
    if priority.empty:
        render_empty_state(
            title="No maintenance data",
            message="No maintenance records match the selected asset scope.",
        )
        return

    priority = build_maintenance_priority(priority)
    high_risk = int(priority["Risk Level"].isin(("High", "Critical")).sum())
    critical = int(priority["Risk Level"].eq("Critical").sum())
    average_health = float(priority["Health Score"].mean())

    render_section_header(
        "Maintenance Attention Summary",
        description=("Current equipment health and future-failure risk indicators."),
    )

    render_metric_row(
        (
            MetricCard(
                label="Assets Monitored",
                value=len(priority),
            ),
            MetricCard(
                label="High-Risk Assets",
                value=high_risk,
            ),
            MetricCard(
                label="Critical Assets",
                value=critical,
            ),
            MetricCard(
                label="Avg Health Score",
                value=f"{average_health:.1f}",
            ),
        )
    )

    left_column, right_column = st.columns((3, 2))

    with left_column:
        render_section_header(
            "Maintenance Priority",
            description=(
                "Assets ranked by failure risk, health, and operational urgency."
            ),
        )

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

        health_distribution = (
            priority["Risk Level"]
            .value_counts()
            .rename_axis("Risk Level")
            .reset_index(name="Assets")
        )

        risk_figure = px.bar(
            health_distribution,
            x="Assets",
            y="Risk Level",
            orientation="h",
            color="Risk Level",
            color_discrete_map=RISK_COLORS,
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

        risk_trend = contract.scoped(
            "risk_trend",
            dimensions=FilterDimensions(plant=False, equipment=False, date=False),
        )

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
            color_discrete_map={
                "High Risk Assets": EOIP_DANGER,
                "Critical Assets": EOIP_DANGER_STRONG,
            },
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

        if filters.plant == "All Plants" and filters.equipment_id is None:
            render_plotly_chart(trend_figure, data=risk_long, time_series=True)
        else:
            render_empty_state(
                title="Portfolio-only predictive risk trend",
                message="Choose All Plants and All Equipment to view this source.",
            )

    with right_column:
        render_section_header(
            "Model Diagnostics",
            description=(
                "Portfolio model features; this diagnostic is not asset-scoped."
            ),
        )

        shap_importance = contract.scoped(
            "shap",
            dimensions=FilterDimensions(plant=False, equipment=False, date=False),
        ).sort_values(
            "Mean Absolute SHAP",
            ascending=True,
        )

        shap_figure = px.bar(
            shap_importance,
            x="Mean Absolute SHAP",
            y="Feature",
            orientation="h",
            color_discrete_sequence=[EOIP_PRIMARY],
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
    selected_equipment = st.selectbox(
        "Equipment to review",
        options=priority["Equipment ID"].tolist(),
        key="maintenance_selected_equipment",
    )
    selected = priority.loc[priority["Equipment ID"].eq(selected_equipment)].iloc[0]
    incidents, anomalies, recommendations = related_maintenance_evidence(selected)
    render_section_header(
        "Related Operational Evidence",
        description="Exact plant-and-equipment matches; no causal lineage is implied.",
    )
    render_metric_row(
        (
            MetricCard(label="Related Incidents", value=len(incidents)),
            MetricCard(label="Related Anomalies", value=len(anomalies)),
            MetricCard(label="Relevant Recommendations", value=len(recommendations)),
        )
    )
    render_section_header(
        "Engineering Actions",
        description="Continue investigation with supported equipment context.",
    )
    with st.container(horizontal=True):
        if st.button("Inspect asset", key="maintenance_open_asset"):
            navigate_to(
                "assets",
                plant=str(selected["Plant"]),
                equipment_id=str(selected["Equipment ID"]),
            )
        if st.button("Review anomalies", key="maintenance_open_anomaly"):
            navigate_to(
                "anomaly",
                plant=str(selected["Plant"]),
                equipment_id=str(selected["Equipment ID"]),
            )
        if st.button("Review operations", key="maintenance_open_operations"):
            navigate_to("operations", plant=str(selected["Plant"]))
        if st.button("Review plant performance", key="maintenance_open_plant"):
            navigate_to("plant_performance", plant=str(selected["Plant"]))
    render_csv_download(
        priority,
        label="Download maintenance priority CSV",
        report_name="maintenance-priority",
        filters=filters,
        key="maintenance_download",
    )
