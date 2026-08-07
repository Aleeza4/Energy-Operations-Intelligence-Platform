"""
Unit tests for the EOIP GroundTruthEvent SQLAlchemy ORM model.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index

from eoip.database.models.ground_truth import GroundTruthEventORM
from eoip.synthetic.models.ground_truth import (
    GroundTruthEvent,
    GroundTruthEventType,
    GroundTruthSeverity,
)


def _started_at() -> datetime:
    """Return the standard timezone-aware event start timestamp."""
    return datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def _domain_event(**overrides: object) -> GroundTruthEvent:
    """Return a valid GroundTruthEvent with optional overrides."""
    started_at = _started_at()
    data: dict[str, object] = {
        "ground_truth_id": "GTE-0000001",
        "plant_id": "PLANT-001",
        "event_type": GroundTruthEventType.EQUIPMENT_FAILURE,
        "severity": GroundTruthSeverity.HIGH,
        "started_at": started_at,
        "ended_at": started_at + timedelta(hours=2),
        "equipment_id": "EQP-00001",
        "expected_power_loss_pct": 35.0,
        "expected_energy_loss_kwh": 1_250.0,
        "description": "Synthetic inverter failure event.",
    }
    data.update(overrides)
    return GroundTruthEvent(**data)


def _orm_event(**overrides: object) -> GroundTruthEventORM:
    """Return a valid GroundTruthEventORM with optional overrides."""
    started_at = _started_at()
    data: dict[str, object] = {
        "ground_truth_id": "GTE-0000001",
        "plant_id": "PLANT-001",
        "event_type": GroundTruthEventType.EQUIPMENT_FAILURE.value,
        "severity": GroundTruthSeverity.HIGH.value,
        "started_at": started_at,
        "ended_at": started_at + timedelta(hours=2),
        "equipment_id": "EQP-00001",
        "expected_power_loss_pct": 35.0,
        "expected_energy_loss_kwh": 1_250.0,
        "description": "Synthetic inverter failure event.",
    }
    data.update(overrides)
    return GroundTruthEventORM(**data)


def test_table_name() -> None:
    """Verify the mapped database table name."""
    assert GroundTruthEventORM.__tablename__ == "ground_truth_events"


def test_primary_key_column() -> None:
    """Verify ground_truth_id is the only primary key."""
    primary_keys = {
        column.name for column in GroundTruthEventORM.__table__.primary_key.columns
    }

    assert primary_keys == {"ground_truth_id"}


def test_expected_columns_exist() -> None:
    """Verify the complete persistence contract."""
    assert set(GroundTruthEventORM.__table__.columns.keys()) == {
        "ground_truth_id",
        "plant_id",
        "equipment_id",
        "event_type",
        "severity",
        "started_at",
        "ended_at",
        "expected_power_loss_pct",
        "expected_energy_loss_kwh",
        "description",
        "inserted_at",
        "updated_at",
    }


def test_required_columns_are_not_nullable() -> None:
    """Verify required ground-truth fields are non-nullable."""
    for column_name in (
        "ground_truth_id",
        "plant_id",
        "event_type",
        "severity",
        "started_at",
        "ended_at",
        "expected_power_loss_pct",
        "expected_energy_loss_kwh",
        "inserted_at",
        "updated_at",
    ):
        assert GroundTruthEventORM.__table__.columns[column_name].nullable is False


def test_optional_columns_are_nullable() -> None:
    """Verify optional equipment and description fields are nullable."""
    assert GroundTruthEventORM.__table__.columns["equipment_id"].nullable is True
    assert GroundTruthEventORM.__table__.columns["description"].nullable is True


def test_expected_foreign_keys_exist() -> None:
    """Verify plant and equipment foreign-key targets."""
    targets = {
        foreign_key.target_fullname
        for foreign_key in GroundTruthEventORM.__table__.foreign_keys
    }

    assert targets == {
        "plants.plant_id",
        "equipment.equipment_id",
    }


def test_foreign_key_actions() -> None:
    """Verify foreign-key update and delete behavior."""
    foreign_keys = {
        foreign_key.parent.name: foreign_key
        for foreign_key in GroundTruthEventORM.__table__.foreign_keys
    }

    assert foreign_keys["plant_id"].onupdate == "CASCADE"
    assert foreign_keys["plant_id"].ondelete == "RESTRICT"
    assert foreign_keys["equipment_id"].onupdate == "CASCADE"
    assert foreign_keys["equipment_id"].ondelete == "SET NULL"


def test_foreign_key_constraints_are_declared() -> None:
    """Verify both foreign-key constraints are registered."""
    constraints = [
        constraint
        for constraint in GroundTruthEventORM.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]

    assert len(constraints) == 2


def test_expected_check_constraints_exist() -> None:
    """Verify event, severity, timing, and loss constraints."""
    constraint_names = {
        constraint.name
        for constraint in GroundTruthEventORM.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert constraint_names == {
        "ck_ground_truth_events_valid_event_type",
        "ck_ground_truth_events_valid_severity",
        "ck_ground_truth_events_ended_after_started",
        "ck_ground_truth_events_power_loss_pct_range",
        "ck_ground_truth_events_energy_loss_non_negative",
    }


def test_expected_indexes_exist() -> None:
    """Verify ground-truth analytics indexes are declared."""
    index_names = {
        index.name
        for index in GroundTruthEventORM.__table__.indexes
        if isinstance(index, Index)
    }

    assert index_names == {
        "ix_ground_truth_events_plant_id",
        "ix_ground_truth_events_equipment_id",
        "ix_ground_truth_events_event_type",
        "ix_ground_truth_events_severity",
        "ix_ground_truth_events_started_at",
        "ix_ground_truth_events_ended_at",
        "ix_ground_truth_events_plant_started_at",
        "ix_ground_truth_events_plant_severity",
        "ix_ground_truth_events_equipment_started_at",
    }


@pytest.mark.parametrize(
    ("index_name", "expected_columns"),
    [
        (
            "ix_ground_truth_events_plant_started_at",
            ("plant_id", "started_at"),
        ),
        (
            "ix_ground_truth_events_plant_severity",
            ("plant_id", "severity"),
        ),
        (
            "ix_ground_truth_events_equipment_started_at",
            ("equipment_id", "started_at"),
        ),
    ],
)
def test_composite_index_column_order(
    index_name: str,
    expected_columns: tuple[str, ...],
) -> None:
    """Verify composite index column ordering."""
    index = next(
        item
        for item in GroundTruthEventORM.__table__.indexes
        if item.name == index_name
    )

    assert tuple(column.name for column in index.columns) == expected_columns


def test_from_domain_maps_all_fields() -> None:
    """Verify conversion from the authoritative domain model."""
    started_at = _started_at()
    ended_at = started_at + timedelta(hours=3)
    event = _domain_event(
        plant_id="PLANT-002",
        equipment_id=None,
        event_type=GroundTruthEventType.GRID_OUTAGE,
        severity=GroundTruthSeverity.CRITICAL,
        started_at=started_at,
        ended_at=ended_at,
        expected_power_loss_pct=100.0,
        expected_energy_loss_kwh=5_000.0,
        description="Synthetic grid outage.",
    )

    orm = GroundTruthEventORM.from_domain(event)

    assert orm.ground_truth_id == "GTE-0000001"
    assert orm.plant_id == "PLANT-002"
    assert orm.equipment_id is None
    assert orm.event_type == GroundTruthEventType.GRID_OUTAGE.value
    assert orm.severity == GroundTruthSeverity.CRITICAL.value
    assert orm.started_at == started_at
    assert orm.ended_at == ended_at
    assert orm.expected_power_loss_pct == 100.0
    assert orm.expected_energy_loss_kwh == 5_000.0
    assert orm.description == "Synthetic grid outage."


def test_from_domain_preserves_optional_none_values() -> None:
    """Verify optional fields remain None during conversion."""
    event = _domain_event(
        equipment_id=None,
        description=None,
    )

    orm = GroundTruthEventORM.from_domain(event)

    assert orm.equipment_id is None
    assert orm.description is None


def test_from_domain_rejects_invalid_type() -> None:
    """Verify conversion rejects non-ground-truth values."""
    with pytest.raises(TypeError, match="GroundTruthEvent instance"):
        GroundTruthEventORM.from_domain(object())  # type: ignore[arg-type]


def test_to_domain_returns_authoritative_model() -> None:
    """Verify conversion back to the domain model."""
    orm = _orm_event(
        event_type=GroundTruthEventType.SOILING.value,
        severity=GroundTruthSeverity.MODERATE.value,
        equipment_id=None,
        description=None,
    )

    event = orm.to_domain()

    assert isinstance(event, GroundTruthEvent)
    assert event.ground_truth_id == orm.ground_truth_id
    assert event.plant_id == orm.plant_id
    assert event.equipment_id is None
    assert event.event_type is GroundTruthEventType.SOILING
    assert event.severity is GroundTruthSeverity.MODERATE
    assert event.started_at == orm.started_at
    assert event.ended_at == orm.ended_at
    assert event.expected_power_loss_pct == orm.expected_power_loss_pct
    assert event.expected_energy_loss_kwh == orm.expected_energy_loss_kwh
    assert event.description is None


def test_domain_round_trip_preserves_values() -> None:
    """Verify domain-to-ORM-to-domain conversion is lossless."""
    original = _domain_event(
        event_type=GroundTruthEventType.CURTAILMENT,
        severity=GroundTruthSeverity.LOW,
        equipment_id=None,
    )

    restored = GroundTruthEventORM.from_domain(original).to_domain()

    assert restored == original


@pytest.mark.parametrize(
    ("duration", "expected"),
    [
        (timedelta(seconds=1), 1.0),
        (timedelta(minutes=15), 900.0),
        (timedelta(seconds=125.4321), 125.432),
    ],
)
def test_duration_seconds(
    duration: timedelta,
    expected: float,
) -> None:
    """Verify total event duration calculation."""
    started_at = _started_at()
    orm = _orm_event(
        started_at=started_at,
        ended_at=started_at + duration,
    )

    assert orm.duration_seconds == expected


@pytest.mark.parametrize(
    ("equipment_id", "expected"),
    [
        ("EQP-00001", True),
        (None, False),
    ],
)
def test_is_equipment_specific(
    equipment_id: str | None,
    expected: bool,
) -> None:
    """Verify equipment-specific event classification."""
    orm = _orm_event(equipment_id=equipment_id)

    assert orm.is_equipment_specific is expected


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        (GroundTruthSeverity.LOW.value, False),
        (GroundTruthSeverity.MODERATE.value, False),
        (GroundTruthSeverity.HIGH.value, False),
        (GroundTruthSeverity.CRITICAL.value, True),
    ],
)
def test_is_critical(
    severity: str,
    expected: bool,
) -> None:
    """Verify critical-event classification."""
    orm = _orm_event(severity=severity)

    assert orm.is_critical is expected


def test_update_from_domain_updates_mutable_fields() -> None:
    """Verify ORM values can be refreshed from a matching event."""
    orm = _orm_event()
    started_at = _started_at() + timedelta(days=1)
    ended_at = started_at + timedelta(hours=4)
    updated = _domain_event(
        plant_id="PLANT-002",
        equipment_id=None,
        event_type=GroundTruthEventType.COMMUNICATION_LOSS,
        severity=GroundTruthSeverity.CRITICAL,
        started_at=started_at,
        ended_at=ended_at,
        expected_power_loss_pct=75.0,
        expected_energy_loss_kwh=2_500.0,
        description="Synthetic telemetry communication outage.",
    )

    orm.update_from_domain(updated)

    assert orm.plant_id == "PLANT-002"
    assert orm.equipment_id is None
    assert orm.event_type == GroundTruthEventType.COMMUNICATION_LOSS.value
    assert orm.severity == GroundTruthSeverity.CRITICAL.value
    assert orm.started_at == started_at
    assert orm.ended_at == ended_at
    assert orm.expected_power_loss_pct == 75.0
    assert orm.expected_energy_loss_kwh == 2_500.0
    assert orm.description == "Synthetic telemetry communication outage."


def test_update_from_domain_rejects_invalid_type() -> None:
    """Verify update rejects non-ground-truth values."""
    orm = _orm_event()

    with pytest.raises(TypeError, match="GroundTruthEvent instance"):
        orm.update_from_domain(object())  # type: ignore[arg-type]


def test_update_from_domain_rejects_different_identifier() -> None:
    """Verify persisted event identity cannot be changed."""
    orm = _orm_event()
    different = _domain_event(ground_truth_id="GTE-0000002")

    with pytest.raises(ValueError, match="different ground_truth_id"):
        orm.update_from_domain(different)


def test_to_record_serializes_all_values() -> None:
    """Verify ground-truth records are serialization-ready."""
    inserted_at = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
    updated_at = inserted_at + timedelta(hours=1)
    orm = _orm_event()
    orm.inserted_at = inserted_at
    orm.updated_at = updated_at

    record = orm.to_record()

    assert record == {
        "ground_truth_id": "GTE-0000001",
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "event_type": GroundTruthEventType.EQUIPMENT_FAILURE.value,
        "severity": GroundTruthSeverity.HIGH.value,
        "started_at": _started_at().isoformat(),
        "ended_at": (_started_at() + timedelta(hours=2)).isoformat(),
        "expected_power_loss_pct": 35.0,
        "expected_energy_loss_kwh": 1_250.0,
        "description": "Synthetic inverter failure event.",
        "duration_seconds": 7_200.0,
        "is_equipment_specific": True,
        "is_critical": False,
        "inserted_at": inserted_at.isoformat(),
        "updated_at": updated_at.isoformat(),
    }


def test_to_record_handles_optional_values() -> None:
    """Verify optional fields serialize correctly."""
    record = _orm_event(
        equipment_id=None,
        description=None,
    ).to_record()

    assert record["equipment_id"] is None
    assert record["description"] is None
    assert record["is_equipment_specific"] is False


def test_to_record_handles_unset_audit_timestamps() -> None:
    """Verify unsaved ORM objects serialize missing audit timestamps."""
    record = _orm_event().to_record()

    assert record["inserted_at"] is None
    assert record["updated_at"] is None


def test_repr_contains_key_identity_fields() -> None:
    """Verify developer representation is concise and useful."""
    value = repr(_orm_event())

    assert "GroundTruthEventORM" in value
    assert "GTE-0000001" in value
    assert "PLANT-001" in value
    assert GroundTruthEventType.EQUIPMENT_FAILURE.value in value
    assert GroundTruthSeverity.HIGH.value in value


def test_loss_defaults_are_zero() -> None:
    """Verify expected loss metrics default to zero."""
    power_column = GroundTruthEventORM.__table__.columns["expected_power_loss_pct"]
    energy_column = GroundTruthEventORM.__table__.columns["expected_energy_loss_kwh"]

    assert power_column.default is not None
    assert power_column.default.arg == 0.0
    assert power_column.server_default is not None
    assert energy_column.default is not None
    assert energy_column.default.arg == 0.0
    assert energy_column.server_default is not None


def test_timestamp_columns_are_timezone_aware() -> None:
    """Verify event and audit timestamps preserve timezone data."""
    for column_name in (
        "started_at",
        "ended_at",
        "inserted_at",
        "updated_at",
    ):
        assert GroundTruthEventORM.__table__.columns[column_name].type.timezone is True


def test_plant_relationship_configuration() -> None:
    """Verify ground-truth events link to PlantORM."""
    relationship_property = GroundTruthEventORM.__mapper__.relationships["plant"]

    assert relationship_property.mapper.class_.__name__ == "PlantORM"
    assert relationship_property.uselist is False


def test_equipment_relationship_configuration() -> None:
    """Verify ground-truth events optionally link to EquipmentORM."""
    relationship_property = GroundTruthEventORM.__mapper__.relationships["equipment"]

    assert relationship_property.mapper.class_.__name__ == "EquipmentORM"
    assert relationship_property.uselist is False


def test_description_length_matches_domain_contract() -> None:
    """Verify description storage matches the domain maximum."""
    assert GroundTruthEventORM.__table__.columns["description"].type.length == 1_000


def test_loss_columns_use_float_type() -> None:
    """Verify expected loss metrics use floating-point storage."""
    for column_name in (
        "expected_power_loss_pct",
        "expected_energy_loss_kwh",
    ):
        assert (
            GroundTruthEventORM.__table__.columns[column_name].type.python_type is float
        )
