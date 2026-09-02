"""Data trust and quality governance workspace for EOIP."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd
import plotly.express as px
import streamlit as st

from eoip.app import data_access
from eoip.app.components import (
    MetricCard,
    PageContext,
    render_csv_download,
    render_dataframe,
    render_empty_state,
    render_metric_row,
    render_page_context,
    render_page_intro,
    render_plotly_chart,
    render_section_header,
)
from eoip.app.theme import EOIP_PRIMARY


def _governed_datasets() -> dict[str, pd.DataFrame]:
    """Return the application datasets available to this governance view."""
    return {
        "Plants": data_access.get_plant_performance(),
        "Equipment": data_access.get_assets(),
        "Incidents": data_access.get_incidents(),
        "Forecasts": data_access.get_forecasts(),
        "Anomalies": data_access.get_anomalies(),
        "Recommendations": data_access.get_recommendations(),
        "Maintenance": data_access.get_maintenance_priorities(),
    }


def calculate_completeness(dataframe: pd.DataFrame) -> float | None:
    """Return non-null cells as a percentage of all cells."""
    total_cells = int(dataframe.shape[0] * dataframe.shape[1])
    if total_cells == 0:
        return None
    non_null_cells = int(dataframe.notna().to_numpy().sum())
    return non_null_cells / total_cells * 100


def build_dataset_coverage(
    datasets: Mapping[str, pd.DataFrame],
) -> pd.DataFrame:
    """Summarize volume and directly measurable snapshot quality."""
    rows = []
    for name, dataframe in datasets.items():
        completeness = calculate_completeness(dataframe)
        rows.append(
            {
                "Dataset": name,
                "Records": len(dataframe),
                "Columns": len(dataframe.columns),
                "Missing Cells": int(dataframe.isna().to_numpy().sum()),
                "Duplicate Records": int(dataframe.duplicated().sum()),
                "Completeness (%)": completeness,
            }
        )
    return pd.DataFrame(rows)


def build_integrity_exceptions(
    *,
    equipment: pd.DataFrame,
    related_datasets: Mapping[str, pd.DataFrame],
) -> pd.DataFrame:
    """Find records whose plant/equipment identity is absent from asset master."""
    columns = ("Dataset", "Issue", "Plant", "Equipment", "Severity")
    if equipment.empty:
        return pd.DataFrame(columns=columns)
    known = set(zip(equipment["Plant"], equipment["Equipment ID"], strict=True))
    exceptions: list[dict[str, object]] = []
    for dataset_name, dataframe in related_datasets.items():
        equipment_column = next(
            (name for name in ("Equipment ID", "Equipment") if name in dataframe),
            None,
        )
        if equipment_column is None or "Plant" not in dataframe:
            continue
        for _, row in dataframe.iterrows():
            identity = (row["Plant"], row[equipment_column])
            if identity not in known:
                exceptions.append(
                    {
                        "Dataset": dataset_name,
                        "Issue": "Unknown plant/equipment relationship",
                        "Plant": row["Plant"],
                        "Equipment": row[equipment_column],
                        "Severity": "High",
                    }
                )
    return pd.DataFrame(exceptions, columns=columns)


def build_quality_exceptions(
    coverage: pd.DataFrame, integrity: pd.DataFrame
) -> pd.DataFrame:
    """Combine supported snapshot exceptions without a composite score."""
    rows: list[dict[str, object]] = []
    for _, row in coverage.iterrows():
        if row["Missing Cells"]:
            rows.append(
                {
                    "Dataset": row["Dataset"],
                    "Issue": "Missing values",
                    "Affected Records": int(row["Missing Cells"]),
                    "Severity": "Medium",
                }
            )
        if row["Duplicate Records"]:
            rows.append(
                {
                    "Dataset": row["Dataset"],
                    "Issue": "Duplicate records",
                    "Affected Records": int(row["Duplicate Records"]),
                    "Severity": "Medium",
                }
            )
    if not integrity.empty:
        for dataset, count in integrity.groupby("Dataset").size().items():
            rows.append(
                {
                    "Dataset": dataset,
                    "Issue": "Unknown plant/equipment relationship",
                    "Affected Records": int(count),
                    "Severity": "High",
                }
            )
    return pd.DataFrame(
        rows,
        columns=("Dataset", "Issue", "Affected Records", "Severity"),
    )


def render() -> None:
    """Render the EOIP Data Trust and Quality workspace."""
    render_page_intro(
        title="Data Trust & Quality",
        icon="data_quality",
        description="Snapshot completeness, coverage, and operational integrity.",
    )
    render_page_context(PageContext(scope="Platform"))
    datasets = _governed_datasets()
    coverage = build_dataset_coverage(datasets)
    integrity = build_integrity_exceptions(
        equipment=datasets["Equipment"],
        related_datasets={
            name: frame
            for name, frame in datasets.items()
            if name not in {"Plants", "Equipment", "Forecasts"}
        },
    )
    exceptions = build_quality_exceptions(coverage, integrity)
    records = int(coverage["Records"].sum())
    cells = int((coverage["Records"] * coverage["Columns"]).sum())
    missing = int(coverage["Missing Cells"].sum())
    completeness = None if cells == 0 else (cells - missing) / cells * 100

    render_section_header(
        "Trust Summary",
        description="Directly measured snapshot quantities; no overall quality score.",
    )
    render_metric_row(
        (
            MetricCard(label="Records Evaluated", value=records),
            MetricCard(
                label="Completeness",
                value=None if completeness is None else f"{completeness:.1f}%",
            ),
            MetricCard(label="Missing Cells", value=missing),
            MetricCard(label="Validation Exceptions", value=len(exceptions)),
            MetricCard(label="Integrity Issues", value=len(integrity)),
        )
    )

    render_section_header(
        "Quality Exceptions",
        description="Measured snapshot issues requiring governance attention.",
    )
    if exceptions.empty:
        render_empty_state(
            title="No measured quality exceptions",
            message="No missing, duplicate, or tested integrity issues were detected.",
        )
    else:
        severity_order = {"High": 0, "Medium": 1, "Low": 2}
        exceptions = (
            exceptions.assign(
                _order=exceptions["Severity"].map(severity_order).fillna(3)
            )
            .sort_values(["_order", "Affected Records"], ascending=[True, False])
            .drop(columns="_order")
        )
        render_dataframe(exceptions)

    render_section_header(
        "Dataset Coverage",
        description="Available records and measurable completeness by dataset.",
    )
    coverage_figure = px.bar(
        coverage.sort_values("Records"),
        x="Records",
        y="Dataset",
        orientation="h",
        color_discrete_sequence=[EOIP_PRIMARY],
    )
    coverage_figure.update_layout(xaxis_title="Records", yaxis_title="")
    render_plotly_chart(coverage_figure, data=coverage)
    render_dataframe(
        coverage,
        column_config={
            "Completeness (%)": st.column_config.NumberColumn(format="%.1f%%")
        },
    )

    render_section_header(
        "Integrity & Validation",
        description="Exact plant/equipment relationships tested against asset master.",
    )
    if integrity.empty:
        render_empty_state(
            title="No tested integrity exceptions",
            message="All tested plant/equipment identities exist in asset master.",
        )
    else:
        render_dataframe(integrity)

    with st.expander("Data governance notes and exports"):
        st.caption(
            "Freshness, update frequency, and quality history are not available in "
            "the application data contract and are intentionally omitted."
        )
        render_csv_download(
            exceptions,
            label="Export quality exceptions CSV",
            report_name="quality-exceptions",
            key="quality_exceptions_download",
        )
        render_csv_download(
            coverage,
            label="Export dataset coverage CSV",
            report_name="dataset-coverage",
            key="quality_coverage_download",
        )
