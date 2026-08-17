"""
Unit tests for the EOIP RevenueMeter domain model.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from eoip.synthetic.models.meter import (
    MeterAccuracyClass,
    MeterStatus,
    RevenueMeter,
)


def _meter(**overrides: object) -> RevenueMeter:
    """Return a valid revenue meter with optional overrides."""
    data: dict[str, object] = {
        "meter_id": "MTR-00001",
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "meter_name": "Primary Settlement Meter",
        "manufacturer": "Schneider Electric",
        "model_number": "ION-9000",
        "serial_number": "SN-MTR-00001",
        "accuracy_class": MeterAccuracyClass.CLASS_02S,
        "multiplier": 1_000.0,
        "calibration_date": date(2025, 1, 15),
        "status": MeterStatus.ACTIVE,
        "is_primary": True,
        "notes": "Main point-of-interconnection revenue meter.",
    }
    data.update(overrides)
    return RevenueMeter(**data)


def test_valid_construction() -> None:
    """Verify a valid revenue meter can be created."""
    meter = _meter()

    assert meter.meter_id == "MTR-00001"
    assert meter.plant_id == "PLANT-001"
    assert meter.equipment_id == "EQP-00001"
    assert meter.accuracy_class is MeterAccuracyClass.CLASS_02S
    assert meter.status is MeterStatus.ACTIVE


def test_normalizes_identifiers_and_text() -> None:
    """Verify identifiers and text fields are normalized."""
    meter = _meter(
        meter_id="  mtr-00001  ",
        plant_id="  plant-001  ",
        equipment_id="  eqp-00001  ",
        meter_name="  Primary Settlement Meter  ",
        manufacturer="  Schneider Electric  ",
        model_number="  ion-9000  ",
        serial_number="  sn-mtr-00001  ",
        notes="  Main settlement meter.  ",
    )

    assert meter.meter_id == "MTR-00001"
    assert meter.plant_id == "PLANT-001"
    assert meter.equipment_id == "EQP-00001"
    assert meter.meter_name == "Primary Settlement Meter"
    assert meter.manufacturer == "Schneider Electric"
    assert meter.model_number == "ION-9000"
    assert meter.serial_number == "SN-MTR-00001"
    assert meter.notes == "Main settlement meter."


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("meter_id", "METER-00001", "Invalid meter_id"),
        ("plant_id", "PL-001", "Invalid plant_id"),
        ("equipment_id", "EQUIP-00001", "Invalid equipment_id"),
    ],
)
def test_rejects_invalid_identifiers(
    field_name: str,
    value: str,
    message: str,
) -> None:
    """Verify malformed identifiers are rejected."""
    with pytest.raises(ValueError, match=message):
        _meter(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "meter_name",
        "manufacturer",
        "model_number",
        "serial_number",
    ],
)
def test_rejects_empty_required_text(field_name: str) -> None:
    """Verify required text fields cannot be empty."""
    with pytest.raises(ValueError, match=f"{field_name} cannot be empty"):
        _meter(**{field_name: "   "})


@pytest.mark.parametrize(
    ("field_name", "maximum_length"),
    [
        ("meter_name", 150),
        ("manufacturer", 100),
        ("model_number", 100),
        ("serial_number", 100),
    ],
)
def test_rejects_required_text_above_maximum_length(
    field_name: str,
    maximum_length: int,
) -> None:
    """Verify required text fields enforce maximum lengths."""
    with pytest.raises(ValueError, match=field_name):
        _meter(**{field_name: "X" * (maximum_length + 1)})


def test_notes_can_be_none() -> None:
    """Verify notes are optional."""
    meter = _meter(notes=None)

    assert meter.notes is None


def test_rejects_empty_notes() -> None:
    """Verify blank notes must be represented as None."""
    with pytest.raises(ValueError, match="notes cannot be empty"):
        _meter(notes="   ")


def test_rejects_notes_above_maximum_length() -> None:
    """Verify notes enforce the maximum length."""
    with pytest.raises(ValueError, match="notes"):
        _meter(notes="X" * 1_001)


def test_rejects_invalid_accuracy_class_type() -> None:
    """Verify accuracy_class must use MeterAccuracyClass."""
    with pytest.raises(TypeError, match="MeterAccuracyClass"):
        _meter(accuracy_class="0.2s")


def test_rejects_invalid_status_type() -> None:
    """Verify status must use MeterStatus."""
    with pytest.raises(TypeError, match="MeterStatus"):
        _meter(status="active")


@pytest.mark.parametrize("value", [True, "1000", None])
def test_rejects_non_numeric_multiplier(value: object) -> None:
    """Verify multiplier must be numeric and not Boolean."""
    with pytest.raises(TypeError, match="multiplier must be numeric"):
        _meter(multiplier=value)


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_rejects_non_finite_multiplier(value: float) -> None:
    """Verify multiplier must be finite."""
    with pytest.raises(ValueError, match="multiplier must be finite"):
        _meter(multiplier=value)


@pytest.mark.parametrize("value", [0.0, -1.0])
def test_rejects_non_positive_multiplier(value: float) -> None:
    """Verify multiplier must be greater than zero."""
    with pytest.raises(ValueError, match="greater than zero"):
        _meter(multiplier=value)


def test_rejects_invalid_calibration_date_type() -> None:
    """Verify calibration_date must be a date."""
    with pytest.raises(TypeError, match="calibration_date must be a date"):
        _meter(calibration_date="2025-01-15")


def test_rejects_invalid_is_primary_type() -> None:
    """Verify is_primary must be Boolean."""
    with pytest.raises(TypeError, match="is_primary must be a boolean"):
        _meter(is_primary=1)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (MeterStatus.ACTIVE, True),
        (MeterStatus.CALIBRATION_DUE, True),
        (MeterStatus.OUT_OF_SERVICE, False),
        (MeterStatus.RETIRED, False),
    ],
)
def test_is_operational(
    status: MeterStatus,
    expected: bool,
) -> None:
    """Verify settlement-availability classification."""
    assert _meter(status=status).is_operational is expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (MeterStatus.ACTIVE, False),
        (MeterStatus.CALIBRATION_DUE, True),
        (MeterStatus.OUT_OF_SERVICE, True),
        (MeterStatus.RETIRED, False),
    ],
)
def test_requires_attention(
    status: MeterStatus,
    expected: bool,
) -> None:
    """Verify operational-attention classification."""
    assert _meter(status=status).requires_attention is expected


@pytest.mark.parametrize(
    ("raw_value", "multiplier", "expected"),
    [
        (0.0, 1_000.0, 0.0),
        (12.5, 1_000.0, 12_500.0),
        (123.456789, 2.5, 308.641973),
    ],
)
def test_apply_multiplier(
    raw_value: float,
    multiplier: float,
    expected: float,
) -> None:
    """Verify raw register readings are scaled correctly."""
    meter = _meter(multiplier=multiplier)

    assert meter.apply_multiplier(raw_value) == expected


@pytest.mark.parametrize("value", [True, "10", None])
def test_apply_multiplier_rejects_invalid_types(value: object) -> None:
    """Verify raw register values must be numeric."""
    meter = _meter()

    with pytest.raises(TypeError, match="raw_register_value must be numeric"):
        meter.apply_multiplier(value)


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_apply_multiplier_rejects_non_finite_values(value: float) -> None:
    """Verify raw register values must be finite."""
    meter = _meter()

    with pytest.raises(ValueError, match="raw_register_value must be finite"):
        meter.apply_multiplier(value)


def test_apply_multiplier_rejects_negative_value() -> None:
    """Verify raw register values cannot be negative."""
    meter = _meter()

    with pytest.raises(ValueError, match="greater than or equal to zero"):
        meter.apply_multiplier(-1.0)


def test_to_record_serializes_all_values() -> None:
    """Verify meter records are serialization-ready."""
    meter = _meter()

    assert meter.to_record() == {
        "meter_id": "MTR-00001",
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "meter_name": "Primary Settlement Meter",
        "manufacturer": "Schneider Electric",
        "model_number": "ION-9000",
        "serial_number": "SN-MTR-00001",
        "accuracy_class": MeterAccuracyClass.CLASS_02S.value,
        "multiplier": 1_000.0,
        "calibration_date": "2025-01-15",
        "status": MeterStatus.ACTIVE.value,
        "is_primary": True,
        "notes": "Main point-of-interconnection revenue meter.",
        "is_operational": True,
        "requires_attention": False,
    }


def test_to_record_handles_none_notes() -> None:
    """Verify optional notes serialize as None."""
    record = _meter(notes=None).to_record()

    assert record["notes"] is None


def test_model_is_immutable() -> None:
    """Verify the frozen dataclass cannot be modified."""
    meter = _meter()

    with pytest.raises(FrozenInstanceError):
        meter.status = MeterStatus.RETIRED  # type: ignore[misc]


def test_slots_prevent_dynamic_attributes() -> None:
    """Verify slots prevent undeclared attributes."""
    meter = _meter()

    with pytest.raises((AttributeError, TypeError)):
        meter.unexpected_field = "value"


def test_enum_values_are_stable() -> None:
    """Verify public enum values remain stable."""
    assert tuple(MeterAccuracyClass) == (
        MeterAccuracyClass.CLASS_02S,
        MeterAccuracyClass.CLASS_05S,
        MeterAccuracyClass.CLASS_1,
    )
    assert tuple(MeterStatus) == (
        MeterStatus.ACTIVE,
        MeterStatus.OUT_OF_SERVICE,
        MeterStatus.CALIBRATION_DUE,
        MeterStatus.RETIRED,
    )
