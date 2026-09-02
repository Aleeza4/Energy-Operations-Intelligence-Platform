"""Tests for shared EOIP Plotly configuration."""

from __future__ import annotations

import plotly.graph_objects as go
import pytest

from eoip.app.components.charts import (
    EOIP_CHART_HEIGHT_COMPACT,
    EOIP_CHART_HEIGHT_STANDARD,
    apply_eoip_chart_style,
    eoip_actual_expected_colors,
    eoip_forecast_style,
    plotly_chart_config,
)
from eoip.app.theme import (
    EOIP_GRID,
    EOIP_PRIMARY,
    EOIP_PRIMARY_MUTED,
    EOIP_PRIMARY_SOFT_FILL,
    EOIP_SURFACE,
)


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


def test_chart_layout_uses_centralized_surface_grid_font_and_height() -> None:
    figure = apply_eoip_chart_style(go.Figure())
    assert figure.layout.paper_bgcolor == EOIP_SURFACE
    assert figure.layout.plot_bgcolor == EOIP_SURFACE
    assert figure.layout.yaxis.gridcolor == EOIP_GRID
    assert figure.layout.height == EOIP_CHART_HEIGHT_STANDARD
    assert "Inter" in figure.layout.font.family


@pytest.mark.parametrize("missing_title", (None, "", "None", "null", "undefined"))
def test_missing_chart_title_is_omitted_cleanly(missing_title: str | None) -> None:
    figure = go.Figure(go.Bar(x=["A"], y=[1]))
    if missing_title is not None:
        figure.update_layout(title=missing_title)

    styled = apply_eoip_chart_style(figure)

    assert styled.layout.title.text is None
    assert "title" not in styled.to_plotly_json()["layout"]


def test_real_chart_title_is_preserved_and_styled() -> None:
    figure = apply_eoip_chart_style(
        go.Figure(go.Bar(x=["A"], y=[1])).update_layout(title="Plant output")
    )

    assert figure.layout.title.text == "Plant output"
    assert figure.layout.title.font.size == 15


def test_actual_expected_colors_use_related_brand_shades() -> None:
    colors = eoip_actual_expected_colors("Actual", "Expected")
    assert colors == {"Actual": EOIP_PRIMARY, "Expected": EOIP_PRIMARY_MUTED}
    assert len(set(colors.values())) == 2


def test_forecast_style_uses_muted_dashed_brand_line_and_soft_fill() -> None:
    style = eoip_forecast_style()
    assert style["actual_line"]["color"] == EOIP_PRIMARY
    assert style["forecast_line"]["color"] == EOIP_PRIMARY_MUTED
    assert style["forecast_line"]["dash"] == "dash"
    assert style["confidence_fill"] == EOIP_PRIMARY_SOFT_FILL


def test_donut_regression_hides_overlapping_wedge_percentages() -> None:
    figure = go.Figure(
        go.Pie(labels=["A", "B", "C", "D"], values=[70.1, 17.5, 8, 4.4], hole=0.55)
    )
    styled = apply_eoip_chart_style(figure)
    trace = styled.data[0]
    assert trace.textinfo == "none"
    assert trace.textposition == "none"
    assert "%{percent:.1%}" in trace.hovertemplate
    assert styled.layout.height == EOIP_CHART_HEIGHT_COMPACT


def test_single_series_bar_hides_redundant_legend_and_starts_at_zero() -> None:
    figure = go.Figure(go.Bar(x=["A", "B"], y=[12, 18], name="Generation"))
    styled = apply_eoip_chart_style(figure)
    assert styled.layout.showlegend is False
    assert styled.layout.yaxis.rangemode == "tozero"
    assert styled.data[0].marker.line.width == 0


def test_dense_time_series_removes_markers_and_has_clean_hover() -> None:
    figure = go.Figure(
        go.Scatter(
            x=list(range(30)),
            y=list(range(30)),
            mode="lines+markers",
            name="Actual",
        )
    )
    styled = apply_eoip_chart_style(figure, time_series=True)
    trace = styled.data[0]
    assert trace.mode == "lines"
    assert "<extra></extra>" in trace.hovertemplate
    assert ".2f" in trace.hovertemplate
