"""Tests for the centralized EOIP typography hierarchy."""

from __future__ import annotations

from pathlib import Path

import pytest

from eoip.app.components.common import render_page_intro, render_section_header
from eoip.app.styles import EOIP_CSS
from eoip.app.theme import (
    EOIP_FONT_FAMILY,
    EOIP_FONT_SIZE_BODY,
    EOIP_FONT_SIZE_CAPTION,
    EOIP_FONT_SIZE_PAGE_TITLE,
    EOIP_FONT_SIZE_SECTION_TITLE,
    EOIP_FONT_WEIGHT_BOLD,
    EOIP_FONT_WEIGHT_REGULAR,
    EOIP_FONT_WEIGHT_SEMIBOLD,
    EOIP_LINE_HEIGHT_NORMAL,
    EOIP_SPACING_SCALE,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DASHBOARD_DIR = PROJECT_ROOT / "src" / "eoip" / "app" / "dashboards"


def test_central_typography_tokens_exist_and_form_a_clear_scale() -> None:
    assert "system-ui" in EOIP_FONT_FAMILY
    assert EOIP_FONT_SIZE_PAGE_TITLE != EOIP_FONT_SIZE_SECTION_TITLE
    assert EOIP_FONT_SIZE_SECTION_TITLE != EOIP_FONT_SIZE_BODY
    assert EOIP_FONT_SIZE_BODY != EOIP_FONT_SIZE_CAPTION
    assert EOIP_FONT_WEIGHT_REGULAR < EOIP_FONT_WEIGHT_SEMIBOLD < EOIP_FONT_WEIGHT_BOLD
    assert EOIP_LINE_HEIGHT_NORMAL > 1
    assert tuple(sorted(set(EOIP_SPACING_SCALE))) == EOIP_SPACING_SCALE


def test_css_exposes_canonical_typography_classes() -> None:
    for css_class in (
        ".eoip-page-header",
        ".eoip-page-subtitle",
        ".eoip-section-header",
        ".eoip-section-heading",
        ".eoip-section-description",
        ".eoip-card-title",
        ".eoip-kpi-label",
        ".eoip-kpi-value",
    ):
        assert css_class in EOIP_CSS
    assert "--eoip-font-size-page-title" in EOIP_CSS
    assert "--eoip-space-6" in EOIP_CSS


def test_page_and_section_headers_render_canonical_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rendered: list[str] = []

    def capture(markup: str, *, unsafe_allow_html: bool) -> None:
        assert unsafe_allow_html is True
        rendered.append(markup)

    monkeypatch.setattr("eoip.app.components.common.st.markdown", capture)
    render_page_intro(title="Operations", description="Operational context.")
    render_section_header("Active Incidents", description="Current events.")

    assert "<h1>Operations</h1>" in rendered[0]
    assert "eoip-page-subtitle" in rendered[0]
    assert 'class="eoip-section-heading"' in rendered[1]
    assert "eoip-section-description" in rendered[1]


def test_dashboards_do_not_create_competing_raw_heading_hierarchies() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in DASHBOARD_DIR.glob("*.py")
    )
    assert "st.title(" not in source
    assert "st.header(" not in source
    assert "st.subheader(" not in source
    assert 'st.markdown("#' not in source


def test_typography_markup_contains_no_emoji() -> None:
    assert all(not (0x1F000 <= ord(character) <= 0x1FAFF) for character in EOIP_CSS)
