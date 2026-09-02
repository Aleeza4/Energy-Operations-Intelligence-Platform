"""Centralized visual design tokens and semantic color helpers for EOIP."""

from __future__ import annotations

from typing import Final

import plotly.graph_objects as go

EOIP_FONT_FAMILY: Final = (
    "Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
)
EOIP_FONT_SIZE_PAGE_TITLE: Final = "1.875rem"
EOIP_FONT_SIZE_SECTION_TITLE: Final = "1.1875rem"
EOIP_FONT_SIZE_CARD_TITLE: Final = "0.9375rem"
EOIP_FONT_SIZE_BODY: Final = "0.875rem"
EOIP_FONT_SIZE_LABEL: Final = "0.8125rem"
EOIP_FONT_SIZE_CAPTION: Final = "0.75rem"
EOIP_FONT_SIZE_KPI_VALUE: Final = "1.875rem"
EOIP_FONT_WEIGHT_REGULAR: Final = 400
EOIP_FONT_WEIGHT_MEDIUM: Final = 500
EOIP_FONT_WEIGHT_SEMIBOLD: Final = 600
EOIP_FONT_WEIGHT_BOLD: Final = 700
EOIP_LINE_HEIGHT_TIGHT: Final = 1.2
EOIP_LINE_HEIGHT_NORMAL: Final = 1.45
EOIP_LINE_HEIGHT_RELAXED: Final = 1.55
EOIP_SPACING_SCALE: Final[tuple[int, ...]] = (4, 8, 12, 16, 24, 32)

EOIP_PRIMARY: Final = "#0F5C5E"
EOIP_PRIMARY_STRONG: Final = "#0A4547"
EOIP_PRIMARY_SOFT: Final = "#E7F1F1"
EOIP_PRIMARY_MUTED: Final = "#6F9A9B"
EOIP_PRIMARY_SOFT_FILL: Final = "rgba(15,92,94,0.12)"
EOIP_SECONDARY: Final = "#3F6F8F"
EOIP_SECONDARY_SOFT_FILL: Final = "rgba(63,111,143,0.16)"

EOIP_TEXT_PRIMARY: Final = "#17212B"
EOIP_TEXT_SECONDARY: Final = "#52606D"
EOIP_TEXT_MUTED: Final = "#7B8794"
EOIP_BACKGROUND: Final = "#F7F9FA"
EOIP_SURFACE: Final = "#FFFFFF"
EOIP_SURFACE_SUBTLE: Final = "#F1F4F5"
EOIP_BORDER: Final = "#D9E0E3"
EOIP_BORDER_SUBTLE: Final = "#E8ECEE"
EOIP_GRID: Final = "#E8ECEE"
EOIP_AXIS: Final = "#66737F"

EOIP_SUCCESS: Final = "#2E7D5B"
EOIP_SUCCESS_SOFT: Final = "#E8F3ED"
EOIP_WARNING: Final = "#B7791F"
EOIP_WARNING_SOFT: Final = "#FBF2DF"
EOIP_DANGER: Final = "#B54747"
EOIP_DANGER_STRONG: Final = "#8F3434"
EOIP_DANGER_SOFT: Final = "#F8EAEA"
EOIP_INFO: Final = EOIP_SECONDARY
EOIP_INFO_SOFT: Final = "#EAF0F4"

EOIP_CHART_SEQUENCE: Final[tuple[str, ...]] = (
    EOIP_PRIMARY,
    EOIP_PRIMARY_MUTED,
    "#687A86",
    "#8B9AA3",
    "#AAB5BB",
    "#C2CACE",
)

STATUS_COLORS: Final[dict[str, str]] = {
    "healthy": EOIP_SUCCESS,
    "normal": EOIP_SUCCESS,
    "operational": EOIP_SUCCESS,
    "available": EOIP_SUCCESS,
    "resolved": EOIP_SUCCESS,
    "completed": EOIP_SUCCESS,
    "pass": EOIP_SUCCESS,
    "good": EOIP_SUCCESS,
    "watch": EOIP_WARNING,
    "warning": EOIP_WARNING,
    "degraded": EOIP_WARNING,
    "moderate": EOIP_WARNING,
    "medium": EOIP_WARNING,
    "critical": EOIP_DANGER_STRONG,
    "high": EOIP_DANGER,
    "high risk": EOIP_DANGER,
    "failed": EOIP_DANGER,
    "failure": EOIP_DANGER,
    "error": EOIP_DANGER,
    "low": EOIP_TEXT_MUTED,
    "unknown": EOIP_TEXT_MUTED,
    "offline": EOIP_TEXT_MUTED,
    "no data": EOIP_TEXT_MUTED,
}

RISK_COLORS: Final[dict[str, str]] = {
    "Low": EOIP_SUCCESS,
    "Healthy": EOIP_SUCCESS,
    "Moderate": EOIP_WARNING,
    "Watch": EOIP_WARNING,
    "Degraded": EOIP_WARNING,
    "High": EOIP_DANGER,
    "High Risk": EOIP_DANGER,
    "Critical": EOIP_DANGER_STRONG,
}

