"""
Unit tests for the EOIP common equipment domain model.

These tests verify valid equipment construction, normalization, serialization,
derived properties, immutability, and rejection of invalid master data.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date, datetime, timedelta
from typing import Any

import pytest

from eoip.synthetic.models.equipment import (
    Equipment,
    EquipmentStatus,
    EquipmentType,
)


def _make_equipment(**overrides: Any) -> Equipment:
    """Create a valid Equipment instance with optional field overrides."""
    equipment_data: dict[str, Any] = {
        "equipment_id": "EQP-00001",
        "plant_id": "PLANT-001",
        "equipment_name": "String Inverter 001",
        "equipment_type": EquipmentType.STRING_INVERTER,
        "manufacturer": "SMA",
        "model_number": "SUNNY-HIGHPOWER",
        "serial_number": "SMA-000001",
        "commissioning_date": date(2020, 1, 15),
        "rated_power_kw": 100.0,
        "parent_equipment_id": None,
        "status": EquipmentStatus.OPERATIONAL,
    }
    equipment_data.update(overrides)
    return Equipment(**equipment_data)


def test_equipment_creation_preserves_valid_fields() -> None:
    """A valid equipment record should retain all supplied values."""
    equipment = _make_equipment()

    assert equipment.equipment_id == "EQP-00001"
    assert equipment.plant_id == "PLANT-001"
    assert equipment.equipment_name == "String Inverter 001"
    assert equipment.equipment_type is EquipmentType.STRING_INVERTER
    assert equipment.manufacturer == "SMA"
    assert equipment.model_number == "SUNNY-HIGHPOWER"
    assert equipment.serial_number == "SMA-000001"
    assert equipment.commissioning_date == date(2020, 1, 15)
    assert equipment.rated_power_kw == 100.0
    assert equipment.parent_equipment_id is None
    assert equipment.status is EquipmentStatus.OPERATIONAL


def test_equipment_normalizes_text_fields() -> None:
    """Equipment identifiers and text fields should be normalized."""
    equipment = _make_equipment(
        equipment_id=" eqp-00001 ",
        plant_id=" plant-001 ",
        equipment_name=" String Inverter 001 ",
        manufacturer=" SMA ",
        model_number=" sunny-highpower ",
        serial_number=" sma-000001 ",
        parent_equipment_id=" eqp-00002 ",
    )

    assert equipment.equipment_id == "EQP-00001"
    assert equipment.plant_id == "PLANT-001"
    assert equipment.equipment_name == "String Inverter 001"
    assert equipment.manufacturer == "SMA"
    assert equipment.model_number == "SUNNY-HIGHPOWER"
    assert equipment.serial_number == "SMA-000001"
    assert equipment.parent_equipment_id == "EQP-00002"


def test_equipment_uses_expected_default_values() -> None:
    """Optional fields should use the documented defaults."""
    equipment = Equipment(
        equipment_id="EQP-00001",
        plant_id="PLANT-001",
        equipment_name="Protection Relay 001",
        equipment_type=EquipmentType.PROTECTION_RELAY,
        manufacturer="ABB",
        model_number="RELION-615",
        serial_number="ABB-REL-00001",
        commissioning_date=date(2020, 1, 15),
    )

    assert equipment.rated_power_kw is None
    assert equipment.parent_equipment_id is None
    assert equipment.status is EquipmentStatus.OPERATIONAL


@pytest.mark.parametrize(
    ("equipment_type", "expected"),
    [
        (EquipmentType.STRING_INVERTER, True),
        (EquipmentType.CENTRAL_INVERTER, True),
        (EquipmentType.TRANSFORMER, False),
        (EquipmentType.FEEDER, False),
        (EquipmentType.WEATHER_STATION, False),
        (EquipmentType.REVENUE_METER, False),
        (EquipmentType.PROTECTION_RELAY, False),
    ],
)
def test_is_generation_equipment(
    equipment_type: EquipmentType,
    expected: bool,
) -> None:
    """Only string and central inverters should be generation equipment."""
    equipment = _make_equipment(equipment_type=equipment_type)

    assert equipment.is_generation_equipment is expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (EquipmentStatus.OPERATIONAL, True),
        (EquipmentStatus.PLANNED_OUTAGE, False),
        (EquipmentStatus.FORCED_OUTAGE, False),
        (EquipmentStatus.MAINTENANCE, False),
        (EquipmentStatus.DECOMMISSIONED, False),
    ],
)
def test_is_available(
    status: EquipmentStatus,
    expected: bool,
) -> None:
    """Only operational equipment should be classified as available."""
    equipment = _make_equipment(status=status)

    assert equipment.is_available is expected


def test_to_record_returns_complete_serialized_record() -> None:
    """Serialization should return a complete DataFrame-ready dictionary."""
    equipment = _make_equipment(parent_equipment_id="EQP-00002")

    assert equipment.to_record() == {
        "equipment_id": "EQP-00001",
        "plant_id": "PLANT-001",
        "equipment_name": "String Inverter 001",
        "equipment_type": "string_inverter",
        "manufacturer": "SMA",
        "model_number": "SUNNY-HIGHPOWER",
        "serial_number": "SMA-000001",
        "commissioning_date": "2020-01-15",
        "rated_power_kw": 100.0,
        "parent_equipment_id": "EQP-00002",
        "status": "operational",
        "is_generation_equipment": True,
        "is_available": True,
    }


def test_to_record_preserves_none_optional_fields() -> None:
    """Serialization should retain None for optional unset fields."""
    equipment = _make_equipment(
        rated_power_kw=None,
        parent_equipment_id=None,
    )

    record = equipment.to_record()

    assert record["rated_power_kw"] is None
    assert record["parent_equipment_id"] is None


def test_equipment_is_immutable() -> None:
    """Equipment instances should reject field modification."""
    equipment = _make_equipment()

    with pytest.raises(FrozenInstanceError):
        equipment.equipment_name = "Changed Name"  # type: ignore[misc]


@pytest.mark.parametrize(
    "equipment_id",
    [
        "",
        "   ",
        "EQP-1",
        "EQP-0001",
        "EQP-000001",
        "EQUIPMENT-00001",
        "EQP-ABCDE",
        "EQP_00001",
        "SITE-00001",
    ],
)
def test_equipment_rejects_invalid_equipment_id(
    equipment_id: str,
) -> None:
    """Equipment IDs must follow the EQP-00001 format."""
    with pytest.raises(
        ValueError,
        match="Invalid equipment_id",
    ):
        _make_equipment(equipment_id=equipment_id)


@pytest.mark.parametrize(
    "plant_id",
    [
        "",
        "   ",
        "PLANT-1",
        "PLANT-01",
        "PLANT-0001",
        "SITE-001",
        "PLANT-ABC",
        "PLANT_001",
    ],
)
def test_equipment_rejects_invalid_plant_id(
    plant_id: str,
) -> None:
    """Plant IDs must follow the PLANT-001 format."""
    with pytest.raises(
        ValueError,
        match="Invalid plant_id",
    ):
        _make_equipment(plant_id=plant_id)


@pytest.mark.parametrize(
    "equipment_name",
    ["", "   ", "\t", "\n"],
)
def test_equipment_rejects_empty_equipment_name(
    equipment_name: str,
) -> None:
    """Equipment names must contain visible text."""
    with pytest.raises(
        ValueError,
        match="equipment_name cannot be empty",
    ):
        _make_equipment(equipment_name=equipment_name)


@pytest.mark.parametrize(
    "manufacturer",
    ["", "   ", "\t", "\n"],
)
def test_equipment_rejects_empty_manufacturer(
    manufacturer: str,
) -> None:
    """Manufacturer names must contain visible text."""
    with pytest.raises(
        ValueError,
        match="manufacturer cannot be empty",
    ):
        _make_equipment(manufacturer=manufacturer)


@pytest.mark.parametrize(
    "model_number",
    ["", "   ", "\t", "\n"],
)
def test_equipment_rejects_empty_model_number(
    model_number: str,
) -> None:
    """Model numbers must contain visible text."""
    with pytest.raises(
        ValueError,
        match="model_number cannot be empty",
    ):
        _make_equipment(model_number=model_number)


@pytest.mark.parametrize(
    "serial_number",
    ["", "   ", "\t", "\n"],
)
def test_equipment_rejects_empty_serial_number(
    serial_number: str,
) -> None:
    """Serial numbers must contain visible text."""
    with pytest.raises(
        ValueError,
        match="serial_number cannot be empty",
    ):
        _make_equipment(serial_number=serial_number)


@pytest.mark.parametrize(
    "equipment_type",
    [
        "string_inverter",
        "transformer",
        1,
        None,
    ],
)
def test_equipment_rejects_invalid_equipment_type(
    equipment_type: object,
) -> None:
    """Raw strings and unsupported values must not replace EquipmentType."""
    with pytest.raises(
        TypeError,
        match="Use an EquipmentType value",
    ):
        _make_equipment(equipment_type=equipment_type)


@pytest.mark.parametrize(
    "status",
    [
        "operational",
        "maintenance",
        1,
        None,
    ],
)
def test_equipment_rejects_invalid_status(
    status: object,
) -> None:
    """Raw strings and unsupported values must not replace EquipmentStatus."""
    with pytest.raises(
        TypeError,
        match="Use an EquipmentStatus value",
    ):
        _make_equipment(status=status)


@pytest.mark.parametrize(
    "commissioning_date",
    [
        "2020-01-15",
        datetime(2020, 1, 15, 12, 0),
        20200115,
        None,
    ],
)
def test_equipment_rejects_invalid_commissioning_date_type(
    commissioning_date: object,
) -> None:
    """Commissioning dates must be date values and must reject datetime."""
    with pytest.raises(
        TypeError,
        match="Use a datetime.date value",
    ):
        _make_equipment(commissioning_date=commissioning_date)


def test_equipment_rejects_future_commissioning_date() -> None:
    """A commissioning date later than today must be rejected."""
    future_date = date.today() + timedelta(days=1)

    with pytest.raises(
        ValueError,
        match="is in the future",
    ):
        _make_equipment(commissioning_date=future_date)


def test_equipment_accepts_today_as_commissioning_date() -> None:
    """Today's date should be a valid commissioning date."""
    equipment = _make_equipment(commissioning_date=date.today())

    assert equipment.commissioning_date == date.today()


