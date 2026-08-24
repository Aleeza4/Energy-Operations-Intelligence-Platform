"""Platform-wide Streamlit UI tests for EOIP."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

from eoip.app.navigation import NAVIGATION_ITEMS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_FILE = PROJECT_ROOT / "src" / "eoip" / "app" / "main.py"

APP_TIMEOUT_SECONDS = 20


def _run_app() -> AppTest:
    """Run the EOIP Streamlit application through Streamlit AppTest."""
    app = AppTest.from_file(
        str(APP_FILE),
        default_timeout=APP_TIMEOUT_SECONDS,
    )

    app.run(timeout=APP_TIMEOUT_SECONDS)

    return app


def _assert_no_exceptions(app: AppTest) -> None:
    """Assert that Streamlit rendered without application exceptions."""
    assert not app.exception, (
        "Streamlit application raised an exception: " f"{app.exception}"
    )


def _navigation_radio(app: AppTest) -> Any:
    """Return the EOIP navigation radio widget."""
    assert app.radio, "EOIP navigation radio was not rendered."

    return app.radio[0]


def _find_navigation_option(
    navigation: Any,
    page_label: str,
) -> Any:
    """Find the rendered navigation option for a configured page."""
    matching_option = next(
        (option for option in navigation.options if page_label in str(option)),
        None,
    )

    assert matching_option is not None, (
        "Unable to locate Streamlit navigation option for " f"{page_label}"
    )

    return matching_option


def test_streamlit_application_starts_without_exception() -> None:
    """The Streamlit application should boot successfully."""
    app = _run_app()

    _assert_no_exceptions(app)


def test_default_dashboard_renders() -> None:
    """The default dashboard should render visible application content."""
    app = _run_app()

    _assert_no_exceptions(app)

    assert app.title or app.header or app.subheader or app.markdown


def test_navigation_control_is_rendered() -> None:
    """The EOIP sidebar should expose its navigation control."""
    app = _run_app()

    _assert_no_exceptions(app)

    navigation = _navigation_radio(app)

    assert navigation.options


def test_navigation_contains_all_configured_pages() -> None:
    """The UI navigation should expose all configured EOIP pages."""
    app = _run_app()

    _assert_no_exceptions(app)

    navigation = _navigation_radio(app)

    rendered_options = tuple(str(option) for option in navigation.options)

    expected_labels = tuple(item.label for item in NAVIGATION_ITEMS)

    for label in expected_labels:
        assert any(
            label in option for option in rendered_options
        ), f"Configured navigation page was not rendered: {label}"


@pytest.mark.parametrize(
    "page_label",
    tuple(item.label for item in NAVIGATION_ITEMS),
)
def test_every_dashboard_route_renders_without_exception(
    page_label: str,
) -> None:
    """Every configured EOIP dashboard should render successfully."""
    app = _run_app()

    _assert_no_exceptions(app)

    navigation = _navigation_radio(app)

    matching_option = _find_navigation_option(
        navigation,
        page_label,
    )

    navigation.set_value(matching_option)

    app.run(timeout=APP_TIMEOUT_SECONDS)

    _assert_no_exceptions(app)

    rerendered_navigation = _navigation_radio(app)

    assert str(rerendered_navigation.value) == str(matching_option)


def test_application_exposes_interactive_widgets() -> None:
    """The application should expose interactive Streamlit controls."""
    app = _run_app()

    _assert_no_exceptions(app)

    widget_count = sum(
        (
            len(app.button),
            len(app.checkbox),
            len(app.date_input),
            len(app.multiselect),
            len(app.number_input),
            len(app.radio),
            len(app.selectbox),
            len(app.slider),
            len(app.text_input),
        )
    )

    assert widget_count > 0


def test_application_has_no_uncaught_error_elements() -> None:
    """Normal application startup should not render error elements."""
    app = _run_app()

    _assert_no_exceptions(app)

    assert not app.error


def test_sidebar_branding_is_present() -> None:
    """EOIP branding should be rendered in the application."""
    app = _run_app()

    _assert_no_exceptions(app)

    rendered_text = " ".join(
        str(element.value)
        for element in app.markdown
        if getattr(element, "value", None)
    )

    assert "EOIP" in rendered_text or "Energy Operations" in rendered_text


def test_navigation_selection_survives_rerun() -> None:
    """A selected dashboard should remain selected after Streamlit reruns."""
    app = _run_app()

    _assert_no_exceptions(app)

    navigation = _navigation_radio(app)

    assert len(navigation.options) >= 2

    target = navigation.options[1]

    navigation.set_value(target)

    app.run(timeout=APP_TIMEOUT_SECONDS)

    _assert_no_exceptions(app)

    rerendered_navigation = _navigation_radio(app)

    assert str(rerendered_navigation.value) == str(target)
