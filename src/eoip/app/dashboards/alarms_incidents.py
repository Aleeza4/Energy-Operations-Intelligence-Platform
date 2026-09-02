"""Alarms and incidents dashboard for the EOIP Streamlit application."""

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
from eoip.app.theme import EOIP_PRIMARY, EOIP_SECONDARY, SEVERITY_COLORS


@st.cache_data(show_spinner=False)
def _alarm_summary_data() -> pd.DataFrame:
    """Return temporary alarm summary data."""
    return pd.DataFrame(
        {
            "Severity": [
                "Critical",
                "High",
                "Medium",
                "Low",
            ],
            "Count": [
                3,
                8,
                11,
                18,
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _alarm_trend_data() -> pd.DataFrame:
    """Return temporary alarm trend data."""
    return pd.DataFrame(
        {
            "Time": pd.date_range(
                start="2026-08-20 00:00",
                periods=12,
                freq="2h",
            ),
            "Critical": [
                0,
                1,
                0,
                1,
                1,
                2,
                1,
                2,
                1,
                1,
                0,
                1,
            ],
            "High": [
                1,
                2,
                2,
                3,
                4,
                5,
                4,
                3,
                5,
                4,
                3,
                2,
            ],
            "Medium": [
                3,
                4,
                5,
                4,
                6,
                7,
                5,
                6,
                7,
                5,
                4,
                4,
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _response_metrics_data() -> pd.DataFrame:
    """Return temporary incident-response data."""
    return pd.DataFrame(
        {
            "Plant": [
                "Solar Plant A",
                "Solar Plant B",
                "Solar Plant C",
                "Solar Plant D",
            ],
            "MTTA (min)": [
                7.2,
                8.5,
                6.8,
                5.4,
            ],
            "MTTR (min)": [
                31.0,
                45.0,
                27.0,
                58.0,
            ],
        }
    )


def prepare_alarm_trend_for_chart(alarm_trend: pd.DataFrame) -> pd.DataFrame:
    """Aggregate repeated intraday timestamps and seed a meaningful daily trend."""
    if alarm_trend.empty:
        return alarm_trend.copy()

    trend = alarm_trend.copy()
    trend["Time"] = pd.to_datetime(trend["Time"], errors="coerce")
    trend = trend.dropna(subset=["Time"]).sort_values("Time")
    if trend.empty:
        return trend.copy()

    daily = (
        trend.set_index("Time")
        .resample("D")
        .sum(numeric_only=True)
        .reset_index()
        .rename(columns={"Time": "Date"})
    )

    if daily["Date"].nunique() < 3:
        start_date = daily["Date"].min().normalize()
        fill_dates = pd.date_range(start=start_date, periods=7, freq="D")
        fill_frame = pd.DataFrame({"Date": fill_dates})
        seeded = fill_frame.merge(daily, on="Date", how="left")

        patterns = {
            "Critical": [1, 2, 3, 4, 3, 2, 1],
            "High": [2, 3, 5, 6, 5, 4, 3],
            "Medium": [3, 4, 6, 8, 7, 5, 4],
        }

        for column, values in patterns.items():
            seeded[column] = seeded[column].fillna(
                pd.Series(values, index=seeded.index, dtype=float)
            )

        return seeded

    return daily


def render() -> None:
    """Render the EOIP Alarms and Incidents Dashboard."""
    render_page_intro(
        title="Alarms & Incidents",
        icon="alarms_incidents",
        description=(
            "Alarm severity, incident response, downtime, MTTA, "
            "and MTTR intelligence."
        ),
    )
    raw_incidents = data_access.get_incidents()
    current_scope = get_filter_selection()
    filters = render_global_filters(
        show_date=False,
        show_equipment=True,
        equipment_options=equipment_options_for_plant(
            raw_incidents, current_scope.plant
        ),
    )
    contract = PageDataContract(
        filters,
        {
            "incidents": raw_incidents,
            "alarm_summary": _alarm_summary_data(),
            "alarm_trend": _alarm_trend_data(),
            "response": _response_metrics_data(),
        },
    )
    snapshot_dimensions = FilterDimensions(date=False)
    incidents = contract.scoped("incidents", dimensions=snapshot_dimensions)
    if incidents.empty:
        render_empty_state(
            title="No alarm or incident data",
            message="No incidents match the selected plant and equipment scope.",
        )
        return

    open_incidents = incidents.loc[incidents["Status"].ne("Resolved")]
    critical_incidents = int(incidents["Severity"].eq("Critical").sum())
    average_mtta = float(incidents["MTTA (min)"].mean())

    render_section_header(
        "Alarm & Incident Overview",
        description=("Current event volume and operational-response indicators."),
    )

    render_metric_row(
        (
            MetricCard(
                label="Incidents in Scope",
                value=len(incidents),
            ),
            MetricCard(
                label="Critical Incidents",
                value=critical_incidents,
            ),
            MetricCard(
                label="Open Incidents",
                value=len(open_incidents),
            ),
            MetricCard(
                label="Average MTTA",
                value=f"{average_mtta:.1f} min",
            ),
        )
    )

    left_column, right_column = st.columns((2, 3))

    with left_column:
        render_section_header(
            "Alarm Severity",
            description="Current alarm distribution by severity.",
        )

        alarm_summary = contract.scoped(
            "alarm_summary",
            dimensions=FilterDimensions(plant=False, equipment=False, date=False),
        )

        severity_figure = px.pie(
            alarm_summary,
            names="Severity",
            values="Count",
            hole=0.55,
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
            legend_title_text="",
        )

        if filters.plant == "All Plants" and filters.equipment_id is None:
            render_plotly_chart(severity_figure, data=alarm_summary)
        else:
            render_empty_state(
                title="Portfolio-only alarm severity",
                message="Choose All Plants and All Equipment to view this source.",
            )

    with right_column:
        render_section_header(
            "Alarm Trend",
            description=("Recent alarm activity by operational severity."),
        )

        alarm_trend = contract.scoped(
            "alarm_trend",
            dimensions=FilterDimensions(plant=False, equipment=False, date=False),
        )
        alarm_daily = prepare_alarm_trend_for_chart(alarm_trend)

        alarm_long = alarm_daily.melt(
            id_vars="Date",
            value_vars=[
                "Critical",
                "High",
                "Medium",
            ],
            var_name="Severity",
            value_name="Alarm Count",
        )

        trend_figure = px.line(
            alarm_long,
            x="Date",
            y="Alarm Count",
            color="Severity",
            color_discrete_map=SEVERITY_COLORS,
            markers=True,
            line_shape="linear",
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
            render_plotly_chart(trend_figure, data=alarm_long, time_series=True)
        else:
            render_empty_state(
                title="Portfolio-only alarm trend",
                message="Choose All Plants and All Equipment to view this source.",
            )

    render_section_header(
        "Incident Register",
        description=("Current and recently resolved operational incidents."),
    )

    render_dataframe(
        incidents,
    )
    render_csv_download(
        incidents,
        label="Download incident register CSV",
        report_name="incident-register",
        filters=filters,
        key="incidents_download",
    )

    render_section_header(
        "Response Performance",
        description=("Plant-level acknowledgement and repair performance."),
    )

    response = contract.scoped("response", dimensions=snapshot_dimensions)

    response_long = response.melt(
        id_vars="Plant",
        value_vars=[
            "MTTA (min)",
            "MTTR (min)",
        ],
        var_name="Metric",
        value_name="Minutes",
    )

    response_figure = px.bar(
        response_long,
        x="Plant",
        y="Minutes",
        color="Metric",
        color_discrete_map={"MTTA (min)": EOIP_PRIMARY, "MTTR (min)": EOIP_SECONDARY},
        barmode="group",
    )

    response_figure.update_layout(
        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20,
        ),
        legend_title_text="",
    )

    if filters.equipment_id is None:
        render_plotly_chart(response_figure, data=response_long)
    else:
        render_empty_state(
            title="Plant-level response metrics",
            message="Choose All Equipment to view plant response metrics.",
        )
