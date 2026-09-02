"""Navigation and session-state management for EOIP."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from eoip.app.components.filters import (
    KNOWN_PLANTS,
    SESSION_EQUIPMENT_KEY,
    SESSION_PLANT_KEY,
    _is_valid_equipment_id,
    synchronize_filter_widgets,
)
from eoip.app.icons import get_icon_data_uri, resolve_icon_name


@dataclass(frozen=True, slots=True)
class NavigationItem:
    """Definition of an EOIP application page."""

    key: str
    label: str
    icon: str
    description: str

    def __post_init__(self) -> None:
        """Validate navigation configuration."""
        values = {
            "key": self.key,
            "label": self.label,
            "icon": self.icon,
            "description": self.description,
        }

        for name, value in values.items():
            if not value.strip():
                raise ValueError(f"{name} must not be empty.")

        resolve_icon_name(self.icon)


@dataclass(frozen=True, slots=True)
class NavigationGroup:
    """Visual grouping of existing EOIP page keys."""

    label: str
    page_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("Navigation group label must not be empty.")
        if not self.page_keys:
            raise ValueError("Navigation group must contain at least one page.")


NAVIGATION_ITEMS: tuple[NavigationItem, ...] = (
    NavigationItem(
        key="executive",
        label="Executive Dashboard",
        icon="executive",
        description="Portfolio-level performance and business intelligence.",
    ),
    NavigationItem(
        key="operations",
        label="Operations Dashboard",
        icon="operations",
        description="Representative operational health and activity.",
    ),
    NavigationItem(
        key="plant_performance",
        label="Plant Performance",
        icon="plant_performance",
        description="Plant production, performance, and energy-loss analytics.",
    ),
    NavigationItem(
        key="assets",
        label="Asset Dashboard",
        icon="assets",
        description="Equipment condition and asset-level intelligence.",
    ),
    NavigationItem(
        key="alarms_incidents",
        label="Alarms & Incidents",
        icon="alarms_incidents",
        description="Alarm, incident, downtime, and response intelligence.",
    ),
    NavigationItem(
        key="forecast",
        label="Forecast Dashboard",
        icon="forecast",
        description="Energy forecasts and model performance.",
    ),
    NavigationItem(
        key="anomaly",
        label="Anomaly Dashboard",
        icon="anomaly",
        description="Detected anomalies and abnormal operating behavior.",
    ),
    NavigationItem(
        key="maintenance",
        label="Maintenance Dashboard",
        icon="maintenance",
        description="Predictive maintenance and equipment health.",
    ),
    NavigationItem(
        key="recommendations",
        label="Recommendation Center",
        icon="recommendations",
        description="Prioritized optimization recommendations.",
    ),
    NavigationItem(
        key="data_quality",
        label="Data Quality",
        icon="data_quality",
        description="Data quality, validation, and pipeline health.",
    ),
    NavigationItem(
        key="administration",
        label="Administration",
        icon="administration",
        description="Application configuration and platform information.",
    ),
)

NAVIGATION_GROUPS: tuple[NavigationGroup, ...] = (
    NavigationGroup("Overview", ("executive",)),
    NavigationGroup(
        "Operations",
        ("operations", "plant_performance", "assets", "alarms_incidents"),
    ),
    NavigationGroup(
        "Intelligence",
        ("forecast", "anomaly", "maintenance", "recommendations"),
    ),
    NavigationGroup("Platform", ("data_quality", "administration")),
)


DEFAULT_PAGE_KEY = "executive"
SESSION_PAGE_KEY = "eoip_active_page"
SESSION_NAVIGATION_REQUEST_KEY = "eoip_navigation_request"
NAVIGATION_BUTTON_KEY_PREFIX = "eoip_nav_"


def _validate_navigation_groups() -> None:
    """Ensure grouping presents every configured page exactly once."""
    configured_keys = tuple(item.key for item in NAVIGATION_ITEMS)
    grouped_keys = tuple(
        page_key for group in NAVIGATION_GROUPS for page_key in group.page_keys
    )
    if len(grouped_keys) != len(set(grouped_keys)):
        raise ValueError("Navigation groups contain duplicate page keys.")
    if set(grouped_keys) != set(configured_keys):
        raise ValueError("Navigation groups must contain every configured page.")


_validate_navigation_groups()


def get_navigation_item(
    page_key: str,
) -> NavigationItem:
    """Return navigation configuration for a page."""
    normalized_key = page_key.strip()

    for item in NAVIGATION_ITEMS:
        if item.key == normalized_key:
            return item

    raise ValueError(f"Unknown EOIP page: {page_key}")


def initialize_session_state() -> None:
    """Initialize EOIP Streamlit session state."""
    if SESSION_PAGE_KEY not in st.session_state:
        st.session_state[SESSION_PAGE_KEY] = DEFAULT_PAGE_KEY


def get_active_page_key() -> str:
    """Return the currently active EOIP page."""
    initialize_session_state()

    page_key = str(st.session_state[SESSION_PAGE_KEY])

    try:
        get_navigation_item(page_key)
    except ValueError:
        page_key = DEFAULT_PAGE_KEY
        st.session_state[SESSION_PAGE_KEY] = page_key

    return page_key


def set_active_page(
    page_key: str,
) -> None:
    """Set the currently active EOIP page."""
    item = get_navigation_item(page_key)

    st.session_state[SESSION_PAGE_KEY] = item.key


def prepare_drilldown_state(
    page_key: str,
    *,
    plant: str | None = None,
    equipment_id: str | None = None,
) -> dict[str, str]:
    """Validate a drill-down target and return the required state updates."""
    target = get_navigation_item(page_key)
    state = {SESSION_NAVIGATION_REQUEST_KEY: target.key}

    if plant is not None:
        if not plant.strip():
            raise ValueError("plant must not be empty.")
        if plant not in KNOWN_PLANTS:
            raise ValueError(f"Unknown plant: {plant}")
        state[SESSION_PLANT_KEY] = plant

    if equipment_id is not None:
        if not equipment_id.strip() or equipment_id == "All Equipment":
            raise ValueError("equipment_id must name one equipment record.")
        if not _is_valid_equipment_id(equipment_id):
            raise ValueError(f"Unknown equipment: {equipment_id}")
        state[SESSION_EQUIPMENT_KEY] = equipment_id

    return state


def navigate_to(
    page_key: str,
    *,
    plant: str | None = None,
    equipment_id: str | None = None,
) -> None:
    """Persist drill-down context and request a safe EOIP page transition."""
    for key, value in prepare_drilldown_state(
        page_key,
        plant=plant,
        equipment_id=equipment_id,
    ).items():
        st.session_state[key] = value
    synchronize_filter_widgets(plant=plant, equipment_id=equipment_id)
    st.rerun()


def render_navigation() -> str:
    """Render sidebar navigation and return selected page key."""
    initialize_session_state()

    requested_key = st.session_state.pop(SESSION_NAVIGATION_REQUEST_KEY, None)
    if requested_key is not None:
        set_active_page(str(requested_key))

    active_key = get_active_page_key()

    icon_rules = []
    for item in NAVIGATION_ITEMS:
        resolve_icon_name(item.icon)
        button_class = f".st-key-{NAVIGATION_BUTTON_KEY_PREFIX}{item.key}"
        icon_rules.append(
            f"{button_class} button::before {{"
            f'-webkit-mask-image: url("{get_icon_data_uri(item.icon)}");'
            f'mask-image: url("{get_icon_data_uri(item.icon)}");'
            "}"
        )

    active_button_class = f".st-key-{NAVIGATION_BUTTON_KEY_PREFIX}{active_key}"
    icon_rules.append(
        f"{active_button_class} button {{"
        "background: var(--eoip-primary-soft);"
        "border-left-color: var(--eoip-primary-dark);"
        "color: var(--eoip-primary-dark);"
        "font-weight: var(--eoip-font-weight-bold);"
        "}"
    )

    st.sidebar.markdown(
        f"<style>{''.join(icon_rules)}</style>",
        unsafe_allow_html=True,
    )

    with st.sidebar.container(key="eoip_navigation", gap=None):
        for group in NAVIGATION_GROUPS:
            st.markdown(
                f'<div class="eoip-nav-group-label">{group.label}</div>',
                unsafe_allow_html=True,
            )
            for page_key in group.page_keys:
                item = get_navigation_item(page_key)
                st.button(
                    item.label,
                    key=f"{NAVIGATION_BUTTON_KEY_PREFIX}{item.key}",
                    help=item.description,
                    on_click=set_active_page,
                    args=(item.key,),
                    type="primary" if item.key == active_key else "tertiary",
                    width="stretch",
                )

    return active_key
