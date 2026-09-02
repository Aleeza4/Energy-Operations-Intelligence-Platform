"""Platform-wide Streamlit UI tests for EOIP."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

from eoip.app.navigation import NAVIGATION_GROUPS, NAVIGATION_ITEMS

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


def _navigation_buttons(app: AppTest) -> tuple[Any, ...]:
    """Return EOIP navigation buttons in configured order."""
    expected_keys = {f"eoip_nav_{item.key}" for item in NAVIGATION_ITEMS}
    buttons = tuple(
        button for button in app.sidebar.button if button.key in expected_keys
    )

    assert len(buttons) == len(NAVIGATION_ITEMS)

    return buttons


def _find_navigation_button(
    buttons: tuple[Any, ...],
    page_label: str,
) -> Any:
    """Find the rendered navigation button for a configured page."""
    matching_button = next(
        (button for button in buttons if button.label == page_label),
        None,
    )

    assert matching_button is not None, (
        "Unable to locate Streamlit navigation button for " f"{page_label}"
    )

    return matching_button


def test_streamlit_application_starts_without_exception() -> None:
    """The Streamlit application should boot successfully."""
    app = _run_app()

    _assert_no_exceptions(app)


def test_default_dashboard_renders() -> None:
    """The default dashboard should render visible application content."""
    app = _run_app()

    _assert_no_exceptions(app)

    assert app.title or app.header or app.subheader or app.markdown


def test_executive_charts_do_not_serialize_missing_titles() -> None:
    """Optional Plotly titles must not reach the browser as nullish text."""
    app = _run_app()

    _assert_no_exceptions(app)

    charts = app.get("plotly_chart")
    assert charts
    for chart in charts:
        specification = json.loads(chart.proto.spec)
        title = specification["layout"].get("title")
        assert title is None or title.get("text") not in {
            None,
            "",
            "None",
            "null",
            "undefined",
        }
        assert "undefined" not in chart.proto.spec.casefold()


def test_dashboard_uses_centralized_kpi_cards_not_streamlit_metrics() -> None:
    """EOIP dashboards should expose one consistent KPI visual system."""
    app = _run_app()

    _assert_no_exceptions(app)

    rendered_markup = " ".join(
        str(element.value)
        for element in app.markdown
        if getattr(element, "value", None)
    )
    assert "eoip-kpi-grid" in rendered_markup
    assert "eoip-kpi-card" in rendered_markup
    assert not app.metric


def test_navigation_control_is_rendered() -> None:
    """The EOIP sidebar should expose its navigation control."""
    app = _run_app()

    _assert_no_exceptions(app)

    buttons = _navigation_buttons(app)

    assert buttons
    assert not app.radio


def test_navigation_contains_all_configured_pages() -> None:
    """The UI navigation should expose all configured EOIP pages."""
    app = _run_app()

    _assert_no_exceptions(app)

    buttons = _navigation_buttons(app)
    rendered_labels = tuple(button.label for button in buttons)

    expected_labels = tuple(item.label for item in NAVIGATION_ITEMS)

    for label in expected_labels:
        assert (
            label in rendered_labels
        ), f"Configured navigation page was not rendered: {label}"


def test_navigation_groups_render_in_configured_order() -> None:
    """Sidebar group labels should expose the enterprise hierarchy."""
    app = _run_app()

    group_markup = [
        str(element.value)
        for element in app.sidebar.markdown
        if "eoip-nav-group-label" in str(getattr(element, "value", ""))
    ]

    assert group_markup == [
        f'<div class="eoip-nav-group-label">{group.label}</div>'
        for group in NAVIGATION_GROUPS
    ]


def test_sidebar_has_no_duplicate_current_page_message() -> None:
    """Active navigation styling should be the sole page indicator."""
    app = _run_app()

    sidebar_values = [
        str(getattr(element, "value", "")) for element in app.sidebar.markdown
    ]
    assert all("Current page:" not in value for value in sidebar_values)


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

    matching_button = _find_navigation_button(
        _navigation_buttons(app),
        page_label,
    )

    matching_button.click()

    app.run(timeout=APP_TIMEOUT_SECONDS)

    _assert_no_exceptions(app)

    rendered_markup = " ".join(
        str(element.value)
        for element in app.markdown
        if getattr(element, "value", None)
    )
    assert "eoip-page-context" in rendered_markup

    active_buttons = [
        button for button in _navigation_buttons(app) if button.proto.type == "primary"
    ]

    assert [button.label for button in active_buttons] == [page_label]


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

    target = _navigation_buttons(app)[1]
    target.click()

    app.run(timeout=APP_TIMEOUT_SECONDS)

    _assert_no_exceptions(app)

    app.run(timeout=APP_TIMEOUT_SECONDS)

    active_buttons = [
        button for button in _navigation_buttons(app) if button.proto.type == "primary"
    ]

    assert [button.label for button in active_buttons] == [target.label]


def test_programmatic_navigation_request_updates_active_item() -> None:
    """A drill-down request should update the rendered active navigation item."""
    app = _run_app()

    app.session_state["eoip_navigation_request"] = "maintenance"
    app.run(timeout=APP_TIMEOUT_SECONDS)

    _assert_no_exceptions(app)

    active_buttons = [
        button for button in _navigation_buttons(app) if button.proto.type == "primary"
    ]

    assert [button.label for button in active_buttons] == ["Maintenance Dashboard"]


def test_navigation_has_exactly_one_active_item() -> None:
    """The sidebar should expose one and only one selected page."""
    app = _run_app()

    active_buttons = [
        button for button in _navigation_buttons(app) if button.proto.type == "primary"
    ]

    assert len(active_buttons) == 1


def test_plant_scope_changes_operations_kpi_and_table_data() -> None:
    """A page scope must drive both summary values and detail records."""
    app = _run_app()
    app.session_state["eoip_navigation_request"] = "operations"
    app.session_state["eoip_filter_plant"] = "Solar Plant D"
    app.run(timeout=APP_TIMEOUT_SECONDS)

    _assert_no_exceptions(app)
    rendered_markup = " ".join(
        str(element.value)
        for element in app.markdown
        if getattr(element, "value", None)
    )
    assert "Critical Open Incidents" in rendered_markup
    assert '<div class="eoip-kpi-value">1</div>' in rendered_markup
    assert app.dataframe
    assert set(app.dataframe[0].value["Plant"]) == {"Solar Plant D"}


def test_forecast_exposes_date_scope_without_unsupported_plant_filter() -> None:
    """Forecast must not imply plant scope unsupported by its primary source."""
    app = _run_app()
    app.session_state["eoip_navigation_request"] = "forecast"
    app.run(timeout=APP_TIMEOUT_SECONDS)

    _assert_no_exceptions(app)
    assert "Plant" not in [selectbox.label for selectbox in app.selectbox]
    assert [date_input.label for date_input in app.date_input] == ["Date range"]


def test_executive_drilldown_uses_existing_navigation_and_plant_context() -> None:
    """Executive actions should reuse the existing requested-page workflow."""
    app = _run_app()
    action = next(
        button for button in app.button if button.label == "Open plant performance"
    )

    action.click()
    app.run(timeout=APP_TIMEOUT_SECONDS)

    _assert_no_exceptions(app)
    active_buttons = [
        button for button in _navigation_buttons(app) if button.proto.type == "primary"
    ]
    assert [button.label for button in active_buttons] == ["Plant Performance"]
    assert app.session_state["eoip_filter_plant"] == "Solar Plant D"


def test_operations_incident_drilldown_preserves_plant_and_equipment() -> None:
    """The primary incident action should open the existing investigation route."""
    app = _run_app()
    _find_navigation_button(_navigation_buttons(app), "Operations Dashboard").click()
    app.run(timeout=APP_TIMEOUT_SECONDS)

    action = next(
        button for button in app.button if button.label == "Open incident investigation"
    )
    action.click()
    app.run(timeout=APP_TIMEOUT_SECONDS)

    _assert_no_exceptions(app)
    active_buttons = [
        button for button in _navigation_buttons(app) if button.proto.type == "primary"
    ]
    assert [button.label for button in active_buttons] == ["Alarms & Incidents"]
    assert app.session_state["eoip_filter_plant"] == "Solar Plant D"
    assert app.session_state["eoip_filter_equipment"] == "INV-005"


def test_operations_to_plant_performance_preserves_plant_context() -> None:
    """Operations should open plant engineering analysis in the incident scope."""
    app = _run_app()
    _find_navigation_button(_navigation_buttons(app), "Operations Dashboard").click()
    app.run(timeout=APP_TIMEOUT_SECONDS)

    next(
        button for button in app.button if button.label == "Open plant performance"
    ).click()
    app.run(timeout=APP_TIMEOUT_SECONDS)

    _assert_no_exceptions(app)
    assert app.session_state["eoip_active_page"] == "plant_performance"
    assert app.session_state["eoip_filter_plant"] == "Solar Plant D"


def test_plant_performance_to_assets_preserves_plant_context() -> None:
    """Plant engineering analysis should continue into scoped equipment."""
    app = _run_app()
    app.session_state["eoip_navigation_request"] = "plant_performance"
    app.session_state["eoip_filter_plant"] = "Solar Plant D"
    app.run(timeout=APP_TIMEOUT_SECONDS)

    next(button for button in app.button if button.label == "Inspect assets").click()
    app.run(timeout=APP_TIMEOUT_SECONDS)

    _assert_no_exceptions(app)
    assert app.session_state["eoip_active_page"] == "assets"
    assert app.session_state["eoip_filter_plant"] == "Solar Plant D"


@pytest.mark.parametrize(
    ("action_label", "target_page"),
    (("Open maintenance", "maintenance"), ("Review anomalies", "anomaly")),
)
def test_assets_to_equipment_workflow_preserves_supported_context(
    action_label: str,
    target_page: str,
) -> None:
    """Asset investigation actions should retain exact equipment context."""
    app = _run_app()
    app.session_state["eoip_navigation_request"] = "assets"
    app.session_state["eoip_filter_plant"] = "Solar Plant D"
    app.session_state["eoip_filter_equipment"] = "INV-005"
    app.run(timeout=APP_TIMEOUT_SECONDS)

    next(button for button in app.button if button.label == action_label).click()
    app.run(timeout=APP_TIMEOUT_SECONDS)

    _assert_no_exceptions(app)
    assert app.session_state["eoip_active_page"] == target_page
    assert app.session_state["eoip_filter_plant"] == "Solar Plant D"
    assert app.session_state["eoip_filter_equipment"] == "INV-005"


def test_assets_to_plant_performance_preserves_plant_only() -> None:
    """Plant Performance should inherit plant context without fake equipment scope."""
    app = _run_app()
    app.session_state["eoip_navigation_request"] = "assets"
    app.session_state["eoip_filter_plant"] = "Solar Plant D"
    app.session_state["eoip_filter_equipment"] = "INV-005"
    app.run(timeout=APP_TIMEOUT_SECONDS)

    next(
        button for button in app.button if button.label == "Open plant performance"
    ).click()
    app.run(timeout=APP_TIMEOUT_SECONDS)

    _assert_no_exceptions(app)
    assert app.session_state["eoip_active_page"] == "plant_performance"
    assert app.session_state["eoip_filter_plant"] == "Solar Plant D"


@pytest.mark.parametrize(
    ("source_page", "action_label", "target_page", "keeps_equipment"),
    (
        ("anomaly", "Inspect asset", "assets", True),
        ("anomaly", "Review maintenance", "maintenance", True),
        ("anomaly", "Review operations", "operations", False),
        ("recommendations", "Inspect asset", "assets", True),
        ("recommendations", "Review maintenance", "maintenance", True),
        (
            "recommendations",
            "Review plant performance",
            "plant_performance",
            False,
        ),
        ("recommendations", "Review operations", "operations", False),
        ("maintenance", "Inspect asset", "assets", True),
        ("maintenance", "Review anomalies", "anomaly", True),
        ("maintenance", "Review operations", "operations", False),
        ("maintenance", "Review plant performance", "plant_performance", False),
    ),
)
def test_intelligence_to_action_workflows_preserve_supported_context(
    source_page: str,
    action_label: str,
    target_page: str,
    keeps_equipment: bool,
) -> None:
    """Phase F actions should preserve the maximum destination-supported scope."""
    app = _run_app()
    app.session_state["eoip_navigation_request"] = source_page
    app.session_state["eoip_filter_plant"] = "Solar Plant D"
    app.session_state["eoip_filter_equipment"] = "INV-005"
    app.run(timeout=APP_TIMEOUT_SECONDS)

    next(button for button in app.button if button.label == action_label).click()
    app.run(timeout=APP_TIMEOUT_SECONDS)

    _assert_no_exceptions(app)
    assert app.session_state["eoip_active_page"] == target_page
    assert app.session_state["eoip_filter_plant"] == "Solar Plant D"
    if keeps_equipment:
        assert app.session_state["eoip_filter_equipment"] == "INV-005"


def test_data_quality_renders_global_trust_evidence_without_fake_trends() -> None:
    """Data Quality should expose measured exceptions and platform scope."""
    app = _run_app()
    app.session_state["eoip_navigation_request"] = "data_quality"
    app.run(timeout=APP_TIMEOUT_SECONDS)

    _assert_no_exceptions(app)
    markup = " ".join(str(element.value) for element in app.markdown)
    assert "Trust Summary" in markup
    assert "Integrity &amp; Validation" in markup or "Integrity & Validation" in markup
    assert "Overall Quality Score" not in markup
    assert "Quality Trend" not in markup
    assert not app.metric


def test_administration_is_read_only_and_does_not_render_secrets() -> None:
    """Administration should present safe configured capabilities only."""
    app = _run_app()
    app.session_state["eoip_navigation_request"] = "administration"
    app.run(timeout=APP_TIMEOUT_SECONDS)

    _assert_no_exceptions(app)
    rendered = " ".join(
        [str(element.value) for element in app.markdown]
        + [frame.value.to_string() for frame in app.dataframe]
    ).casefold()
    assert "platform identity" in rendered
    assert "runtime readiness not verified" in rendered
    assert "database password" not in rendered
    assert "api token secret" not in rendered
    assert not app.toggle
