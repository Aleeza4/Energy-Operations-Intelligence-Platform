"""Unit tests for reusable EOIP Streamlit components."""

from __future__ import annotations

import pytest

from eoip.app.components.common import (
    MetricCard,
    PageContext,
    page_context_markup,
    render_page_context,
    render_page_intro,
)


class TestMetricCard:
    """Tests for reusable EOIP metric-card configuration."""

    def test_accepts_valid_metric(self) -> None:
        metric = MetricCard(
            label="Performance Ratio",
            value="82.4%",
            delta="+1.8%",
            help_text="Current portfolio PR.",
        )

        assert metric.label == "Performance Ratio"
        assert metric.value == "82.4%"
        assert metric.delta == "+1.8%"

    def test_accepts_metric_without_optional_fields(
        self,
    ) -> None:
        metric = MetricCard(
            label="Plant Count",
            value="12",
        )

        assert metric.delta is None
        assert metric.help_text is None

    def test_rejects_empty_label(self) -> None:
        with pytest.raises(
            ValueError,
            match="Metric label must not be empty.",
        ):
            MetricCard(
                label=" ",
                value="100",
            )

    def test_rejects_empty_value(self) -> None:
        with pytest.raises(
            ValueError,
            match="Metric value must not be empty.",
        ):
            MetricCard(
                label="Availability",
                value=" ",
            )


def test_page_intro_renders_shared_lucide_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rendered: list[tuple[str, bool]] = []

    def capture_markdown(markup: str, *, unsafe_allow_html: bool) -> None:
        rendered.append((markup, unsafe_allow_html))

    monkeypatch.setattr("eoip.app.components.common.st.markdown", capture_markdown)

    render_page_intro(
        title="Executive Dashboard",
        description="Portfolio intelligence.",
        icon="executive",
    )

    markup, unsafe_allow_html = rendered[0]
    assert unsafe_allow_html is True
    assert "eoip-page-header" in markup
    assert "Executive Dashboard" in markup
    assert 'viewBox="0 0 24 24"' in markup
    assert 'width="24"' in markup


def test_page_context_renders_full_known_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rendered: list[str] = []
    monkeypatch.setattr(
        "eoip.app.components.common.st.markdown",
        lambda markup, **_: rendered.append(markup),
    )

    render_page_context(
        PageContext(
            scope="Solar Plant A / INV-001",
            period="01 Aug 2026 – 24 Aug 2026",
            freshness="24 Aug 2026 10:42 UTC",
        )
    )

    assert len(rendered) == 1
    assert all(label in rendered[0] for label in ("Scope", "Period", "As of"))


def test_page_context_omits_missing_values_and_fake_live_state() -> None:
    markup = page_context_markup(PageContext(scope="Portfolio"))

    assert "Portfolio" in markup
    assert "Period" not in markup
    assert "As of" not in markup
    assert "Live" not in markup


def test_page_context_with_no_known_values_renders_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rendered: list[str] = []
    monkeypatch.setattr(
        "eoip.app.components.common.st.markdown",
        lambda markup, **_: rendered.append(markup),
    )

    render_page_context(PageContext())

    assert rendered == []
