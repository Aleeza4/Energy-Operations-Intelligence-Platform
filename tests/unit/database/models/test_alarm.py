"""
Unit tests for the EOIP Alarm SQLAlchemy ORM model.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index

from eoip.database.models.alarm import AlarmORM
from eoip.synthetic.models.alarm import (
    Alarm,
    AlarmCategory,
    AlarmSeverity,
    AlarmStatus,
)


def _raised_at() -> datetime:
    """Return the standard timezone-aware alarm timestamp."""
    return datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def _domain_alarm(**overrides: object) -> Alarm:
    """Return a valid Alarm domain model with optional overrides."""
    data: dict[str, object] = {
        "alarm_id": "ALM-0000001",
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "alarm_code": "INV_OVERTEMP",
        "alarm_name": "Inverter Overtemperature",
        "category": AlarmCategory.EQUIPMENT,
        "severity": AlarmSeverity.CRITICAL,
        "raised_at": _raised_at(),
        "status": AlarmStatus.ACTIVE,
        "acknowledged_at": None,
        "cleared_at": None,
        "message": "Inverter temperature exceeded its operating threshold.",
        "is_synthetic_ground_truth": False,
    }
    data.update(overrides)
    return Alarm(**data)


def _orm_alarm(**overrides: object) -> AlarmORM:
    """Return a valid AlarmORM object with optional overrides."""
    data: dict[str, object] = {
        "alarm_id": "ALM-0000001",
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "alarm_code": "INV_OVERTEMP",
        "alarm_name": "Inverter Overtemperature",
        "category": AlarmCategory.EQUIPMENT.value,
        "severity": AlarmSeverity.CRITICAL.value,
        "raised_at": _raised_at(),
        "status": AlarmStatus.ACTIVE.value,
        "acknowledged_at": None,
        "cleared_at": None,
        "message": "Inverter temperature exceeded its operating threshold.",
        "is_synthetic_ground_truth": False,
    }
    data.update(overrides)
    return AlarmORM(**data)


def test_table_name() -> None:
    """Verify the mapped database table name."""
    assert AlarmORM.__tablename__ == "alarms"


def test_primary_key_column() -> None:
    """Verify alarm_id is the only primary-key column."""
    primary_keys = {column.name for column in AlarmORM.__table__.primary_key.columns}

    assert primary_keys == {"alarm_id"}


def test_expected_columns_exist() -> None:
    """Verify the complete persistence contract."""
    assert set(AlarmORM.__table__.columns.keys()) == {
        "alarm_id",
        "plant_id",
        "equipment_id",
        "alarm_code",
        "alarm_name",
        "category",
        "severity",
        "raised_at",
        "status",
        "acknowledged_at",
        "cleared_at",
        "message",
        "is_synthetic_ground_truth",
        "created_at",
        "updated_at",
    }


def test_required_columns_are_not_nullable() -> None:
    """Verify required alarm fields are non-nullable."""
    for column_name in (
        "alarm_id",
        "plant_id",
        "equipment_id",
        "alarm_code",
        "alarm_name",
        "category",
        "severity",
        "raised_at",
        "status",
        "is_synthetic_ground_truth",
        "created_at",
        "updated_at",
    ):
        assert AlarmORM.__table__.columns[column_name].nullable is False


def test_optional_columns_are_nullable() -> None:
    """Verify optional lifecycle and message fields are nullable."""
    assert AlarmORM.__table__.columns["acknowledged_at"].nullable is True
    assert AlarmORM.__table__.columns["cleared_at"].nullable is True
    assert AlarmORM.__table__.columns["message"].nullable is True


def test_expected_foreign_keys_exist() -> None:
    """Verify plant and equipment foreign keys."""
    targets = {
        foreign_key.target_fullname for foreign_key in AlarmORM.__table__.foreign_keys
    }

    assert targets == {
        "plants.plant_id",
        "equipment.equipment_id",
    }


def test_foreign_key_actions() -> None:
    """Verify foreign-key update and delete behavior."""
    foreign_keys = {
        foreign_key.parent.name: foreign_key
        for foreign_key in AlarmORM.__table__.foreign_keys
    }

    assert foreign_keys["plant_id"].onupdate == "CASCADE"
    assert foreign_keys["plant_id"].ondelete == "RESTRICT"
    assert foreign_keys["equipment_id"].onupdate == "CASCADE"
    assert foreign_keys["equipment_id"].ondelete == "RESTRICT"


def test_foreign_key_constraints_are_declared() -> None:
    """Verify both foreign-key constraints are registered."""
    constraints = [
        constraint
        for constraint in AlarmORM.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]

    assert len(constraints) == 2


def test_expected_check_constraints_exist() -> None:
    """Verify controlled-value and lifecycle constraints."""
    constraint_names = {
        constraint.name
        for constraint in AlarmORM.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert constraint_names == {
        "ck_alarms_valid_category",
        "ck_alarms_valid_severity",
        "ck_alarms_valid_status",
        "ck_alarms_acknowledged_not_before_raised",
        "ck_alarms_cleared_not_before_raised",
        "ck_alarms_cleared_not_before_acknowledged",
        "ck_alarms_active_has_no_cleared_at",
        "ck_alarms_acknowledged_has_timestamp",
        "ck_alarms_acknowledged_has_no_cleared_at",
        "ck_alarms_cleared_has_timestamp",
    }


def test_expected_indexes_exist() -> None:
    """Verify alarm analytics indexes are declared."""
    index_names = {
        index.name for index in AlarmORM.__table__.indexes if isinstance(index, Index)
    }

    assert index_names == {
        "ix_alarms_plant_id",
        "ix_alarms_equipment_id",
        "ix_alarms_alarm_code",
        "ix_alarms_category",
        "ix_alarms_severity",
        "ix_alarms_status",
        "ix_alarms_raised_at",
        "ix_alarms_plant_equipment_raised_at",
    }


def test_composite_index_column_order() -> None:
    """Verify the composite operational-history index order."""
    index = next(
        index
        for index in AlarmORM.__table__.indexes
        if index.name == "ix_alarms_plant_equipment_raised_at"
    )

    assert tuple(column.name for column in index.columns) == (
        "plant_id",
        "equipment_id",
        "raised_at",
    )


def test_from_domain_maps_all_fields() -> None:
    """Verify conversion from the authoritative domain model."""
    raised_at = _raised_at()
    acknowledged_at = raised_at + timedelta(minutes=2)
    cleared_at = raised_at + timedelta(minutes=17)
    alarm = _domain_alarm(
        category=AlarmCategory.PERFORMANCE,
        severity=AlarmSeverity.WARNING,
        status=AlarmStatus.CLEARED,
        acknowledged_at=acknowledged_at,
        cleared_at=cleared_at,
        message="Output remained below expected generation.",
        is_synthetic_ground_truth=True,
    )

    orm = AlarmORM.from_domain(alarm)

    assert orm.alarm_id == alarm.alarm_id
    assert orm.plant_id == alarm.plant_id
    assert orm.equipment_id == alarm.equipment_id
    assert orm.alarm_code == alarm.alarm_code
    assert orm.alarm_name == alarm.alarm_name
    assert orm.category == AlarmCategory.PERFORMANCE.value
    assert orm.severity == AlarmSeverity.WARNING.value
    assert orm.raised_at == raised_at
    assert orm.status == AlarmStatus.CLEARED.value
    assert orm.acknowledged_at == acknowledged_at
    assert orm.cleared_at == cleared_at
    assert orm.message == "Output remained below expected generation."
    assert orm.is_synthetic_ground_truth is True


def test_from_domain_preserves_none_values() -> None:
    """Verify optional values remain None during conversion."""
    alarm = _domain_alarm(
        acknowledged_at=None,
        cleared_at=None,
        message=None,
    )

    orm = AlarmORM.from_domain(alarm)

    assert orm.acknowledged_at is None
    assert orm.cleared_at is None
    assert orm.message is None


def test_from_domain_rejects_invalid_type() -> None:
    """Verify conversion rejects non-Alarm values."""
    with pytest.raises(TypeError, match="Alarm instance"):
        AlarmORM.from_domain(object())  # type: ignore[arg-type]


def test_to_domain_returns_authoritative_model() -> None:
    """Verify conversion back to the Alarm domain model."""
    raised_at = _raised_at()
    acknowledged_at = raised_at + timedelta(minutes=5)
    orm = _orm_alarm(
        category=AlarmCategory.GRID.value,
        severity=AlarmSeverity.MAJOR.value,
        status=AlarmStatus.ACKNOWLEDGED.value,
        acknowledged_at=acknowledged_at,
        message=None,
        is_synthetic_ground_truth=True,
    )

    alarm = orm.to_domain()

    assert isinstance(alarm, Alarm)
    assert alarm.alarm_id == orm.alarm_id
    assert alarm.plant_id == orm.plant_id
    assert alarm.equipment_id == orm.equipment_id
    assert alarm.alarm_code == orm.alarm_code
    assert alarm.alarm_name == orm.alarm_name
    assert alarm.category is AlarmCategory.GRID
    assert alarm.severity is AlarmSeverity.MAJOR
    assert alarm.raised_at == raised_at
    assert alarm.status is AlarmStatus.ACKNOWLEDGED
    assert alarm.acknowledged_at == acknowledged_at
    assert alarm.cleared_at is None
    assert alarm.message is None
    assert alarm.is_synthetic_ground_truth is True


def test_domain_round_trip_preserves_values() -> None:
    """Verify domain-to-ORM-to-domain conversion is lossless."""
    raised_at = _raised_at()
    original = _domain_alarm(
        category=AlarmCategory.COMMUNICATION,
        severity=AlarmSeverity.INFORMATIONAL,
        status=AlarmStatus.CLEARED,
        acknowledged_at=raised_at + timedelta(minutes=1),
        cleared_at=raised_at + timedelta(minutes=8),
        is_synthetic_ground_truth=True,
    )

    restored = AlarmORM.from_domain(original).to_domain()

    assert restored == original


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (AlarmStatus.ACTIVE.value, True),
        (AlarmStatus.ACKNOWLEDGED.value, True),
        (AlarmStatus.CLEARED.value, False),
    ],
)
def test_is_open(status: str, expected: bool) -> None:
    """Verify open-alarm classification."""
    orm = _orm_alarm(status=status)

    assert orm.is_open is expected


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        (AlarmSeverity.INFORMATIONAL.value, False),
        (AlarmSeverity.WARNING.value, False),
        (AlarmSeverity.MAJOR.value, False),
        (AlarmSeverity.CRITICAL.value, True),
    ],
)
def test_is_critical(severity: str, expected: bool) -> None:
    """Verify critical-alarm classification."""
    orm = _orm_alarm(severity=severity)

    assert orm.is_critical is expected


def test_acknowledgement_seconds() -> None:
    """Verify elapsed acknowledgement time."""
    raised_at = _raised_at()
    orm = _orm_alarm(
        raised_at=raised_at,
        acknowledged_at=raised_at + timedelta(seconds=125.4321),
    )

    assert orm.acknowledgement_seconds == 125.432


def test_acknowledgement_seconds_is_none_without_timestamp() -> None:
    """Verify missing acknowledgement produces no duration."""
    assert _orm_alarm(acknowledged_at=None).acknowledgement_seconds is None


def test_resolution_seconds() -> None:
    """Verify elapsed resolution time."""
    raised_at = _raised_at()
    orm = _orm_alarm(
        raised_at=raised_at,
        cleared_at=raised_at + timedelta(seconds=945.6789),
    )

    assert orm.resolution_seconds == 945.679


def test_resolution_seconds_is_none_without_timestamp() -> None:
    """Verify missing clearance produces no duration."""
    assert _orm_alarm(cleared_at=None).resolution_seconds is None


def test_update_from_domain_updates_mutable_fields() -> None:
    """Verify ORM values can be refreshed from a matching domain object."""
    orm = _orm_alarm()
    raised_at = _raised_at() + timedelta(days=1)
    updated = _domain_alarm(
        plant_id="PLANT-002",
        equipment_id="EQP-00002",
        alarm_code="GRID_LOSS",
        alarm_name="Grid Connection Lost",
        category=AlarmCategory.GRID,
        severity=AlarmSeverity.MAJOR,
        raised_at=raised_at,
        status=AlarmStatus.CLEARED,
        acknowledged_at=raised_at + timedelta(minutes=3),
        cleared_at=raised_at + timedelta(minutes=20),
        message="Grid export connection was unavailable.",
        is_synthetic_ground_truth=True,
    )

    orm.update_from_domain(updated)

    assert orm.plant_id == "PLANT-002"
    assert orm.equipment_id == "EQP-00002"
    assert orm.alarm_code == "GRID_LOSS"
    assert orm.alarm_name == "Grid Connection Lost"
    assert orm.category == AlarmCategory.GRID.value
    assert orm.severity == AlarmSeverity.MAJOR.value
    assert orm.raised_at == raised_at
    assert orm.status == AlarmStatus.CLEARED.value
    assert orm.acknowledged_at == raised_at + timedelta(minutes=3)
    assert orm.cleared_at == raised_at + timedelta(minutes=20)
    assert orm.message == "Grid export connection was unavailable."
    assert orm.is_synthetic_ground_truth is True


def test_update_from_domain_rejects_invalid_type() -> None:
    """Verify update rejects non-Alarm values."""
    orm = _orm_alarm()

    with pytest.raises(TypeError, match="Alarm instance"):
        orm.update_from_domain(object())  # type: ignore[arg-type]


def test_update_from_domain_rejects_different_identifier() -> None:
    """Verify persisted alarm identity cannot be changed."""
    orm = _orm_alarm()
    different = _domain_alarm(alarm_id="ALM-0000002")

    with pytest.raises(ValueError, match="different alarm_id"):
        orm.update_from_domain(different)


def test_to_record_serializes_all_values() -> None:
    """Verify database records are serialization-ready."""
    raised_at = _raised_at()
    acknowledged_at = raised_at + timedelta(minutes=2)
    cleared_at = raised_at + timedelta(minutes=17)
    created_at = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
    updated_at = created_at + timedelta(hours=1)

    orm = _orm_alarm(
        raised_at=raised_at,
        status=AlarmStatus.CLEARED.value,
        acknowledged_at=acknowledged_at,
        cleared_at=cleared_at,
        is_synthetic_ground_truth=True,
    )
    orm.created_at = created_at
    orm.updated_at = updated_at

    record = orm.to_record()

    assert record == {
        "alarm_id": "ALM-0000001",
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "alarm_code": "INV_OVERTEMP",
        "alarm_name": "Inverter Overtemperature",
        "category": AlarmCategory.EQUIPMENT.value,
        "severity": AlarmSeverity.CRITICAL.value,
        "raised_at": raised_at.isoformat(),
        "status": AlarmStatus.CLEARED.value,
        "acknowledged_at": acknowledged_at.isoformat(),
        "cleared_at": cleared_at.isoformat(),
        "message": "Inverter temperature exceeded its operating threshold.",
        "is_synthetic_ground_truth": True,
        "is_open": False,
        "is_critical": True,
        "acknowledgement_seconds": 120.0,
        "resolution_seconds": 1020.0,
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
    }


def test_to_record_handles_optional_values() -> None:
    """Verify optional values serialize correctly."""
    record = _orm_alarm(
        acknowledged_at=None,
        cleared_at=None,
        message=None,
    ).to_record()

    assert record["acknowledged_at"] is None
    assert record["cleared_at"] is None
    assert record["message"] is None
    assert record["acknowledgement_seconds"] is None
    assert record["resolution_seconds"] is None


def test_to_record_handles_unset_audit_timestamps() -> None:
    """Verify unsaved ORM objects serialize missing audit timestamps."""
    record = _orm_alarm().to_record()

    assert record["created_at"] is None
    assert record["updated_at"] is None


def test_repr_contains_key_identity_fields() -> None:
    """Verify developer representation is concise and useful."""
    value = repr(_orm_alarm())

    assert "AlarmORM" in value
    assert "ALM-0000001" in value
    assert "EQP-00001" in value
    assert AlarmSeverity.CRITICAL.value in value
    assert AlarmStatus.ACTIVE.value in value


def test_status_default_matches_domain_default() -> None:
    """Verify ORM status defaults to active."""
    column = AlarmORM.__table__.columns["status"]

    assert column.default is not None
    assert column.default.arg == AlarmStatus.ACTIVE.value
    assert column.server_default is not None


def test_ground_truth_default_is_false() -> None:
    """Verify synthetic ground-truth defaults to false."""
    column = AlarmORM.__table__.columns["is_synthetic_ground_truth"]

    assert column.default is not None
    assert column.default.arg is False
    assert column.server_default is not None


def test_timestamp_columns_are_timezone_aware() -> None:
    """Verify lifecycle and audit timestamps preserve timezone data."""
    for column_name in (
        "raised_at",
        "acknowledged_at",
        "cleared_at",
        "created_at",
        "updated_at",
    ):
        assert AlarmORM.__table__.columns[column_name].type.timezone is True


def test_plant_relationship_configuration() -> None:
    """Verify alarm links to the Plant ORM model."""
    relationship_property = AlarmORM.__mapper__.relationships["plant"]

    assert relationship_property.mapper.class_.__name__ == "PlantORM"
    assert relationship_property.uselist is False


def test_equipment_relationship_configuration() -> None:
    """Verify alarm links to the Equipment ORM model."""
    relationship_property = AlarmORM.__mapper__.relationships["equipment"]

    assert relationship_property.mapper.class_.__name__ == "EquipmentORM"
    assert relationship_property.uselist is False


def test_alarm_code_length_is_50() -> None:
    """Verify alarm codes match the domain maximum length."""
    assert AlarmORM.__table__.columns["alarm_code"].type.length == 50


def test_alarm_name_length_is_150() -> None:
    """Verify alarm names match the domain maximum length."""
    assert AlarmORM.__table__.columns["alarm_name"].type.length == 150


def test_message_length_is_500() -> None:
    """Verify alarm messages match the domain maximum length."""
    assert AlarmORM.__table__.columns["message"].type.length == 500
