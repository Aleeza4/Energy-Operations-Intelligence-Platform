"""Reusable enterprise KPI cards for EOIP dashboards."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from html import escape
from numbers import Number
from typing import Literal

import streamlit as st

from eoip.app.icons import get_icon_svg

DeltaSemantic = Literal["positive", "negative", "warning", "neutral"]
DeltaDirection = Literal["up", "down", "flat"]

_SEMANTIC_CLASSES = frozenset(("positive", "negative", "warning", "neutral"))

_METRIC_ICON_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("alarm", "incident", "anomal"), "triangle-alert"),
    (("downtime", "mttr", "mtta", "duration", "age"), "clock"),
    (("revenue", "cost", "financial", "value", "saving"), "banknote"),
    (("availability", "performance ratio", "capacity factor"), "gauge"),
    (("plant", "asset", "equipment", "work order"), "boxes"),
    (("forecast", "mape", "mae", "rmse"), "trending-up"),
    (("quality", "completeness", "validity", "freshness"), "shield-check"),
    (("maintenance", "failure", "risk"), "wrench"),
    (("energy", "generation", "power"), "zap"),
)


@dataclass(frozen=True, slots=True)
class MetricCard:
    """Configuration for a presentation-only EOIP KPI card."""

    label: str
    value: str | Number | None
    delta: str | None = None
    delta_semantic: DeltaSemantic | str = "neutral"
    delta_context: str | None = "vs previous period"
    icon: str | None = None
    help_text: str | None = None
    subtitle: str | None = None
    status: str | None = None
    compact: bool = False

    def __post_init__(self) -> None:
        """Validate required KPI content without changing business values."""
        if not self.label.strip():
            raise ValueError("Metric label must not be empty.")
        if isinstance(self.value, str) and not self.value.strip():
            raise ValueError("Metric value must not be empty.")


def normalize_metric_value(value: str | Number | None) -> str:
    """Return a professional display value for valid or missing KPI data."""
    if value is None:
        return "—"
    if isinstance(value, float) and value != value:
        return "—"
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}"
    normalized = str(value).strip()
    if normalized.casefold() in {"none", "nan", "undefined"}:
        return "—"
    return normalized or "—"


def resolve_delta_semantic(value: str) -> DeltaSemantic:
    """Resolve invalid or unknown semantic values safely to neutral."""
    normalized = value.strip().casefold()
    if normalized in _SEMANTIC_CLASSES:
        return normalized  # type: ignore[return-value]
    return "neutral"


def infer_delta_direction(delta: str | None) -> DeltaDirection:
    """Infer visual direction only; business meaning remains explicitly configured."""
    if delta is None:
        return "flat"
    normalized = delta.strip()
    if normalized.startswith(("+", "↑")):
        return "up"
    if normalized.startswith(("-", "−", "↓")):
        return "down"
    return "flat"


def get_metric_icon(label: str) -> str:
    """Return a restrained semantic Lucide icon for a KPI label."""
    normalized = label.casefold()
    for terms, icon in _METRIC_ICON_RULES:
        if any(term in normalized for term in terms):
            return icon
    return "activity"


def metric_card_markup(metric: MetricCard) -> str:
    """Build escaped KPI markup for Streamlit rendering and focused tests."""
    icon_name = metric.icon or get_metric_icon(metric.label)
    compact_class = " eoip-kpi-card-compact" if metric.compact else ""
    label = escape(metric.label.strip())
    value = escape(normalize_metric_value(metric.value))
    help_markup = ""
    if metric.help_text is not None and metric.help_text.strip():
        help_text = escape(metric.help_text.strip(), quote=True)
        help_markup = (
            '<span class="eoip-kpi-help" role="img" '
            f'aria-label="More information: {help_text}" title="{help_text}">'
            f'{get_icon_svg("info", size=14)}</span>'
        )

    delta_markup = ""
    if metric.delta is not None and metric.delta.strip():
        direction = infer_delta_direction(metric.delta)
        semantic = resolve_delta_semantic(str(metric.delta_semantic))
        context = ""
        if metric.delta_context is not None and metric.delta_context.strip():
            context = (
                '<span class="eoip-kpi-context">'
                f"{escape(metric.delta_context.strip())}</span>"
            )
        delta_markup = (
            f'<div class="eoip-kpi-delta eoip-kpi-delta-{semantic}">'
            '<span class="eoip-kpi-delta-icon">'
            f"{get_icon_svg(direction, size=14)}</span>"
            f'<span>{escape(metric.delta.strip().lstrip("+−-↑↓"))}</span>'
            f"{context}</div>"
        )

    subtitle_markup = ""
    if metric.subtitle is not None and metric.subtitle.strip():
        subtitle_markup = (
            f'<div class="eoip-kpi-subtitle">{escape(metric.subtitle.strip())}</div>'
        )

    status_markup = ""
    if metric.status is not None and metric.status.strip():
        status_markup = (
            '<div class="eoip-kpi-status">'
            f'{get_icon_svg("info", size=14)}<span>'
            f"{escape(metric.status.strip())}</span>"
            "</div>"
        )

    return (
        f'<article class="eoip-kpi-card{compact_class}">'
        '<div class="eoip-kpi-header">'
        f'<span class="eoip-kpi-icon">{get_icon_svg(icon_name, size=17)}</span>'
        f'<span class="eoip-kpi-label">{label}</span>{help_markup}</div>'
        f'<div class="eoip-kpi-value">{value}</div>'
        f"{delta_markup}{subtitle_markup}{status_markup}</article>"
    )


def render_metric_card(metric: MetricCard) -> None:
    """Render one EOIP KPI card."""
    st.markdown(metric_card_markup(metric), unsafe_allow_html=True)


def render_metric_row(metrics: Sequence[MetricCard]) -> None:
    """Render a responsive, aligned KPI grid."""
    if not metrics:
        raise ValueError("At least one metric is required.")
    cards = "".join(metric_card_markup(metric) for metric in metrics)
    st.markdown(
        f'<div class="eoip-kpi-grid">{cards}</div>',
        unsafe_allow_html=True,
    )
