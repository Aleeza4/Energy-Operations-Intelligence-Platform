"""
Unit tests for the EOIP Equipment SQLAlchemy ORM model.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, UniqueConstraint

from eoip.database.models.equipment import EquipmentORM
from eoip.synthetic.models.equipment import (
    Equipment,
    EquipmentStatus,
    EquipmentType,
)


def _domain_equipment(**overrides: object) -> Equipment:
    """Return a valid Equipment domain model with optional overrides."""
    data: dict[str, object] = {
        "equipment_id": "EQP-00001",
        "plant_id": "PLANT-001",
        "equipment_name": "String Inverter 01",
        "equipment_type": EquipmentType.STRING_INVERTER,
        "manufacturer": "Huawei",
        "model_number": "SUN2000",
        "serial_number": "SN00000001",
        "commissioning_date": date(2024, 1, 15),
        "rated_power_kw": 250.0,
        "parent_equipment_id": "EQP-00010",
        "status": EquipmentStatus.OPERATIONAL,
    }
    data.update(overrides)
    return Equipment(**data)


def _orm_equipment(**overrides: object) -> EquipmentORM:
    """Return a valid EquipmentORM object with optional overrides."""
    data: dict[str, object] = {
        "equipment_id": "EQP-00001",
        "plant_id": "PLANT-001",
        "equipment_name": "String Inverter 01",
        "equipment_type": EquipmentType.STRING_INVERTER.value,
        "manufacturer": "Huawei",
        "model_number": "SUN2000",
        "serial_number": "SN00000001",
        "commissioning_date": date(2024, 1, 15),
        "rated_power_kw": 250.0,
        "parent_equipment_id": "EQP-00010",
        "status": EquipmentStatus.OPERATIONAL.value,
    }
    data.update(overrides)
    return EquipmentORM(**data)


def test_table_name() -> None:
    """Verify the mapped table name."""
    assert EquipmentORM.__tablename__ == "equipment"


def test_primary_key_column() -> None:
    """Verify equipment_id is the only primary-key column."""
    primary_keys = {
        column.name for column in EquipmentORM.__table__.primary_key.columns
    }

    assert primary_keys == {"equipment_id"}


def test_expected_columns_exist() -> None:
    """Verify the complete persistence contract."""
    assert set(EquipmentORM.__table__.columns.keys()) == {
        "equipment_id",
        "plant_id",
        "equipment_name",
        "equipment_type",
        "manufacturer",
        "model_number",
        "serial_number",
        "commissioning_date",
        "rated_power_kw",
        "parent_equipment_id",
        "status",
        "created_at",
        "updated_at",
    }


def test_required_columns_are_not_nullable() -> None:
    """Verify required equipment fields are non-nullable."""
    for column_name in (
        "equipment_id",
        "plant_id",
        "equipment_name",
        "equipment_type",
        "manufacturer",
        "model_number",
        "serial_number",
        "commissioning_date",
        "status",
        "created_at",
        "updated_at",
    ):
        assert EquipmentORM.__table__.columns[column_name].nullable is False


def test_optional_columns_are_nullable() -> None:
    """Verify optional domain fields remain nullable."""
    assert EquipmentORM.__table__.columns["rated_power_kw"].nullable is True
    assert EquipmentORM.__table__.columns["parent_equipment_id"].nullable is True


def test_expected_foreign_keys_exist() -> None:
    """Verify plant and parent-equipment foreign keys."""
    targets = {
        foreign_key.target_fullname
        for foreign_key in EquipmentORM.__table__.foreign_keys
    }

    assert targets == {
        "plants.plant_id",
        "equipment.equipment_id",
    }


def test_foreign_key_actions() -> None:
    """Verify database update and delete actions."""
    foreign_keys = {
        foreign_key.parent.name: foreign_key
        for foreign_key in EquipmentORM.__table__.foreign_keys
    }

    assert foreign_keys["plant_id"].onupdate == "CASCADE"
    assert foreign_keys["plant_id"].ondelete == "RESTRICT"
    assert foreign_keys["parent_equipment_id"].onupdate == "CASCADE"
    assert foreign_keys["parent_equipment_id"].ondelete == "SET NULL"


def test_foreign_key_constraints_are_declared() -> None:
    """Verify SQLAlchemy exposes both foreign-key constraints."""
    constraints = [
        constraint
        for constraint in EquipmentORM.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]

    assert len(constraints) == 2


def test_serial_number_unique_constraint_exists() -> None:
    """Verify serial numbers must be globally unique."""
    unique_constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in EquipmentORM.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert unique_constraints == {"uq_equipment_serial_number": ("serial_number",)}


def test_expected_check_constraints_exist() -> None:
    """Verify controlled-value and engineering constraints."""
    constraint_names = {
        constraint.name
        for constraint in EquipmentORM.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert constraint_names == {
        "ck_equipment_rated_power_positive",
        "ck_equipment_not_own_parent",
        "ck_equipment_valid_equipment_type",
        "ck_equipment_valid_status",
    }


def test_expected_indexes_exist() -> None:
    """Verify commonly queried fields have indexes."""
    index_names = {
        index.name
        for index in EquipmentORM.__table__.indexes
        if isinstance(index, Index)
    }

    assert index_names == {
        "ix_equipment_plant_id",
        "ix_equipment_equipment_type",
        "ix_equipment_status",
        "ix_equipment_parent_equipment_id",
        "ix_equipment_commissioning_date",
    }


def test_from_domain_maps_all_fields() -> None:
    """Verify conversion from the authoritative domain model."""
    equipment = _domain_equipment(
        equipment_type=EquipmentType.TRANSFORMER,
        rated_power_kw=5_000.0,
        status=EquipmentStatus.MAINTENANCE,
    )

    orm = EquipmentORM.from_domain(equipment)

    assert orm.equipment_id == equipment.equipment_id
    assert orm.plant_id == equipment.plant_id
    assert orm.equipment_name == equipment.equipment_name
    assert orm.equipment_type == EquipmentType.TRANSFORMER.value
    assert orm.manufacturer == equipment.manufacturer
    assert orm.model_number == equipment.model_number
    assert orm.serial_number == equipment.serial_number
    assert orm.commissioning_date == equipment.commissioning_date
    assert orm.rated_power_kw == 5_000.0
    assert orm.parent_equipment_id == equipment.parent_equipment_id
    assert orm.status == EquipmentStatus.MAINTENANCE.value


def test_from_domain_preserves_none_values() -> None:
    """Verify optional values remain None during conversion."""
    equipment = _domain_equipment(
        rated_power_kw=None,
        parent_equipment_id=None,
    )

    orm = EquipmentORM.from_domain(equipment)

    assert orm.rated_power_kw is None
    assert orm.parent_equipment_id is None


def test_from_domain_rejects_invalid_type() -> None:
    """Verify conversion rejects non-Equipment values."""
    with pytest.raises(TypeError, match="Equipment instance"):
        EquipmentORM.from_domain(object())  # type: ignore[arg-type]


def test_to_domain_returns_authoritative_model() -> None:
    """Verify conversion back to the Equipment domain model."""
    orm = _orm_equipment(
        equipment_type=EquipmentType.REVENUE_METER.value,
        rated_power_kw=None,
        parent_equipment_id=None,
        status=EquipmentStatus.PLANNED_OUTAGE.value,
    )

    equipment = orm.to_domain()

    assert isinstance(equipment, Equipment)
    assert equipment.equipment_id == orm.equipment_id
    assert equipment.plant_id == orm.plant_id
    assert equipment.equipment_name == orm.equipment_name
    assert equipment.equipment_type is EquipmentType.REVENUE_METER
    assert equipment.manufacturer == orm.manufacturer
    assert equipment.model_number == orm.model_number
    assert equipment.serial_number == orm.serial_number
    assert equipment.commissioning_date == orm.commissioning_date
    assert equipment.rated_power_kw is None
    assert equipment.parent_equipment_id is None
    assert equipment.status is EquipmentStatus.PLANNED_OUTAGE


def test_domain_round_trip_preserves_values() -> None:
    """Verify domain-to-ORM-to-domain conversion is lossless."""
    original = _domain_equipment(
        equipment_type=EquipmentType.PROTECTION_RELAY,
        rated_power_kw=None,
        parent_equipment_id="EQP-00020",
        status=EquipmentStatus.FORCED_OUTAGE,
    )

    restored = EquipmentORM.from_domain(original).to_domain()

    assert restored == original


@pytest.mark.parametrize(
    ("equipment_type", "expected"),
    [
        (EquipmentType.STRING_INVERTER.value, True),
        (EquipmentType.CENTRAL_INVERTER.value, True),
        (EquipmentType.TRANSFORMER.value, False),
        (EquipmentType.FEEDER.value, False),
        (EquipmentType.WEATHER_STATION.value, False),
        (EquipmentType.REVENUE_METER.value, False),
        (EquipmentType.PROTECTION_RELAY.value, False),
    ],
)
def test_is_generation_equipment(
    equipment_type: str,
    expected: bool,
) -> None:
    """Verify generation-equipment classification."""
    orm = _orm_equipment(equipment_type=equipment_type)

    assert orm.is_generation_equipment is expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (EquipmentStatus.OPERATIONAL.value, True),
        (EquipmentStatus.PLANNED_OUTAGE.value, False),
        (EquipmentStatus.FORCED_OUTAGE.value, False),
        (EquipmentStatus.MAINTENANCE.value, False),
        (EquipmentStatus.DECOMMISSIONED.value, False),
    ],
)
def test_is_available(status: str, expected: bool) -> None:
    """Verify equipment availability classification."""
    orm = _orm_equipment(status=status)

    assert orm.is_available is expected


def test_update_from_domain_updates_mutable_fields() -> None:
    """Verify ORM values can be refreshed from a matching domain object."""
    orm = _orm_equipment()
    updated = _domain_equipment(
        plant_id="PLANT-002",
        equipment_name="Transformer Updated",
        equipment_type=EquipmentType.TRANSFORMER,
        manufacturer="ABB",
        model_number="TX-33KV",
        serial_number="SN00009999",
        commissioning_date=date(2023, 6, 1),
        rated_power_kw=5_000.0,
        parent_equipment_id=None,
        status=EquipmentStatus.MAINTENANCE,
    )

    orm.update_from_domain(updated)

    assert orm.plant_id == "PLANT-002"
    assert orm.equipment_name == "Transformer Updated"
    assert orm.equipment_type == EquipmentType.TRANSFORMER.value
    assert orm.manufacturer == "ABB"
    assert orm.model_number == "TX-33KV"
    assert orm.serial_number == "SN00009999"
    assert orm.commissioning_date == date(2023, 6, 1)
    assert orm.rated_power_kw == 5_000.0
    assert orm.parent_equipment_id is None
    assert orm.status == EquipmentStatus.MAINTENANCE.value


def test_update_from_domain_rejects_invalid_type() -> None:
    """Verify update rejects non-Equipment values."""
    orm = _orm_equipment()

    with pytest.raises(TypeError, match="Equipment instance"):
        orm.update_from_domain(object())  # type: ignore[arg-type]


def test_update_from_domain_rejects_different_identifier() -> None:
    """Verify persisted identity cannot be changed."""
    orm = _orm_equipment()
    different = _domain_equipment(equipment_id="EQP-00002")

    with pytest.raises(ValueError, match="different equipment_id"):
        orm.update_from_domain(different)


def test_to_record_serializes_all_values() -> None:
    """Verify database records are serialization-ready."""
    created_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    updated_at = created_at + timedelta(hours=1)
    orm = _orm_equipment()
    orm.created_at = created_at
    orm.updated_at = updated_at

    record = orm.to_record()

    assert record == {
        "equipment_id": "EQP-00001",
        "plant_id": "PLANT-001",
        "equipment_name": "String Inverter 01",
        "equipment_type": EquipmentType.STRING_INVERTER.value,
        "manufacturer": "Huawei",
        "model_number": "SUN2000",
        "serial_number": "SN00000001",
        "commissioning_date": "2024-01-15",
        "rated_power_kw": 250.0,
        "parent_equipment_id": "EQP-00010",
        "status": EquipmentStatus.OPERATIONAL.value,
        "is_generation_equipment": True,
        "is_available": True,
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
    }


def test_to_record_handles_optional_values() -> None:
    """Verify optional domain values serialize correctly."""
    orm = _orm_equipment(
        rated_power_kw=None,
        parent_equipment_id=None,
    )

    record = orm.to_record()

    assert record["rated_power_kw"] is None
    assert record["parent_equipment_id"] is None


def test_to_record_handles_unset_audit_timestamps() -> None:
    """Verify unsaved ORM objects serialize missing audit timestamps."""
    record = _orm_equipment().to_record()

    assert record["created_at"] is None
    assert record["updated_at"] is None


def test_repr_contains_key_identity_fields() -> None:
    """Verify developer representation is concise and useful."""
    value = repr(_orm_equipment())

    assert "EquipmentORM" in value
    assert "EQP-00001" in value
    assert "String Inverter 01" in value
    assert EquipmentType.STRING_INVERTER.value in value
    assert EquipmentStatus.OPERATIONAL.value in value


def test_status_default_matches_domain_default() -> None:
    """Verify ORM status defaults to operational."""
    column = EquipmentORM.__table__.columns["status"]

    assert column.default is not None
    assert column.default.arg == EquipmentStatus.OPERATIONAL.value
    assert column.server_default is not None


def test_audit_columns_are_timezone_aware() -> None:
    """Verify audit timestamps use timezone-aware SQL types."""
    created_type = EquipmentORM.__table__.columns["created_at"].type
    updated_type = EquipmentORM.__table__.columns["updated_at"].type

    assert created_type.timezone is True
    assert updated_type.timezone is True


def test_parent_relationship_configuration() -> None:
    """Verify the self-referencing parent relationship is configured."""
    relationship = EquipmentORM.__mapper__.relationships["parent"]

    assert relationship.mapper.class_ is EquipmentORM
    assert relationship.uselist is False
    assert relationship.back_populates == "children"


def test_children_relationship_configuration() -> None:
    """Verify the self-referencing children relationship is configured."""
    relationship = EquipmentORM.__mapper__.relationships["children"]

    assert relationship.mapper.class_ is EquipmentORM
    assert relationship.uselist is True
    assert relationship.back_populates == "parent"


def test_plant_relationship_configuration() -> None:
    """Verify equipment links to the Plant ORM model."""
    relationship = EquipmentORM.__mapper__.relationships["plant"]

    assert relationship.mapper.class_.__name__ == "PlantORM"
    assert relationship.uselist is False


def test_serial_number_column_is_not_nullable() -> None:
    """Verify serial_number is mandatory at persistence level."""
    column = EquipmentORM.__table__.columns["serial_number"]

    assert column.nullable is False


def test_rated_power_column_uses_float_type() -> None:
    """Verify rated power is stored as a floating-point value."""
    column_type = EquipmentORM.__table__.columns["rated_power_kw"].type

    assert column_type.python_type is float
