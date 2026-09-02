"""Regression tests for EOIP operational-status messaging."""

from __future__ import annotations

from pathlib import Path

import pytest

from eoip.app.components.common import render_status

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DASHBOARD_DIR = PROJECT_ROOT / "src" / "eoip" / "app" / "dashboards"

DECORATIVE_MESSAGES = (
    "Portfolio intelligence is operational.",
    "Operations monitoring is active.",
    "Plant performance analytics are operational.",
    "Asset intelligence is operational.",
    "Alarm and incident monitoring is operational.",
    "Forecasting intelligence is operational.",
    "Anomaly detection is operational.",
    "Predictive-maintenance intelligence is operational.",
    "Optimization recommendations are operational.",
    "Data-quality monitoring is operational.",
    "EOIP platform services are operational.",
)


def test_decorative_success_messages_are_absent_from_dashboards() -> None:
    production_source = "\n".join(
        path.read_text(encoding="utf-8") for path in DASHBOARD_DIR.glob("*.py")
    )
    for message in DECORATIVE_MESSAGES:
        assert message not in production_source


def test_no_static_dashboard_success_alerts_or_fake_live_badges() -> None:
    production_source = "\n".join(
        path.read_text(encoding="utf-8") for path in DASHBOARD_DIR.glob("*.py")
    )
    assert 'level="success"' not in production_source
    assert "st.success(" not in production_source
    assert "Live</" not in production_source


@pytest.mark.parametrize(
    ("level", "renderer_name"),
    [
        ("success", "success"),
        ("warning", "warning"),
        ("error", "error"),
        ("info", "info"),
    ],
)
def test_shared_status_component_preserves_meaningful_feedback(
    level: str,
    renderer_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rendered: list[str] = []
    monkeypatch.setattr(
        f"eoip.app.components.common.st.{renderer_name}",
        rendered.append,
    )

    messages = {
        "success": "Configuration saved successfully.",
        "warning": "SCADA data is stale.",
        "error": "Unable to connect to database.",
        "info": "No forecast is available for the selected period.",
    }
    render_status(messages[level], level=level)  # type: ignore[arg-type]
    assert rendered == [messages[level]]


def test_no_emoji_status_indicators_are_introduced() -> None:
    production_source = "\n".join(
        path.read_text(encoding="utf-8") for path in DASHBOARD_DIR.glob("*.py")
    )
    assert all(
        not (0x1F000 <= ord(character) <= 0x1FAFF) for character in production_source
    )
