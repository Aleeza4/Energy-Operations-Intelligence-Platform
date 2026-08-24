"""Tests for shared EOIP Plotly configuration."""

from __future__ import annotations

import plotly.graph_objects as go

from eoip.app.components.charts import apply_eoip_chart_style, plotly_chart_config


def test_plotly_config_is_responsive_and_hides_logo() -> None:
    config = plotly_chart_config()

    assert config["responsive"] is True
    assert config["displaylogo"] is False
    assert "select2d" in config["modeBarButtonsToRemove"]


def test_plotly_config_returns_fresh_mapping() -> None:
    first = plotly_chart_config()
    second = plotly_chart_config()

    first["responsive"] = False

    assert second["responsive"] is True


def test_time_series_style_uses_unified_hover() -> None:
    figure = apply_eoip_chart_style(go.Figure(), time_series=True)

    assert figure.layout.hovermode == "x unified"
    assert figure.layout.xaxis.type == "date"
