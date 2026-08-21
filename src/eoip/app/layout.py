"""Shared application layout for the EOIP Streamlit interface."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Configuration for the EOIP Streamlit application."""

    page_title: str = "EOIP | Energy Operations Intelligence Platform"
    page_icon: str = "⚡"
    layout: str = "wide"
    initial_sidebar_state: str = "expanded"


APP_CONFIG = AppConfig()


def configure_page(
    config: AppConfig = APP_CONFIG,
) -> None:
    """Configure global Streamlit page settings."""
    st.set_page_config(
        page_title=config.page_title,
        page_icon=config.page_icon,
        layout=config.layout,
        initial_sidebar_state=config.initial_sidebar_state,
    )


def render_sidebar_header() -> None:
    """Render the shared EOIP sidebar header."""
    with st.sidebar:
        st.markdown("## ⚡ EOIP")
        st.caption("Energy Operations Intelligence Platform")
        st.divider()


def render_page_header(
    title: str,
    *,
    subtitle: str | None = None,
) -> None:
    """Render a consistent page heading."""
    if not title.strip():
        raise ValueError("Page title must not be empty.")

    st.title(title)

    if subtitle is not None:
        normalized_subtitle = subtitle.strip()

        if normalized_subtitle:
            st.caption(normalized_subtitle)


def render_page_footer() -> None:
    """Render the shared application footer."""
    st.divider()

    st.caption(
        "EOIP · Energy Operations Intelligence Platform · "
        "Operational Intelligence for Renewable Energy Assets"
    )


def render_application_shell(
    *,
    title: str,
    subtitle: str | None = None,
) -> None:
    """Render shared elements used by EOIP pages."""
    render_sidebar_header()

    render_page_header(
        title,
        subtitle=subtitle,
    )
