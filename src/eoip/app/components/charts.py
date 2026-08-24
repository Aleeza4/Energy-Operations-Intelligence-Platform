"""Shared Plotly presentation helpers for EOIP dashboards."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from eoip.app.components.common import render_empty_state

EOIP_COLOR_SEQUENCE: tuple[str, ...] = (
    "#f5b400",
    "#2563eb",
    "#16803c",
    "#c0392b",
    "#7c3aed",
    "#64748b",
)


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
    figure.update_layout(
        colorway=list(EOIP_COLOR_SEQUENCE),
        hovermode="x unified" if time_series else "closest",
        legend={"title_text": "", "orientation": "h", "y": 1.08},
        margin={"l": 36, "r": 20, "t": 42, "b": 36},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, Segoe UI, Arial, sans-serif", "color": "#1f2937"},
    )
    figure.update_xaxes(showgrid=False, automargin=True)
    figure.update_yaxes(gridcolor="rgba(107,114,128,0.15)", automargin=True)

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
