"""Unit tests for EOIP Streamlit navigation."""

from __future__ import annotations

import pytest

from eoip.app.components.filters import SESSION_EQUIPMENT_KEY, SESSION_PLANT_KEY
from eoip.app.icons import resolve_icon_name
from eoip.app.main import DASHBOARD_RENDERERS
from eoip.app.navigation import (
    DEFAULT_PAGE_KEY,
    NAVIGATION_GROUPS,
    NAVIGATION_ITEMS,
    SESSION_NAVIGATION_REQUEST_KEY,
    NavigationItem,
    get_navigation_item,
    prepare_drilldown_state,
)


class TestNavigationItem:
    """Tests for navigation-item validation."""

    def test_accepts_valid_item(self) -> None:
        item = NavigationItem(
            key="executive",
            label="Executive Dashboard",
            icon="executive",
            description="Portfolio intelligence.",
        )

        assert item.key == "executive"

    @pytest.mark.parametrize(
        "field_name",
        [
            "key",
            "label",
            "icon",
            "description",
        ],
    )
    def test_rejects_empty_fields(
        self,
        field_name: str,
    ) -> None:
        values = {
            "key": "executive",
            "label": "Executive Dashboard",
            "icon": "executive",
            "description": "Portfolio intelligence.",
        }

        values[field_name] = " "

        with pytest.raises(
            ValueError,
            match=f"{field_name} must not be empty.",
        ):
            NavigationItem(**values)


class TestNavigationConfiguration:
    """Tests for EOIP navigation configuration."""

    def test_contains_eleven_pages(self) -> None:
        assert len(NAVIGATION_ITEMS) == 11

    def test_navigation_keys_are_unique(self) -> None:
        keys = [item.key for item in NAVIGATION_ITEMS]

        assert len(keys) == len(set(keys))

    def test_navigation_labels_are_unique(self) -> None:
        labels = [item.label for item in NAVIGATION_ITEMS]

        assert len(labels) == len(set(labels))

    def test_navigation_icons_resolve_to_lucide_icons(self) -> None:
        resolved_icons = [resolve_icon_name(item.icon) for item in NAVIGATION_ITEMS]

        assert len(resolved_icons) == len(NAVIGATION_ITEMS)

    def test_navigation_icon_values_contain_no_emoji(self) -> None:
        icon_values = "".join(item.icon for item in NAVIGATION_ITEMS)

        assert all(
            not (0x1F000 <= ord(character) <= 0x1FAFF) for character in icon_values
        )

    def test_default_page_exists(self) -> None:
        item = get_navigation_item(DEFAULT_PAGE_KEY)

        assert item.key == DEFAULT_PAGE_KEY

    def test_get_navigation_item(self) -> None:
        item = get_navigation_item("maintenance")

        assert item.label == "Maintenance Dashboard"

    def test_rejects_unknown_page(self) -> None:
        with pytest.raises(
            ValueError,
            match="Unknown EOIP page: missing",
        ):
            get_navigation_item("missing")

    def test_every_navigation_page_has_renderer(self) -> None:
        navigation_keys = {item.key for item in NAVIGATION_ITEMS}

        assert set(DASHBOARD_RENDERERS) == navigation_keys
        assert len(DASHBOARD_RENDERERS) == len(set(DASHBOARD_RENDERERS))

    def test_navigation_groups_have_expected_order_and_membership(self) -> None:
        assert tuple(group.label for group in NAVIGATION_GROUPS) == (
            "Overview",
            "Operations",
            "Intelligence",
            "Platform",
        )
        assert {group.label: group.page_keys for group in NAVIGATION_GROUPS} == {
            "Overview": ("executive",),
            "Operations": (
                "operations",
                "plant_performance",
                "assets",
                "alarms_incidents",
            ),
            "Intelligence": (
                "forecast",
                "anomaly",
                "maintenance",
                "recommendations",
            ),
            "Platform": ("data_quality", "administration"),
        }

    def test_navigation_groups_contain_each_page_once(self) -> None:
        grouped_keys = [
            page_key for group in NAVIGATION_GROUPS for page_key in group.page_keys
        ]

        assert grouped_keys == [item.key for item in NAVIGATION_ITEMS]
        assert len(grouped_keys) == len(set(grouped_keys))


class TestDrillDownNavigation:
    """Tests for pure drill-down target and state preparation."""

    def test_prepares_page_and_filter_state(self) -> None:
        state = prepare_drilldown_state(
            "maintenance",
            plant="Solar Plant B",
            equipment_id="INV-003",
        )

        assert state == {
            SESSION_NAVIGATION_REQUEST_KEY: "maintenance",
            SESSION_PLANT_KEY: "Solar Plant B",
            SESSION_EQUIPMENT_KEY: "INV-003",
        }

    def test_rejects_invalid_target(self) -> None:
        with pytest.raises(ValueError, match="Unknown EOIP page"):
            prepare_drilldown_state("missing")

    def test_rejects_invalid_drilldown_values(self) -> None:
        with pytest.raises(ValueError, match="Unknown plant"):
            prepare_drilldown_state("assets", plant="Missing Plant")

        with pytest.raises(ValueError, match="Unknown equipment"):
            prepare_drilldown_state("assets", equipment_id="INV-999")
