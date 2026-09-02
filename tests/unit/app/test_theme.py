"""Tests for the centralized EOIP visual color system."""

from __future__ import annotations

import re
from pathlib import Path

import plotly.graph_objects as go

from eoip.app.components.charts import apply_eoip_chart_style
from eoip.app.theme import (
    EOIP_BACKGROUND,
    EOIP_CHART_SEQUENCE,
    EOIP_DANGER,
    EOIP_GRID,
    EOIP_PRIMARY,
    EOIP_SUCCESS,
    EOIP_SURFACE,
    EOIP_TEXT_MUTED,
    EOIP_WARNING,
    get_alarm_severity_color,
    get_risk_color,
    get_status_color,
)

HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DASHBOARD_DIR = PROJECT_ROOT / "src" / "eoip" / "app" / "dashboards"


def test_required_theme_tokens_are_valid_hex_colors() -> None:
    colors = (
        EOIP_PRIMARY,
        EOIP_BACKGROUND,
        EOIP_SURFACE,
        EOIP_GRID,
        EOIP_SUCCESS,
        EOIP_WARNING,
        EOIP_DANGER,
    )
    assert all(HEX_COLOR.fullmatch(color) for color in colors)


def test_semantic_colors_are_distinct_from_each_other_and_primary() -> None:
    semantic_colors = {EOIP_SUCCESS, EOIP_WARNING, EOIP_DANGER}
    assert len(semantic_colors) == 3
    assert EOIP_PRIMARY not in semantic_colors


def test_chart_sequence_is_unique_and_restrained() -> None:
    assert EOIP_CHART_SEQUENCE
    assert len(EOIP_CHART_SEQUENCE) == len(set(EOIP_CHART_SEQUENCE))
    assert EOIP_CHART_SEQUENCE[0] == EOIP_PRIMARY


def test_domain_status_mappings_and_neutral_fallback() -> None:
    assert get_status_color("Healthy") == EOIP_SUCCESS
    assert get_status_color("Watch") == EOIP_WARNING
    assert get_alarm_severity_color("High") == EOIP_DANGER
    assert get_risk_color("Moderate") == EOIP_WARNING
    assert get_status_color("unmapped state") == EOIP_TEXT_MUTED


def test_plotly_theme_applies_colorway_and_neutral_surfaces() -> None:
    figure = apply_eoip_chart_style(go.Figure())
    assert tuple(figure.layout.colorway) == EOIP_CHART_SEQUENCE
    assert figure.layout.paper_bgcolor == EOIP_SURFACE
    assert figure.layout.plot_bgcolor == EOIP_SURFACE
    assert figure.layout.yaxis.gridcolor == EOIP_GRID


def test_dashboards_do_not_embed_raw_ui_colors_or_plotly_defaults() -> None:
    forbidden = ("plotly.colors.qualitative", "px.colors.qualitative")
    for path in DASHBOARD_DIR.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert not re.search(r"#[0-9A-Fa-f]{3,8}", source), path.name
        assert not any(value in source for value in forbidden), path.name
