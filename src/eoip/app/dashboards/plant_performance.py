"""Plant performance dashboard for the EOIP Streamlit application."""

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
def _daily_performance_data() -> pd.DataFrame:
    """Return temporary daily plant-performance data."""
    return pd.DataFrame(
        {
            "Date": pd.date_range(
                start="2026-08-13",
                periods=8,
                freq="D",
            ),
            "Actual Energy (MWh)": [
                515.0,
                532.0,
                548.0,
                521.0,
                559.0,
                571.0,
                560.0,
                578.0,
            ],
            "Expected Energy (MWh)": [
                530.0,
                545.0,
                560.0,
                550.0,
                575.0,
                580.0,
                585.0,
                590.0,
            ],
            "Performance Ratio (%)": [
                79.8,
                80.9,
                82.1,
                78.7,
                81.5,
                83.2,
                80.6,
                82.7,
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _plant_comparison_data() -> pd.DataFrame:
    """Return temporary plant comparison data."""
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
            "Capacity Factor (%)": [
                24.8,
                22.9,
                25.6,
                21.7,
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
def _loss_breakdown_data() -> pd.DataFrame:
    """Return temporary plant energy-loss breakdown."""
    return pd.DataFrame(
        {
            "Loss Type": [
                "Curtailment",
                "Soiling",
                "Clipping",
                "Equipment Downtime",
                "Grid Unavailability",
            ],
            "Energy Loss (MWh)": [
                128.0,
                94.0,
                62.0,
                143.0,
                87.0,
            ],
        }
    )


def render() -> None:
    """Render the EOIP Plant Performance Dashboard."""
    render_page_intro(
        title="Plant Performance",
        icon="☀️",
        description=(
            "Energy production, performance ratio, availability, "
            "capacity factor, and loss intelligence."
        ),
    )
    filters = render_global_filters()
    st.caption(format_filter_caption(filters, show_equipment=False))

    render_status(
        "Plant performance analytics are operational.",
        level="success",
    )

    render_section_header(
        "Performance Overview",
        description=("Current production and technical-performance indicators."),
    )

    render_metric_row(
        (
            MetricCard(
                label="Actual Energy",
                value="15.36 GWh",
                delta="+2.8%",
            ),
            MetricCard(
                label="Expected Energy",
                value="15.85 GWh",
                delta="+1.9%",
            ),
            MetricCard(
                label="Performance Ratio",
                value="81.6%",
                delta="+1.2%",
            ),
            MetricCard(
                label="Capacity Factor",
                value="23.8%",
                delta="+0.7%",
            ),
        )
    )

    st.write("")

    daily = apply_dataframe_filters(_daily_performance_data(), filters)

    render_section_header(
        "Daily Energy Performance",
        description=("Actual and expected energy generation over time."),
    )

    energy_long = daily.melt(
        id_vars="Date",
        value_vars=[
            "Actual Energy (MWh)",
            "Expected Energy (MWh)",
        ],
        var_name="Energy Type",
        value_name="Energy (MWh)",
    )

    energy_figure = px.line(
        energy_long,
        x="Date",
        y="Energy (MWh)",
        color="Energy Type",
        markers=True,
    )

    energy_figure.update_layout(
        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20,
        ),
        legend_title_text="",
    )

    render_plotly_chart(
        energy_figure,
        data=energy_long,
        time_series=True,
    )

    left_column, right_column = st.columns((3, 2))

    with left_column:
        render_section_header(
            "Performance Ratio Trend",
            description=("Daily plant performance ratio."),
        )

        pr_figure = px.line(
            daily,
            x="Date",
            y="Performance Ratio (%)",
            markers=True,
        )

        pr_figure.update_layout(
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
            pr_figure,
            data=daily,
            time_series=True,
        )

    with right_column:
        render_section_header(
            "Energy Loss Breakdown",
            description=("Primary contributors to lost energy."),
        )

        losses = _loss_breakdown_data()

        loss_figure = px.pie(
            losses,
            names="Loss Type",
            values="Energy Loss (MWh)",
            hole=0.5,
        )

        loss_figure.update_layout(
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20,
            ),
            legend_title_text="",
        )

        render_plotly_chart(
            loss_figure,
            data=losses,
        )

    render_section_header(
        "Plant Comparison",
        description=("Comparison of production and technical performance by plant."),
    )

    comparison = apply_dataframe_filters(_plant_comparison_data(), filters)

    render_dataframe(
        comparison,
        column_config={
            "Performance Ratio (%)": st.column_config.ProgressColumn(
                "Performance Ratio (%)",
                min_value=0.0,
                max_value=100.0,
                format="%.1f%%",
            ),
            "Capacity Factor (%)": st.column_config.ProgressColumn(
                "Capacity Factor (%)",
                min_value=0.0,
                max_value=100.0,
                format="%.1f%%",
            ),
            "Availability (%)": st.column_config.ProgressColumn(
                "Availability (%)",
                min_value=0.0,
                max_value=100.0,
                format="%.1f%%",
            ),
        },
    )
    render_csv_download(
        comparison,
        label="Download plant comparison CSV",
        report_name="plant-comparison",
        filters=filters,
        key="plant_comparison_download",
    )
    render_csv_download(
        losses,
        label="Download energy losses CSV",
        report_name="plant-energy-losses",
        filters=filters,
        key="plant_losses_download",
    )
