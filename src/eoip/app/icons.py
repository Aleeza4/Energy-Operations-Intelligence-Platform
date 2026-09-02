"""Local Lucide SVG registry and rendering helpers for EOIP."""

from __future__ import annotations

from html import escape
from urllib.parse import quote

LUCIDE_STROKE_WIDTH = 1.9

# Path markup is sourced from Lucide's 24px outline icon set. Application code
# refers to semantic EOIP names through ICON_ALIASES instead of embedding SVG.
ICON_PATHS: dict[str, str] = {
    "arrow-down": '<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>',
    "arrow-up": '<path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>',
    "banknote": (
        '<rect width="20" height="12" x="2" y="6" rx="2"/>'
        '<circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/>'
    ),
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "boxes": (
        '<path d="M2.97 12.92 7 15.25l4-2.33"/>'
        '<path d="m7 8.66-4.03 2.33L7 13.32l4-2.33L7 8.66Z"/>'
        '<path d="M7 13.32v4.66"/><path d="m13 5.66 4 2.33 4-2.33"/>'
        '<path d="m17 1.66-4 2.33L17 6.32l4-2.33-4-2.33Z"/>'
        '<path d="M17 6.32v4.66"/><path d="m13 18.66 4 2.33 4-2.33"/>'
        '<path d="m17 14.66-4 2.33L17 19.32l4-2.33-4-2.33Z"/>'
        '<path d="M17 19.32v4.66"/>'
    ),
    "chart-line": ('<path d="M3 3v18h18"/>' '<path d="m19 9-5 5-4-4-3 3"/>'),
    "clock": (
        '<circle cx="12" cy="12" r="10"/>' '<polyline points="12 6 12 12 16 14"/>'
    ),
    "circle-check": (
        '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>' '<path d="m9 11 3 3L22 4"/>'
    ),
    "circle-x": (
        '<circle cx="12" cy="12" r="10"/>' '<path d="m15 9-6 6"/><path d="m9 9 6 6"/>'
    ),
    "info": (
        '<circle cx="12" cy="12" r="10"/>' '<path d="M12 16v-4"/><path d="M12 8h.01"/>'
    ),
    "gauge": ('<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>'),
    "layout-dashboard": (
        '<rect width="7" height="9" x="3" y="3" rx="1"/>'
        '<rect width="7" height="5" x="14" y="3" rx="1"/>'
        '<rect width="7" height="9" x="14" y="12" rx="1"/>'
        '<rect width="7" height="5" x="3" y="16" rx="1"/>'
    ),
    "lightbulb": (
        '<path d="M9 18h6"/><path d="M10 22h4"/>'
        '<path d="M15.09 14c.18-.69.66-1.24 1.16-1.75A6 6 0 1 0 '
        '7.75 12.25c.48.49.97 1.05 1.16 1.75"/>'
    ),
    "minus": '<path d="M5 12h14"/>',
    "scan-search": (
        '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/>'
        '<path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/>'
        '<circle cx="11" cy="11" r="3"/><path d="m16 16-2.1-2.1"/>'
    ),
    "sliders-horizontal": (
        '<line x1="21" x2="14" y1="4" y2="4"/>'
        '<line x1="10" x2="3" y1="4" y2="4"/>'
        '<line x1="21" x2="12" y1="12" y2="12"/>'
        '<line x1="8" x2="3" y1="12" y2="12"/>'
        '<line x1="21" x2="16" y1="20" y2="20"/>'
        '<line x1="12" x2="3" y1="20" y2="20"/>'
        '<line x1="14" x2="14" y1="2" y2="6"/>'
        '<line x1="8" x2="8" y1="10" y2="14"/>'
        '<line x1="16" x2="16" y1="18" y2="22"/>'
    ),
    "shield-check": (
        '<path d="M20 13c0 5-3.5 7.5-8 9-4.5-1.5-8-4-8-9V5l8-3 8 3v8Z"/>'
        '<path d="m9 12 2 2 4-4"/>'
    ),
    "trending-up": '<path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>',
    "triangle-alert": (
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16'
        'a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>'
    ),
    "wrench": (
        '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77'
        "a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91"
        'a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>'
    ),
    "zap": (
        '<path d="M4 14a1 1 0 0 1-.78-1.63l9-11a.5.5 0 0 1 .87.43l-1.69 6.74'
        "A1 1 0 0 0 11.37 10H20a1 1 0 0 1 .78 1.63l-9 11a.5.5 0 0 1-.87-.43"
        'l1.69-6.74A1 1 0 0 0 11.63 14H4z"/>'
    ),
}

ICON_ALIASES: dict[str, str] = {
    "down": "arrow-down",
    "flat": "minus",
    "administration": "sliders-horizontal",
    "alarms_incidents": "triangle-alert",
    "anomaly": "scan-search",
    "assets": "boxes",
    "data_quality": "shield-check",
    "energy": "zap",
    "executive": "layout-dashboard",
    "forecast": "trending-up",
    "maintenance": "wrench",
    "operations": "activity",
    "plant_performance": "chart-line",
    "recommendations": "lightbulb",
    "success": "circle-check",
    "warning": "triangle-alert",
    "up": "arrow-up",
    "error": "circle-x",
}


def resolve_icon_name(name: str) -> str:
    """Resolve an EOIP semantic icon name to a registered Lucide icon."""
    normalized_name = name.strip()
    icon_name = ICON_ALIASES.get(normalized_name, normalized_name)
    if icon_name not in ICON_PATHS:
        raise ValueError(f"Unknown EOIP icon: {name}")
    return icon_name


def get_icon_svg(
    name: str,
    size: int = 18,
    class_name: str | None = None,
) -> str:
    """Return safe, decorative Lucide SVG markup for a registered icon."""
    if size <= 0:
        raise ValueError("Icon size must be greater than zero.")

    icon_name = resolve_icon_name(name)
    css_class = "eoip-icon-svg"
    if class_name is not None and class_name.strip():
        css_class = f"{css_class} {escape(class_name.strip(), quote=True)}"

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" '
        f'height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="{LUCIDE_STROKE_WIDTH}" '
        'stroke-linecap="round" stroke-linejoin="round" '
        f'class="{css_class}" aria-hidden="true" focusable="false">'
        f"{ICON_PATHS[icon_name]}</svg>"
    )


def get_icon_data_uri(name: str) -> str:
    """Return a compact SVG data URI suitable for masks or page icons."""
    svg = get_icon_svg(name).replace("currentColor", "#000000")
    return f"data:image/svg+xml,{quote(svg, safe='')}"
