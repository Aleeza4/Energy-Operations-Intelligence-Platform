"""Main Streamlit entry point for EOIP."""

from __future__ import annotations

import streamlit as st

from eoip.app.layout import (
    configure_page,
    render_page_footer,
    render_sidebar_header,
)
from eoip.app.navigation import (
    get_navigation_item,
    initialize_session_state,
    render_navigation,
)
from eoip.app.styles import apply_global_styles


def render_page_placeholder(
    page_key: str,
) -> None:
    """Render a temporary page until its dashboard is implemented."""
    page = get_navigation_item(page_key)

    st.title(f"{page.icon} {page.label}")

    st.caption(page.description)

    st.info("This dashboard is registered and ready " "for implementation.")


def main() -> None:
    """Run the EOIP Streamlit application."""
    configure_page()

    apply_global_styles()

    initialize_session_state()

    render_sidebar_header()

    active_page = render_navigation()

    render_page_placeholder(active_page)

    render_page_footer()


if __name__ == "__main__":
    main()
