"""Reusable Streamlit UI components for EOIP."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd
import streamlit as st

LOGGER = logging.getLogger(__name__)

StatusLevel = Literal[
    "success",
    "warning",
    "error",
    "info",
]


@dataclass(frozen=True, slots=True)
class MetricCard:
    """Configuration for an EOIP metric card."""

    label: str
    value: str
    delta: str | None = None
    help_text: str | None = None

    def __post_init__(self) -> None:
        """Validate metric-card configuration."""
        if not self.label.strip():
            raise ValueError("Metric label must not be empty.")

        if not self.value.strip():
            raise ValueError("Metric value must not be empty.")


def render_section_header(
    title: str,
    *,
    description: str | None = None,
) -> None:
    """Render a consistent EOIP section heading."""
    normalized_title = title.strip()

    if not normalized_title:
        raise ValueError("Section title must not be empty.")

    st.subheader(normalized_title)

    if description is not None:
        normalized_description = description.strip()

        if normalized_description:
            st.caption(normalized_description)


def render_metric_card(
    metric: MetricCard,
) -> None:
    """Render one EOIP KPI metric."""
    st.metric(
        label=metric.label,
        value=metric.value,
        delta=metric.delta,
        help=metric.help_text,
        width="stretch",
    )


def render_metric_row(
    metrics: Sequence[MetricCard],
) -> None:
    """Render metrics across a responsive row."""
    if not metrics:
        raise ValueError("At least one metric is required.")

    with st.container(horizontal=True, gap="small"):
        for metric in metrics:
            render_metric_card(metric)


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

    st.markdown(f"### {normalized_title}")

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
            icon=":material/error:",
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

    if icon is not None and icon.strip():
        heading = f"{icon.strip()} " f"{normalized_title}"
    else:
        heading = normalized_title

    st.title(heading)

    st.caption(normalized_description)


def render_divider() -> None:
    """Render a shared visual divider."""
    st.divider()
