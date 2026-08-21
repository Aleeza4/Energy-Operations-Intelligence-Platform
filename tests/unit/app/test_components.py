"""Unit tests for reusable EOIP Streamlit components."""

from __future__ import annotations

import pytest

from eoip.app.components.common import MetricCard


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