@pytest.mark.parametrize(
    "rated_power_kw",
    [
        0,
        0.0,
        -1,
        -0.1,
        -100.0,
    ],
)
def test_equipment_rejects_non_positive_rated_power(
    rated_power_kw: float,
) -> None:
    """Rated power must be greater than zero when supplied."""
    with pytest.raises(
        ValueError,
        match="Rated power must be greater than zero",
    ):
        _make_equipment(rated_power_kw=rated_power_kw)


@pytest.mark.parametrize(
    "rated_power_kw",
    [
        True,
        False,
        "100",
        [],
        {},
        object(),
    ],
)
def test_equipment_rejects_invalid_rated_power_type(
    rated_power_kw: object,
) -> None:
    """Rated power must be numeric, excluding boolean values."""
    with pytest.raises(
        TypeError,
        match="Use a positive numeric value or None",
    ):
        _make_equipment(rated_power_kw=rated_power_kw)


@pytest.mark.parametrize(
    "rated_power_kw",
    [
        1,
        1.0,
        100,
        100.5,
    ],
)
def test_equipment_accepts_positive_rated_power(
    rated_power_kw: float,
) -> None:
    """Positive integer and floating-point rated powers should be accepted."""
    equipment = _make_equipment(rated_power_kw=rated_power_kw)

    assert equipment.rated_power_kw == rated_power_kw


