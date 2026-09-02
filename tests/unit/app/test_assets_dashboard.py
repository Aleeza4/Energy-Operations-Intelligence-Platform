"""Focused tests for the Asset engineering workspace."""

from __future__ import annotations

import inspect
from datetime import date

import pandas as pd

from eoip.app import data_access
from eoip.app.components.filters import FilterSelection
from eoip.app.dashboards import assets
from eoip.app.dashboards.assets import (
    build_asset_evidence,
    build_equipment_priority,
)
from eoip.app.data_filters import apply_dataframe_filters


def test_equipment_priority_uses_declared_rank() -> None:
    """Asset ordering must use the source rank without a synthetic score."""
    priority = build_equipment_priority(data_access.get_assets())

    assert priority["Equipment ID"].tolist()[:3] == [
        "INV-005",
        "INV-006",
        "INV-003",
    ]
    assert "Risk Score" not in priority.columns
    assert "Priority Score" not in priority.columns


def test_asset_scope_supports_plant_and_equipment() -> None:
    """Plant and equipment filters must constrain the same source records."""
    scoped = apply_dataframe_filters(
        data_access.get_assets(),
        FilterSelection(
            plant="Solar Plant D",
            equipment_id="INV-005",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
        ),
    )

    assert scoped["Equipment ID"].tolist() == ["INV-005"]
    assert scoped.iloc[0]["Risk Level"] == "Critical"


def test_evidence_requires_exact_plant_and_equipment_match() -> None:
    """Relationships must match both identifiers, not display names alone."""
    asset = (
        data_access.get_assets()
        .loc[data_access.get_assets()["Equipment ID"].eq("INV-005")]
        .iloc[0]
    )
    evidence = build_asset_evidence(
        asset,
        incidents=data_access.get_incidents(),
        anomalies=data_access.get_anomalies(),
        maintenance=data_access.get_maintenance_priorities(),
    )

    assert evidence.incidents["Incident ID"].tolist() == ["INC-1042"]
    assert evidence.anomalies["Anomaly ID"].tolist() == ["ANM-2031"]
    assert evidence.maintenance["Equipment ID"].tolist() == ["INV-005"]


def test_conflicting_plant_attribution_is_not_joined() -> None:
    """An equipment identifier at a different plant is not related evidence."""
    asset = (
        data_access.get_assets()
        .loc[data_access.get_assets()["Equipment ID"].eq("INV-006")]
        .iloc[0]
    )
    evidence = build_asset_evidence(
        asset,
        incidents=pd.DataFrame(columns=data_access.get_incidents().columns),
        anomalies=pd.DataFrame(columns=data_access.get_anomalies().columns),
        maintenance=data_access.get_maintenance_priorities(),
    )

    assert evidence.maintenance.empty


def test_empty_asset_sources_are_safe() -> None:
    """The priority derivation must preserve a usable empty schema."""
    empty = build_equipment_priority(pd.DataFrame())

    assert empty.empty
    assert "Equipment ID" in empty.columns


def test_asset_page_avoids_unsupported_visual_patterns() -> None:
    """Phase E must avoid new scores, raw metrics, emoji, and local colors."""
    source = inspect.getsource(assets)

    assert "st.metric(" not in source
    assert "st.success(" not in source
    assert "px.pie(" not in source
    assert "Risk Score" not in source
    assert "#" not in source
    assert not any(ord(character) > 0xFFFF for character in source)
