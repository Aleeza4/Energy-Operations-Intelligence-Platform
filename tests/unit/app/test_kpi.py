"""Focused tests for the reusable EOIP KPI component."""

from __future__ import annotations

import pytest

from eoip.app.components.kpi import (
    MetricCard,
    get_metric_icon,
    metric_card_markup,
    normalize_metric_value,
    resolve_delta_semantic,
)


def test_card_renders_label_value_delta_and_context() -> None:
    markup = metric_card_markup(
        MetricCard(
            label="Technical Availability",
            value="98.4%",
            delta="+1.2%",
            delta_semantic="positive",
        )
    )
    assert "Technical Availability" in markup
    assert "98.4%" in markup
    assert "1.2%" in markup
    assert "vs previous period" in markup
    assert "eoip-kpi-delta-positive" in markup


def test_delta_is_omitted_when_absent() -> None:
    markup = metric_card_markup(MetricCard(label="Plant Count", value="4"))
    assert "eoip-kpi-delta" not in markup


def test_help_is_omitted_without_content_and_rendered_when_meaningful() -> None:
    plain = metric_card_markup(MetricCard(label="Plant Count", value="4"))
    explained = metric_card_markup(
        MetricCard(
            label="Performance Ratio",
            value="81.6%",
            help_text="Actual output relative to theoretical output.",
        )
    )
    assert "eoip-kpi-help" not in plain
    assert "More information" in explained
    assert "Actual output relative to theoretical output." in explained


@pytest.mark.parametrize("missing", [None, float("nan"), "NaN", "undefined"])
def test_missing_values_render_as_em_dash(missing: object) -> None:
    assert normalize_metric_value(missing) == "—"  # type: ignore[arg-type]


def test_integer_values_receive_thousands_separators() -> None:
    assert normalize_metric_value(12457) == "12,457"


@pytest.mark.parametrize(
    ("semantic", "expected"),
    [
        ("positive", "positive"),
        ("negative", "negative"),
        ("neutral", "neutral"),
        ("unsupported", "neutral"),
    ],
)
def test_delta_semantics_resolve_safely(semantic: str, expected: str) -> None:
    assert resolve_delta_semantic(semantic) == expected


def test_metric_icon_uses_centralized_lucide_system_without_emoji() -> None:
    markup = metric_card_markup(MetricCard(label="Active Alarms", value="24"))
    assert get_metric_icon("Active Alarms") == "triangle-alert"
    assert 'viewBox="0 0 24 24"' in markup
    assert all(not (0x1F000 <= ord(character) <= 0x1FAFF) for character in markup)


def test_card_escapes_untrusted_content() -> None:
    markup = metric_card_markup(
        MetricCard(
            label='<script>alert("label")</script>',
            value='<img src=x onerror="alert(1)">',
            delta="+<b>5</b>",
            help_text='Helpful "detail" <script>bad</script>',
        )
    )
    assert "<script>" not in markup
    assert "<img" not in markup
    assert "<b>" not in markup
    assert "&lt;script&gt;" in markup
