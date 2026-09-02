"""Plant performance engineering workspace for EOIP."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from eoip.app import data_access
from eoip.app.components import (
    MetricCard,
    eoip_actual_expected_colors,
    render_csv_download,
    render_dataframe,
    render_empty_state,
    render_global_filters,
    render_metric_row,
    render_page_intro,
    render_plotly_chart,
    render_section_header,
)
from eoip.app.data_filters import FilterDimensions, PageDataContract
from eoip.app.navigation import navigate_to
from eoip.app.theme import EOIP_PRIMARY


@st.cache_data(show_spinner=False)
def _daily_performance_data() -> pd.DataFrame:
    """Return portfolio-only daily performance data."""
    return pd.DataFrame(
        {
            "Date": pd.date_range(start="2026-08-13", periods=8, freq="D"),
            "Actual Energy (MWh)": [515, 532, 548, 521, 559, 571, 560, 578],
            "Expected Energy (MWh)": [530, 545, 560, 550, 575, 580, 585, 590],
            "Performance Ratio (%)": [79.8, 80.9, 82.1, 78.7, 81.5, 83.2, 80.6, 82.7],
        }
    )


@st.cache_data(show_spinner=False)
def _loss_breakdown_data() -> pd.DataFrame:
    """Return portfolio-only recorded loss categories."""
    return pd.DataFrame(
        {
            "Loss Type": [
                "Curtailment",
                "Soiling",
                "Clipping",
                "Equipment Downtime",
                "Grid Unavailability",
            ],
            "Energy Loss (MWh)": [128.0, 94.0, 62.0, 143.0, 87.0],
        }
    )


def calculate_generation_variance(
    actual: float, expected: float
) -> tuple[float, float | None]:
    """Return generation variance and safe percentage variance."""
    variance = actual - expected
    variance_pct = None if expected == 0 else variance / expected * 100
    return variance, variance_pct


def build_performance_benchmark(performance: pd.DataFrame) -> pd.DataFrame:
    """Add variance fields and rank plants by variance to expected."""
    columns = (
        "Plant",
        "Actual Energy (MWh)",
        "Expected Energy (MWh)",
        "Variance (MWh)",
        "Variance (%)",
        "Performance Ratio (%)",
        "Availability (%)",
    )
    if performance.empty:
        return pd.DataFrame(columns=columns)
    benchmark = performance.copy(deep=True)
    benchmark["Variance (MWh)"] = (
        benchmark["Actual Energy (MWh)"] - benchmark["Expected Energy (MWh)"]
    )
    benchmark["Variance (%)"] = (
        benchmark["Variance (MWh)"].div(
            benchmark["Expected Energy (MWh)"].replace(0, pd.NA)
        )
        * 100
    )
    return benchmark.loc[:, columns].sort_values("Variance (MWh)")


def _render_investigation_actions(plant: str | None) -> None:
    """Render supported plant-level engineering actions."""
    render_section_header(
        "Engineering Investigation",
        description="Continue into supported operational evidence.",
    )
    with st.container(horizontal=True):
        if st.button("Inspect assets", key="plant_performance_open_assets"):
            navigate_to("assets", plant=plant)
        if st.button("Review operations", key="plant_performance_open_operations"):
            navigate_to("operations", plant=plant)
        if st.button(
            "Review alarms & incidents", key="plant_performance_open_incidents"
        ):
            navigate_to("alarms_incidents", plant=plant)
        if st.button("Review anomalies", key="plant_performance_open_anomalies"):
            navigate_to("anomaly", plant=plant)


def render() -> None:
    """Render the Plant Performance engineering workspace."""
    render_page_intro(
        title="Plant Performance",
        icon="plant_performance",
        description="Plant-level variance, peer comparison, and investigation.",
    )
    filters = render_global_filters(show_date=False)
    raw_comparison = data_access.get_plant_performance()
    selected = PageDataContract(filters, {"comparison": raw_comparison}).scoped(
        "comparison", dimensions=FilterDimensions(date=False)
    )
    portfolio = build_performance_benchmark(raw_comparison)

    section_title = (
        "Selected Plant Performance"
        if filters.plant != "All Plants"
        else "Portfolio Performance"
    )
    render_section_header(
        section_title,
        description="Observed generation and technical indicators in scope.",
    )
    if selected.empty:
        render_empty_state(
            title="No plant performance data",
            message="No performance records match the selected plant scope.",
        )
        _render_investigation_actions(
            None if filters.plant == "All Plants" else filters.plant
        )
        return

    actual = float(selected["Actual Energy (MWh)"].sum())
    expected = float(selected["Expected Energy (MWh)"].sum())
    variance, variance_pct = calculate_generation_variance(actual, expected)
    pr = float(selected["Performance Ratio (%)"].mean())
    availability = float(selected["Availability (%)"].mean())
    variance_context = (
        "Expected generation is zero"
        if variance_pct is None
        else f"{variance_pct:+.1f}% to expected"
    )
    render_metric_row(
        (
            MetricCard(label="Actual Generation", value=f"{actual:,.0f} MWh"),
            MetricCard(label="Expected Generation", value=f"{expected:,.0f} MWh"),
            MetricCard(
                label="Variance to Expected",
                value=f"{variance:+,.0f} MWh",
                subtitle=variance_context,
            ),
            MetricCard(label="Performance Ratio", value=f"{pr:.1f}%"),
            MetricCard(label="Availability", value=f"{availability:.1f}%"),
        )
    )

    render_section_header(
        "Actual vs Expected",
        description="Aggregate comparison; no plant-level time series is available.",
    )
    comparison_chart = pd.DataFrame(
        {
            "Measure": ["Actual Generation", "Expected Generation"],
            "Energy (MWh)": [actual, expected],
        }
    )
    figure = px.bar(
        comparison_chart,
        x="Measure",
        y="Energy (MWh)",
        color="Measure",
        color_discrete_map=eoip_actual_expected_colors(
            "Actual Generation", "Expected Generation"
        ),
    )
    figure.update_layout(showlegend=False, xaxis_title="", yaxis_title="Energy (MWh)")
    render_plotly_chart(figure, data=comparison_chart)

    render_section_header(
        "Performance Trend",
        description="Timestamped coverage is portfolio-wide without plant attribution.",
    )
    if filters.plant == "All Plants":
        daily = _daily_performance_data()
        trend = daily.melt(
            id_vars="Date",
            value_vars=("Actual Energy (MWh)", "Expected Energy (MWh)"),
            var_name="Measure",
            value_name="Energy (MWh)",
        )
        trend_figure = px.line(
            trend,
            x="Date",
            y="Energy (MWh)",
            color="Measure",
            markers=True,
            color_discrete_map=eoip_actual_expected_colors(
                "Actual Energy (MWh)", "Expected Energy (MWh)"
            ),
        )
        trend_figure.update_layout(legend_title_text="", yaxis_title="Energy (MWh)")
        render_plotly_chart(trend_figure, data=trend, time_series=True)
    else:
        render_empty_state(
            title="Plant trend unavailable",
            message=(
                "The timestamped source cannot be attributed to the selected plant."
            ),
        )

    render_section_header(
        "Recorded Loss Context",
        description=(
            "Portfolio categories; records are not attributed to individual plants."
        ),
    )
    losses = _loss_breakdown_data().sort_values("Energy Loss (MWh)")
    if losses.empty:
        render_empty_state(
            title="No recorded loss data",
            message="Portfolio loss-category records are unavailable.",
        )
    else:
        loss_figure = px.bar(
            losses,
            x="Energy Loss (MWh)",
            y="Loss Type",
            orientation="h",
            color_discrete_sequence=[EOIP_PRIMARY],
        )
        loss_figure.update_layout(xaxis_title="Recorded loss (MWh)", yaxis_title="")
        render_plotly_chart(loss_figure, data=losses)

    render_section_header(
        "Portfolio Benchmark",
        description="Plant-attributed peers ranked by variance to expected.",
    )
    render_dataframe(
        portfolio,
        column_config={
            "Actual Energy (MWh)": st.column_config.NumberColumn(format="%.0f MWh"),
            "Expected Energy (MWh)": st.column_config.NumberColumn(format="%.0f MWh"),
            "Variance (MWh)": st.column_config.NumberColumn(format="%+.0f MWh"),
            "Variance (%)": st.column_config.NumberColumn(format="%+.1f%%"),
            "Performance Ratio (%)": st.column_config.NumberColumn(format="%.1f%%"),
            "Availability (%)": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )
    with st.expander("Exports"):
        render_csv_download(
            selected,
            label="Download selected performance CSV",
            report_name="plant-performance",
            filters=filters,
            key="plant_performance_download",
        )
        render_csv_download(
            losses,
            label="Download portfolio recorded losses CSV",
            report_name="portfolio-recorded-losses",
            key="plant_losses_download",
        )
    _render_investigation_actions(
        None if filters.plant == "All Plants" else filters.plant
    )
