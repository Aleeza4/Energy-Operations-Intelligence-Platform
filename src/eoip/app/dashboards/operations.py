"""Operational command center for the EOIP Streamlit application."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import plotly.express as px
import streamlit as st

from eoip.app import data_access
from eoip.app.components import (
    MetricCard,
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
from eoip.app.theme import SEVERITY_COLORS


@st.cache_data(show_spinner=False)
def _operations_status_data() -> pd.DataFrame:
    """Return temporary plant operational-state data."""
    return pd.DataFrame(
        {
            "Plant": [
                "Solar Plant A",
                "Solar Plant B",
                "Solar Plant C",
                "Solar Plant D",
            ],
            "Status": ["Normal", "Watch", "Normal", "Critical"],
            "Active Alarms": [2, 7, 1, 14],
            "Open Incidents": [0, 2, 0, 4],
            "Availability (%)": [98.8, 95.9, 99.2, 91.6],
        }
    )


@st.cache_data(show_spinner=False)
def _alarm_trend_data() -> pd.DataFrame:
    """Return portfolio alarm-count history without plant attribution."""
    return pd.DataFrame(
        {
            "Hour": [
                "00:00",
                "03:00",
                "06:00",
                "09:00",
                "12:00",
                "15:00",
                "18:00",
                "21:00",
            ],
            "Active Alarms": [4, 3, 5, 8, 13, 11, 7, 5],
        }
    )


@dataclass(frozen=True, slots=True)
class OperationsAttentionSummary:
    """Supported exception-first operational measures."""

    critical_open_incidents: int | None
    open_incidents: int | None
    plants_requiring_attention: int | None
    lowest_availability_percent: float | None
    active_downtime_minutes: float | None


def derive_attention_summary(
    plant_status: pd.DataFrame,
    incidents: pd.DataFrame,
) -> OperationsAttentionSummary:
    """Derive attention metrics from the current scoped sources."""
    critical_open = open_count = active_downtime = None
    if not incidents.empty:
        open_incidents = incidents.loc[incidents["Status"].ne("Resolved")]
        critical_open = int(open_incidents["Severity"].eq("Critical").sum())
        open_count = len(open_incidents)
        active_downtime = float(open_incidents["Downtime (min)"].sum())

    attention_plants = lowest_availability = None
    if not plant_status.empty:
        attention_plants = int(plant_status["Status"].ne("Normal").sum())
        lowest_availability = float(plant_status["Availability (%)"].min())

    return OperationsAttentionSummary(
        critical_open_incidents=critical_open,
        open_incidents=open_count,
        plants_requiring_attention=attention_plants,
        lowest_availability_percent=lowest_availability,
        active_downtime_minutes=active_downtime,
    )


def build_active_exception_queue(incidents: pd.DataFrame) -> pd.DataFrame:
    """Return unresolved incidents ordered by severity then downtime."""
    columns = (
        "Severity",
        "Type",
        "Incident ID",
        "Plant",
        "Equipment",
        "Status",
        "Downtime (min)",
        "MTTA (min)",
    )
    if incidents.empty:
        return pd.DataFrame(columns=columns)

    severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    queue = incidents.loc[incidents["Status"].ne("Resolved")].copy()
    queue["Type"] = "Incident"
    queue["_severity_order"] = queue["Severity"].map(severity_order).fillna(4)
    return (
        queue.sort_values(
            ["_severity_order", "Downtime (min)"], ascending=[True, False]
        )
        .drop(columns="_severity_order")
        .loc[:, columns]
        .reset_index(drop=True)
    )


def build_plant_health_matrix(plant_status: pd.DataFrame) -> pd.DataFrame:
    """Return plant state ordered by existing status then availability."""
    if plant_status.empty:
        return plant_status.copy()

    status_order = {"Critical": 0, "Watch": 1, "Normal": 2}
    matrix = plant_status.assign(
        _status_order=plant_status["Status"].map(status_order).fillna(3)
    )
    return (
        matrix.sort_values(
            ["_status_order", "Availability (%)"], ascending=[True, True]
        )
        .drop(columns="_status_order")
        .reset_index(drop=True)
    )


def build_response_performance(incidents: pd.DataFrame) -> pd.DataFrame:
    """Aggregate supported response measures by plant."""
    if incidents.empty:
        return pd.DataFrame(columns=("Plant", "Average MTTA (min)", "Downtime (min)"))

    return (
        incidents.groupby("Plant", as_index=False)
        .agg(
            **{
                "Average MTTA (min)": ("MTTA (min)", "mean"),
                "Downtime (min)": ("Downtime (min)", "sum"),
            }
        )
        .sort_values("Downtime (min)", ascending=False, ignore_index=True)
    )


def _render_attention_summary(summary: OperationsAttentionSummary) -> None:
    metrics: list[MetricCard] = []
    if summary.critical_open_incidents is not None:
        metrics.append(
            MetricCard(
                label="Critical Open Incidents",
                value=summary.critical_open_incidents,
                subtitle="Requires immediate review",
            )
        )
    if summary.open_incidents is not None:
        metrics.append(MetricCard(label="Open Incidents", value=summary.open_incidents))
    if summary.plants_requiring_attention is not None:
        metrics.append(
            MetricCard(
                label="Plants Requiring Attention",
                value=summary.plants_requiring_attention,
                subtitle="Existing Watch or Critical state",
            )
        )
    if summary.lowest_availability_percent is not None:
        metrics.append(
            MetricCard(
                label="Lowest Availability",
                value=f"{summary.lowest_availability_percent:.1f}%",
            )
        )
    if summary.active_downtime_minutes is not None:
        metrics.append(
            MetricCard(
                label="Active Downtime",
                value=f"{summary.active_downtime_minutes:.0f} min",
                subtitle="Across unresolved incidents",
            )
        )

    if metrics:
        render_metric_row(metrics)
    else:
        render_empty_state(
            title="Attention summary unavailable",
            message="No plant-state or incident summary data is available.",
        )


def render() -> None:
    """Render the EOIP Operations Command Center."""
    render_page_intro(
        title="Operations Dashboard",
        icon="operations",
        description=(
            "Current operational exceptions, plant state, response performance, "
            "and investigation workflow."
        ),
    )
    filters = render_global_filters(show_date=False)
    contract = PageDataContract(
        filters,
        {
            "plant_status": _operations_status_data(),
            "incidents": data_access.get_incidents(),
            "alarm_trend": _alarm_trend_data(),
        },
    )
    snapshot_dimensions = FilterDimensions(date=False)
    plant_status = contract.scoped("plant_status", dimensions=snapshot_dimensions)
    incidents = contract.scoped("incidents", dimensions=snapshot_dimensions)

    render_section_header(
        "Attention Summary",
        description="Exception-first measures for the selected operating scope.",
    )
    _render_attention_summary(derive_attention_summary(plant_status, incidents))

    render_section_header(
        "Active Exception Queue",
        description=(
            "Unresolved incidents ordered by severity and then active downtime."
        ),
    )
    active_queue = build_active_exception_queue(incidents)
    render_dataframe(
        active_queue,
        empty_title="No active incidents",
        empty_message="No unresolved incidents match the selected plant scope.",
        column_config={
            "Downtime (min)": st.column_config.NumberColumn(format="%.0f min"),
            "MTTA (min)": st.column_config.NumberColumn(format="%.0f min"),
        },
    )

    render_section_header(
        "Plant Health Matrix",
        description="Current plant state, alarm load, incidents, and availability.",
    )
    plant_matrix = build_plant_health_matrix(plant_status)
    render_dataframe(
        plant_matrix,
        empty_title="Plant state unavailable",
        empty_message="No plant-status records match the selected scope.",
        column_config={
            "Availability (%)": st.column_config.ProgressColumn(
                "Availability (%)", min_value=0.0, max_value=100.0, format="%.1f%%"
            )
        },
    )

    render_section_header(
        "Portfolio Alarm Activity",
        description="Active alarm volume across the available portfolio history.",
    )
    trend = contract.scoped(
        "alarm_trend",
        dimensions=FilterDimensions(plant=False, equipment=False, date=False),
    )
    if filters.plant != "All Plants":
        render_empty_state(
            title="Portfolio-only alarm trend",
            message=(
                "The alarm history source has no plant attribution. "
                "Choose All Plants to view it."
            ),
        )
    elif trend.empty:
        render_empty_state(
            title="Alarm activity unavailable",
            message="No alarm-history records are currently available.",
        )
    else:
        latest_count = int(trend.iloc[-1]["Active Alarms"])
        change = latest_count - int(trend.iloc[0]["Active Alarms"])
        st.caption(
            f"Latest active-alarm count: {latest_count} "
            f"({change:+d} versus start of available history)."
        )
        alarm_figure = px.line(trend, x="Hour", y="Active Alarms", markers=True)
        alarm_figure.update_layout(
            xaxis_title="Time",
            yaxis_title="Active alarms",
        )
        render_plotly_chart(alarm_figure, data=trend)

    render_section_header(
        "Response Performance",
        description=(
            "Observed acknowledgement time and downtime by plant; no SLA assumed."
        ),
    )
    response = build_response_performance(incidents)
    if response.empty:
        render_empty_state(
            title="Response data unavailable",
            message="No incident response records match the selected scope.",
        )
    else:
        response_long = response.melt(
            id_vars="Plant",
            value_vars=("Average MTTA (min)", "Downtime (min)"),
            var_name="Measure",
            value_name="Minutes",
        )
        response_figure = px.bar(
            response_long,
            x="Plant",
            y="Minutes",
            color="Measure",
            color_discrete_map={
                "Average MTTA (min)": SEVERITY_COLORS["Medium"],
                "Downtime (min)": SEVERITY_COLORS["Critical"],
            },
            barmode="group",
        )
        response_figure.update_layout(
            xaxis_title="Plant",
            yaxis_title="Minutes",
            legend_title_text="",
        )
        render_plotly_chart(response_figure, data=response_long)

    render_section_header(
        "Investigation",
        description=(
            "Review one prioritized incident and continue in the relevant workflow."
        ),
    )
    if active_queue.empty:
        render_empty_state(
            title="No incident selected",
            message=(
                "An investigation becomes available when an active incident exists."
            ),
        )
    else:
        selected_id = st.selectbox(
            "Active incident",
            options=active_queue["Incident ID"].tolist(),
            key="operations_active_incident",
        )
        selected = active_queue.loc[active_queue["Incident ID"].eq(selected_id)].iloc[0]
        render_dataframe(active_queue.loc[active_queue["Incident ID"].eq(selected_id)])

        action_columns = st.columns(3)
        with action_columns[0]:
            if st.button(
                "Open incident investigation",
                key="operations_open_incident",
                width="stretch",
            ):
                navigate_to(
                    "alarms_incidents",
                    plant=str(selected["Plant"]),
                    equipment_id=str(selected["Equipment"]),
                )
        with action_columns[1]:
            if st.button(
                "Open affected asset",
                key="operations_open_asset",
                width="stretch",
            ):
                navigate_to(
                    "assets",
                    plant=str(selected["Plant"]),
                    equipment_id=str(selected["Equipment"]),
                )
        with action_columns[2]:
            if st.button(
                "Open plant performance",
                key="operations_open_plant",
                width="stretch",
            ):
                navigate_to("plant_performance", plant=str(selected["Plant"]))

    resolved = incidents.loc[incidents["Status"].eq("Resolved")]
    if not resolved.empty:
        with st.expander("Recent resolved incidents"):
            render_dataframe(resolved)

    with st.expander("Exports"):
        render_csv_download(
            plant_matrix,
            label="Download scoped plant health CSV",
            report_name="operations-plant-health",
            filters=filters,
            key="operations_status_download",
        )
        render_csv_download(
            active_queue,
            label="Download scoped active incidents CSV",
            report_name="operations-active-incidents",
            filters=filters,
            key="operations_incidents_download",
        )
