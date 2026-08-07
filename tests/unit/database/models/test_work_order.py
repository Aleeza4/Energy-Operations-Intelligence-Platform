"""
Unit tests for the EOIP WorkOrder SQLAlchemy ORM model.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index

from eoip.database.models.work_order import WorkOrderORM
from eoip.synthetic.models.work_order import (
    WorkOrder,
    WorkOrderPriority,
    WorkOrderStatus,
    WorkOrderType,
)


def _created_at() -> datetime:
    """Return the standard timezone-aware work-order creation timestamp."""
    return datetime(2026, 1, 1, 8, 0, tzinfo=UTC)


def _domain_work_order(**overrides: object) -> WorkOrder:
    """Return a valid WorkOrder domain model with optional overrides."""
    data: dict[str, object] = {
        "work_order_id": "WO-0000001",
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "work_order_name": "Inspect Inverter Cooling System",
        "work_order_type": WorkOrderType.INSPECTION,
        "priority": WorkOrderPriority.MEDIUM,
        "created_at": _created_at(),
        "status": WorkOrderStatus.OPEN,
        "linked_incident_id": "INC-0000001",
        "assigned_team": None,
        "scheduled_at": None,
        "started_at": None,
        "completed_at": None,
        "cancelled_at": None,
        "estimated_labor_hours": 4.0,
        "actual_labor_hours": None,
        "estimated_cost": 500.0,
        "actual_cost": None,
        "description": "Inspect cooling fans and clean ventilation paths.",
        "completion_notes": None,
        "is_synthetic_ground_truth": False,
    }
    data.update(overrides)
    return WorkOrder(**data)


def _orm_work_order(**overrides: object) -> WorkOrderORM:
    """Return a valid WorkOrderORM object with optional overrides."""
    data: dict[str, object] = {
        "work_order_id": "WO-0000001",
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "work_order_name": "Inspect Inverter Cooling System",
        "work_order_type": WorkOrderType.INSPECTION.value,
        "priority": WorkOrderPriority.MEDIUM.value,
        "created_at": _created_at(),
        "status": WorkOrderStatus.OPEN.value,
        "linked_incident_id": "INC-0000001",
        "assigned_team": None,
        "scheduled_at": None,
        "started_at": None,
        "completed_at": None,
        "cancelled_at": None,
        "estimated_labor_hours": 4.0,
        "actual_labor_hours": None,
        "estimated_cost": 500.0,
        "actual_cost": None,
        "description": "Inspect cooling fans and clean ventilation paths.",
        "completion_notes": None,
        "is_synthetic_ground_truth": False,
    }
    data.update(overrides)
    return WorkOrderORM(**data)


def test_table_name() -> None:
    """Verify the mapped database table name."""
    assert WorkOrderORM.__tablename__ == "work_orders"


def test_primary_key_column() -> None:
    """Verify work_order_id is the only primary-key column."""
    primary_keys = {
        column.name for column in WorkOrderORM.__table__.primary_key.columns
    }

    assert primary_keys == {"work_order_id"}


def test_expected_columns_exist() -> None:
    """Verify the complete persistence contract."""
    assert set(WorkOrderORM.__table__.columns.keys()) == {
        "work_order_id",
        "plant_id",
        "equipment_id",
        "work_order_name",
        "work_order_type",
        "priority",
        "created_at",
        "status",
        "linked_incident_id",
        "assigned_team",
        "scheduled_at",
        "started_at",
        "completed_at",
        "cancelled_at",
        "estimated_labor_hours",
        "actual_labor_hours",
        "estimated_cost",
        "actual_cost",
        "description",
        "completion_notes",
        "is_synthetic_ground_truth",
        "inserted_at",
        "updated_at",
    }


def test_required_columns_are_not_nullable() -> None:
    """Verify required work-order fields are non-nullable."""
    for column_name in (
        "work_order_id",
        "plant_id",
        "equipment_id",
        "work_order_name",
        "work_order_type",
        "priority",
        "created_at",
        "status",
        "is_synthetic_ground_truth",
        "inserted_at",
        "updated_at",
    ):
        assert WorkOrderORM.__table__.columns[column_name].nullable is False


def test_optional_columns_are_nullable() -> None:
    """Verify optional work-order fields remain nullable."""
    for column_name in (
        "linked_incident_id",
        "assigned_team",
        "scheduled_at",
        "started_at",
        "completed_at",
        "cancelled_at",
        "estimated_labor_hours",
        "actual_labor_hours",
        "estimated_cost",
        "actual_cost",
        "description",
        "completion_notes",
    ):
        assert WorkOrderORM.__table__.columns[column_name].nullable is True


def test_expected_foreign_keys_exist() -> None:
    """Verify plant, equipment, and incident foreign keys."""
    targets = {
        foreign_key.target_fullname
        for foreign_key in WorkOrderORM.__table__.foreign_keys
    }

    assert targets == {
        "plants.plant_id",
        "equipment.equipment_id",
        "incidents.incident_id",
    }


def test_foreign_key_actions() -> None:
    """Verify foreign-key update and delete behavior."""
    foreign_keys = {
        foreign_key.parent.name: foreign_key
        for foreign_key in WorkOrderORM.__table__.foreign_keys
    }

    assert foreign_keys["plant_id"].onupdate == "CASCADE"
    assert foreign_keys["plant_id"].ondelete == "RESTRICT"
    assert foreign_keys["equipment_id"].onupdate == "CASCADE"
    assert foreign_keys["equipment_id"].ondelete == "RESTRICT"
    assert foreign_keys["linked_incident_id"].onupdate == "CASCADE"
    assert foreign_keys["linked_incident_id"].ondelete == "SET NULL"


def test_foreign_key_constraints_are_declared() -> None:
    """Verify all foreign-key constraints are registered."""
    constraints = [
        constraint
        for constraint in WorkOrderORM.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]

    assert len(constraints) == 3


def test_expected_check_constraints_exist() -> None:
    """Verify lifecycle, numeric, and controlled-value constraints."""
    constraint_names = {
        constraint.name
        for constraint in WorkOrderORM.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert constraint_names == {
        "ck_work_orders_valid_work_order_type",
        "ck_work_orders_valid_priority",
        "ck_work_orders_valid_status",
        "ck_work_orders_scheduled_not_before_created",
        "ck_work_orders_started_not_before_created",
        "ck_work_orders_completed_not_before_created",
        "ck_work_orders_cancelled_not_before_created",
        "ck_work_orders_started_not_before_scheduled",
        "ck_work_orders_completed_not_before_started",
        "ck_work_orders_estimated_labor_non_negative",
        "ck_work_orders_actual_labor_non_negative",
        "ck_work_orders_estimated_cost_non_negative",
        "ck_work_orders_actual_cost_non_negative",
        "ck_work_orders_open_has_no_started_at",
        "ck_work_orders_open_has_no_completed_at",
        "ck_work_orders_open_has_no_cancelled_at",
        "ck_work_orders_assigned_has_team",
        "ck_work_orders_assigned_has_no_started_at",
        "ck_work_orders_in_progress_has_team",
        "ck_work_orders_in_progress_has_started_at",
        "ck_work_orders_in_progress_has_no_completed_at",
        "ck_work_orders_in_progress_has_no_cancelled_at",
        "ck_work_orders_completed_has_started_at",
        "ck_work_orders_completed_has_completed_at",
        "ck_work_orders_completed_has_no_cancelled_at",
        "ck_work_orders_cancelled_has_cancelled_at",
        "ck_work_orders_cancelled_has_no_completed_at",
    }


def test_expected_indexes_exist() -> None:
    """Verify maintenance analytics indexes are declared."""
    index_names = {
        index.name
        for index in WorkOrderORM.__table__.indexes
        if isinstance(index, Index)
    }

    assert index_names == {
        "ix_work_orders_plant_id",
        "ix_work_orders_equipment_id",
        "ix_work_orders_linked_incident_id",
        "ix_work_orders_work_order_type",
        "ix_work_orders_priority",
        "ix_work_orders_status",
        "ix_work_orders_created_at",
        "ix_work_orders_scheduled_at",
        "ix_work_orders_plant_equipment_created_at",
    }


def test_composite_index_column_order() -> None:
    """Verify the composite work-order history index order."""
    index = next(
        index
        for index in WorkOrderORM.__table__.indexes
        if index.name == "ix_work_orders_plant_equipment_created_at"
    )

    assert tuple(column.name for column in index.columns) == (
        "plant_id",
        "equipment_id",
        "created_at",
    )


def test_from_domain_maps_all_fields() -> None:
    """Verify conversion from the authoritative domain model."""
    created_at = _created_at()
    scheduled_at = created_at + timedelta(hours=2)
    started_at = scheduled_at + timedelta(hours=1)
    completed_at = started_at + timedelta(hours=5)

    work_order = _domain_work_order(
        work_order_type=WorkOrderType.CORRECTIVE,
        priority=WorkOrderPriority.HIGH,
        status=WorkOrderStatus.COMPLETED,
        assigned_team="Field Maintenance Team A",
        scheduled_at=scheduled_at,
        started_at=started_at,
        completed_at=completed_at,
        actual_labor_hours=5.5,
        actual_cost=620.0,
        completion_notes="Cooling fan replaced successfully.",
        is_synthetic_ground_truth=True,
    )

    orm = WorkOrderORM.from_domain(work_order)

    assert orm.work_order_id == work_order.work_order_id
    assert orm.plant_id == work_order.plant_id
    assert orm.equipment_id == work_order.equipment_id
    assert orm.work_order_name == work_order.work_order_name
    assert orm.work_order_type == WorkOrderType.CORRECTIVE.value
    assert orm.priority == WorkOrderPriority.HIGH.value
    assert orm.created_at == created_at
    assert orm.status == WorkOrderStatus.COMPLETED.value
    assert orm.linked_incident_id == work_order.linked_incident_id
    assert orm.assigned_team == "Field Maintenance Team A"
    assert orm.scheduled_at == scheduled_at
    assert orm.started_at == started_at
    assert orm.completed_at == completed_at
    assert orm.cancelled_at is None
    assert orm.estimated_labor_hours == 4.0
    assert orm.actual_labor_hours == 5.5
    assert orm.estimated_cost == 500.0
    assert orm.actual_cost == 620.0
    assert orm.description == work_order.description
    assert orm.completion_notes == "Cooling fan replaced successfully."
    assert orm.is_synthetic_ground_truth is True


def test_from_domain_preserves_none_values() -> None:
    """Verify optional values remain None during conversion."""
    work_order = _domain_work_order(
        linked_incident_id=None,
        assigned_team=None,
        scheduled_at=None,
        started_at=None,
        completed_at=None,
        cancelled_at=None,
        estimated_labor_hours=None,
        actual_labor_hours=None,
        estimated_cost=None,
        actual_cost=None,
        description=None,
        completion_notes=None,
    )

    orm = WorkOrderORM.from_domain(work_order)

    assert orm.linked_incident_id is None
    assert orm.assigned_team is None
    assert orm.scheduled_at is None
    assert orm.started_at is None
    assert orm.completed_at is None
    assert orm.cancelled_at is None
    assert orm.estimated_labor_hours is None
    assert orm.actual_labor_hours is None
    assert orm.estimated_cost is None
    assert orm.actual_cost is None
    assert orm.description is None
    assert orm.completion_notes is None


def test_from_domain_rejects_invalid_type() -> None:
    """Verify conversion rejects non-WorkOrder values."""
    with pytest.raises(TypeError, match="WorkOrder instance"):
        WorkOrderORM.from_domain(object())  # type: ignore[arg-type]


def test_to_domain_returns_authoritative_model() -> None:
    """Verify conversion back to the WorkOrder domain model."""
    created_at = _created_at()
    scheduled_at = created_at + timedelta(hours=1)

    orm = _orm_work_order(
        work_order_type=WorkOrderType.PREVENTIVE.value,
        priority=WorkOrderPriority.LOW.value,
        status=WorkOrderStatus.ASSIGNED.value,
        assigned_team="Preventive Maintenance Team",
        scheduled_at=scheduled_at,
        linked_incident_id=None,
        description=None,
        is_synthetic_ground_truth=True,
    )

    work_order = orm.to_domain()

    assert isinstance(work_order, WorkOrder)
    assert work_order.work_order_id == orm.work_order_id
    assert work_order.plant_id == orm.plant_id
    assert work_order.equipment_id == orm.equipment_id
    assert work_order.work_order_name == orm.work_order_name
    assert work_order.work_order_type is WorkOrderType.PREVENTIVE
    assert work_order.priority is WorkOrderPriority.LOW
    assert work_order.created_at == created_at
    assert work_order.status is WorkOrderStatus.ASSIGNED
    assert work_order.linked_incident_id is None
    assert work_order.assigned_team == "Preventive Maintenance Team"
    assert work_order.scheduled_at == scheduled_at
    assert work_order.started_at is None
    assert work_order.completed_at is None
    assert work_order.cancelled_at is None
    assert work_order.description is None
    assert work_order.is_synthetic_ground_truth is True


def test_domain_round_trip_preserves_values() -> None:
    """Verify domain-to-ORM-to-domain conversion is lossless."""
    created_at = _created_at()
    started_at = created_at + timedelta(hours=2)
    original = _domain_work_order(
        work_order_type=WorkOrderType.EMERGENCY,
        priority=WorkOrderPriority.CRITICAL,
        status=WorkOrderStatus.IN_PROGRESS,
        assigned_team="Emergency Response Team",
        scheduled_at=created_at + timedelta(hours=1),
        started_at=started_at,
        estimated_labor_hours=8.0,
        estimated_cost=2_000.0,
        is_synthetic_ground_truth=True,
    )

    restored = WorkOrderORM.from_domain(original).to_domain()

    assert restored == original


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (WorkOrderStatus.OPEN.value, True),
        (WorkOrderStatus.ASSIGNED.value, True),
        (WorkOrderStatus.IN_PROGRESS.value, True),
        (WorkOrderStatus.COMPLETED.value, False),
        (WorkOrderStatus.CANCELLED.value, False),
    ],
)
def test_is_open(status: str, expected: bool) -> None:
    """Verify actionable work-order classification."""
    assert _orm_work_order(status=status).is_open is expected


@pytest.mark.parametrize(
    ("estimated_cost", "actual_cost", "expected"),
    [
        (500.0, 600.0, True),
        (500.0, 500.0, False),
        (500.0, 400.0, False),
        (None, 400.0, None),
        (500.0, None, None),
    ],
)
def test_is_over_budget(
    estimated_cost: float | None,
    actual_cost: float | None,
    expected: bool | None,
) -> None:
    """Verify over-budget classification."""
    orm = _orm_work_order(
        estimated_cost=estimated_cost,
        actual_cost=actual_cost,
    )

    assert orm.is_over_budget is expected


def test_labor_variance_hours() -> None:
    """Verify actual-minus-estimated labor variance."""
    orm = _orm_work_order(
        estimated_labor_hours=4.0,
        actual_labor_hours=5.2349,
    )

    assert orm.labor_variance_hours == 1.235


@pytest.mark.parametrize(
    ("estimated", "actual"),
    [
        (None, 5.0),
        (4.0, None),
        (None, None),
    ],
)
def test_labor_variance_is_none_when_incomplete(
    estimated: float | None,
    actual: float | None,
) -> None:
    """Verify labor variance requires both values."""
    orm = _orm_work_order(
        estimated_labor_hours=estimated,
        actual_labor_hours=actual,
    )

    assert orm.labor_variance_hours is None


def test_cost_variance() -> None:
    """Verify actual-minus-estimated cost variance."""
    orm = _orm_work_order(
        estimated_cost=500.0,
        actual_cost=620.567,
    )

    assert orm.cost_variance == 120.57


@pytest.mark.parametrize(
    ("estimated", "actual"),
    [
        (None, 500.0),
        (500.0, None),
        (None, None),
    ],
)
def test_cost_variance_is_none_when_incomplete(
    estimated: float | None,
    actual: float | None,
) -> None:
    """Verify cost variance requires both values."""
    orm = _orm_work_order(
        estimated_cost=estimated,
        actual_cost=actual,
    )

    assert orm.cost_variance is None


def test_completion_seconds() -> None:
    """Verify elapsed completion duration."""
    started_at = _created_at() + timedelta(hours=2)
    completed_at = started_at + timedelta(seconds=7_245.6789)
    orm = _orm_work_order(
        started_at=started_at,
        completed_at=completed_at,
    )

    assert orm.completion_seconds == 7245.679


@pytest.mark.parametrize(
    ("started_at", "completed_at"),
    [
        (None, _created_at() + timedelta(hours=2)),
        (_created_at(), None),
        (None, None),
    ],
)
def test_completion_seconds_is_none_when_incomplete(
    started_at: datetime | None,
    completed_at: datetime | None,
) -> None:
    """Verify completion duration requires both timestamps."""
    orm = _orm_work_order(
        started_at=started_at,
        completed_at=completed_at,
    )

    assert orm.completion_seconds is None


def test_update_from_domain_updates_mutable_fields() -> None:
    """Verify ORM values can be refreshed from a matching domain object."""
    orm = _orm_work_order()
    created_at = _created_at() + timedelta(days=1)
    scheduled_at = created_at + timedelta(hours=1)
    started_at = scheduled_at + timedelta(hours=1)
    completed_at = started_at + timedelta(hours=6)

    updated = _domain_work_order(
        plant_id="PLANT-002",
        equipment_id="EQP-00002",
        work_order_name="Replace Transformer Cooling Fan",
        work_order_type=WorkOrderType.CORRECTIVE,
        priority=WorkOrderPriority.HIGH,
        created_at=created_at,
        status=WorkOrderStatus.COMPLETED,
        linked_incident_id="INC-0000002",
        assigned_team="Electrical Maintenance Team",
        scheduled_at=scheduled_at,
        started_at=started_at,
        completed_at=completed_at,
        estimated_labor_hours=5.0,
        actual_labor_hours=6.0,
        estimated_cost=1_000.0,
        actual_cost=1_150.0,
        description="Replace defective transformer cooling fan.",
        completion_notes="Fan replaced and tested.",
        is_synthetic_ground_truth=True,
    )

    orm.update_from_domain(updated)

    assert orm.plant_id == "PLANT-002"
    assert orm.equipment_id == "EQP-00002"
    assert orm.work_order_name == "Replace Transformer Cooling Fan"
    assert orm.work_order_type == WorkOrderType.CORRECTIVE.value
    assert orm.priority == WorkOrderPriority.HIGH.value
    assert orm.created_at == created_at
    assert orm.status == WorkOrderStatus.COMPLETED.value
    assert orm.linked_incident_id == "INC-0000002"
    assert orm.assigned_team == "Electrical Maintenance Team"
    assert orm.scheduled_at == scheduled_at
    assert orm.started_at == started_at
    assert orm.completed_at == completed_at
    assert orm.cancelled_at is None
    assert orm.estimated_labor_hours == 5.0
    assert orm.actual_labor_hours == 6.0
    assert orm.estimated_cost == 1_000.0
    assert orm.actual_cost == 1_150.0
    assert orm.description == "Replace defective transformer cooling fan."
    assert orm.completion_notes == "Fan replaced and tested."
    assert orm.is_synthetic_ground_truth is True


def test_update_from_domain_rejects_invalid_type() -> None:
    """Verify update rejects non-WorkOrder values."""
    orm = _orm_work_order()

    with pytest.raises(TypeError, match="WorkOrder instance"):
        orm.update_from_domain(object())  # type: ignore[arg-type]


def test_update_from_domain_rejects_different_identifier() -> None:
    """Verify persisted work-order identity cannot be changed."""
    orm = _orm_work_order()
    different = _domain_work_order(work_order_id="WO-0000002")

    with pytest.raises(ValueError, match="different work_order_id"):
        orm.update_from_domain(different)


def test_to_record_serializes_all_values() -> None:
    """Verify database records are serialization-ready."""
    created_at = _created_at()
    scheduled_at = created_at + timedelta(hours=1)
    started_at = scheduled_at + timedelta(hours=1)
    completed_at = started_at + timedelta(hours=5)
    inserted_at = datetime(2026, 1, 2, 8, 0, tzinfo=UTC)
    updated_at = inserted_at + timedelta(hours=1)

    orm = _orm_work_order(
        work_order_type=WorkOrderType.CORRECTIVE.value,
        priority=WorkOrderPriority.HIGH.value,
        status=WorkOrderStatus.COMPLETED.value,
        assigned_team="Field Maintenance Team A",
        scheduled_at=scheduled_at,
        started_at=started_at,
        completed_at=completed_at,
        estimated_labor_hours=4.0,
        actual_labor_hours=5.5,
        estimated_cost=500.0,
        actual_cost=620.0,
        completion_notes="Cooling fan replaced successfully.",
        is_synthetic_ground_truth=True,
    )
    orm.inserted_at = inserted_at
    orm.updated_at = updated_at

    record = orm.to_record()

    assert record == {
        "work_order_id": "WO-0000001",
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "work_order_name": "Inspect Inverter Cooling System",
        "work_order_type": WorkOrderType.CORRECTIVE.value,
        "priority": WorkOrderPriority.HIGH.value,
        "created_at": created_at.isoformat(),
        "status": WorkOrderStatus.COMPLETED.value,
        "linked_incident_id": "INC-0000001",
        "assigned_team": "Field Maintenance Team A",
        "scheduled_at": scheduled_at.isoformat(),
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "cancelled_at": None,
        "estimated_labor_hours": 4.0,
        "actual_labor_hours": 5.5,
        "estimated_cost": 500.0,
        "actual_cost": 620.0,
        "description": "Inspect cooling fans and clean ventilation paths.",
        "completion_notes": "Cooling fan replaced successfully.",
        "is_synthetic_ground_truth": True,
        "is_open": False,
        "is_over_budget": True,
        "labor_variance_hours": 1.5,
        "cost_variance": 120.0,
        "completion_seconds": 18000.0,
        "inserted_at": inserted_at.isoformat(),
        "updated_at": updated_at.isoformat(),
    }


def test_to_record_handles_optional_values() -> None:
    """Verify optional values serialize correctly."""
    record = _orm_work_order(
        linked_incident_id=None,
        assigned_team=None,
        scheduled_at=None,
        started_at=None,
        completed_at=None,
        cancelled_at=None,
        estimated_labor_hours=None,
        actual_labor_hours=None,
        estimated_cost=None,
        actual_cost=None,
        description=None,
        completion_notes=None,
    ).to_record()

    assert record["linked_incident_id"] is None
    assert record["assigned_team"] is None
    assert record["scheduled_at"] is None
    assert record["started_at"] is None
    assert record["completed_at"] is None
    assert record["cancelled_at"] is None
    assert record["estimated_labor_hours"] is None
    assert record["actual_labor_hours"] is None
    assert record["estimated_cost"] is None
    assert record["actual_cost"] is None
    assert record["description"] is None
    assert record["completion_notes"] is None
    assert record["is_over_budget"] is None
    assert record["labor_variance_hours"] is None
    assert record["cost_variance"] is None
    assert record["completion_seconds"] is None


def test_to_record_handles_unset_audit_timestamps() -> None:
    """Verify unsaved ORM objects serialize missing audit timestamps."""
    record = _orm_work_order().to_record()

    assert record["inserted_at"] is None
    assert record["updated_at"] is None


def test_serialize_timestamp() -> None:
    """Verify optional timestamp serialization helper."""
    value = _created_at()

    assert WorkOrderORM._serialize_timestamp(value) == value.isoformat()
    assert WorkOrderORM._serialize_timestamp(None) is None


def test_repr_contains_key_identity_fields() -> None:
    """Verify developer representation is concise and useful."""
    value = repr(_orm_work_order())

    assert "WorkOrderORM" in value
    assert "WO-0000001" in value
    assert "EQP-00001" in value
    assert WorkOrderPriority.MEDIUM.value in value
    assert WorkOrderStatus.OPEN.value in value


def test_status_default_matches_domain_default() -> None:
    """Verify ORM status defaults to open."""
    column = WorkOrderORM.__table__.columns["status"]

    assert column.default is not None
    assert column.default.arg == WorkOrderStatus.OPEN.value
    assert column.server_default is not None


def test_ground_truth_default_is_false() -> None:
    """Verify synthetic ground-truth defaults to false."""
    column = WorkOrderORM.__table__.columns["is_synthetic_ground_truth"]

    assert column.default is not None
    assert column.default.arg is False
    assert column.server_default is not None


def test_timestamp_columns_are_timezone_aware() -> None:
    """Verify lifecycle and audit timestamps preserve timezone data."""
    for column_name in (
        "created_at",
        "scheduled_at",
        "started_at",
        "completed_at",
        "cancelled_at",
        "inserted_at",
        "updated_at",
    ):
        assert WorkOrderORM.__table__.columns[column_name].type.timezone is True


def test_plant_relationship_configuration() -> None:
    """Verify work orders link to the Plant ORM model."""
    relationship_property = WorkOrderORM.__mapper__.relationships["plant"]

    assert relationship_property.mapper.class_.__name__ == "PlantORM"
    assert relationship_property.uselist is False


def test_equipment_relationship_configuration() -> None:
    """Verify work orders link to the Equipment ORM model."""
    relationship_property = WorkOrderORM.__mapper__.relationships["equipment"]

    assert relationship_property.mapper.class_.__name__ == "EquipmentORM"
    assert relationship_property.uselist is False


def test_linked_incident_relationship_configuration() -> None:
    """Verify work orders optionally link to IncidentORM."""
    relationship_property = WorkOrderORM.__mapper__.relationships["linked_incident"]

    assert relationship_property.mapper.class_.__name__ == "IncidentORM"
    assert relationship_property.uselist is False


def test_text_column_lengths_match_domain_contract() -> None:
    """Verify text columns match domain maximum lengths."""
    assert WorkOrderORM.__table__.columns["work_order_name"].type.length == 150
    assert WorkOrderORM.__table__.columns["assigned_team"].type.length == 100
    assert WorkOrderORM.__table__.columns["description"].type.length == 1_000
    assert WorkOrderORM.__table__.columns["completion_notes"].type.length == 1_000


def test_numeric_columns_use_float_type() -> None:
    """Verify labor and cost values use floating-point storage."""
    for column_name in (
        "estimated_labor_hours",
        "actual_labor_hours",
        "estimated_cost",
        "actual_cost",
    ):
        assert WorkOrderORM.__table__.columns[column_name].type.python_type is float
