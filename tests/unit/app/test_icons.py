"""Unit tests for the shared EOIP Lucide icon system."""

from __future__ import annotations

import pytest

from eoip.app.icons import ICON_ALIASES, ICON_PATHS, get_icon_svg, resolve_icon_name
from eoip.app.navigation import NAVIGATION_ITEMS


def test_known_icon_returns_svg() -> None:
    svg = get_icon_svg("executive")

    assert svg.startswith("<svg")
    assert 'viewBox="0 0 24 24"' in svg
    assert 'stroke="currentColor"' in svg


def test_requested_size_is_respected() -> None:
    svg = get_icon_svg("maintenance", size=24)

    assert 'width="24"' in svg
    assert 'height="24"' in svg


def test_unknown_icon_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="Unknown EOIP icon: missing"):
        get_icon_svg("missing")


def test_decorative_icon_is_hidden_from_accessibility_tree() -> None:
    svg = get_icon_svg("warning")

    assert 'aria-hidden="true"' in svg
    assert 'focusable="false"' in svg


def test_generated_svg_contains_no_emoji() -> None:
    svg = "".join(get_icon_svg(name) for name in ICON_PATHS)

    assert all(not (0x1F000 <= ord(character) <= 0x1FAFF) for character in svg)


def test_navigation_icons_are_registered() -> None:
    for item in NAVIGATION_ITEMS:
        assert resolve_icon_name(item.icon) in ICON_PATHS


def test_icon_registries_have_unique_semantic_keys() -> None:
    assert len(ICON_PATHS) == len(set(ICON_PATHS))
    assert len(ICON_ALIASES) == len(set(ICON_ALIASES))
