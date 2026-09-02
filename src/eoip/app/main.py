"""Main Streamlit entry point for EOIP."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from eoip.app.dashboards import (
    administration,
    alarms_incidents,
    anomaly,
    assets,
    data_quality,
    executive,
    forecast,
    maintenance,
    operations,
    plant_performance,
    recommendations,
)
from eoip.app.data_access import BackendUnavailableError
from eoip.app.layout import (
    configure_page,
    render_footer,
    render_page_header,
    render_sidebar_header,
)
from eoip.app.navigation import (
    get_navigation_item,
    initialize_session_state,
    render_navigation,
)
from eoip.app.styles import apply_global_styles

DashboardRenderer = Callable[[], None]

DASHBOARD_RENDERERS: dict[str, DashboardRenderer] = {
    "executive": executive.render,
    "operations": operations.render,
    "plant_performance": plant_performance.render,
    "assets": assets.render,
    "alarms_incidents": alarms_incidents.render,
    "forecast": forecast.render,
    "anomaly": anomaly.render,
    "maintenance": maintenance.render,
    "recommendations": recommendations.render,
    "data_quality": data_quality.render,
    "administration": administration.render,
}


def render_page_placeholder(
    page_key: str,
) -> None:
    """Render a temporary page until its dashboard is implemented."""
    page = get_navigation_item(page_key)

    render_page_header(page.label, subtitle=page.description, icon=page.icon)

    st.info("This dashboard is registered and ready " "for implementation.")


def main() -> None:
    """Run the EOIP Streamlit application."""
    configure_page()

    apply_global_styles()

    initialize_session_state()

    render_sidebar_header()

    active_page = render_navigation()

    renderer = DASHBOARD_RENDERERS.get(active_page)
    if renderer is None:
        render_page_placeholder(active_page)
    else:
        try:
            renderer()
        except BackendUnavailableError:
            st.error(
                "EOIP backend unavailable. Connect to the configured API and "
                "provide a valid EOIP_API_ACCESS_TOKEN."
            )

    render_footer()


if __name__ == "__main__":
    main()
