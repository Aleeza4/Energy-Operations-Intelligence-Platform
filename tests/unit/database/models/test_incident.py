"""
Unit tests for the EOIP Incident SQLAlchemy ORM model.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index

from eoip.database.models.incident import IncidentORM
from eoip.synthetic.models.incident import (
    Incident,
    IncidentCategory,
    IncidentSeverity,
    IncidentStatus,
)


def _occurred_at() -> datetime:
    """Return the standard timezone-aware incident timestamp."""
    return datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def _domain_incident(**overrides: object) -> Incident:
    """Return a valid Incident domain model with optional overrides."""
    data: dict[str, object] = {
        "incident_id": "INC-0000001",
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "incident_name": "Inverter Trip Incident",
        "category": IncidentCategory.EQUIPMENT_FAILURE,
        "severity": IncidentSeverity.HIGH,
        "occurred_at": _occurred_at(),
        "status": IncidentStatus.OPEN,
        "detected_at": None,
        "resolved_at": None,
        "description": "The inverter stopped producing power.",
        "root_cause": None,
        "linked_alarm_id": "ALM-0000001",
        "is_synthetic_ground_truth": False,
    }
    data.update(overrides)
    return Incident(**data)


def _orm_incident(**overrides: object) -> IncidentORM:
    """Return a valid IncidentORM object with optional overrides."""
    data: dict[str, object] = {
        "incident_id": "INC-0000001",
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "incident_name": "Inverter Trip Incident",
        "category": IncidentCategory.EQUIPMENT_FAILURE.value,
        "severity": IncidentSeverity.HIGH.value,
        "occurred_at": _occurred_at(),
        "status": IncidentStatus.OPEN.value,
        "detected_at": None,
        "resolved_at": None,
        "description": "The inverter stopped producing power.",
        "root_cause": None,
        "linked_alarm_id": "ALM-0000001",
        "is_synthetic_ground_truth": False,
    }
    data.update(overrides)
    return IncidentORM(**data)


def test_table_name() -> None:
    """Verify the mapped database table name."""
    assert IncidentORM.__tablename__ == "incidents"


def test_primary_key_column() -> None:
    """Verify incident_id is the only primary-key column."""
    primary_keys = {column.name for column in IncidentORM.__table__.primary_key.columns}

    assert primary_keys == {"incident_id"}


def test_expected_columns_exist() -> None:
    """Verify the complete persistence contract."""
    assert set(IncidentORM.__table__.columns.keys()) == {
        "incident_id",
        "plant_id",
        "equipment_id",
        "incident_name",
        "category",
        "severity",
        "occurred_at",
        "status",
        "detected_at",
        "resolved_at",
        "description",
        "root_cause",
        "linked_alarm_id",
        "is_synthetic_ground_truth",
        "created_at",
        "updated_at",
    }


def test_required_columns_are_not_nullable() -> None:
    """Verify required incident fields are non-nullable."""
    for column_name in (
        "incident_id",
        "plant_id",
        "equipment_id",
        "incident_name",
        "category",
        "severity",
        "occurred_at",
        "status",
        "is_synthetic_ground_truth",
        "created_at",
        "updated_at",
    ):
        assert IncidentORM.__table__.columns[column_name].nullable is False


def test_optional_columns_are_nullable() -> None:
    """Verify optional incident fields remain nullable."""
    for column_name in (
        "detected_at",
        "resolved_at",
        "description",
        "root_cause",
        "linked_alarm_id",
    ):
        assert IncidentORM.__table__.columns[column_name].nullable is True


def test_expected_foreign_keys_exist() -> None:
    """Verify plant, equipment, and alarm foreign keys."""
    targets = {
        foreign_key.target_fullname
        for foreign_key in IncidentORM.__table__.foreign_keys
    }

    assert targets == {
        "plants.plant_id",
        "equipment.equipment_id",
        "alarms.alarm_id",
    }


def test_foreign_key_actions() -> None:
    """Verify foreign-key update and delete behavior."""
    foreign_keys = {
        foreign_key.parent.name: foreign_key
        for foreign_key in IncidentORM.__table__.foreign_keys
    }

    assert foreign_keys["plant_id"].onupdate == "CASCADE"
    assert foreign_keys["plant_id"].ondelete == "RESTRICT"
    assert foreign_keys["equipment_id"].onupdate == "CASCADE"
    assert foreign_keys["equipment_id"].ondelete == "RESTRICT"
    assert foreign_keys["linked_alarm_id"].onupdate == "CASCADE"
    assert foreign_keys["linked_alarm_id"].ondelete == "SET NULL"


def test_foreign_key_constraints_are_declared() -> None:
    """Verify all foreign-key constraints are registered."""
    constraints = [
        constraint
        for constraint in IncidentORM.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]

    assert len(constraints) == 3


def test_expected_check_constraints_exist() -> None:
    """Verify controlled-value and lifecycle constraints."""
    constraint_names = {
        constraint.name
        for constraint in IncidentORM.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert constraint_names == {
        "ck_incidents_valid_category",
        "ck_incidents_valid_severity",
        "ck_incidents_valid_status",
        "ck_incidents_detected_not_before_occurred",
        "ck_incidents_resolved_not_before_occurred",
        "ck_incidents_resolved_not_before_detected",
        "ck_incidents_open_has_no_resolved_at",
        "ck_incidents_investigating_has_detected_at",
        "ck_incidents_investigating_has_no_resolved_at",
        "ck_incidents_resolved_has_timestamp",
    }


def test_expected_indexes_exist() -> None:
    """Verify incident analytics indexes are declared."""
    index_names = {
        index.name
        for index in IncidentORM.__table__.indexes
        if isinstance(index, Index)
    }

    assert index_names == {
        "ix_incidents_plant_id",
        "ix_incidents_equipment_id",
        "ix_incidents_linked_alarm_id",
        "ix_incidents_category",
        "ix_incidents_severity",
        "ix_incidents_status",
        "ix_incidents_occurred_at",
        "ix_incidents_plant_equipment_occurred_at",
    }


def test_composite_index_column_order() -> None:
    """Verify the composite operational-history index order."""
    index = next(
        index
        for index in IncidentORM.__table__.indexes
        if index.name == "ix_incidents_plant_equipment_occurred_at"
    )

    assert tuple(column.name for column in index.columns) == (
        "plant_id",
        "equipment_id",
        "occurred_at",
    )


def test_from_domain_maps_all_fields() -> None:
    """Verify conversion from the authoritative domain model."""
    occurred_at = _occurred_at()
    detected_at = occurred_at + timedelta(minutes=4)
    resolved_at = occurred_at + timedelta(hours=2)
    incident = _domain_incident(
        category=IncidentCategory.GRID_EVENT,
        severity=IncidentSeverity.CRITICAL,
        status=IncidentStatus.RESOLVED,
        detected_at=detected_at,
        resolved_at=resolved_at,
        description="Grid export was unavailable.",
        root_cause="Utility-side protection operation.",
        linked_alarm_id="ALM-0000002",
        is_synthetic_ground_truth=True,
    )

    orm = IncidentORM.from_domain(incident)

    assert orm.incident_id == incident.incident_id
    assert orm.plant_id == incident.plant_id
    assert orm.equipment_id == incident.equipment_id
    assert orm.incident_name == incident.incident_name
    assert orm.category == IncidentCategory.GRID_EVENT.value
    assert orm.severity == IncidentSeverity.CRITICAL.value
    assert orm.occurred_at == occurred_at
    assert orm.status == IncidentStatus.RESOLVED.value
    assert orm.detected_at == detected_at
    assert orm.resolved_at == resolved_at
    assert orm.description == "Grid export was unavailable."
    assert orm.root_cause == "Utility-side protection operation."
    assert orm.linked_alarm_id == "ALM-0000002"
    assert orm.is_synthetic_ground_truth is True


def test_from_domain_preserves_none_values() -> None:
    """Verify optional values remain None during conversion."""
    incident = _domain_incident(
        detected_at=None,
        resolved_at=None,
        description=None,
        root_cause=None,
        linked_alarm_id=None,
    )

    orm = IncidentORM.from_domain(incident)

    assert orm.detected_at is None
    assert orm.resolved_at is None
    assert orm.description is None
    assert orm.root_cause is None
    assert orm.linked_alarm_id is None


def test_from_domain_rejects_invalid_type() -> None:
    """Verify conversion rejects non-Incident values."""
    with pytest.raises(TypeError, match="Incident instance"):
        IncidentORM.from_domain(object())  # type: ignore[arg-type]


def test_to_domain_returns_authoritative_model() -> None:
    """Verify conversion back to the Incident domain model."""
    occurred_at = _occurred_at()
    detected_at = occurred_at + timedelta(minutes=3)
    orm = _orm_incident(
        category=IncidentCategory.COMMUNICATION_FAILURE.value,
        severity=IncidentSeverity.MODERATE.value,
        status=IncidentStatus.INVESTIGATING.value,
        detected_at=detected_at,
        resolved_at=None,
        description=None,
        root_cause=None,
        linked_alarm_id=None,
        is_synthetic_ground_truth=True,
    )

    incident = orm.to_domain()

    assert isinstance(incident, Incident)
    assert incident.incident_id == orm.incident_id
    assert incident.plant_id == orm.plant_id
    assert incident.equipment_id == orm.equipment_id
    assert incident.incident_name == orm.incident_name
    assert incident.category is IncidentCategory.COMMUNICATION_FAILURE
    assert incident.severity is IncidentSeverity.MODERATE
    assert incident.occurred_at == occurred_at
    assert incident.status is IncidentStatus.INVESTIGATING
    assert incident.detected_at == detected_at
    assert incident.resolved_at is None
    assert incident.description is None
    assert incident.root_cause is None
    assert incident.linked_alarm_id is None
    assert incident.is_synthetic_ground_truth is True


def test_domain_round_trip_preserves_values() -> None:
    """Verify domain-to-ORM-to-domain conversion is lossless."""
    occurred_at = _occurred_at()
    original = _domain_incident(
        category=IncidentCategory.PERFORMANCE_DEGRADATION,
        severity=IncidentSeverity.LOW,
        status=IncidentStatus.RESOLVED,
        detected_at=occurred_at + timedelta(minutes=6),
        resolved_at=occurred_at + timedelta(hours=4),
        root_cause="Soiling accumulation.",
        is_synthetic_ground_truth=True,
    )

    restored = IncidentORM.from_domain(original).to_domain()

    assert restored == original


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (IncidentStatus.OPEN.value, True),
        (IncidentStatus.INVESTIGATING.value, True),
        (IncidentStatus.RESOLVED.value, False),
    ],
)
def test_is_open(status: str, expected: bool) -> None:
    """Verify open-incident classification."""
    orm = _orm_incident(status=status)

    assert orm.is_open is expected


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        (IncidentSeverity.LOW.value, False),
        (IncidentSeverity.MODERATE.value, False),
        (IncidentSeverity.HIGH.value, False),
        (IncidentSeverity.CRITICAL.value, True),
    ],
)
def test_is_critical(severity: str, expected: bool) -> None:
    """Verify critical-incident classification."""
    orm = _orm_incident(severity=severity)

    assert orm.is_critical is expected


def test_detection_seconds() -> None:
    """Verify elapsed incident-detection time."""
    occurred_at = _occurred_at()
    orm = _orm_incident(
        occurred_at=occurred_at,
        detected_at=occurred_at + timedelta(seconds=125.4321),
    )

    assert orm.detection_seconds == 125.432


def test_detection_seconds_is_none_without_timestamp() -> None:
    """Verify missing detection timestamp produces no duration."""
    assert _orm_incident(detected_at=None).detection_seconds is None


def test_resolution_seconds() -> None:
    """Verify elapsed incident-resolution time."""
    occurred_at = _occurred_at()
    orm = _orm_incident(
        occurred_at=occurred_at,
        resolved_at=occurred_at + timedelta(seconds=7_245.6789),
    )

    assert orm.resolution_seconds == 7245.679


def test_resolution_seconds_is_none_without_timestamp() -> None:
    """Verify missing resolution timestamp produces no duration."""
    assert _orm_incident(resolved_at=None).resolution_seconds is None


def test_update_from_domain_updates_mutable_fields() -> None:
    """Verify ORM values can be refreshed from a matching domain object."""
    orm = _orm_incident()
    occurred_at = _occurred_at() + timedelta(days=1)
    updated = _domain_incident(
        plant_id="PLANT-002",
        equipment_id="EQP-00002",
        incident_name="Grid Event Updated",
        category=IncidentCategory.GRID_EVENT,
        severity=IncidentSeverity.CRITICAL,
        occurred_at=occurred_at,
        status=IncidentStatus.RESOLVED,
        detected_at=occurred_at + timedelta(minutes=2),
        resolved_at=occurred_at + timedelta(hours=1),
        description="Grid export connection was interrupted.",
        root_cause="External grid outage.",
        linked_alarm_id="ALM-0000003",
        is_synthetic_ground_truth=True,
    )

    orm.update_from_domain(updated)

    assert orm.plant_id == "PLANT-002"
    assert orm.equipment_id == "EQP-00002"
    assert orm.incident_name == "Grid Event Updated"
    assert orm.category == IncidentCategory.GRID_EVENT.value
    assert orm.severity == IncidentSeverity.CRITICAL.value
    assert orm.occurred_at == occurred_at
    assert orm.status == IncidentStatus.RESOLVED.value
    assert orm.detected_at == occurred_at + timedelta(minutes=2)
    assert orm.resolved_at == occurred_at + timedelta(hours=1)
    assert orm.description == "Grid export connection was interrupted."
    assert orm.root_cause == "External grid outage."
    assert orm.linked_alarm_id == "ALM-0000003"
    assert orm.is_synthetic_ground_truth is True


def test_update_from_domain_rejects_invalid_type() -> None:
    """Verify update rejects non-Incident values."""
    orm = _orm_incident()

    with pytest.raises(TypeError, match="Incident instance"):
        orm.update_from_domain(object())  # type: ignore[arg-type]


def test_update_from_domain_rejects_different_identifier() -> None:
    """Verify persisted incident identity cannot be changed."""
    orm = _orm_incident()
    different = _domain_incident(incident_id="INC-0000002")

    with pytest.raises(ValueError, match="different incident_id"):
        orm.update_from_domain(different)


def test_to_record_serializes_all_values() -> None:
    """Verify database records are serialization-ready."""
    occurred_at = _occurred_at()
    detected_at = occurred_at + timedelta(minutes=4)
    resolved_at = occurred_at + timedelta(hours=2)
    created_at = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
    updated_at = created_at + timedelta(hours=1)

    orm = _orm_incident(
        occurred_at=occurred_at,
        status=IncidentStatus.RESOLVED.value,
        detected_at=detected_at,
        resolved_at=resolved_at,
        root_cause="Inverter internal protection trip.",
        is_synthetic_ground_truth=True,
    )
    orm.created_at = created_at
    orm.updated_at = updated_at

    record = orm.to_record()

    assert record == {
        "incident_id": "INC-0000001",
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "incident_name": "Inverter Trip Incident",
        "category": IncidentCategory.EQUIPMENT_FAILURE.value,
        "severity": IncidentSeverity.HIGH.value,
        "occurred_at": occurred_at.isoformat(),
        "status": IncidentStatus.RESOLVED.value,
        "detected_at": detected_at.isoformat(),
        "resolved_at": resolved_at.isoformat(),
        "description": "The inverter stopped producing power.",
        "root_cause": "Inverter internal protection trip.",
        "linked_alarm_id": "ALM-0000001",
        "is_synthetic_ground_truth": True,
        "is_open": False,
        "is_critical": False,
        "detection_seconds": 240.0,
        "resolution_seconds": 7200.0,
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
    }


def test_to_record_handles_optional_values() -> None:
    """Verify optional values serialize correctly."""
    record = _orm_incident(
        detected_at=None,
        resolved_at=None,
        description=None,
        root_cause=None,
        linked_alarm_id=None,
    ).to_record()

    assert record["detected_at"] is None
    assert record["resolved_at"] is None
    assert record["description"] is None
    assert record["root_cause"] is None
    assert record["linked_alarm_id"] is None
    assert record["detection_seconds"] is None
    assert record["resolution_seconds"] is None


def test_to_record_handles_unset_audit_timestamps() -> None:
    """Verify unsaved ORM objects serialize missing audit timestamps."""
    record = _orm_incident().to_record()

    assert record["created_at"] is None
    assert record["updated_at"] is None


def test_repr_contains_key_identity_fields() -> None:
    """Verify developer representation is concise and useful."""
    value = repr(_orm_incident())

    assert "IncidentORM" in value
    assert "INC-0000001" in value
    assert "EQP-00001" in value
    assert IncidentSeverity.HIGH.value in value
    assert IncidentStatus.OPEN.value in value


def test_status_default_matches_domain_default() -> None:
    """Verify ORM status defaults to open."""
    column = IncidentORM.__table__.columns["status"]

    assert column.default is not None
    assert column.default.arg == IncidentStatus.OPEN.value
    assert column.server_default is not None


def test_ground_truth_default_is_false() -> None:
    """Verify synthetic ground-truth defaults to false."""
    column = IncidentORM.__table__.columns["is_synthetic_ground_truth"]

    assert column.default is not None
    assert column.default.arg is False
    assert column.server_default is not None


def test_timestamp_columns_are_timezone_aware() -> None:
    """Verify lifecycle and audit timestamps preserve timezone data."""
    for column_name in (
        "occurred_at",
        "detected_at",
        "resolved_at",
        "created_at",
        "updated_at",
    ):
        assert IncidentORM.__table__.columns[column_name].type.timezone is True


def test_plant_relationship_configuration() -> None:
    """Verify incident links to the Plant ORM model."""
    relationship_property = IncidentORM.__mapper__.relationships["plant"]

    assert relationship_property.mapper.class_.__name__ == "PlantORM"
    assert relationship_property.uselist is False


def test_equipment_relationship_configuration() -> None:
    """Verify incident links to the Equipment ORM model."""
    relationship_property = IncidentORM.__mapper__.relationships["equipment"]

    assert relationship_property.mapper.class_.__name__ == "EquipmentORM"
    assert relationship_property.uselist is False


def test_linked_alarm_relationship_configuration() -> None:
    """Verify incident optionally links to the Alarm ORM model."""
    relationship_property = IncidentORM.__mapper__.relationships["linked_alarm"]

    assert relationship_property.mapper.class_.__name__ == "AlarmORM"
    assert relationship_property.uselist is False


def test_incident_name_length_is_150() -> None:
    """Verify incident names match the domain maximum length."""
    assert IncidentORM.__table__.columns["incident_name"].type.length == 150


def test_description_length_is_1000() -> None:
    """Verify incident descriptions match the domain maximum length."""
    assert IncidentORM.__table__.columns["description"].type.length == 1_000


def test_root_cause_length_is_500() -> None:
    """Verify root-cause text matches the domain maximum length."""
    assert IncidentORM.__table__.columns["root_cause"].type.length == 500
