"""Recommendation Center for the EOIP Streamlit application."""

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
def _recommendation_data() -> pd.DataFrame:
    """Return temporary optimization recommendation data."""
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
                "INV-003",
                "TRF-004",
                "INV-006",
                "INV-002",
            ],
            "Plant": [
                "Solar Plant D",
                "Solar Plant B",
                "Solar Plant D",
                "Solar Plant C",
                "Solar Plant A",
            ],
            "Recommendation Type": [
                "maintenance",
                "performance_recovery",
                "maintenance",
                "monitor",
                "performance_recovery",
            ],
            "Risk Score": [
                0.86,
                0.68,
                0.72,
                0.44,
                0.31,
            ],
            "Recoverable Energy (kWh)": [
                4200.0,
                7600.0,
                1800.0,
                900.0,
                2400.0,
            ],
            "Net Financial Impact ($)": [
                18200.0,
                14600.0,
                9800.0,
                2300.0,
                5100.0,
            ],
            "ROI (%)": [
                284.0,
                196.0,
                163.0,
                48.0,
                92.0,
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _scenario_data() -> pd.DataFrame:
    """Return temporary scenario-analysis data."""
    return pd.DataFrame(
        {
            "Scenario": [
                "Baseline",
                "Maintenance Intervention",
                "Performance Recovery",
                "Combined Action",
            ],
            "Energy (MWh)": [
                15280.0,
                15440.0,
                15620.0,
                15780.0,
            ],
            "Operating Cost ($)": [
                68400.0,
                63100.0,
                64800.0,
                59800.0,
            ],
            "Portfolio Risk": [
                0.42,
                0.31,
                0.38,
                0.24,
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _financial_summary_data() -> pd.DataFrame:
    """Return temporary financial-impact summary."""
    return pd.DataFrame(
        {
            "Impact Type": [
                "Recovered Energy Value",
                "Avoided Failure Cost",
                "Operating Cost Saving",
            ],
            "Value ($)": [
                16800.0,
                24100.0,
                9100.0,
            ],
        }
    )


def render() -> None:
    """Render the EOIP Recommendation Center."""
    render_page_intro(
        title="Recommendation Center",
        icon="💡",
        description=(
            "Prioritized optimization actions, recoverable opportunity, "
            "financial impact, ROI, and scenario intelligence."
        ),
    )
    filters = render_global_filters(show_equipment=True)
    st.caption(format_filter_caption(filters))

    render_status(
        "Optimization recommendations are operational.",
        level="success",
    )

    render_section_header(
        "Optimization Overview",
        description=("Highest-value opportunities identified across the portfolio."),
    )

    render_metric_row(
        (
            MetricCard(
                label="Active Recommendations",
                value="18",
                delta="+4",
            ),
            MetricCard(
                label="Recoverable Energy",
                value="16.9 MWh",
                delta="+6.1%",
            ),
            MetricCard(
                label="Net Financial Impact",
                value="$50.0K",
                delta="+9.4%",
            ),
            MetricCard(
                label="Average ROI",
                value="156%",
                delta="+18%",
            ),
        )
    )

    st.write("")

    recommendations = apply_dataframe_filters(_recommendation_data(), filters)

    render_section_header(
        "Prioritized Recommendations",
        description=(
            "Recommended actions ranked by operational and financial priority."
        ),
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
            "Net Financial Impact ($)": st.column_config.NumberColumn(
                "Net Financial Impact ($)",
                format="$%.0f",
            ),
            "ROI (%)": st.column_config.NumberColumn(
                "ROI (%)",
                format="%.0f%%",
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
        target = (
            "maintenance"
            if recommendation["Recommendation Type"] == "maintenance"
            else "assets"
        )
        if st.button("Open recommended action", key="recommendations_open_action"):
            navigate_to(
                target,
                plant=str(recommendation["Plant"]),
                equipment_id=str(recommendation["Equipment ID"]),
            )

    left_column, right_column = st.columns((3, 2))

    with left_column:
        render_section_header(
            "Financial Opportunity by Asset",
            description=("Estimated net value generated by recommended actions."),
        )

        financial_figure = px.bar(
            recommendations,
            x="Equipment ID",
            y="Net Financial Impact ($)",
            color="Recommendation Type",
        )

        financial_figure.update_layout(
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20,
            ),
            legend_title_text="",
        )

        render_plotly_chart(
            financial_figure,
            data=recommendations,
        )

    with right_column:
        render_section_header(
            "Financial Benefit Mix",
            description=("Sources of projected financial benefit."),
        )

        financial_summary = _financial_summary_data()

        financial_mix_figure = px.pie(
            financial_summary,
            names="Impact Type",
            values="Value ($)",
            hole=0.55,
        )

        financial_mix_figure.update_layout(
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20,
            ),
            legend_title_text="",
        )

        render_plotly_chart(
            financial_mix_figure,
            data=financial_summary,
        )

    render_section_header(
        "Scenario Analysis",
        description=("Comparison of baseline and intervention scenarios."),
    )

    scenarios = _scenario_data()

    scenario_long = scenarios.melt(
        id_vars="Scenario",
        value_vars=[
            "Energy (MWh)",
            "Operating Cost ($)",
        ],
        var_name="Metric",
        value_name="Value",
    )

    scenario_figure = px.bar(
        scenario_long,
        x="Scenario",
        y="Value",
        color="Metric",
        barmode="group",
    )

    scenario_figure.update_layout(
        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20,
        ),
        legend_title_text="",
    )

    render_plotly_chart(
        scenario_figure,
        data=scenario_long,
    )

    render_section_header(
        "Scenario Summary",
        description=("Energy, operating cost, and portfolio-risk comparison."),
    )

    render_dataframe(
        scenarios,
        column_config={
            "Portfolio Risk": st.column_config.ProgressColumn(
                "Portfolio Risk",
                min_value=0.0,
                max_value=1.0,
                format="%.2f",
            ),
            "Operating Cost ($)": st.column_config.NumberColumn(
                "Operating Cost ($)",
                format="$%.0f",
            ),
        },
    )
    render_csv_download(
        scenarios,
        label="Download scenario analysis CSV",
        report_name="scenario-analysis",
        filters=filters,
        key="scenarios_download",
    )
