"""Shared Plotly presentation helpers for EOIP dashboards."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from eoip.app.components.common import render_empty_state
from eoip.app.theme import (
    EOIP_AXIS,
    EOIP_CHART_SEQUENCE,
    EOIP_FONT_FAMILY,
    EOIP_GRID,
    EOIP_PLOTLY_TEMPLATE,
    EOIP_PRIMARY,
    EOIP_PRIMARY_MUTED,
    EOIP_PRIMARY_SOFT_FILL,
    EOIP_SURFACE,
    EOIP_TEXT_PRIMARY,
    EOIP_TEXT_SECONDARY,
)

EOIP_COLOR_SEQUENCE = EOIP_CHART_SEQUENCE
EOIP_CHART_HEIGHT_COMPACT = 300
EOIP_CHART_HEIGHT_STANDARD = 350
EOIP_CHART_HEIGHT_LARGE = 430
MISSING_CHART_TITLES = frozenset({"", "none", "null", "undefined"})


def _normalized_chart_title(value: object) -> str | None:
    """Return a displayable chart title, excluding missing-value sentinels."""
    if value is None:
        return None

    title = str(value).strip()
    if title.casefold() in MISSING_CHART_TITLES:
        return None
    return title


def eoip_actual_expected_colors(
    actual_label: str,
    expected_label: str,
) -> dict[str, str]:
    """Return related brand shades for an actual/expected comparison."""
    return {actual_label: EOIP_PRIMARY, expected_label: EOIP_PRIMARY_MUTED}


def eoip_forecast_style() -> dict[str, Any]:
    """Return fresh, accessible forecast line and confidence-band styling."""
    return {
        "actual_line": {"color": EOIP_PRIMARY, "width": 2.5},
        "forecast_line": {
            "color": EOIP_PRIMARY_MUTED,
            "width": 2.25,
            "dash": "dash",
        },
        "confidence_fill": EOIP_PRIMARY_SOFT_FILL,
    }


def _style_donut_trace(trace: go.Pie) -> None:
    """Keep donut categories legible through legend and hover, not wedge text."""
    trace.update(
        textinfo="none",
        textposition="none",
        sort=False,
        direction="clockwise",
        marker={"line": {"color": EOIP_SURFACE, "width": 2}},
        hovertemplate=(
            "%{label}<br><b>%{value:,.0f}</b> (%{percent:.1%})<extra></extra>"
        ),
    )


def _style_bar_trace(trace: go.Bar) -> None:
    """Apply restrained bars and concise, consistent hover output."""
    hovertemplate = "%{fullData.name}<br>%{x}<br><b>%{y:,.2f}</b><extra></extra>"
    if trace.orientation == "h":
        hovertemplate = "%{fullData.name}<br>%{y}<br><b>%{x:,.2f}</b><extra></extra>"
    trace.update(marker_line_width=0, hovertemplate=hovertemplate)


def _style_scatter_trace(trace: go.Scatter, *, time_series: bool) -> None:
    """Standardize line weight, reference styles, and dense-series markers."""
    name = str(trace.name or "")
    if "lines" in str(trace.mode):
        trace.line.width = trace.line.width or 2.25
        if any(term in name.casefold() for term in ("expected", "forecast")):
            trace.line.dash = "dash"
        elif any(term in name.casefold() for term in ("target", "baseline")):
            trace.line.dash = "dot"
        elif "threshold" in name.casefold():
            trace.line.dash = "dash"

    point_count = len(trace.x) if trace.x is not None else 0
    if point_count > 24 and trace.mode == "lines+markers":
        trace.mode = "lines"

    x_value = "%{x|%d %b %Y, %H:%M}" if time_series else "%{x}"
    trace.hovertemplate = (
        f"%{{fullData.name}}<br>{x_value}<br><b>%{{y:,.2f}}</b><extra></extra>"
    )


def style_eoip_donut(figure: go.Figure) -> go.Figure:
    """Apply the shared EOIP donut readability policy."""
    for trace in figure.data:
        if isinstance(trace, go.Pie):
            _style_donut_trace(trace)
    figure.update_layout(
        height=EOIP_CHART_HEIGHT_COMPACT,
        legend={"orientation": "v", "x": 1.02, "y": 0.5, "yanchor": "middle"},
        margin={"l": 12, "r": 12, "t": 20, "b": 20},
    )
    return figure


def plotly_chart_config() -> dict[str, Any]:
    """Return a fresh, deterministic Plotly toolbar configuration."""
    return {
        "displaylogo": False,
        "responsive": True,
        "scrollZoom": True,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        "toImageButtonOptions": {
            "format": "png",
            "filename": "eoip-chart",
            "scale": 2,
        },
    }


def apply_eoip_chart_style(
    figure: go.Figure,
    *,
    time_series: bool = False,
) -> go.Figure:
    """Apply consistent EOIP layout and interaction defaults to a figure."""
    chart_title = _normalized_chart_title(figure.layout.title.text)
    figure.update_layout(
        template=EOIP_PLOTLY_TEMPLATE,
        colorway=list(EOIP_CHART_SEQUENCE),
        hovermode="x unified" if time_series else "closest",
        height=EOIP_CHART_HEIGHT_STANDARD,
        legend={
            "title_text": "",
            "orientation": "h",
            "y": 1.08,
            "x": 0,
            "font": {"color": EOIP_TEXT_SECONDARY},
        },
        margin={"l": 36, "r": 20, "t": 42, "b": 36},
        paper_bgcolor=EOIP_SURFACE,
        plot_bgcolor=EOIP_SURFACE,
        font={
            "family": EOIP_FONT_FAMILY,
            "size": 12,
            "color": EOIP_TEXT_PRIMARY,
        },
    )
    if chart_title is None:
        figure.layout.title = None
    else:
        figure.update_layout(
            title={
                "text": chart_title,
                "font": {"size": 15, "color": EOIP_TEXT_PRIMARY},
            }
        )
    figure.update_xaxes(showgrid=False, linecolor=EOIP_AXIS, automargin=True)
    figure.update_yaxes(
        gridcolor=EOIP_GRID,
        linecolor=EOIP_AXIS,
        automargin=True,
        separatethousands=True,
    )
    figure.update_xaxes(
        tickfont={"size": 11, "color": EOIP_TEXT_SECONDARY},
        title_font={"size": 12, "color": EOIP_TEXT_SECONDARY},
    )
    figure.update_yaxes(
        tickfont={"size": 11, "color": EOIP_TEXT_SECONDARY},
        title_font={"size": 12, "color": EOIP_TEXT_SECONDARY},
    )

    trace_count = len(figure.data)
    has_pie = any(isinstance(trace, go.Pie) for trace in figure.data)
    for trace in figure.data:
        if isinstance(trace, go.Pie):
            _style_donut_trace(trace)
        elif isinstance(trace, go.Bar):
            _style_bar_trace(trace)
        elif isinstance(trace, go.Scatter):
            _style_scatter_trace(trace, time_series=time_series)

    if trace_count == 1 and not has_pie:
        figure.update_layout(showlegend=False)
    if any(isinstance(trace, go.Bar) for trace in figure.data):
        if any(
            isinstance(trace, go.Bar) and trace.orientation == "h"
            for trace in figure.data
        ):
            figure.update_xaxes(rangemode="tozero")
        else:
            figure.update_yaxes(rangemode="tozero")
        figure.update_layout(bargap=0.28)
    if has_pie:
        style_eoip_donut(figure)

    if time_series:
        figure.update_xaxes(
            type="date",
            tickformat="%d %b\n%Y",
            hoverformat="%d %b %Y %H:%M",
            rangeslider={"visible": False},
        )

    return figure


def render_plotly_chart(
    figure: go.Figure,
    *,
    data: pd.DataFrame | None = None,
    time_series: bool = False,
    key: str | None = None,
    config: Mapping[str, Any] | None = None,
) -> bool:
    """Render a styled responsive chart, or an empty state when data has no rows."""
    if data is not None and data.empty:
        render_empty_state(
            title="No chart data",
            message="No records match the active filters for this visualization.",
        )
        return False

    chart_config = plotly_chart_config()
    if config is not None:
        chart_config.update(config)

    st.plotly_chart(
        apply_eoip_chart_style(figure, time_series=time_series),
        width="stretch",
        config=chart_config,
        key=key,
    )
    return True
