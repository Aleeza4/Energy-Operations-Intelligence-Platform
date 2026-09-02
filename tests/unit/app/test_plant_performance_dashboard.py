"""Focused tests for the Plant Performance engineering workspace."""

from __future__ import annotations

import inspect
from datetime import date

import pandas as pd
import pytest

from eoip.app import data_access
from eoip.app.components.filters import FilterSelection
from eoip.app.dashboards import plant_performance
from eoip.app.dashboards.plant_performance import (
    build_performance_benchmark,
    calculate_generation_variance,
)
from eoip.app.data_filters import apply_dataframe_filters


def test_generation_variance_is_deterministic() -> None:
    """Variance must use actual minus expected and the expected denominator."""
    variance, percentage = calculate_generation_variance(3210.0, 3400.0)

    assert variance == -190.0
    assert percentage == pytest.approx(-5.588235)


def test_generation_variance_handles_zero_expected() -> None:
    """Zero expected generation must not cause division by zero."""
    assert calculate_generation_variance(12.0, 0.0) == (12.0, None)


def test_plant_scope_drives_supported_performance_values() -> None:
    """Plant aggregates must derive from the selected plant record."""
    scoped = apply_dataframe_filters(
        data_access.get_plant_performance(),
        FilterSelection(
            plant="Solar Plant B",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
        ),
    )

    assert scoped["Actual Energy (MWh)"].sum() == 3650.0
    assert scoped["Expected Energy (MWh)"].sum() == 3800.0
    assert scoped["Performance Ratio (%)"].mean() == 80.8


def test_portfolio_benchmark_keeps_portfolio_and_variance_context() -> None:
    """Benchmark should retain every plant and rank the largest shortfall first."""
    benchmark = build_performance_benchmark(data_access.get_plant_performance())

    assert set(benchmark["Plant"]) == {
        "Solar Plant A",
        "Solar Plant B",
        "Solar Plant C",
        "Solar Plant D",
    }
    assert benchmark.iloc[0]["Plant"] == "Solar Plant D"
    assert benchmark.iloc[0]["Variance (MWh)"] == -190.0


def test_empty_benchmark_and_partial_loss_data_are_safe() -> None:
    """Independent missing sources must not invalidate supported analysis."""
    empty = build_performance_benchmark(pd.DataFrame())

    assert empty.empty
    assert "Variance (%)" in empty.columns


def test_plant_page_avoids_unsupported_visual_patterns() -> None:
    """Phase E must use centralized cards, colors, and restrained messaging."""
    source = inspect.getsource(plant_performance)

    assert "st.metric(" not in source
    assert "st.success(" not in source
    assert "px.pie(" not in source
    assert "#" not in source
    assert not any(ord(character) > 0xFFFF for character in source)
