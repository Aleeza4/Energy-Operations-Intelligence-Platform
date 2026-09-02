"""Focused Phase F intelligence-to-action derivation tests."""

from __future__ import annotations

import pandas as pd
import pytest

from eoip.app import data_access
from eoip.app.dashboards.anomaly import build_anomaly_priority
from eoip.app.dashboards.forecast import calculate_forecast_variance
from eoip.app.dashboards.maintenance import (
    build_maintenance_priority,
    related_maintenance_evidence,
)
from eoip.app.dashboards.recommendations import (
    aggregate_recommendation_impact,
    build_recommendation_priority,
)


def test_forecast_variance_and_zero_denominator() -> None:
    """Forecast variance uses actual minus forecast and handles zero safely."""
    assert calculate_forecast_variance(90.0, 100.0) == (-10.0, -10.0)
    assert calculate_forecast_variance(12.0, 0.0) == (12.0, None)


def test_anomaly_priority_uses_declared_severity_then_score() -> None:
    """Anomaly queue ordering must be deterministic and assumption-free."""
    priority = build_anomaly_priority(data_access.get_anomalies())

    assert priority["Anomaly ID"].tolist() == [
        "ANM-2031",
        "ANM-2028",
        "ANM-2026",
        "ANM-2022",
    ]


def test_empty_anomaly_priority_is_safe() -> None:
    """An empty anomaly source remains empty without fabricated rows."""
    assert build_anomaly_priority(pd.DataFrame()).empty


def test_recommendation_priority_uses_existing_rank() -> None:
    """Recommendations must retain the source priority semantics."""
    priority = build_recommendation_priority(data_access.get_recommendations())

    assert priority["Priority Rank"].tolist() == [1, 2, 3, 4, 5]


def test_recommendation_impacts_remain_separate() -> None:
    """Energy and financial impacts are aggregated without a composite score."""
    energy, financial = aggregate_recommendation_impact(
        data_access.get_recommendations()
    )

    assert energy == 16900.0
    assert financial is None
    assert aggregate_recommendation_impact(pd.DataFrame()) == (0.0, None)


def test_maintenance_priority_uses_existing_rank() -> None:
    """Maintenance ordering must not calculate a replacement score."""
    priority = build_maintenance_priority(data_access.get_maintenance_priorities())

    assert priority["Equipment ID"].tolist()[:3] == [
        "INV-005",
        "TRF-004",
        "INV-003",
    ]


def test_maintenance_evidence_requires_exact_composite_identity() -> None:
    """Related evidence must match both plant and equipment identifiers."""
    item = data_access.get_maintenance_priorities().iloc[0]
    incidents, anomalies, recommendations = related_maintenance_evidence(item)

    assert incidents["Incident ID"].tolist() == ["INC-1042"]
    assert anomalies["Anomaly ID"].tolist() == ["ANM-2031"]
    assert recommendations["Equipment ID"].tolist() == ["INV-005"]


def test_maintenance_empty_priority_is_safe() -> None:
    """Empty maintenance input must not create attention records."""
    assert build_maintenance_priority(pd.DataFrame()).empty


@pytest.mark.parametrize(
    "builder",
    (build_anomaly_priority, build_recommendation_priority, build_maintenance_priority),
)
def test_derivations_do_not_mutate_sources(builder) -> None:
    """Phase F queue derivations must preserve immutable source handling."""
    source = pd.DataFrame()
    original = source.copy(deep=True)

    builder(source)

    pd.testing.assert_frame_equal(source, original)
