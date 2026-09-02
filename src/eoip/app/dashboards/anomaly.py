"""Anomaly dashboard for the EOIP Streamlit application."""

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
from eoip.app.theme import (
    EOIP_CHART_SEQUENCE,
    EOIP_DANGER,
    EOIP_PRIMARY,
    EOIP_SECONDARY,
    EOIP_WARNING,
    SEVERITY_COLORS,
)


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


def build_anomaly_priority(anomalies: pd.DataFrame) -> pd.DataFrame:
    """Order anomalies by declared severity and then anomaly score."""
    if anomalies.empty:
        return anomalies.copy()
    severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    priority = anomalies.assign(
        _severity_order=anomalies["Severity"].map(severity_order).fillna(4)
    )
    return priority.sort_values(
        ["_severity_order", "Anomaly Score"], ascending=[True, False]
    ).drop(columns="_severity_order")


def render() -> None:
    """Render the EOIP Anomaly Dashboard."""
    render_page_intro(
        title="Anomaly Investigation",
        icon="anomaly",
        description=(
            "Abnormal operating behavior, anomaly scores, "
            "detection performance, and investigation intelligence."
        ),
    )
    raw_anomalies = data_access.get_anomalies()
    current_scope = get_filter_selection()
    filters = render_global_filters(
        show_date=False,
        show_equipment=True,
        equipment_options=equipment_options_for_plant(
            raw_anomalies, current_scope.plant
        ),
    )
    contract = PageDataContract(
        filters,
        {
            "anomalies": raw_anomalies,
            "trend": _anomaly_trend_data(),
            "performance": _method_performance_data(),
        },
    )
    anomalies = contract.scoped("anomalies", dimensions=FilterDimensions(date=False))
    if anomalies.empty:
        render_empty_state(
            title="No anomaly data",
            message="No anomalies match the selected plant and equipment scope.",
        )
        return

    critical_anomalies = int(anomalies["Severity"].eq("Critical").sum())
    high_anomalies = int(anomalies["Severity"].eq("High").sum())
    affected_equipment = int(anomalies["Equipment"].nunique())
    highest_score = float(anomalies["Anomaly Score"].max())
    performance = contract.scoped(
        "performance",
        dimensions=FilterDimensions(plant=False, equipment=False, date=False),
    )

    render_section_header(
        "Anomaly Attention Summary",
        description=("Current anomaly volume and detection-quality indicators."),
    )

    render_metric_row(
        (
            MetricCard(
                label="Active Anomalies",
                value=len(anomalies),
            ),
            MetricCard(
                label="Critical Anomalies",
                value=critical_anomalies,
            ),
            MetricCard(
                label="High-Severity Anomalies",
                value=high_anomalies,
            ),
            MetricCard(
                label="Affected Equipment",
                value=affected_equipment,
            ),
            MetricCard(
                label="Highest Anomaly Score",
                value=f"{highest_score:.2f}",
                subtitle="Source score; not a probability",
            ),
        )
    )

    priority = build_anomaly_priority(anomalies)
    render_section_header(
        "Highest-Priority Findings",
        description="Declared severity first, followed by anomaly score.",
    )
    render_dataframe(priority)
    selected_id = st.selectbox(
        "Anomaly to investigate",
        options=priority["Anomaly ID"].tolist(),
        key="anomaly_drilldown_id",
    )
    anomaly = priority.loc[priority["Anomaly ID"].eq(selected_id)].iloc[0]
    render_section_header(
        "Anomaly Evidence",
        description=(
            "Supported finding fields; no timestamp or causal explanation is stored."
        ),
    )
    render_dataframe(pd.DataFrame([anomaly]))
    with st.container(horizontal=True):
        if st.button("Inspect asset", key="anomaly_investigate_asset"):
            navigate_to(
                "assets",
                plant=str(anomaly["Plant"]),
                equipment_id=str(anomaly["Equipment"]),
            )
        if st.button("Review maintenance", key="anomaly_open_maintenance"):
            navigate_to(
                "maintenance",
                plant=str(anomaly["Plant"]),
                equipment_id=str(anomaly["Equipment"]),
            )
        if st.button("Review operations", key="anomaly_open_operations"):
            navigate_to("operations", plant=str(anomaly["Plant"]))

    render_section_header(
        "Anomaly Score Trend",
        description=("Recent anomaly scores against the active detection threshold."),
    )

    trend = contract.scoped(
        "trend",
        dimensions=FilterDimensions(plant=False, equipment=False, date=False),
    )

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
        color_discrete_map={"Anomaly Score": EOIP_DANGER, "Threshold": EOIP_WARNING},
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

    if filters.plant == "All Plants" and filters.equipment_id is None:
        render_plotly_chart(trend_figure, data=trend_long, time_series=True)
    else:
        render_empty_state(
            title="Portfolio-only anomaly trend",
            message="Choose All Plants and All Equipment to view this source.",
        )

    left_column, right_column = st.columns((3, 2))

    with left_column:
        render_section_header(
            "Model Diagnostics",
            description=(
                "Global model precision, recall, and F1 score by anomaly method."
            ),
        )

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
            color_discrete_map={
                "Precision (%)": EOIP_PRIMARY,
                "Recall (%)": EOIP_SECONDARY,
                "F1 Score (%)": EOIP_CHART_SEQUENCE[2],
            },
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

        severity = (
            anomalies["Severity"]
            .value_counts()
            .rename_axis("Severity")
            .reset_index(name="Count")
        )

        severity_figure = px.bar(
            severity,
            x="Count",
            y="Severity",
            orientation="h",
            color="Severity",
            color_discrete_map=SEVERITY_COLORS,
        )

        severity_figure.update_layout(
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20,
            ),
            showlegend=False,
            xaxis_title="Anomalies",
            yaxis_title="",
        )

        render_plotly_chart(
            severity_figure,
            data=severity,
        )

    render_csv_download(
        anomalies,
        label="Download active anomalies CSV",
        report_name="active-anomalies",
        filters=filters,
        key="anomalies_download",
    )
