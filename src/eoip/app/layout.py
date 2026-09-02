"""Shared application layout for the EOIP Streamlit interface."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from eoip.app.icons import get_icon_data_uri, get_icon_svg


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Configuration for the EOIP Streamlit application."""

    page_title: str = "EOIP | Energy Operations Intelligence Platform"
    page_icon: str = get_icon_data_uri("energy")
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
        st.markdown(
            '<div class="eoip-brand">'
            '<span class="eoip-icon eoip-icon-accent">'
            f'{get_icon_svg("energy", size=20)}'
            "</span><span>EOIP</span></div>",
            unsafe_allow_html=True,
        )
        st.caption("Energy Operations Intelligence Platform")
        st.divider()


def render_page_header(
    title: str,
    *,
    subtitle: str | None = None,
    icon: str | None = None,
) -> None:
    """Render a consistent page heading."""
    if not title.strip():
        raise ValueError("Page title must not be empty.")

    from eoip.app.components.common import render_page_intro

    render_page_intro(
        title=title,
        description=subtitle or "Energy operations intelligence",
        icon=icon,
    )


def render_footer() -> None:
    """Render the shared EOIP footer with developer credit."""
    st.markdown(
        "<div style='text-align: center; color: #6b7280; font-size: 0.8rem; margin-top: 2rem;'>"
        "Developed by Aleeza Iftikhar | github.com/Aleeza4"
        "</div>",
        unsafe_allow_html=True,
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

    render_footer()
