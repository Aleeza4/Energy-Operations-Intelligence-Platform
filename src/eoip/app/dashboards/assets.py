"""Asset engineering workspace for the EOIP Streamlit application."""

from __future__ import annotations

from dataclasses import dataclass

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
from eoip.app.theme import RISK_COLORS


@dataclass(frozen=True, slots=True)
class AssetEvidence:
    """Exact plant-and-equipment operational relationships."""

    incidents: pd.DataFrame
    anomalies: pd.DataFrame
    maintenance: pd.DataFrame


def build_equipment_priority(assets: pd.DataFrame) -> pd.DataFrame:
    """Order equipment by the source-provided priority rank."""
    columns = (
        "Priority Rank",
        "Equipment ID",
        "Plant",
        "Equipment Type",
        "Risk Level",
        "Health Score",
        "Failure Probability",
    )
    if assets.empty:
        return pd.DataFrame(columns=columns)
    return assets.loc[:, columns].sort_values(
        ["Priority Rank", "Equipment ID"], kind="stable"
    )


def build_asset_evidence(
    asset: pd.Series,
    *,
    incidents: pd.DataFrame,
    anomalies: pd.DataFrame,
    maintenance: pd.DataFrame,
) -> AssetEvidence:
    """Link evidence only through matching plant and equipment identifiers."""
    plant = str(asset["Plant"])
    equipment = str(asset["Equipment ID"])
    linked_incidents = incidents.loc[
        incidents["Plant"].eq(plant) & incidents["Equipment"].eq(equipment)
    ].copy()
    linked_anomalies = anomalies.loc[
        anomalies["Plant"].eq(plant) & anomalies["Equipment"].eq(equipment)
    ].copy()
    linked_maintenance = maintenance.loc[
        maintenance["Plant"].eq(plant) & maintenance["Equipment ID"].eq(equipment)
    ].copy()
    return AssetEvidence(linked_incidents, linked_anomalies, linked_maintenance)


def _render_asset_actions(asset: pd.Series, evidence: AssetEvidence) -> None:
    """Render context-sensitive engineering workflow actions."""
    plant = str(asset["Plant"])
    equipment = str(asset["Equipment ID"])
    render_section_header(
        "Engineering Actions",
        description="Continue with the maximum context supported by each destination.",
    )
    with st.container(horizontal=True):
        if not evidence.anomalies.empty and st.button(
            "Review anomalies", key="assets_open_anomaly"
        ):
            navigate_to("anomaly", plant=plant, equipment_id=equipment)
        if not evidence.maintenance.empty and st.button(
            "Open maintenance", key="assets_open_maintenance"
        ):
            navigate_to("maintenance", plant=plant, equipment_id=equipment)
        if st.button("Review alarms & incidents", key="assets_open_incidents"):
            incident_equipment = equipment if not evidence.incidents.empty else None
            navigate_to(
                "alarms_incidents",
                plant=plant,
                equipment_id=incident_equipment,
            )
        if st.button("Open plant performance", key="assets_open_plant"):
            navigate_to("plant_performance", plant=plant)


def render() -> None:
    """Render the EOIP Asset engineering workspace."""
    render_page_intro(
        title="Asset Dashboard",
        icon="assets",
        description="Equipment priority, declared risk, evidence, and investigation.",
    )
    raw_assets = data_access.get_assets()
    current_scope = get_filter_selection()
    filters = render_global_filters(
        show_date=False,
        show_equipment=True,
        equipment_options=equipment_options_for_plant(raw_assets, current_scope.plant),
    )
    assets = PageDataContract(filters, {"assets": raw_assets}).scoped(
        "assets", dimensions=FilterDimensions(date=False)
    )

    render_section_header(
        "Asset Attention Summary",
        description="Condition and source-declared risk in the selected scope.",
    )
    if assets.empty:
        render_empty_state(
            title="No asset data",
            message=(
                "No equipment records match the selected plant and equipment scope."
            ),
        )
        return

    high_risk = int(assets["Risk Level"].isin(("High", "Critical")).sum())
    critical = int(assets["Risk Level"].eq("Critical").sum())
    render_metric_row(
        (
            MetricCard(label="Equipment in Scope", value=len(assets)),
            MetricCard(label="High-Risk Equipment", value=high_risk),
            MetricCard(label="Critical Equipment", value=critical),
            MetricCard(
                label="Average Health Score",
                value=f"{float(assets['Health Score'].mean()):.1f}",
                subtitle="Source-provided condition measure",
            ),
        )
    )

    priority = build_equipment_priority(assets)
    render_section_header(
        "Equipment Priority",
        description="Ordered by the existing source-provided priority rank.",
    )
    render_dataframe(
        priority,
        column_config={
            "Health Score": st.column_config.NumberColumn(format="%.0f"),
            "Failure Probability": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    render_section_header(
        "Equipment Condition",
        description=(
            "Health measure by equipment with declared risk-category semantics."
        ),
    )
    condition = priority.sort_values("Health Score")
    condition_figure = px.bar(
        condition,
        x="Health Score",
        y="Equipment ID",
        color="Risk Level",
        orientation="h",
        color_discrete_map=RISK_COLORS,
        hover_data=("Plant", "Equipment Type", "Failure Probability"),
    )
    condition_figure.update_layout(xaxis_title="Health score", yaxis_title="")
    render_plotly_chart(condition_figure, data=condition)

    render_section_header(
        "Selected Equipment Detail",
        description="Concise engineering context for one equipment record.",
    )
    selected_equipment = st.selectbox(
        "Equipment to investigate",
        options=priority["Equipment ID"].tolist(),
        key="assets_investigation_equipment",
    )
    asset = priority.loc[priority["Equipment ID"].eq(selected_equipment)].iloc[0]
    detail_columns = (
        "Equipment ID",
        "Plant",
        "Equipment Type",
        "Risk Level",
        "Priority Rank",
        "Health Score",
        "Failure Probability",
    )
    render_dataframe(pd.DataFrame([asset.loc[list(detail_columns)]]))

    evidence = build_asset_evidence(
        asset,
        incidents=data_access.get_incidents(),
        anomalies=data_access.get_anomalies(),
        maintenance=data_access.get_maintenance_priorities(),
    )
    render_section_header(
        "Related Operational Evidence",
        description="Records linked by exact plant and equipment identifiers only.",
    )
    open_incidents = evidence.incidents.loc[evidence.incidents["Status"].ne("Resolved")]
    render_metric_row(
        (
            MetricCard(label="Linked Open Incidents", value=len(open_incidents)),
            MetricCard(label="Linked Active Anomalies", value=len(evidence.anomalies)),
            MetricCard(
                label="Linked Maintenance Priority Records",
                value=len(evidence.maintenance),
            ),
        )
    )
    evidence_sections = (
        ("Incident evidence", evidence.incidents),
        ("Anomaly evidence", evidence.anomalies),
        ("Maintenance priority evidence", evidence.maintenance),
    )
    for label, frame in evidence_sections:
        with st.expander(label):
            if frame.empty:
                render_empty_state(
                    title=f"No {label.lower()}",
                    message=(
                        "No exact plant-and-equipment relationship exists in "
                        "this source."
                    ),
                )
            else:
                render_dataframe(frame)

    with st.expander("Exports"):
        render_csv_download(
            assets,
            label="Download scoped equipment CSV",
            report_name="asset-engineering",
            filters=filters,
            key="asset_health_download",
        )
    _render_asset_actions(asset, evidence)