@pytest.mark.parametrize(
    "parent_equipment_id",
    [
        "",
        "   ",
        "EQP-1",
        "EQP-0001",
        "EQP-000001",
        "PARENT-00001",
        "EQP-ABCDE",
        "EQP_00001",
    ],
)
def test_equipment_rejects_invalid_parent_equipment_id(
    parent_equipment_id: str,
) -> None:
    """Parent IDs must use the same EQP-00001 identifier format."""
    with pytest.raises(
        ValueError,
        match="Invalid parent_equipment_id",
    ):
        _make_equipment(parent_equipment_id=parent_equipment_id)


def test_equipment_rejects_self_parent_reference() -> None:
    """Equipment must not identify itself as its own parent."""
    with pytest.raises(
        ValueError,
        match="Equipment cannot be its own parent",
    ):
        _make_equipment(parent_equipment_id="EQP-00001")


def test_equipment_accepts_valid_parent_equipment_id() -> None:
    """A different valid equipment ID should be accepted as the parent."""
    equipment = _make_equipment(parent_equipment_id="EQP-00002")

    assert equipment.parent_equipment_id == "EQP-00002"


@pytest.mark.parametrize("equipment_type", list(EquipmentType))
def test_equipment_accepts_every_supported_equipment_type(
    equipment_type: EquipmentType,
) -> None:
    """Every documented EquipmentType member should be accepted."""
    equipment = _make_equipment(equipment_type=equipment_type)

    assert equipment.equipment_type is equipment_type


@pytest.mark.parametrize("status", list(EquipmentStatus))
def test_equipment_accepts_every_supported_status(
    status: EquipmentStatus,
) -> None:
    """Every documented EquipmentStatus member should be accepted."""
    equipment = _make_equipment(status=status)

    assert equipment.status is status
