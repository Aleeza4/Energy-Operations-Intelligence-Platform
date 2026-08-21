"""Executive dashboard for the EOIP Streamlit application."""

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
def _portfolio_performance_data() -> pd.DataFrame:
    """Return temporary portfolio-performance data for the UI."""
    return pd.DataFrame(
        {
            "Plant": [
                "Solar Plant A",
                "Solar Plant B",
                "Solar Plant C",
                "Solar Plant D",
            ],
            "Actual Energy (MWh)": [
                4120.0,
                3650.0,
                4380.0,
                3210.0,
            ],
            "Expected Energy (MWh)": [
                4250.0,
                3800.0,
                4400.0,
                3400.0,
            ],
            "Performance Ratio (%)": [
                82.4,
                80.8,
                84.1,
                78.9,
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _risk_data() -> pd.DataFrame:
    """Return temporary operational-risk data for the UI."""
    return pd.DataFrame(
        {
            "Category": [
                "Healthy",
                "Watch",
                "High Risk",
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
def _recommendation_data() -> pd.DataFrame:
    """Return temporary executive recommendation data."""
    return pd.DataFrame(
        {
            "Priority": [
                "Critical",
                "High",
                "High",
                "Medium",
            ],
            "Plant": [
                "Solar Plant D",
                "Solar Plant B",
                "Solar Plant A",
                "Solar Plant C",
            ],
            "Recommendation": [
                "Investigate inverter degradation",
                "Schedule preventive maintenance",
                "Recover identified energy losses",
                "Review recurring anomaly pattern",
            ],
            "Estimated Impact ($)": [
                18500.0,
                12400.0,
                9600.0,
                4200.0,
            ],
        }
    )


def render() -> None:
    """Render the EOIP Executive Dashboard."""
    render_page_intro(
        title="Executive Dashboard",
        icon="📊",
        description=(
            "Portfolio-level operational, financial, and " "asset-health intelligence."
        ),
    )
    filters = render_global_filters()
    st.caption(format_filter_caption(filters, show_equipment=False))

    render_status(
        "Portfolio intelligence is operational.",
        level="success",
    )

    render_section_header(
        "Portfolio Overview",
        description=("High-level indicators across the renewable-energy portfolio."),
    )

    render_metric_row(
        (
            MetricCard(
                label="Actual Energy",
                value="15.36 GWh",
                delta="+2.8%",
                help_text="Total portfolio energy production.",
            ),
            MetricCard(
                label="Performance Ratio",
                value="81.6%",
                delta="+1.2%",
                help_text="Portfolio weighted performance ratio.",
            ),
            MetricCard(
                label="Technical Availability",
                value="97.4%",
                delta="+0.6%",
                help_text="Portfolio technical availability.",
            ),
            MetricCard(
                label="Recoverable Opportunity",
                value="$44.7K",
                delta="+8.3%",
                help_text=("Estimated recoverable financial opportunity."),
            ),
        )
    )

    st.write("")

    performance = apply_dataframe_filters(_portfolio_performance_data(), filters)

    left_column, right_column = st.columns((2, 1))

    with left_column:
        render_section_header(
            "Plant Performance",
            description=("Actual versus expected energy generation."),
        )

        performance_long = performance.melt(
            id_vars="Plant",
            value_vars=[
                "Actual Energy (MWh)",
                "Expected Energy (MWh)",
            ],
            var_name="Energy Type",
            value_name="Energy (MWh)",
        )

        figure = px.bar(
            performance_long,
            x="Plant",
            y="Energy (MWh)",
            color="Energy Type",
            barmode="group",
        )

        figure.update_layout(
            margin=dict(
                l=20,
                r=20,
                t=30,
                b=20,
            ),
            legend_title_text="",
        )

        render_plotly_chart(
            figure,
            data=performance_long,
        )

    with right_column:
        render_section_header(
            "Asset Health",
            description=("Current equipment risk distribution."),
        )

        risk = _risk_data()

        risk_figure = px.pie(
            risk,
            names="Category",
            values="Assets",
            hole=0.58,
        )

        risk_figure.update_layout(
            margin=dict(
                l=20,
                r=20,
                t=30,
                b=20,
            ),
            legend_title_text="",
        )

        render_plotly_chart(
            risk_figure,
            data=risk,
        )

    render_section_header(
        "Performance by Plant",
        description=("Portfolio performance indicators for executive review."),
    )

    render_dataframe(
        performance,
    )
    render_csv_download(
        performance,
        label="Download plant performance CSV",
        report_name="executive-plant-performance",
        filters=filters,
        key="executive_performance_download",
    )

    if not performance.empty:
        with st.container(horizontal=True, vertical_alignment="bottom"):
            selected_plant = st.selectbox(
                "Plant drill-down",
                options=performance["Plant"].tolist(),
                key="executive_drilldown_plant",
            )
            if st.button("View plant", key="executive_view_plant"):
                navigate_to("plant_performance", plant=selected_plant)

    render_section_header(
        "Priority Recommendations",
        description=("Highest-value operational actions identified by EOIP."),
    )

    recommendations = apply_dataframe_filters(_recommendation_data(), filters)

    render_dataframe(
        recommendations,
        column_config={
            "Estimated Impact ($)": st.column_config.NumberColumn(
                "Estimated Impact ($)",
                format="$%.0f",
            )
        },
    )
    render_csv_download(
        recommendations,
        label="Download recommendations CSV",
        report_name="executive-recommendations",
        filters=filters,
        key="executive_recommendations_download",
    )
