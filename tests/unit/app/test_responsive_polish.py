"""Structural regression tests for centralized responsive UI polish."""

from __future__ import annotations

from pathlib import Path

from eoip.app.styles import EOIP_CSS

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DASHBOARD_DIR = PROJECT_ROOT / "src" / "eoip" / "app" / "dashboards"


def _dashboard_source() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(DASHBOARD_DIR.glob("*.py"))
    )


def test_shared_css_covers_compact_desktop_tablet_and_mobile() -> None:
    assert "@media (max-width: 1200px)" in EOIP_CSS
    assert "@media (max-width: 900px)" in EOIP_CSS
    assert "@media (max-width: 600px)" in EOIP_CSS
    assert "grid-template-columns: 1fr" in EOIP_CSS
    assert "flex: 1 1 12rem" in EOIP_CSS


def test_shared_css_handles_dense_content_and_motion_preferences() -> None:
    assert "overscroll-behavior-inline: contain" in EOIP_CSS
    assert '[data-testid="stPlotlyChart"] .modebar' in EOIP_CSS
    assert "@media (prefers-reduced-motion: reduce)" in EOIP_CSS


def test_shared_css_removes_streamlit_chrome_without_hiding_sidebar_controls() -> None:
    assert '[data-testid="stHeader"]' in EOIP_CSS
    assert '[data-testid="stToolbar"]' in EOIP_CSS
    assert '[data-testid="stAppDeployButton"]' in EOIP_CSS
    assert '[data-testid="stMainMenu"]' in EOIP_CSS
    assert '[data-testid="stStatusWidget"]' in EOIP_CSS
    assert '[data-testid="stToolbarActions"]' in EOIP_CSS
    assert '[data-testid="stDecoration"]' in EOIP_CSS
    assert (
        '[data-testid="stHeader"],\n'
        '[data-testid="stToolbar"] {\n'
        "    background: transparent;\n}"
    ) in EOIP_CSS
    assert '[data-testid="stHeader"] {\n    height: 0' not in EOIP_CSS
    assert '[data-testid="stToolbar"] {\n    display: none;\n}' not in EOIP_CSS
    assert '[data-testid="stSidebarCollapseButton"]' in EOIP_CSS
    assert '[data-testid="stExpandSidebarButton"]' in EOIP_CSS
    assert "visibility: visible" in EOIP_CSS
    assert "pointer-events: auto" in EOIP_CSS


def test_collapsed_sidebar_geometry_is_left_to_streamlit() -> None:
    collapsed_sidebar = '[data-testid="stSidebar"][aria-expanded="false"]'

    assert collapsed_sidebar not in EOIP_CSS
    assert '+ [data-testid="stMain"]' not in EOIP_CSS
    assert "transform: translateX(0) !important" not in EOIP_CSS
    assert "width: 4.5rem !important" not in EOIP_CSS


def test_sidebar_brand_has_clear_subtitle_spacing() -> None:
    assert "margin-bottom: var(--eoip-space-1)" in EOIP_CSS


def test_dashboards_do_not_scatter_responsive_css_or_spacer_hacks() -> None:
    source = _dashboard_source()
    assert "@media" not in source
    assert 'st.write("")' not in source
    assert "st.write('')" not in source
    assert "<br>" not in source
    assert "<br/>" not in source


def test_dashboards_do_not_use_deprecated_container_width_argument() -> None:
    assert "use_container_width" not in _dashboard_source()
