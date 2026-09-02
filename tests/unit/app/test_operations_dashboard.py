"""Behavior tests for the Operations Command Center."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from eoip.app import data_access
from eoip.app.dashboards.operations import (
    _operations_status_data,
    build_active_exception_queue,
    build_plant_health_matrix,
    build_response_performance,
    derive_attention_summary,
)


def test_attention_summary_derives_supported_scoped_metrics() -> None:
    summary = derive_attention_summary(
        _operations_status_data(), data_access.get_incidents()
    )

    assert summary.critical_open_incidents == 1
    assert summary.open_incidents == 4
    assert summary.plants_requiring_attention == 2
    assert summary.lowest_availability_percent == 91.6
    assert summary.active_downtime_minutes == 180.0


def test_exception_queue_orders_severity_then_downtime() -> None:
    queue = build_active_exception_queue(data_access.get_incidents())

    assert queue["Incident ID"].tolist() == [
        "INC-1042",
        "INC-1041",
        "INC-1038",
        "INC-1039",
    ]
    assert queue["Severity"].tolist() == ["Critical", "High", "High", "Medium"]
    assert "INC-1034" not in queue["Incident ID"].tolist()


def test_exception_queue_uses_only_available_urgency_fields() -> None:
    queue = build_active_exception_queue(data_access.get_incidents())

    assert tuple(queue.columns) == (
        "Severity",
        "Type",
        "Incident ID",
        "Plant",
        "Equipment",
        "Status",
        "Downtime (min)",
        "MTTA (min)",
    )
    assert not {"Acknowledged", "Owner", "SLA", "Escalation", "Age"}.intersection(
        queue.columns
    )


def test_plant_matrix_uses_existing_status_and_prioritizes_attention() -> None:
    matrix = build_plant_health_matrix(_operations_status_data())

    assert matrix["Plant"].tolist() == [
        "Solar Plant D",
        "Solar Plant B",
        "Solar Plant A",
        "Solar Plant C",
    ]
    assert matrix["Status"].tolist() == ["Critical", "Watch", "Normal", "Normal"]


def test_response_performance_uses_observed_mtta_and_downtime() -> None:
    response = build_response_performance(data_access.get_incidents())
    plant_d = response.loc[response["Plant"].eq("Solar Plant D")].iloc[0]

    assert plant_d["Average MTTA (min)"] == 5.0
    assert plant_d["Downtime (min)"] == 117


def test_empty_and_partial_sources_remain_independently_safe() -> None:
    empty = pd.DataFrame()
    summary = derive_attention_summary(_operations_status_data(), empty)

    assert summary.open_incidents is None
    assert summary.plants_requiring_attention == 2
    assert build_active_exception_queue(empty).empty
    assert build_plant_health_matrix(empty).empty
    assert build_response_performance(empty).empty


def test_operations_source_has_no_fabricated_or_legacy_ui_fields() -> None:
    source = Path("src/eoip/app/dashboards/operations.py").read_text(encoding="utf-8")

    assert all(
        field not in source
        for field in ("Acknowledged", "Assignee", "SLA breached", "Escalation")
    )
    assert "st.metric(" not in source
    assert "st.success(" not in source
    assert not any(0x1F000 <= ord(character) <= 0x1FAFF for character in source)
