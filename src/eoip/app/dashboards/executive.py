"""Executive portfolio command dashboard for EOIP."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import plotly.express as px
import streamlit as st

from eoip.app import data_access
from eoip.app.components import (
    MetricCard,
    PageContext,
    eoip_actual_expected_colors,
    render_dataframe,
    render_empty_state,
    render_metric_row,
    render_page_context,
    render_page_intro,
    render_plotly_chart,
    render_section_header,
)
from eoip.app.navigation import navigate_to


def _risk_data() -> pd.DataFrame:
    """Return temporary operational-risk data for the UI."""
    return pd.DataFrame(
        {
            "Category": ["Healthy", "Watch", "High Risk", "Critical"],
            "Assets": [68, 17, 9, 3],
        }
    )


def _recommendation_data() -> pd.DataFrame:
    """Return governed recommendation summaries without invented money."""
    source = data_access.get_recommendations().copy()
    priority = {1: "Critical", 2: "High", 3: "High", 4: "Medium", 5: "Low"}
    source["Priority"] = source["Priority Rank"].map(priority)
    source["Recommendation"] = source["Recommendation Type"].str.replace(
        "_", " ", regex=False
    )
    return source[
        [
            "Recommendation ID",
            "Priority",
            "Plant",
            "Recommendation",
            "Governance Status",
            "Owner",
        ]
    ]


@dataclass(frozen=True, slots=True)
class ExecutivePortfolioSummary:
    """Decision-level portfolio measures derived from Executive sources."""

    actual_energy_mwh: float | None
    expected_energy_mwh: float | None
    generation_variance_percent: float | None
    performance_ratio_percent: float | None
    critical_assets: int | None
    recoverable_opportunity: float | None


def derive_portfolio_summary(
    performance: pd.DataFrame,
    risk: pd.DataFrame,
    recommendations: pd.DataFrame,
) -> ExecutivePortfolioSummary:
    """Derive Executive KPIs without fallback values or source mutation."""
    actual = expected = variance = performance_ratio = None
    if not performance.empty:
        actual = float(performance["Actual Energy (MWh)"].sum())
        expected = float(performance["Expected Energy (MWh)"].sum())
        if expected != 0:
            variance = ((actual - expected) / expected) * 100
        performance_ratio = float(performance["Performance Ratio (%)"].mean())

    critical_assets = None
    if not risk.empty:
        critical_assets = int(risk.loc[risk["Category"].eq("Critical"), "Assets"].sum())

    recoverable_opportunity = None
    # No approved price/currency/cost assumptions support monetary aggregation.
    _ = recommendations

    return ExecutivePortfolioSummary(
        actual_energy_mwh=actual,
        expected_energy_mwh=expected,
        generation_variance_percent=variance,
        performance_ratio_percent=performance_ratio,
        critical_assets=critical_assets,
        recoverable_opportunity=recoverable_opportunity,
    )


def build_plant_comparison(performance: pd.DataFrame) -> pd.DataFrame:
    """Return a concise plant ranking with explicit plan status."""
    columns = (
        "Plant",
        "Actual Energy (MWh)",
        "Expected Energy (MWh)",
        "Variance (MWh)",
        "Variance (%)",
        "Performance Ratio (%)",
        "Status",
    )
    if performance.empty:
        return pd.DataFrame(columns=columns)

    comparison = performance.copy()
    comparison["Variance (MWh)"] = (
        comparison["Actual Energy (MWh)"] - comparison["Expected Energy (MWh)"]
    )
    comparison["Variance (%)"] = (
        comparison["Variance (MWh)"] / comparison["Expected Energy (MWh)"] * 100
    )
    comparison["Status"] = comparison["Variance (MWh)"].map(
        lambda value: "On plan" if value >= 0 else "Below plan"
    )
    return comparison.loc[:, columns].sort_values(
        "Variance (%)", ascending=True, ignore_index=True
    )


def build_attention_queue(performance: pd.DataFrame) -> pd.DataFrame:
    """Rank below-plan exceptions without inventing a composite risk score."""
    comparison = build_plant_comparison(performance)
    if comparison.empty:
        return pd.DataFrame(columns=("Plant", "Issue", "Impact", "Status"))

    exceptions = comparison.loc[comparison["Variance (MWh)"].lt(0)].copy()
    exceptions["Issue"] = "Generation below expected"
    exceptions["Impact"] = exceptions["Variance (MWh)"].map(
        lambda value: f"{abs(value):,.0f} MWh shortfall"
    )
    return exceptions.loc[:, ("Plant", "Issue", "Impact", "Status")].head(4)


def build_management_priorities(recommendations: pd.DataFrame) -> pd.DataFrame:
    """Rank existing outputs by declared priority without invented impact."""
    if recommendations.empty:
        return recommendations.copy()

    priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    priorities = recommendations.assign(
        _priority_order=recommendations["Priority"].map(priority_order).fillna(4)
    )
    return (
        priorities.sort_values(["_priority_order", "Recommendation ID"])
        .drop(columns="_priority_order")
        .head(4)
        .reset_index(drop=True)
    )


def _render_portfolio_status(summary: ExecutivePortfolioSummary) -> None:
    metrics: list[MetricCard] = []
    if summary.actual_energy_mwh is not None:
        metrics.append(
            MetricCard(
                label="Portfolio Generation",
                value=f"{summary.actual_energy_mwh / 1000:.2f} GWh",
                subtitle="Current reporting dataset",
            )
        )
    if summary.generation_variance_percent is not None:
        variance = summary.generation_variance_percent
        energy_variance = (summary.actual_energy_mwh or 0) - (
            summary.expected_energy_mwh or 0
        )
        metrics.append(
            MetricCard(
                label="Generation vs Expected",
                value=f"{energy_variance:+,.0f} MWh",
                delta=f"{variance:+.1f}%",
                delta_semantic="positive" if variance >= 0 else "negative",
                delta_context="above plan" if variance >= 0 else "below plan",
            )
        )
    if summary.performance_ratio_percent is not None:
        metrics.append(
            MetricCard(
                label="Portfolio PR",
                value=f"{summary.performance_ratio_percent:.1f}%",
                subtitle="Average across reporting plants",
            )
        )
    if summary.critical_assets is not None:
        metrics.append(
            MetricCard(
                label="Critical Assets",
                value=summary.critical_assets,
                subtitle="Current health classification",
            )
        )
    if metrics:
        render_metric_row(metrics)
    else:
        render_empty_state(
            title="Portfolio status unavailable",
            message="No Executive source data is available for portfolio KPIs.",
        )


def render() -> None:
    """Render the EOIP Executive Portfolio Command Dashboard."""
    render_page_intro(
        title="Executive Dashboard",
        icon="executive",
        description=(
            "Portfolio production, operational exceptions, business impact, "
            "and management priorities."
        ),
    )
    render_page_context(PageContext(scope="Portfolio"))

    performance = data_access.get_plant_performance()
    risk = _risk_data()
    recommendations = _recommendation_data()
    summary = derive_portfolio_summary(performance, risk, recommendations)

    render_section_header(
        "Portfolio Status",
        description="Current production, plan delivery, asset risk, and opportunity.",
    )
    _render_portfolio_status(summary)

    render_section_header(
        "Performance vs Plan",
        description="Actual and expected generation by plant, ordered for comparison.",
    )
    comparison = build_plant_comparison(performance)
    if comparison.empty:
        render_empty_state(
            title="Performance data unavailable",
            message="Actual and expected generation data could not be loaded.",
        )
    else:
        performance_long = comparison.melt(
            id_vars="Plant",
            value_vars=("Actual Energy (MWh)", "Expected Energy (MWh)"),
            var_name="Energy Type",
            value_name="Energy (MWh)",
        )
        figure = px.bar(
            performance_long,
            x="Plant",
            y="Energy (MWh)",
            color="Energy Type",
            color_discrete_map=eoip_actual_expected_colors(
                "Actual Energy (MWh)", "Expected Energy (MWh)"
            ),
            barmode="group",
        )
        figure.update_layout(
            xaxis_title="Plant",
            yaxis_title="Generation (MWh)",
            legend_title_text="",
        )
        render_plotly_chart(figure, data=performance_long)

    render_section_header(
        "Attention Required",
        description="Plants with an explicit generation shortfall against plan.",
    )
    render_dataframe(
        build_attention_queue(performance),
        empty_title="No production exceptions",
        empty_message="No plants are currently below expected generation.",
    )

    render_section_header(
        "Financial & Business Impact",
        description="Financial conversion requires approved business assumptions.",
    )
    render_empty_state(
        title="Financial impact unavailable",
        message=(
            "No approved price, currency, intervention-cost, or analysis-horizon "
            "assumptions support a monetary claim."
        ),
    )

    render_section_header(
        "Plant Portfolio Comparison",
        description="Plants ranked from greatest shortfall to strongest delivery.",
    )
    render_dataframe(
        comparison,
        empty_title="Plant comparison unavailable",
        empty_message="No plant-level performance data is currently available.",
        column_config={
            "Actual Energy (MWh)": st.column_config.NumberColumn(format="%.0f MWh"),
            "Expected Energy (MWh)": st.column_config.NumberColumn(format="%.0f MWh"),
            "Variance (MWh)": st.column_config.NumberColumn(format="%+.0f MWh"),
            "Variance (%)": st.column_config.NumberColumn(format="%+.1f%%"),
            "Performance Ratio (%)": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )

    render_section_header(
        "Management Priorities",
        description="Highest-priority actions already identified by EOIP outputs.",
    )
    priorities = build_management_priorities(recommendations)
    render_dataframe(
        priorities,
        empty_title="No management priorities",
        empty_message="No prioritized recommendations are currently available.",
    )

    if not priorities.empty:
        selected_plant = st.selectbox(
            "Priority plant",
            options=priorities["Plant"].drop_duplicates().tolist(),
            key="executive_priority_plant",
        )
        action_columns = st.columns(3)
        with action_columns[0]:
            if st.button(
                "Open plant performance",
                key="executive_open_performance",
                width="stretch",
            ):
                navigate_to("plant_performance", plant=selected_plant)
        with action_columns[1]:
            if st.button(
                "Review operations",
                key="executive_open_operations",
                width="stretch",
            ):
                navigate_to("operations", plant=selected_plant)
        with action_columns[2]:
            if st.button(
                "Review recommendations",
                key="executive_open_recommendations",
                width="stretch",
            ):
                navigate_to("recommendations", plant=selected_plant)
