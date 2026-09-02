"""Behavior tests for the Executive Portfolio Command Dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from eoip.app import data_access
from eoip.app.dashboards.executive import (
    _recommendation_data,
    _risk_data,
    build_attention_queue,
    build_management_priorities,
    build_plant_comparison,
    derive_portfolio_summary,
)


def test_portfolio_status_derives_every_kpi_from_source_frames() -> None:
    summary = derive_portfolio_summary(
        data_access.get_plant_performance(), _risk_data(), _recommendation_data()
    )

    assert summary.actual_energy_mwh == 15360.0
    assert summary.expected_energy_mwh == 15850.0
    assert summary.generation_variance_percent == pytest.approx(-3.09148265)
    assert summary.performance_ratio_percent == pytest.approx(81.55)
    assert summary.critical_assets == 3
    assert summary.recoverable_opportunity is None


def test_performance_comparison_is_ranked_and_derived_from_plant_data() -> None:
    source = data_access.get_plant_performance()
    comparison = build_plant_comparison(source)

    assert comparison["Plant"].tolist() == [
        "Solar Plant D",
        "Solar Plant B",
        "Solar Plant A",
        "Solar Plant C",
    ]
    assert comparison["Variance (MWh)"].tolist() == [
        -190.0,
        -150.0,
        -130.0,
        -20.0,
    ]
    assert set(comparison["Status"]) == {"Below plan"}
    assert "Variance (MWh)" not in source.columns


def test_attention_queue_prioritizes_largest_supported_shortfall() -> None:
    attention = build_attention_queue(data_access.get_plant_performance())

    assert attention.iloc[0].to_dict() == {
        "Plant": "Solar Plant D",
        "Issue": "Generation below expected",
        "Impact": "190 MWh shortfall",
        "Status": "Below plan",
    }


def test_management_priorities_use_declared_priority_without_fake_money() -> None:
    priorities = build_management_priorities(_recommendation_data())

    assert priorities["Priority"].tolist() == [
        "Critical",
        "High",
        "High",
        "Medium",
    ]
    assert priorities["Plant"].tolist()[:3] == [
        "Solar Plant D",
        "Solar Plant B",
        "Solar Plant D",
    ]
    assert "Estimated Impact ($)" not in priorities
    assert priorities["Governance Status"].eq("PROPOSED").all()


def test_empty_and_partial_sources_do_not_create_fake_values() -> None:
    empty = pd.DataFrame()
    summary = derive_portfolio_summary(empty, empty, _recommendation_data())

    assert summary.actual_energy_mwh is None
    assert summary.generation_variance_percent is None
    assert summary.critical_assets is None
    assert summary.recoverable_opportunity is None
    assert build_plant_comparison(empty).empty
    assert build_attention_queue(empty).empty
    assert build_management_priorities(empty).empty


def test_executive_source_contains_no_fixed_cards_or_local_visual_hacks() -> None:
    source = Path("src/eoip/app/dashboards/executive.py").read_text(encoding="utf-8")

    assert 'value="15.36 GWh"' not in source
    assert "st.metric(" not in source
    assert "#0" not in source
    assert "Live" not in source
    assert all(not (0x1F000 <= ord(character) <= 0x1FAFF) for character in source)
    assert "Estimated Impact ($)" not in source
    assert 'value=f"$' not in source
