"""Shared, persistent filter controls for EOIP dashboards."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

import streamlit as st

DEFAULT_PLANTS: tuple[str, ...] = (
    "All Plants",
    "Solar Plant A",
    "Solar Plant B",
    "Solar Plant C",
    "Solar Plant D",
)

DEFAULT_EQUIPMENT: tuple[str, ...] = (
    "All Equipment",
    "INV-001",
    "INV-002",
    "INV-003",
    "INV-004",
    "INV-005",
    "INV-006",
    "TRF-002",
    "TRF-004",
)

SESSION_PLANT_KEY = "eoip_filter_plant"
SESSION_START_DATE_KEY = "eoip_filter_start_date"
SESSION_END_DATE_KEY = "eoip_filter_end_date"
SESSION_EQUIPMENT_KEY = "eoip_filter_equipment"

_WIDGET_PLANT_KEY = "eoip_filter_widget_plant"
_WIDGET_DATE_RANGE_KEY = "eoip_filter_widget_date_range"
_WIDGET_EQUIPMENT_KEY = "eoip_filter_widget_equipment"


@dataclass(frozen=True, slots=True)
class FilterSelection:
    """Current validated EOIP dashboard filter selection."""

    plant: str
    start_date: date
    end_date: date
    equipment_id: str | None = None

    def __post_init__(self) -> None:
        """Validate filter selection values and chronology."""
        if self.plant not in DEFAULT_PLANTS:
            raise ValueError(f"Unknown plant: {self.plant}")
        if not isinstance(self.start_date, date):
            raise ValueError("start_date must be a date.")
        if not isinstance(self.end_date, date):
            raise ValueError("end_date must be a date.")
        if self.start_date > self.end_date:
            raise ValueError("start_date must not be after end_date.")
        if self.equipment_id is not None and self.equipment_id not in DEFAULT_EQUIPMENT:
            raise ValueError(f"Unknown equipment: {self.equipment_id}")
        if self.equipment_id == "All Equipment":
            raise ValueError("equipment_id must be None for all equipment.")


def normalize_filter_selection(
    *,
    plant: object,
    start_date: object,
    end_date: object,
    equipment: object = "All Equipment",
    plants: Sequence[str] = DEFAULT_PLANTS,
    equipment_options: Sequence[str] = DEFAULT_EQUIPMENT,
    today: date | None = None,
) -> FilterSelection:
    """Normalize potentially stale values into a safe filter selection."""
    reference_date = today or date.today()
    default_start = reference_date - timedelta(days=6)
    valid_plants = tuple(plants) or DEFAULT_PLANTS
    valid_equipment = tuple(equipment_options) or ("All Equipment",)

    normalized_plant = str(plant) if plant in valid_plants else valid_plants[0]
    normalized_start = start_date if isinstance(start_date, date) else default_start
    normalized_end = end_date if isinstance(end_date, date) else reference_date

    if normalized_start > normalized_end:
        normalized_start, normalized_end = normalized_end, normalized_start

    normalized_equipment = (
        str(equipment) if equipment in valid_equipment else valid_equipment[0]
    )
    equipment_id = (
        None if normalized_equipment == "All Equipment" else normalized_equipment
    )

    return FilterSelection(
        plant=normalized_plant,
        start_date=normalized_start,
        end_date=normalized_end,
        equipment_id=equipment_id,
    )


def initialize_filter_state() -> None:
    """Initialize and repair shared EOIP filter state."""
    selection = normalize_filter_selection(
        plant=st.session_state.get(SESSION_PLANT_KEY),
        start_date=st.session_state.get(SESSION_START_DATE_KEY),
        end_date=st.session_state.get(SESSION_END_DATE_KEY),
        equipment=st.session_state.get(SESSION_EQUIPMENT_KEY),
    )
    st.session_state[SESSION_PLANT_KEY] = selection.plant
    st.session_state[SESSION_START_DATE_KEY] = selection.start_date
    st.session_state[SESSION_END_DATE_KEY] = selection.end_date
    st.session_state[SESSION_EQUIPMENT_KEY] = selection.equipment_id or "All Equipment"


def get_filter_selection() -> FilterSelection:
    """Return the current repaired shared filter selection."""
    initialize_filter_state()
    return normalize_filter_selection(
        plant=st.session_state[SESSION_PLANT_KEY],
        start_date=st.session_state[SESSION_START_DATE_KEY],
        end_date=st.session_state[SESSION_END_DATE_KEY],
        equipment=st.session_state[SESSION_EQUIPMENT_KEY],
    )


def set_filter_selection(selection: FilterSelection) -> None:
    """Persist a validated filter selection for navigation or tests."""
    st.session_state[SESSION_PLANT_KEY] = selection.plant
    st.session_state[SESSION_START_DATE_KEY] = selection.start_date
    st.session_state[SESSION_END_DATE_KEY] = selection.end_date
    st.session_state[SESSION_EQUIPMENT_KEY] = selection.equipment_id or "All Equipment"


def _sync_filter_widgets() -> None:
    """Copy rendered widget values into persistent shared state."""
    plant = st.session_state.get(_WIDGET_PLANT_KEY)
    if plant in DEFAULT_PLANTS:
        st.session_state[SESSION_PLANT_KEY] = plant

    equipment = st.session_state.get(_WIDGET_EQUIPMENT_KEY)
    if equipment in DEFAULT_EQUIPMENT:
        st.session_state[SESSION_EQUIPMENT_KEY] = equipment

    selected_dates = st.session_state.get(_WIDGET_DATE_RANGE_KEY)
    if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
        if (
            isinstance(start_date, date)
            and isinstance(end_date, date)
            and start_date <= end_date
        ):
            st.session_state[SESSION_START_DATE_KEY] = start_date
            st.session_state[SESSION_END_DATE_KEY] = end_date


def render_global_filters(
    *,
    show_equipment: bool = False,
    equipment_options: Sequence[str] = DEFAULT_EQUIPMENT,
) -> FilterSelection:
    """Render compact persistent filters and return their validated selection."""
    initialize_filter_state()
    options = tuple(equipment_options) or ("All Equipment",)
    if "All Equipment" not in options:
        options = ("All Equipment", *options)

    current = get_filter_selection()
    current_equipment = current.equipment_id or "All Equipment"
    if current_equipment not in options:
        current_equipment = "All Equipment"
        st.session_state[SESSION_EQUIPMENT_KEY] = current_equipment

    with st.container(border=True):
        st.caption("Filters")
        columns = st.columns(
            3 if show_equipment else 2,
            vertical_alignment="bottom",
        )

        with columns[0]:
            st.selectbox(
                "Plant",
                options=DEFAULT_PLANTS,
                index=DEFAULT_PLANTS.index(current.plant),
                key=_WIDGET_PLANT_KEY,
                on_change=_sync_filter_widgets,
            )

        with columns[1]:
            st.date_input(
                "Date range",
                value=(current.start_date, current.end_date),
                key=_WIDGET_DATE_RANGE_KEY,
                on_change=_sync_filter_widgets,
            )

        if show_equipment:
            with columns[2]:
                st.selectbox(
                    "Equipment",
                    options=options,
                    index=options.index(current_equipment),
                    key=_WIDGET_EQUIPMENT_KEY,
                    on_change=_sync_filter_widgets,
                )

    _sync_filter_widgets()
    return get_filter_selection()


def format_filter_caption(
    filters: FilterSelection,
    *,
    show_equipment: bool = True,
) -> str:
    """Return a compact human-readable active-filter summary."""
    parts = [filters.plant]
    if show_equipment and filters.equipment_id is not None:
        parts.append(filters.equipment_id)
    parts.append(f"{filters.start_date:%d %b %Y} to {filters.end_date:%d %b %Y}")
    return f"Active filters: {' · '.join(parts)}"