SEVERITY_COLORS: Final[dict[str, str]] = {
    "Low": EOIP_TEXT_MUTED,
    "Medium": EOIP_WARNING,
    "High": EOIP_DANGER,
    "Critical": EOIP_DANGER_STRONG,
}


def _normalized(value: object) -> str:
    return str(value).strip().casefold()


def get_status_color(status: object) -> str:
    """Resolve a domain status to its semantic color or neutral fallback."""
    return STATUS_COLORS.get(_normalized(status), EOIP_TEXT_MUTED)


def get_risk_color(risk: object) -> str:
    """Resolve an equipment risk/health band to a semantic color."""
    return get_status_color(risk)


def get_alarm_severity_color(severity: object) -> str:
    """Resolve alarm severity, retaining a darker critical distinction."""
    return get_status_color(severity)


def get_quality_color(status: object) -> str:
    """Resolve quality status using the shared semantic vocabulary."""
    return get_status_color(status)


EOIP_PLOTLY_TEMPLATE: Final = go.layout.Template(
    layout=go.Layout(
        colorway=list(EOIP_CHART_SEQUENCE),
        paper_bgcolor=EOIP_SURFACE,
        plot_bgcolor=EOIP_SURFACE,
        font={
            "family": EOIP_FONT_FAMILY,
            "size": 12,
            "color": EOIP_TEXT_PRIMARY,
        },
        xaxis={
            "gridcolor": EOIP_GRID,
            "linecolor": EOIP_AXIS,
            "zerolinecolor": EOIP_GRID,
        },
        yaxis={
            "gridcolor": EOIP_GRID,
            "linecolor": EOIP_AXIS,
            "zerolinecolor": EOIP_GRID,
        },
        legend={
            "bgcolor": "rgba(255,255,255,0)",
            "font": {"color": EOIP_TEXT_SECONDARY},
        },
        hoverlabel={
            "bgcolor": EOIP_SURFACE,
            "bordercolor": EOIP_BORDER,
            "font": {"color": EOIP_TEXT_PRIMARY},
        },
    )
)


def css_theme_variables() -> str:
    """Return CSS custom properties generated from the Python token source."""
    return f"""
:root {{
    --eoip-font-family: {EOIP_FONT_FAMILY};
    --eoip-font-size-page-title: {EOIP_FONT_SIZE_PAGE_TITLE};
    --eoip-font-size-section-title: {EOIP_FONT_SIZE_SECTION_TITLE};
    --eoip-font-size-card-title: {EOIP_FONT_SIZE_CARD_TITLE};
    --eoip-font-size-body: {EOIP_FONT_SIZE_BODY};
    --eoip-font-size-label: {EOIP_FONT_SIZE_LABEL};
    --eoip-font-size-caption: {EOIP_FONT_SIZE_CAPTION};
    --eoip-font-size-kpi-value: {EOIP_FONT_SIZE_KPI_VALUE};
    --eoip-font-weight-regular: {EOIP_FONT_WEIGHT_REGULAR};
    --eoip-font-weight-medium: {EOIP_FONT_WEIGHT_MEDIUM};
    --eoip-font-weight-semibold: {EOIP_FONT_WEIGHT_SEMIBOLD};
    --eoip-font-weight-bold: {EOIP_FONT_WEIGHT_BOLD};
    --eoip-line-height-tight: {EOIP_LINE_HEIGHT_TIGHT};
    --eoip-line-height-normal: {EOIP_LINE_HEIGHT_NORMAL};
    --eoip-line-height-relaxed: {EOIP_LINE_HEIGHT_RELAXED};
    --eoip-space-1: {EOIP_SPACING_SCALE[0]}px;
    --eoip-space-2: {EOIP_SPACING_SCALE[1]}px;
    --eoip-space-3: {EOIP_SPACING_SCALE[2]}px;
    --eoip-space-4: {EOIP_SPACING_SCALE[3]}px;
    --eoip-space-6: {EOIP_SPACING_SCALE[4]}px;
    --eoip-space-8: {EOIP_SPACING_SCALE[5]}px;
    --eoip-bg: {EOIP_BACKGROUND};
    --eoip-surface: {EOIP_SURFACE};
    --eoip-surface-soft: {EOIP_SURFACE_SUBTLE};
    --eoip-text: {EOIP_TEXT_PRIMARY};
    --eoip-text-secondary: {EOIP_TEXT_SECONDARY};
    --eoip-muted: {EOIP_TEXT_MUTED};
    --eoip-border: {EOIP_BORDER};
    --eoip-border-subtle: {EOIP_BORDER_SUBTLE};
    --eoip-primary: {EOIP_PRIMARY};
    --eoip-primary-dark: {EOIP_PRIMARY_STRONG};
    --eoip-primary-soft: {EOIP_PRIMARY_SOFT};
    --eoip-success: {EOIP_SUCCESS};
    --eoip-success-soft: {EOIP_SUCCESS_SOFT};
    --eoip-warning: {EOIP_WARNING};
    --eoip-warning-soft: {EOIP_WARNING_SOFT};
    --eoip-danger: {EOIP_DANGER};
    --eoip-danger-soft: {EOIP_DANGER_SOFT};
    --eoip-info: {EOIP_INFO};
    --eoip-info-soft: {EOIP_INFO_SOFT};
}}
""".strip()
