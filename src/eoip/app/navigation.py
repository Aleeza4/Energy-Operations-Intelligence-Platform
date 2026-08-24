"""Navigation and session-state management for EOIP."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from eoip.app.components.filters import (
    DEFAULT_EQUIPMENT,
    DEFAULT_PLANTS,
    SESSION_EQUIPMENT_KEY,
    SESSION_PLANT_KEY,
)


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


NAVIGATION_ITEMS: tuple[NavigationItem, ...] = (
    NavigationItem(
        key="executive",
        label="Executive Dashboard",
        icon="📊",
        description="Portfolio-level performance and business intelligence.",
    ),
    NavigationItem(
        key="operations",
        label="Operations Dashboard",
        icon="⚙️",
        description="Real-time operational health and activity.",
    ),
    NavigationItem(
        key="plant_performance",
        label="Plant Performance",
        icon="☀️",
        description="Plant production, performance, and energy-loss analytics.",
    ),
    NavigationItem(
        key="assets",
        label="Asset Dashboard",
        icon="🔧",
        description="Equipment condition and asset-level intelligence.",
    ),
    NavigationItem(
        key="alarms_incidents",
        label="Alarms & Incidents",
        icon="🚨",
        description="Alarm, incident, downtime, and response intelligence.",
    ),
    NavigationItem(
        key="forecast",
        label="Forecast Dashboard",
        icon="📈",
        description="Energy forecasts and model performance.",
    ),
    NavigationItem(
        key="anomaly",
        label="Anomaly Dashboard",
        icon="🔍",
        description="Detected anomalies and abnormal operating behavior.",
    ),
    NavigationItem(
        key="maintenance",
        label="Maintenance Dashboard",
        icon="🛠️",
        description="Predictive maintenance and equipment health.",
    ),
    NavigationItem(
        key="recommendations",
        label="Recommendation Center",
        icon="💡",
        description="Prioritized optimization recommendations.",
    ),
    NavigationItem(
        key="data_quality",
        label="Data Quality",
        icon="✅",
        description="Data quality, validation, and pipeline health.",
    ),
    NavigationItem(
        key="administration",
        label="Administration",
        icon="⚙️",
        description="Application configuration and platform information.",
    ),
)


DEFAULT_PAGE_KEY = "executive"
SESSION_PAGE_KEY = "eoip_active_page"
SESSION_NAVIGATION_REQUEST_KEY = "eoip_navigation_request"
SESSION_NAVIGATION_WIDGET_KEY = "eoip_navigation_radio"


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
        if plant not in DEFAULT_PLANTS:
            raise ValueError(f"Unknown plant: {plant}")
        state[SESSION_PLANT_KEY] = plant

    if equipment_id is not None:
        if equipment_id not in DEFAULT_EQUIPMENT or equipment_id == "All Equipment":
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
    st.rerun()


def render_navigation() -> str:
    """Render sidebar navigation and return selected page key."""
    initialize_session_state()

    requested_key = st.session_state.pop(SESSION_NAVIGATION_REQUEST_KEY, None)
    if requested_key is not None:
        set_active_page(str(requested_key))
        st.session_state.pop(SESSION_NAVIGATION_WIDGET_KEY, None)

    active_key = get_active_page_key()

    labels = {f"{item.icon}  {item.label}": item.key for item in NAVIGATION_ITEMS}

    active_item = get_navigation_item(active_key)

    active_label = f"{active_item.icon}  " f"{active_item.label}"

    selected_label = st.sidebar.radio(
        "Navigation",
        options=list(labels),
        index=list(labels).index(active_label),
        key=SESSION_NAVIGATION_WIDGET_KEY,
    )

    selected_key = labels[selected_label]

    set_active_page(selected_key)

    selected_item = get_navigation_item(selected_key)

    st.sidebar.caption(selected_item.description)

    return selected_key
