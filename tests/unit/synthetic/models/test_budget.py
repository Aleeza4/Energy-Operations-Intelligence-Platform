"""
Unit tests for the EOIP budget domain model.
"""

from __future__ import annotations

import math
from dataclasses import FrozenInstanceError
from datetime import date
from typing import Any

import pytest

from eoip.synthetic.models.budget import (
    Budget,
    BudgetCategory,
    BudgetStatus,
)


def _make_budget(**overrides: Any) -> Budget:
    data = {
        "budget_id": "BUD-00001",
        "plant_id": "PLANT-001",
        "budget_name": "Annual Maintenance",
        "category": BudgetCategory.MAINTENANCE,
        "fiscal_year": 2026,
        "allocated_amount": 1_000_000.0,
        "spent_amount": 250_000.0,
        "currency_code": "PKR",
        "approved_on": date(2026, 1, 1),
        "status": BudgetStatus.APPROVED,
    }
    data.update(overrides)
    return Budget(**data)


def test_budget_preserves_valid_fields() -> None:
    b = _make_budget()
    assert b.budget_id == "BUD-00001"
    assert b.plant_id == "PLANT-001"
    assert b.category is BudgetCategory.MAINTENANCE
    assert b.status is BudgetStatus.APPROVED


def test_budget_normalizes_text() -> None:
    b = _make_budget(
        budget_id=" bud-00001 ",
        plant_id=" plant-001 ",
        budget_name=" Annual Maintenance ",
        currency_code=" pkr ",
    )
    assert b.budget_id == "BUD-00001"
    assert b.plant_id == "PLANT-001"
    assert b.budget_name == "Annual Maintenance"
    assert b.currency_code == "PKR"


def test_remaining_amount() -> None:
    assert _make_budget().remaining_amount == 750000.0


def test_utilization_percentage() -> None:
    assert _make_budget().utilization_pct == 25.0


def test_budget_not_over_budget() -> None:
    assert _make_budget().is_over_budget is False


def test_to_record() -> None:
    record = _make_budget().to_record()
    assert record["category"] == "maintenance"
    assert record["status"] == "approved"
    assert record["remaining_amount"] == 750000.0
    assert record["utilization_pct"] == 25.0


def test_budget_is_immutable() -> None:
    b = _make_budget()
    with pytest.raises(FrozenInstanceError):
        b.budget_name = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize("value", ["", "BUD-1", "ABC"])
def test_invalid_budget_id(value: str) -> None:
    with pytest.raises(ValueError):
        _make_budget(budget_id=value)


@pytest.mark.parametrize("value", ["", "SITE-001", "PLANT-1"])
def test_invalid_plant_id(value: str) -> None:
    with pytest.raises(ValueError):
        _make_budget(plant_id=value)


@pytest.mark.parametrize("value", [-1.0, -100.0])
def test_negative_amounts(value: float) -> None:
    with pytest.raises(ValueError):
        _make_budget(allocated_amount=value)


def test_spent_cannot_exceed_allocated() -> None:
    with pytest.raises(ValueError):
        _make_budget(spent_amount=2_000_000.0)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_amounts(value: float) -> None:
    with pytest.raises(ValueError):
        _make_budget(allocated_amount=value)


def test_approved_requires_date() -> None:
    with pytest.raises(ValueError):
        _make_budget(approved_on=None)


@pytest.mark.parametrize("category", list(BudgetCategory))
def test_accepts_all_categories(category: BudgetCategory) -> None:
    assert _make_budget(category=category).category is category


@pytest.mark.parametrize("status", [BudgetStatus.DRAFT, BudgetStatus.CLOSED])
def test_accepts_other_statuses(status: BudgetStatus) -> None:
    kwargs = {"status": status}
    if status is BudgetStatus.DRAFT:
        kwargs["approved_on"] = None
    assert _make_budget(**kwargs).status is status
