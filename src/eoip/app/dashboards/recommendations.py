"""Recommendation Center for the EOIP Streamlit application."""

from __future__ import annotations

import pandas as pd
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
    render_section_header,
)
from eoip.app.data_filters import (
    FilterDimensions,
    PageDataContract,
    equipment_options_for_plant,
)
from eoip.app.navigation import navigate_to


def build_recommendation_priority(recommendations: pd.DataFrame) -> pd.DataFrame:
    """Order recommendations by the existing source priority rank."""
    if recommendations.empty:
        return recommendations.copy()
    return recommendations.sort_values(["Priority Rank", "Equipment ID"], kind="stable")


def aggregate_recommendation_impact(
    recommendations: pd.DataFrame,
) -> tuple[float, float | None]:
    """Aggregate supported energy and financial impact without combining units."""
    if recommendations.empty:
        return 0.0, None
    financial = pd.to_numeric(
        recommendations.get("Financial Impact"), errors="coerce"
    ).dropna()
    return float(recommendations["Recoverable Energy (kWh)"].sum()), (
        float(financial.sum()) if not financial.empty else None
    )


def render() -> None:
    """Render the EOIP Recommendation Center."""
    render_page_intro(
        title="Decision & Action Center",
        icon="recommendations",
        description=(
            "Prioritized actions with explicit governance, provenance, and "
            "financial availability semantics."
        ),
    )
    raw_recommendations = data_access.get_recommendations()
    current_scope = get_filter_selection()
    filters = render_global_filters(
        show_date=False,
        show_equipment=True,
        equipment_options=equipment_options_for_plant(
            raw_recommendations, current_scope.plant
        ),
    )
    contract = PageDataContract(
        filters,
        {"recommendations": raw_recommendations},
    )
    recommendations = contract.scoped(
        "recommendations", dimensions=FilterDimensions(date=False)
    )
    if recommendations.empty:
        render_empty_state(
            title="No recommendations",
            message="No recommendations match the selected asset scope.",
        )
        return

    recommendations = build_recommendation_priority(recommendations)
    recoverable_energy, financial_impact = aggregate_recommendation_impact(
        recommendations
    )

    render_section_header(
        "Opportunity Summary",
        description=("Highest-value opportunities identified across the portfolio."),
    )

    render_metric_row(
        (
            MetricCard(
                label="Active Recommendations",
                value=len(recommendations),
            ),
            MetricCard(
                label="Recoverable Energy",
                value=f"{recoverable_energy / 1000:.1f} MWh",
            ),
            MetricCard(
                label="Financial conversion",
                value=("Available" if financial_impact is not None else "Unavailable"),
                subtitle=(
                    None
                    if financial_impact is not None
                    else "No approved price, currency, cost, or horizon assumptions"
                ),
            ),
            MetricCard(
                label="Top Priority",
                value=f"Rank {int(recommendations['Priority Rank'].min())}",
            ),
        )
    )

    render_section_header(
        "Priority Actions",
        description=("Recommended actions ranked by the existing source priority."),
    )

    render_dataframe(
        recommendations,
        column_config={
            "Risk Score": st.column_config.ProgressColumn(
                "Risk Score",
                min_value=0.0,
                max_value=1.0,
                format="%.2f",
            ),
        },
    )
    render_csv_download(
        recommendations,
        label="Download recommendations CSV",
        report_name="optimization-recommendations",
        filters=filters,
        key="recommendations_download",
    )

    if not recommendations.empty:
        selected_equipment = st.selectbox(
            "Recommendation drill-down",
            options=recommendations["Equipment ID"].tolist(),
            key="recommendations_drilldown_equipment",
        )
        recommendation = recommendations.loc[
            recommendations["Equipment ID"].eq(selected_equipment)
        ].iloc[0]
        render_section_header(
            "Recommendation Detail",
            description=(
                "Governance, provenance, evidence, and availability fields for "
                "the selected recommendation."
            ),
        )
        render_dataframe(pd.DataFrame([recommendation]))
        with st.container(horizontal=True):
            if st.button("Inspect asset", key="recommendations_open_asset"):
                navigate_to(
                    "assets",
                    plant=str(recommendation["Plant"]),
                    equipment_id=str(recommendation["Equipment ID"]),
                )
            if st.button("Review maintenance", key="recommendations_open_maintenance"):
                navigate_to(
                    "maintenance",
                    plant=str(recommendation["Plant"]),
                    equipment_id=str(recommendation["Equipment ID"]),
                )
            if st.button("Review plant performance", key="recommendations_open_plant"):
                navigate_to("plant_performance", plant=str(recommendation["Plant"]))
            if st.button("Review operations", key="recommendations_open_operations"):
                navigate_to("operations", plant=str(recommendation["Plant"]))

    render_section_header(
        "Financial traceability",
        description=(
            "Monetary conversion is withheld until approved, versioned business "
            "assumptions establish price, currency, cost, and analysis horizon."
        ),
    )
    render_empty_state(
        title="Revenue at Risk unavailable",
        message=(
            "No approved energy-price assumption, currency, or future "
            "energy-at-risk horizon is configured."
        ),
    )
