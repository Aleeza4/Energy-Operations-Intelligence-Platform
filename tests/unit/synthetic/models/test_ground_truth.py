"""
Unit tests for the EOIP ground-truth event domain model.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from eoip.synthetic.models.ground_truth import (
    GroundTruthEvent,
    GroundTruthEventType,
    GroundTruthSeverity,
)


def _start() -> datetime:
    return datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


def _make_event(**overrides: Any) -> GroundTruthEvent:
    data = {
        "ground_truth_id": "GTE-0000001",
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "event_type": GroundTruthEventType.EQUIPMENT_FAILURE,
        "severity": GroundTruthSeverity.CRITICAL,
        "started_at": _start(),
        "ended_at": _start() + timedelta(minutes=45),
        "expected_power_loss_pct": 100.0,
        "expected_energy_loss_kwh": 75.0,
        "description": "Inverter forced outage.",
    }
    data.update(overrides)
    return GroundTruthEvent(**data)


def test_preserves_fields() -> None:
    e = _make_event()
    assert e.ground_truth_id == "GTE-0000001"
    assert e.plant_id == "PLANT-001"
    assert e.equipment_id == "EQP-00001"
    assert e.is_equipment_specific is True
    assert e.is_critical is True
    assert e.duration_seconds == 2700.0


def test_normalizes_fields() -> None:
    e = _make_event(
        ground_truth_id=" gte-0000001 ",
        plant_id=" plant-001 ",
        equipment_id=" eqp-00001 ",
        description=" Test ",
    )
    assert e.ground_truth_id == "GTE-0000001"
    assert e.plant_id == "PLANT-001"
    assert e.equipment_id == "EQP-00001"
    assert e.description == "Test"


def test_to_record() -> None:
    r = _make_event().to_record()
    assert r["event_type"] == "equipment_failure"
    assert r["severity"] == "critical"
    assert r["duration_seconds"] == 2700.0
    assert r["is_equipment_specific"] is True
    assert r["is_critical"] is True


def test_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        _make_event().description = "x"  # type: ignore[misc]


@pytest.mark.parametrize("value", ["", "GTE-1", "ABC"])
def test_invalid_ground_truth_id(value: str) -> None:
    with pytest.raises(ValueError):
        _make_event(ground_truth_id=value)


@pytest.mark.parametrize("value", ["", "SITE-001", "PLANT-1"])
def test_invalid_plant_id(value: str) -> None:
    with pytest.raises(ValueError):
        _make_event(plant_id=value)


@pytest.mark.parametrize("value", ["EQP-1", "ABC", ""])
def test_invalid_equipment_id(value: str) -> None:
    with pytest.raises(ValueError):
        _make_event(equipment_id=value)


@pytest.mark.parametrize("field", ["event_type", "severity"])
def test_invalid_enums(field: str) -> None:
    with pytest.raises(TypeError):
        _make_event(**{field: "bad"})


def test_end_after_start_required() -> None:
    with pytest.raises(ValueError):
        _make_event(ended_at=_start())


@pytest.mark.parametrize("field", ["started_at", "ended_at"])
def test_timezone_required(field: str) -> None:
    naive = datetime(2026, 1, 15, 12, 0)
    with pytest.raises(ValueError):
        _make_event(**{field: naive})


@pytest.mark.parametrize(
    "field,value",
    [
        ("expected_power_loss_pct", -1.0),
        ("expected_power_loss_pct", 101.0),
        ("expected_energy_loss_kwh", -1.0),
    ],
)
def test_invalid_numeric_ranges(field: str, value: float) -> None:
    with pytest.raises(ValueError):
        _make_event(**{field: value})


def test_none_equipment_is_allowed() -> None:
    e = _make_event(equipment_id=None)
    assert e.is_equipment_specific is False
