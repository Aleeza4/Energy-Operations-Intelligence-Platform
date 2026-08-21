"""Asset dashboard for the EOIP Streamlit application."""

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
def _asset_health_data() -> pd.DataFrame:
    """Return temporary asset-health data."""
    return pd.DataFrame(
        {
            "Equipment ID": [
                "INV-001",
                "INV-002",
                "INV-003",
                "INV-004",
                "INV-005",
                "INV-006",
            ],
            "Plant": [
                "Solar Plant A",
                "Solar Plant A",
                "Solar Plant B",
                "Solar Plant C",
                "Solar Plant D",
                "Solar Plant D",
            ],
            "Equipment Type": [
                "Inverter",
                "Inverter",
                "Inverter",
                "Transformer",
                "Inverter",
                "Transformer",
            ],
            "Health Score": [
                94.0,
                82.0,
                68.0,
                88.0,
                42.0,
                55.0,
            ],
            "Failure Probability": [
                0.08,
                0.18,
                0.36,
                0.12,
                0.78,
                0.58,
            ],
            "Risk Level": [
                "Low",
                "Low",
                "Moderate",
                "Low",
                "Critical",
                "High",
            ],
            "Priority Rank": [
                6,
                5,
                3,
                4,
                1,
                2,
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _health_distribution_data() -> pd.DataFrame:
    """Return temporary health-distribution data."""
    return pd.DataFrame(
        {
            "Health Band": [
                "Healthy",
                "Watch",
                "Degraded",
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


def render() -> None:
    """Render the EOIP Asset Dashboard."""
    render_page_intro(
        title="Asset Dashboard",
        icon="🔧",
        description=(
            "Equipment health, failure probability, risk classification, "
            "and maintenance-priority intelligence."
        ),
    )
    filters = render_global_filters(
        show_equipment=True,
    )
    st.caption(format_filter_caption(filters))

    render_status(
        "Asset intelligence is operational.",
        level="success",
    )

    render_section_header(
        "Asset Overview",
        description=("Current condition and predictive-maintenance indicators."),
    )

    render_metric_row(
        (
            MetricCard(
                label="Tracked Assets",
                value="97",
                delta="+4",
            ),
            MetricCard(
                label="Average Health Score",
                value="84.2",
                delta="-1.4",
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
        )
    )

    st.write("")

    assets = apply_dataframe_filters(_asset_health_data(), filters)

    left_column, right_column = st.columns((3, 2))

    with left_column:
        render_section_header(
            "Asset Health and Risk",
            description=("Equipment-level predictive-maintenance status."),
        )

        render_dataframe(
            assets,
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
            },
        )

    with right_column:
        render_section_header(
            "Health Distribution",
            description=("Portfolio equipment-health classification."),
        )

        distribution = _health_distribution_data()

        figure = px.pie(
            distribution,
            names="Health Band",
            values="Assets",
            hole=0.55,
        )

        figure.update_layout(
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20,
            ),
            legend_title_text="",
        )

        render_plotly_chart(
            figure,
            data=distribution,
        )

    render_section_header(
        "Failure Risk vs Health",
        description=(
            "Relationship between equipment health and predicted failure risk."
        ),
    )

    scatter = px.scatter(
        assets,
        x="Health Score",
        y="Failure Probability",
        color="Risk Level",
        size="Priority Rank",
        hover_name="Equipment ID",
        hover_data=[
            "Plant",
            "Equipment Type",
        ],
    )

    scatter.update_layout(
        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20,
        )
    )

    render_plotly_chart(
        scatter,
        data=assets,
    )

    render_section_header(
        "Maintenance Priority",
        description=("Assets ordered by predictive-maintenance priority."),
    )

    priority = assets.sort_values(by="Priority Rank")

    render_dataframe(
        priority[
            [
                "Priority Rank",
                "Equipment ID",
                "Plant",
                "Equipment Type",
                "Health Score",
                "Failure Probability",
                "Risk Level",
            ]
        ],
    )
    render_csv_download(
        assets,
        label="Download asset health CSV",
        report_name="asset-health",
        filters=filters,
        key="asset_health_download",
    )

    if not assets.empty:
        selected_equipment = st.selectbox(
            "Asset drill-down",
            options=assets["Equipment ID"].tolist(),
            key="assets_drilldown_equipment",
        )
        asset = assets.loc[assets["Equipment ID"].eq(selected_equipment)].iloc[0]
        if st.button("Open maintenance view", key="assets_open_maintenance"):
            navigate_to(
                "maintenance",
                plant=str(asset["Plant"]),
                equipment_id=str(asset["Equipment ID"]),
            )
