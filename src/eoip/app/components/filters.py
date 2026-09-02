"""Shared, persistent filter controls for EOIP dashboards."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

import streamlit as st

from eoip.app.components.common import PageContext, render_page_context

DEFAULT_PLANTS: tuple[str, ...] = ("All Plants",)
DEFAULT_EQUIPMENT: tuple[str, ...] = ("All Equipment",)
KNOWN_PLANTS: tuple[str, ...] = (
    "All Plants",
    "Solar Plant A",
    "Solar Plant B",
    "Solar Plant C",
    "Solar Plant D",
)
KNOWN_EQUIPMENT: tuple[str, ...] = (
    "All Equipment",
    "INV-001",
    "INV-003",
    "INV-005",
    "INV-006",
    "TRF-004",
)


def _is_valid_plant(value: object) -> bool:
    """Accept only canonical EOIP portfolio plant names."""
    return isinstance(value, str) and value in KNOWN_PLANTS


def _is_valid_equipment_id(value: object) -> bool:
    """Allow plausible equipment IDs while rejecting obvious placeholder failures."""
    if not isinstance(value, str):
        return False
    value = value.strip()
    if not value or value == "All Equipment":
        return False
    if value in KNOWN_EQUIPMENT:
        return True
    if "-" not in value:
        return False
    prefix, suffix = value.split("-", 1)
    if not prefix or not suffix.isdigit():
        return False
    return 0 < int(suffix) < 900


SESSION_PLANT_KEY = "eoip_filter_plant"
SESSION_START_DATE_KEY = "eoip_filter_start_date"
SESSION_END_DATE_KEY = "eoip_filter_end_date"
SESSION_EQUIPMENT_KEY = "eoip_filter_equipment"

_WIDGET_PLANT_KEY = "eoip_filter_widget_plant"
_WIDGET_DATE_RANGE_KEY = "eoip_filter_widget_date_range"
_WIDGET_EQUIPMENT_KEY = "eoip_filter_widget_equipment"
_PENDING_WIDGET_PLANT_KEY = "eoip_pending_filter_widget_plant"
_PENDING_WIDGET_EQUIPMENT_KEY = "eoip_pending_filter_widget_equipment"


@dataclass(frozen=True, slots=True)
class FilterSelection:
    """Current validated EOIP dashboard filter selection."""

    plant: str
    start_date: date
    end_date: date
    equipment_id: str | None = None

    def __post_init__(self) -> None:
        """Validate filter selection values and chronology."""
        if not self.plant.strip():
            raise ValueError("plant must not be empty.")
        if not _is_valid_plant(self.plant):
            raise ValueError(f"Unknown plant: {self.plant}")
        if not isinstance(self.start_date, date):
            raise ValueError("start_date must be a date.")
        if not isinstance(self.end_date, date):
            raise ValueError("end_date must be a date.")
        if self.start_date > self.end_date:
            raise ValueError("start_date must not be after end_date.")
        if self.equipment_id == "All Equipment":
            raise ValueError("equipment_id must be None for all equipment.")
        if self.equipment_id is not None and not _is_valid_equipment_id(
            self.equipment_id
        ):
            raise ValueError(f"Unknown equipment: {self.equipment_id}")


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


def synchronize_filter_widgets(
    *,
    plant: str | None = None,
    equipment_id: str | None = None,
) -> None:
    """Queue widget synchronization for the rerun after programmatic navigation."""
    if plant is not None:
        st.session_state[_PENDING_WIDGET_PLANT_KEY] = plant
    if equipment_id is not None:
        st.session_state[_PENDING_WIDGET_EQUIPMENT_KEY] = equipment_id


def _apply_pending_filter_widget_state() -> None:
    """Apply queued navigation values before filter widgets are instantiated."""
    pending_plant = st.session_state.pop(_PENDING_WIDGET_PLANT_KEY, None)
    if pending_plant is not None:
        st.session_state[_WIDGET_PLANT_KEY] = pending_plant

    pending_equipment = st.session_state.pop(_PENDING_WIDGET_EQUIPMENT_KEY, None)
    if pending_equipment is not None:
        st.session_state[_WIDGET_EQUIPMENT_KEY] = pending_equipment


def _sync_filter_widgets() -> None:
    """Copy rendered widget values into persistent shared state."""
    plant = st.session_state.get(_WIDGET_PLANT_KEY)
    if isinstance(plant, str) and plant.strip():
        st.session_state[SESSION_PLANT_KEY] = plant

    equipment = st.session_state.get(_WIDGET_EQUIPMENT_KEY)
    if isinstance(equipment, str) and equipment.strip():
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
    show_plant: bool = True,
    show_date: bool = True,
    show_equipment: bool = False,
    show_context: bool = True,
    equipment_options: Sequence[str] = DEFAULT_EQUIPMENT,
) -> FilterSelection:
    """Render compact persistent filters and return their validated selection."""
    initialize_filter_state()
    _apply_pending_filter_widget_state()
    from eoip.app.data_access import get_filter_options

    live_plants, live_equipment = get_filter_options()
    options = (
        tuple(equipment_options)
        if equipment_options != DEFAULT_EQUIPMENT
        else live_equipment
    )
    options = options or ("All Equipment",)
    if "All Equipment" not in options:
        options = ("All Equipment", *options)

    current = get_filter_selection()
    current_equipment = current.equipment_id or "All Equipment"
    if current_equipment not in options:
        current_equipment = "All Equipment"
        st.session_state[SESSION_EQUIPMENT_KEY] = current_equipment
        st.session_state[_WIDGET_EQUIPMENT_KEY] = current_equipment
        current = get_filter_selection()

    if show_context:
        render_filter_context(
            current,
            show_plant=show_plant,
            show_date=show_date,
            show_equipment=show_equipment,
        )

    visible_filter_count = sum((show_plant, show_date, show_equipment))
    if visible_filter_count == 0:
        return current

    with st.container(border=True):
        st.markdown(
            '<div class="eoip-filter-heading">Filters</div>',
            unsafe_allow_html=True,
        )
        columns = st.columns(visible_filter_count, vertical_alignment="bottom")
        column_index = 0

        if show_plant:
            with columns[column_index]:
                st.selectbox(
                    "Plant",
                    options=live_plants,
                    index=(
                        live_plants.index(current.plant)
                        if current.plant in live_plants
                        else 0
                    ),
                    key=_WIDGET_PLANT_KEY,
                    on_change=_sync_filter_widgets,
                )
            column_index += 1

        if show_date:
            with columns[column_index]:
                st.date_input(
                    "Date range",
                    value=(current.start_date, current.end_date),
                    key=_WIDGET_DATE_RANGE_KEY,
                    on_change=_sync_filter_widgets,
                )
            column_index += 1

        if show_equipment:
            with columns[column_index]:
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
    show_plant: bool = True,
    show_date: bool = True,
    show_equipment: bool = True,
) -> str:
    """Return a compact human-readable active-filter summary."""
    parts = [filters.plant] if show_plant else []
    if show_equipment and filters.equipment_id is not None:
        parts.append(filters.equipment_id)
    if show_date:
        parts.append(f"{filters.start_date:%d %b %Y} to {filters.end_date:%d %b %Y}")
    return f"Active filters: {' · '.join(parts)}"


def page_context_from_filters(
    filters: FilterSelection,
    *,
    show_plant: bool = True,
    show_date: bool = True,
    show_equipment: bool = True,
    freshness: str | None = None,
) -> PageContext:
    """Translate trusted Phase A scope into reusable shell context."""
    scope_parts: list[str] = []
    if show_plant:
        scope_parts.append(
            "Portfolio" if filters.plant == "All Plants" else filters.plant
        )
    elif not show_equipment:
        scope_parts.append("Portfolio")
    if show_equipment and filters.equipment_id is not None:
        scope_parts.append(filters.equipment_id)

    period = None
    if show_date:
        period = f"{filters.start_date:%d %b %Y} – {filters.end_date:%d %b %Y}"

    return PageContext(
        scope=" / ".join(scope_parts) or None,
        period=period,
        freshness=freshness,
    )


def render_filter_context(
    filters: FilterSelection,
    *,
    show_plant: bool = True,
    show_date: bool = True,
    show_equipment: bool = True,
    freshness: str | None = None,
) -> None:
    """Render compact context for the current trusted filter selection."""
    render_page_context(
        page_context_from_filters(
            filters,
            show_plant=show_plant,
            show_date=show_date,
            show_equipment=show_equipment,
            freshness=freshness,
        )
    )
