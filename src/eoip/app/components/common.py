"""Reusable Streamlit UI components for EOIP."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from html import escape
from typing import Any, Literal

import pandas as pd
import streamlit as st

from eoip.app.components.kpi import (
    MetricCard as MetricCard,
)
from eoip.app.components.kpi import (
    render_metric_card as render_metric_card,
)
from eoip.app.components.kpi import (
    render_metric_row as render_metric_row,
)
from eoip.app.icons import get_icon_svg

LOGGER = logging.getLogger(__name__)

StatusLevel = Literal[
    "success",
    "warning",
    "error",
    "info",
]


@dataclass(frozen=True, slots=True)
class PageContext:
    """Known scope metadata for a dashboard page."""

    scope: str | None = None
    period: str | None = None
    freshness: str | None = None


def page_context_markup(context: PageContext) -> str:
    """Build compact escaped markup while omitting unavailable context."""
    values = (
        ("Scope", context.scope),
        ("Period", context.period),
        ("As of", context.freshness),
    )
    items = "".join(
        '<div class="eoip-context-item">'
        f"<dt>{label}</dt><dd>{escape(value.strip())}</dd></div>"
        for label, value in values
        if value is not None and value.strip()
    )
    if not items:
        return ""
    return f'<dl class="eoip-page-context">{items}</dl>'


def render_page_context(context: PageContext) -> None:
    """Render known page scope without inventing missing freshness data."""
    markup = page_context_markup(context)
    if markup:
        st.markdown(markup, unsafe_allow_html=True)


def render_section_header(
    title: str,
    *,
    description: str | None = None,
) -> None:
    """Render a consistent EOIP section heading."""
    normalized_title = title.strip()

    if not normalized_title:
        raise ValueError("Section title must not be empty.")

    description_markup = ""
    if description is not None and description.strip():
        description_markup = (
            '<p class="eoip-section-description">' f"{escape(description.strip())}</p>"
        )
    st.markdown(
        '<header class="eoip-section-header">'
        f'<h2 class="eoip-section-heading">{escape(normalized_title)}</h2>'
        f"{description_markup}</header>",
        unsafe_allow_html=True,
    )


def render_status(
    message: str,
    *,
    level: StatusLevel = "info",
) -> None:
    """Render a standardized EOIP status message."""
    normalized_message = message.strip()

    if not normalized_message:
        raise ValueError("Status message must not be empty.")

    renderers = {
        "success": st.success,
        "warning": st.warning,
        "error": st.error,
        "info": st.info,
    }

    renderer = renderers[level]

    renderer(normalized_message)


def render_empty_state(
    *,
    title: str,
    message: str,
) -> None:
    """Render a standardized empty-data state."""
    normalized_title = title.strip()
    normalized_message = message.strip()

    if not normalized_title:
        raise ValueError("Empty-state title must not be empty.")

    if not normalized_message:
        raise ValueError("Empty-state message must not be empty.")

    st.markdown(
        f'<div class="eoip-card-title">{escape(normalized_title)}</div>',
        unsafe_allow_html=True,
    )

    st.info(normalized_message)


def render_dataframe(
    dataframe: pd.DataFrame,
    *,
    empty_title: str = "No matching records",
    empty_message: str = "No records match the active filters.",
    **kwargs: Any,
) -> bool:
    """Render a full-width DataFrame or a consistent empty state."""
    if dataframe.empty:
        render_empty_state(title=empty_title, message=empty_message)
        return False

    st.dataframe(dataframe, width="stretch", hide_index=True, **kwargs)
    return True


def load_dashboard_data(
    loader: Callable[[], pd.DataFrame],
    *,
    source_name: str,
) -> pd.DataFrame | None:
    """Load dashboard data while handling predictable source-boundary failures."""
    try:
        return loader()
    except (OSError, RuntimeError, ValueError) as error:
        LOGGER.exception("Unable to load dashboard source %s", source_name)
        st.error(
            f"{source_name} is temporarily unavailable. Refresh the page or try again.",
        )
        st.caption(f"Technical detail: {type(error).__name__}")
        return None


@contextmanager
def dashboard_loading(message: str = "Loading dashboard data...") -> Iterator[None]:
    """Provide consistent loading feedback around genuinely expensive work."""
    normalized_message = message.strip()
    if not normalized_message:
        raise ValueError("Loading message must not be empty.")

    with st.spinner(normalized_message, show_time=True):
        yield


def render_page_intro(
    *,
    title: str,
    description: str,
    icon: str | None = None,
) -> None:
    """Render a consistent dashboard introduction."""
    normalized_title = title.strip()
    normalized_description = description.strip()

    if not normalized_title:
        raise ValueError("Page title must not be empty.")

    if not normalized_description:
        raise ValueError("Page description must not be empty.")

    icon_markup = ""
    if icon is not None and icon.strip():
        icon_markup = (
            '<span class="eoip-icon eoip-page-icon">'
            f"{get_icon_svg(icon.strip(), size=24)}"
            "</span>"
        )

    st.markdown(
        '<div class="eoip-page-header">'
        '<div class="eoip-title-row">'
        f"{icon_markup}<h1>{escape(normalized_title)}</h1>"
        "</div>"
        f'<p class="eoip-page-subtitle">{escape(normalized_description)}</p>'
        "</div>",
        unsafe_allow_html=True,
    )


def render_divider() -> None:
    """Render a shared visual divider."""
    st.divider()
