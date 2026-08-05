"""
Unit tests for the EOIP maintenance work-order domain model.

These tests verify valid work-order construction, normalization, lifecycle
states, derived metrics, serialization, validation rules, and immutability.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest

from eoip.synthetic.models.work_order import (
    WorkOrder,
    WorkOrderPriority,
    WorkOrderStatus,
    WorkOrderType,
)


def _created_at() -> datetime:
    """Return the standard creation timestamp used by work-order tests."""
    return datetime(2026, 1, 15, 8, 0, tzinfo=UTC)


def _make_work_order(**overrides: Any) -> WorkOrder:
    """Create a valid open work order with optional field overrides."""
    work_order_data: dict[str, Any] = {
        "work_order_id": "WO-0000001",
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "work_order_name": "Replace inverter cooling fan",
        "work_order_type": WorkOrderType.CORRECTIVE,
        "priority": WorkOrderPriority.HIGH,
        "created_at": _created_at(),
        "status": WorkOrderStatus.OPEN,
        "linked_incident_id": None,
        "assigned_team": None,
        "scheduled_at": None,
        "started_at": None,
        "completed_at": None,
        "cancelled_at": None,
        "estimated_labor_hours": None,
        "actual_labor_hours": None,
        "estimated_cost": None,
        "actual_cost": None,
        "description": "Replace the failed inverter cooling fan.",
        "completion_notes": None,
        "is_synthetic_ground_truth": False,
    }
    work_order_data.update(overrides)
    return WorkOrder(**work_order_data)


def test_work_order_preserves_valid_open_fields() -> None:
    """A valid open work order should retain all supplied values."""
    work_order = _make_work_order()

    assert work_order.work_order_id == "WO-0000001"
    assert work_order.plant_id == "PLANT-001"
    assert work_order.equipment_id == "EQP-00001"
    assert work_order.work_order_name == "Replace inverter cooling fan"
    assert work_order.work_order_type is WorkOrderType.CORRECTIVE
    assert work_order.priority is WorkOrderPriority.HIGH
    assert work_order.created_at == _created_at()
    assert work_order.status is WorkOrderStatus.OPEN
    assert work_order.linked_incident_id is None
    assert work_order.assigned_team is None
    assert work_order.scheduled_at is None
    assert work_order.started_at is None
    assert work_order.completed_at is None
    assert work_order.cancelled_at is None
    assert work_order.estimated_labor_hours is None
    assert work_order.actual_labor_hours is None
    assert work_order.estimated_cost is None
    assert work_order.actual_cost is None
    assert work_order.description == "Replace the failed inverter cooling fan."
    assert work_order.completion_notes is None
    assert work_order.is_synthetic_ground_truth is False


def test_work_order_normalizes_identifiers_and_text() -> None:
    """Identifiers and supported text fields should be normalized."""
    work_order = _make_work_order(
        work_order_id=" wo-0000001 ",
        plant_id=" plant-001 ",
        equipment_id=" eqp-00001 ",
        work_order_name=" Replace inverter cooling fan ",
        linked_incident_id=" inc-0000001 ",
        assigned_team=" Field Maintenance Team ",
        description=" Replace the failed cooling fan. ",
        completion_notes=" Fan replaced and inverter restarted. ",
    )

    assert work_order.work_order_id == "WO-0000001"
    assert work_order.plant_id == "PLANT-001"
    assert work_order.equipment_id == "EQP-00001"
    assert work_order.work_order_name == "Replace inverter cooling fan"
    assert work_order.linked_incident_id == "INC-0000001"
    assert work_order.assigned_team == "Field Maintenance Team"
    assert work_order.description == "Replace the failed cooling fan."
    assert work_order.completion_notes == ("Fan replaced and inverter restarted.")


def test_work_order_uses_expected_defaults() -> None:
    """Optional fields should use their documented default values."""
    work_order = WorkOrder(
        work_order_id="WO-0000001",
        plant_id="PLANT-001",
        equipment_id="EQP-00001",
        work_order_name="Inspect inverter",
        work_order_type=WorkOrderType.INSPECTION,
        priority=WorkOrderPriority.MEDIUM,
        created_at=_created_at(),
    )

    assert work_order.status is WorkOrderStatus.OPEN
    assert work_order.linked_incident_id is None
    assert work_order.assigned_team is None
    assert work_order.scheduled_at is None
    assert work_order.started_at is None
    assert work_order.completed_at is None
    assert work_order.cancelled_at is None
    assert work_order.estimated_labor_hours is None
    assert work_order.actual_labor_hours is None
    assert work_order.estimated_cost is None
    assert work_order.actual_cost is None
    assert work_order.description is None
    assert work_order.completion_notes is None
    assert work_order.is_synthetic_ground_truth is False


def test_assigned_work_order_is_valid() -> None:
    """Assigned work orders should require and retain a team."""
    work_order = _make_work_order(
        status=WorkOrderStatus.ASSIGNED,
        assigned_team="Field Maintenance Team",
        scheduled_at=_created_at() + timedelta(hours=2),
    )

    assert work_order.status is WorkOrderStatus.ASSIGNED
    assert work_order.assigned_team == "Field Maintenance Team"
    assert work_order.is_open is True


def test_in_progress_work_order_is_valid() -> None:
    """In-progress work orders should require a team and start time."""
    started_at = _created_at() + timedelta(hours=2)

    work_order = _make_work_order(
        status=WorkOrderStatus.IN_PROGRESS,
        assigned_team="Field Maintenance Team",
        scheduled_at=started_at,
        started_at=started_at,
    )

    assert work_order.status is WorkOrderStatus.IN_PROGRESS
    assert work_order.started_at == started_at
    assert work_order.is_open is True


def test_completed_work_order_is_valid() -> None:
    """Completed work orders should retain start and completion timestamps."""
    started_at = _created_at() + timedelta(hours=1)
    completed_at = started_at + timedelta(hours=3)

    work_order = _make_work_order(
        status=WorkOrderStatus.COMPLETED,
        assigned_team="Field Maintenance Team",
        scheduled_at=started_at,
        started_at=started_at,
        completed_at=completed_at,
        estimated_labor_hours=2.5,
        actual_labor_hours=3.0,
        estimated_cost=1000.0,
        actual_cost=1200.0,
        completion_notes="Cooling fan replaced successfully.",
    )

    assert work_order.status is WorkOrderStatus.COMPLETED
    assert work_order.started_at == started_at
    assert work_order.completed_at == completed_at
    assert work_order.is_open is False


def test_cancelled_work_order_is_valid() -> None:
    """Cancelled work orders should retain their cancellation timestamp."""
    cancelled_at = _created_at() + timedelta(hours=1)

    work_order = _make_work_order(
        status=WorkOrderStatus.CANCELLED,
        cancelled_at=cancelled_at,
    )

    assert work_order.status is WorkOrderStatus.CANCELLED
    assert work_order.cancelled_at == cancelled_at
    assert work_order.is_open is False


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (WorkOrderStatus.OPEN, True),
        (WorkOrderStatus.ASSIGNED, True),
        (WorkOrderStatus.IN_PROGRESS, True),
        (WorkOrderStatus.COMPLETED, False),
        (WorkOrderStatus.CANCELLED, False),
    ],
)
def test_is_open_reflects_status(
    status: WorkOrderStatus,
    expected: bool,
) -> None:
    """Only unfinished work-order states should be considered open."""
    overrides: dict[str, Any] = {"status": status}

    if status is WorkOrderStatus.ASSIGNED:
        overrides["assigned_team"] = "Field Maintenance Team"

    if status is WorkOrderStatus.IN_PROGRESS:
        overrides.update(
            assigned_team="Field Maintenance Team",
            started_at=_created_at() + timedelta(hours=1),
        )

    if status is WorkOrderStatus.COMPLETED:
        started_at = _created_at() + timedelta(hours=1)
        overrides.update(
            started_at=started_at,
            completed_at=started_at + timedelta(hours=2),
        )

    if status is WorkOrderStatus.CANCELLED:
        overrides["cancelled_at"] = _created_at() + timedelta(hours=1)

    work_order = _make_work_order(**overrides)

    assert work_order.is_open is expected


@pytest.mark.parametrize(
    ("estimated_cost", "actual_cost", "expected"),
    [
        (1000.0, 1200.0, True),
        (1000.0, 1000.0, False),
        (1000.0, 800.0, False),
        (None, 1200.0, None),
        (1000.0, None, None),
        (None, None, None),
    ],
)
def test_is_over_budget(
    estimated_cost: float | None,
    actual_cost: float | None,
    expected: bool | None,
) -> None:
    """Budget status should compare actual and estimated cost."""
    work_order = _make_work_order(
        estimated_cost=estimated_cost,
        actual_cost=actual_cost,
    )

    assert work_order.is_over_budget is expected


@pytest.mark.parametrize(
    ("estimated_hours", "actual_hours", "expected"),
    [
        (2.5, 3.0, 0.5),
        (3.0, 2.5, -0.5),
        (3.0, 3.0, 0.0),
        (None, 3.0, None),
        (3.0, None, None),
        (None, None, None),
    ],
)
def test_labor_variance_hours(
    estimated_hours: float | None,
    actual_hours: float | None,
    expected: float | None,
) -> None:
    """Labor variance should return actual minus estimated hours."""
    work_order = _make_work_order(
        estimated_labor_hours=estimated_hours,
        actual_labor_hours=actual_hours,
    )

    assert work_order.labor_variance_hours == expected


@pytest.mark.parametrize(
    ("estimated_cost", "actual_cost", "expected"),
    [
        (1000.0, 1200.0, 200.0),
        (1000.0, 800.0, -200.0),
        (1000.0, 1000.0, 0.0),
        (None, 1200.0, None),
        (1000.0, None, None),
        (None, None, None),
    ],
)
def test_cost_variance(
    estimated_cost: float | None,
    actual_cost: float | None,
    expected: float | None,
) -> None:
    """Cost variance should return actual minus estimated cost."""
    work_order = _make_work_order(
        estimated_cost=estimated_cost,
        actual_cost=actual_cost,
    )

    assert work_order.cost_variance == expected


def test_completion_seconds_returns_elapsed_time() -> None:
    """Completion time should be measured from start to completion."""
    started_at = _created_at() + timedelta(hours=1)
    completed_at = started_at + timedelta(hours=3)

    work_order = _make_work_order(
        status=WorkOrderStatus.COMPLETED,
        started_at=started_at,
        completed_at=completed_at,
    )

    assert work_order.completion_seconds == 10800.0


def test_completion_seconds_is_none_without_start_or_completion() -> None:
    """Completion duration should be absent without both timestamps."""
    work_order = _make_work_order()

    assert work_order.completion_seconds is None


def test_work_order_is_immutable() -> None:
    """Work-order instances should reject field modification."""
    work_order = _make_work_order()

    with pytest.raises(FrozenInstanceError):
        work_order.work_order_name = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "work_order_id",
    [
        "",
        "   ",
        "WO-1",
        "WO-000001",
        "WO-00000001",
        "WORKORDER-0000001",
        "WO-ABCDEFG",
        "WO_0000001",
    ],
)
def test_work_order_rejects_invalid_work_order_id(
    work_order_id: str,
) -> None:
    """Work-order IDs must follow the WO-0000001 format."""
    with pytest.raises(ValueError, match="Invalid work_order_id"):
        _make_work_order(work_order_id=work_order_id)


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
def test_work_order_rejects_invalid_plant_id(
    plant_id: str,
) -> None:
    """Plant IDs must follow the PLANT-001 format."""
    with pytest.raises(ValueError, match="Invalid plant_id"):
        _make_work_order(plant_id=plant_id)


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
    ],
)
def test_work_order_rejects_invalid_equipment_id(
    equipment_id: str,
) -> None:
    """Equipment IDs must follow the EQP-00001 format."""
    with pytest.raises(ValueError, match="Invalid equipment_id"):
        _make_work_order(equipment_id=equipment_id)


@pytest.mark.parametrize(
    "linked_incident_id",
    [
        "",
        " ",
        "INC-1",
        "INC-000001",
        "INC-00000001",
        "INCIDENT-0000001",
        "INC-ABCDEFG",
        "INC_0000001",
    ],
)
def test_work_order_rejects_invalid_linked_incident_id(
    linked_incident_id: str,
) -> None:
    """Linked incident IDs must follow the INC-0000001 format."""
    with pytest.raises(ValueError, match="Invalid linked_incident_id"):
        _make_work_order(linked_incident_id=linked_incident_id)


def test_work_order_accepts_valid_linked_incident_id() -> None:
    """A valid linked incident ID should be normalized."""
    work_order = _make_work_order(
        linked_incident_id=" inc-0000001 ",
    )

    assert work_order.linked_incident_id == "INC-0000001"


@pytest.mark.parametrize(
    "work_order_name",
    [
        "",
        "   ",
        "\t",
        "\n",
    ],
)
def test_work_order_rejects_empty_work_order_name(
    work_order_name: str,
) -> None:
    """Work-order names must contain visible text."""
    with pytest.raises(
        ValueError,
        match="work_order_name cannot be empty",
    ):
        _make_work_order(work_order_name=work_order_name)


def test_work_order_rejects_work_order_name_longer_than_limit() -> None:
    """Work-order names must not exceed 150 characters."""
    with pytest.raises(
        ValueError,
        match="Use no more than 150",
    ):
        _make_work_order(work_order_name="A" * 151)


def test_work_order_accepts_work_order_name_at_limit() -> None:
    """Exactly 150 characters should be accepted."""
    work_order = _make_work_order(
        work_order_name="A" * 150,
    )

    assert len(work_order.work_order_name) == 150


@pytest.mark.parametrize(
    "assigned_team",
    [
        "",
        "   ",
        "\t",
        "\n",
    ],
)
def test_work_order_rejects_empty_assigned_team(
    assigned_team: str,
) -> None:
    """Blank assigned teams should use None."""
    with pytest.raises(
        ValueError,
        match="assigned_team cannot be empty",
    ):
        _make_work_order(assigned_team=assigned_team)


def test_work_order_accepts_none_assigned_team() -> None:
    """None should represent an unassigned work order."""
    work_order = _make_work_order(
        assigned_team=None,
    )

    assert work_order.assigned_team is None


def test_work_order_rejects_assigned_team_longer_than_limit() -> None:
    """Assigned team names must not exceed 100 characters."""
    with pytest.raises(
        ValueError,
        match="Use no more than 100",
    ):
        _make_work_order(
            assigned_team="A" * 101,
        )


@pytest.mark.parametrize(
    "description",
    [
        "",
        "   ",
        "\t",
        "\n",
    ],
)
def test_work_order_rejects_empty_description(
    description: str,
) -> None:
    """Blank descriptions should use None."""
    with pytest.raises(
        ValueError,
        match="description cannot be empty",
    ):
        _make_work_order(description=description)


def test_work_order_accepts_none_description() -> None:
    """None should be accepted for description."""
    work_order = _make_work_order(description=None)

    assert work_order.description is None


def test_work_order_rejects_description_longer_than_limit() -> None:
    """Descriptions must not exceed 1000 characters."""
    with pytest.raises(
        ValueError,
        match="Use no more than 1000",
    ):
        _make_work_order(description="A" * 1001)


@pytest.mark.parametrize(
    "completion_notes",
    [
        "",
        "   ",
        "\t",
        "\n",
    ],
)
def test_work_order_rejects_empty_completion_notes(
    completion_notes: str,
) -> None:
    """Blank completion notes should use None."""
    with pytest.raises(
        ValueError,
        match="completion_notes cannot be empty",
    ):
        _make_work_order(
            completion_notes=completion_notes,
        )


def test_work_order_accepts_none_completion_notes() -> None:
    """None should be accepted for completion notes."""
    work_order = _make_work_order(
        completion_notes=None,
    )

    assert work_order.completion_notes is None


def test_work_order_rejects_completion_notes_longer_than_limit() -> None:
    """Completion notes must not exceed 1000 characters."""
    with pytest.raises(
        ValueError,
        match="Use no more than 1000",
    ):
        _make_work_order(
            completion_notes="A" * 1001,
        )


@pytest.mark.parametrize(
    "work_order_type",
    list(WorkOrderType),
)
def test_work_order_accepts_every_type(
    work_order_type: WorkOrderType,
) -> None:
    """Every WorkOrderType should be accepted."""
    work_order = _make_work_order(
        work_order_type=work_order_type,
    )

    assert work_order.work_order_type is work_order_type


@pytest.mark.parametrize(
    "work_order_type",
    [
        "corrective",
        "inspection",
        1,
        None,
    ],
)
def test_work_order_rejects_invalid_type(
    work_order_type: object,
) -> None:
    """Only WorkOrderType enum values are valid."""
    with pytest.raises(
        TypeError,
        match="Use a WorkOrderType value",
    ):
        _make_work_order(
            work_order_type=work_order_type,
        )


@pytest.mark.parametrize(
    "priority",
    list(WorkOrderPriority),
)
def test_work_order_accepts_every_priority(
    priority: WorkOrderPriority,
) -> None:
    """Every WorkOrderPriority should be accepted."""
    work_order = _make_work_order(priority=priority)

    assert work_order.priority is priority


@pytest.mark.parametrize(
    "priority",
    [
        "critical",
        "high",
        1,
        None,
    ],
)
def test_work_order_rejects_invalid_priority(
    priority: object,
) -> None:
    """Only WorkOrderPriority enum values are valid."""
    with pytest.raises(
        TypeError,
        match="Use a WorkOrderPriority value",
    ):
        _make_work_order(priority=priority)


@pytest.mark.parametrize(
    "status",
    [
        "open",
        "assigned",
        "completed",
        1,
        None,
    ],
)
def test_work_order_rejects_invalid_status(
    status: object,
) -> None:
    """Only WorkOrderStatus enum values are valid."""
    with pytest.raises(
        TypeError,
        match="Use a WorkOrderStatus value",
    ):
        _make_work_order(status=status)


@pytest.mark.parametrize(
    "is_synthetic_ground_truth",
    [
        True,
        False,
    ],
)
def test_work_order_accepts_boolean_ground_truth_flag(
    is_synthetic_ground_truth: bool,
) -> None:
    """Boolean values should be accepted."""
    work_order = _make_work_order(
        is_synthetic_ground_truth=is_synthetic_ground_truth,
    )

    assert work_order.is_synthetic_ground_truth is is_synthetic_ground_truth


@pytest.mark.parametrize(
    "is_synthetic_ground_truth",
    [
        1,
        0,
        "true",
        None,
    ],
)
def test_work_order_rejects_non_boolean_ground_truth_flag(
    is_synthetic_ground_truth: object,
) -> None:
    """Only actual boolean values are valid for the ground-truth flag."""
    with pytest.raises(
        TypeError,
        match="Invalid is_synthetic_ground_truth value",
    ):
        _make_work_order(
            is_synthetic_ground_truth=is_synthetic_ground_truth,
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("created_at", "2026-01-15T08:00:00+00:00"),
        ("created_at", 20260115),
        ("created_at", None),
        ("scheduled_at", "2026-01-15T09:00:00+00:00"),
        ("scheduled_at", 20260115),
        ("started_at", "2026-01-15T10:00:00+00:00"),
        ("started_at", 20260115),
        ("completed_at", "2026-01-15T12:00:00+00:00"),
        ("completed_at", 20260115),
        ("cancelled_at", "2026-01-15T09:00:00+00:00"),
        ("cancelled_at", 20260115),
    ],
)
def test_work_order_rejects_invalid_timestamp_types(
    field_name: str,
    value: object,
) -> None:
    """Work-order timestamps must be datetime values when supplied."""
    with pytest.raises(TypeError, match=f"Invalid {field_name}"):
        _make_work_order(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "created_at",
        "scheduled_at",
        "started_at",
        "completed_at",
        "cancelled_at",
    ],
)
def test_work_order_rejects_timezone_naive_timestamps(
    field_name: str,
) -> None:
    """Every work-order timestamp must be timezone-aware."""
    naive_timestamp = datetime(2026, 1, 15, 8, 0)

    with pytest.raises(ValueError, match="timezone-naive"):
        _make_work_order(**{field_name: naive_timestamp})


def test_work_order_accepts_non_utc_timezone() -> None:
    """Timezone-aware timestamps outside UTC should be accepted."""
    local_timezone = timezone(timedelta(hours=5))
    created_at = datetime(
        2026,
        1,
        15,
        8,
        0,
        tzinfo=local_timezone,
    )

    work_order = _make_work_order(created_at=created_at)

    assert work_order.created_at == created_at
    assert work_order.created_at.utcoffset() == timedelta(hours=5)


@pytest.mark.parametrize(
    "field_name",
    [
        "scheduled_at",
        "started_at",
        "completed_at",
        "cancelled_at",
    ],
)
def test_work_order_rejects_timestamp_before_creation(
    field_name: str,
) -> None:
    """Optional lifecycle timestamps must not occur before creation."""
    earlier_timestamp = _created_at() - timedelta(seconds=1)

    with pytest.raises(ValueError, match="occurs before created_at"):
        _make_work_order(**{field_name: earlier_timestamp})


def test_work_order_rejects_start_before_schedule() -> None:
    """Work must not start before its scheduled timestamp."""
    scheduled_at = _created_at() + timedelta(hours=2)
    started_at = _created_at() + timedelta(hours=1)

    with pytest.raises(ValueError, match="occurs before scheduled_at"):
        _make_work_order(
            status=WorkOrderStatus.IN_PROGRESS,
            assigned_team="Field Maintenance Team",
            scheduled_at=scheduled_at,
            started_at=started_at,
        )


def test_work_order_rejects_completion_before_start() -> None:
    """Work completion must not occur before work starts."""
    started_at = _created_at() + timedelta(hours=2)
    completed_at = _created_at() + timedelta(hours=1)

    with pytest.raises(ValueError, match="occurs before started_at"):
        _make_work_order(
            status=WorkOrderStatus.COMPLETED,
            assigned_team="Field Maintenance Team",
            started_at=started_at,
            completed_at=completed_at,
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "estimated_labor_hours",
        "actual_labor_hours",
        "estimated_cost",
        "actual_cost",
    ],
)
@pytest.mark.parametrize(
    "invalid_value",
    [
        True,
        False,
        "10",
        [],
        {},
        object(),
    ],
)
def test_work_order_rejects_non_numeric_values(
    field_name: str,
    invalid_value: object,
) -> None:
    """Labor and cost values must be numeric and must reject booleans."""
    with pytest.raises(TypeError, match=f"Invalid {field_name}"):
        _make_work_order(**{field_name: invalid_value})


@pytest.mark.parametrize(
    "field_name",
    [
        "estimated_labor_hours",
        "actual_labor_hours",
        "estimated_cost",
        "actual_cost",
    ],
)
@pytest.mark.parametrize(
    "invalid_value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_work_order_rejects_non_finite_numeric_values(
    field_name: str,
    invalid_value: float,
) -> None:
    """Labor and cost values must be finite."""
    with pytest.raises(ValueError, match="must be finite"):
        _make_work_order(**{field_name: invalid_value})


@pytest.mark.parametrize(
    "field_name",
    [
        "estimated_labor_hours",
        "actual_labor_hours",
        "estimated_cost",
        "actual_cost",
    ],
)
@pytest.mark.parametrize(
    "invalid_value",
    [
        -0.001,
        -1.0,
        -100.0,
    ],
)
def test_work_order_rejects_negative_numeric_values(
    field_name: str,
    invalid_value: float,
) -> None:
    """Labor and cost values must not be negative."""
    with pytest.raises(
        ValueError,
        match="greater than or equal to zero",
    ):
        _make_work_order(**{field_name: invalid_value})


@pytest.mark.parametrize(
    "field_name",
    [
        "estimated_labor_hours",
        "actual_labor_hours",
        "estimated_cost",
        "actual_cost",
    ],
)
@pytest.mark.parametrize(
    "valid_value",
    [
        0,
        0.0,
        1,
        1.5,
        1000.0,
    ],
)
def test_work_order_accepts_non_negative_numeric_values(
    field_name: str,
    valid_value: float,
) -> None:
    """Zero and positive labor or cost values should be accepted."""
    work_order = _make_work_order(**{field_name: valid_value})

    assert getattr(work_order, field_name) == valid_value


def test_open_work_order_rejects_started_at() -> None:
    """OPEN work orders must not contain a start timestamp."""
    with pytest.raises(ValueError, match="status 'open'.*started_at"):
        _make_work_order(
            started_at=_created_at() + timedelta(hours=1),
        )


def test_open_work_order_rejects_completed_at() -> None:
    """OPEN work orders must not contain a completion timestamp."""
    with pytest.raises(ValueError, match="status 'open'.*completed_at"):
        _make_work_order(
            completed_at=_created_at() + timedelta(hours=2),
        )


def test_open_work_order_rejects_cancelled_at() -> None:
    """OPEN work orders must not contain a cancellation timestamp."""
    with pytest.raises(ValueError, match="status 'open'.*cancelled_at"):
        _make_work_order(
            cancelled_at=_created_at() + timedelta(hours=1),
        )


def test_assigned_work_order_requires_assigned_team() -> None:
    """ASSIGNED work orders require an assigned team."""
    with pytest.raises(ValueError, match="assigned_team is missing"):
        _make_work_order(
            status=WorkOrderStatus.ASSIGNED,
        )


def test_assigned_work_order_rejects_started_at() -> None:
    """ASSIGNED work orders must not already contain started_at."""
    with pytest.raises(ValueError, match="status 'assigned'.*started_at"):
        _make_work_order(
            status=WorkOrderStatus.ASSIGNED,
            assigned_team="Field Maintenance Team",
            started_at=_created_at() + timedelta(hours=1),
        )


def test_in_progress_work_order_requires_assigned_team() -> None:
    """IN_PROGRESS work orders require an assigned team."""
    with pytest.raises(ValueError, match="assigned_team is missing"):
        _make_work_order(
            status=WorkOrderStatus.IN_PROGRESS,
            started_at=_created_at() + timedelta(hours=1),
        )


def test_in_progress_work_order_requires_started_at() -> None:
    """IN_PROGRESS work orders require a start timestamp."""
    with pytest.raises(ValueError, match="started_at is missing"):
        _make_work_order(
            status=WorkOrderStatus.IN_PROGRESS,
            assigned_team="Field Maintenance Team",
        )


def test_in_progress_work_order_rejects_completed_at() -> None:
    """IN_PROGRESS work orders must not contain completed_at."""
    started_at = _created_at() + timedelta(hours=1)

    with pytest.raises(ValueError, match="status 'in_progress'.*completed_at"):
        _make_work_order(
            status=WorkOrderStatus.IN_PROGRESS,
            assigned_team="Field Maintenance Team",
            started_at=started_at,
            completed_at=started_at + timedelta(hours=2),
        )


def test_in_progress_work_order_rejects_cancelled_at() -> None:
    """IN_PROGRESS work orders must not contain cancelled_at."""
    started_at = _created_at() + timedelta(hours=1)

    with pytest.raises(ValueError, match="status 'in_progress'.*cancelled_at"):
        _make_work_order(
            status=WorkOrderStatus.IN_PROGRESS,
            assigned_team="Field Maintenance Team",
            started_at=started_at,
            cancelled_at=started_at + timedelta(hours=2),
        )


def test_completed_work_order_requires_started_at() -> None:
    """COMPLETED work orders require started_at."""
    with pytest.raises(ValueError, match="started_at is missing"):
        _make_work_order(
            status=WorkOrderStatus.COMPLETED,
            completed_at=_created_at() + timedelta(hours=2),
        )


def test_completed_work_order_requires_completed_at() -> None:
    """COMPLETED work orders require completed_at."""
    with pytest.raises(ValueError, match="completed_at is missing"):
        _make_work_order(
            status=WorkOrderStatus.COMPLETED,
            started_at=_created_at() + timedelta(hours=1),
        )


def test_completed_work_order_rejects_cancelled_at() -> None:
    """COMPLETED work orders must not also contain cancelled_at."""
    started_at = _created_at() + timedelta(hours=1)
    completed_at = started_at + timedelta(hours=2)

    with pytest.raises(ValueError, match="status 'completed'.*cancelled_at"):
        _make_work_order(
            status=WorkOrderStatus.COMPLETED,
            started_at=started_at,
            completed_at=completed_at,
            cancelled_at=completed_at,
        )


def test_cancelled_work_order_requires_cancelled_at() -> None:
    """CANCELLED work orders require cancelled_at."""
    with pytest.raises(ValueError, match="cancelled_at is missing"):
        _make_work_order(
            status=WorkOrderStatus.CANCELLED,
        )


def test_cancelled_work_order_rejects_completed_at() -> None:
    """CANCELLED work orders must not also contain completed_at."""
    completed_at = _created_at() + timedelta(hours=2)

    with pytest.raises(ValueError, match="status 'cancelled'.*completed_at"):
        _make_work_order(
            status=WorkOrderStatus.CANCELLED,
            completed_at=completed_at,
            cancelled_at=completed_at,
        )


def test_to_record_returns_complete_open_work_order_record() -> None:
    """Open work-order serialization should return a complete record."""
    work_order = _make_work_order(
        linked_incident_id="INC-0000001",
        is_synthetic_ground_truth=True,
    )

    assert work_order.to_record() == {
        "work_order_id": "WO-0000001",
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "work_order_name": "Replace inverter cooling fan",
        "work_order_type": "corrective",
        "priority": "high",
        "created_at": "2026-01-15T08:00:00+00:00",
        "status": "open",
        "linked_incident_id": "INC-0000001",
        "assigned_team": None,
        "scheduled_at": None,
        "started_at": None,
        "completed_at": None,
        "cancelled_at": None,
        "estimated_labor_hours": None,
        "actual_labor_hours": None,
        "estimated_cost": None,
        "actual_cost": None,
        "description": "Replace the failed inverter cooling fan.",
        "completion_notes": None,
        "is_synthetic_ground_truth": True,
        "is_open": True,
        "is_over_budget": None,
        "labor_variance_hours": None,
        "cost_variance": None,
        "completion_seconds": None,
    }


def test_to_record_serializes_assigned_work_order() -> None:
    """Assigned work-order serialization should include assignment data."""
    scheduled_at = _created_at() + timedelta(hours=2)

    work_order = _make_work_order(
        status=WorkOrderStatus.ASSIGNED,
        assigned_team="Field Maintenance Team",
        scheduled_at=scheduled_at,
    )

    record = work_order.to_record()

    assert record["status"] == "assigned"
    assert record["assigned_team"] == "Field Maintenance Team"
    assert record["scheduled_at"] == "2026-01-15T10:00:00+00:00"
    assert record["started_at"] is None
    assert record["is_open"] is True


def test_to_record_serializes_in_progress_work_order() -> None:
    """In-progress serialization should include start information."""
    started_at = _created_at() + timedelta(hours=1)

    work_order = _make_work_order(
        status=WorkOrderStatus.IN_PROGRESS,
        assigned_team="Field Maintenance Team",
        scheduled_at=started_at,
        started_at=started_at,
    )

    record = work_order.to_record()

    assert record["status"] == "in_progress"
    assert record["assigned_team"] == "Field Maintenance Team"
    assert record["scheduled_at"] == "2026-01-15T09:00:00+00:00"
    assert record["started_at"] == "2026-01-15T09:00:00+00:00"
    assert record["completed_at"] is None
    assert record["is_open"] is True


def test_to_record_serializes_completed_work_order() -> None:
    """Completed serialization should include metrics and lifecycle data."""
    started_at = _created_at() + timedelta(hours=1)
    completed_at = started_at + timedelta(hours=3)

    work_order = _make_work_order(
        status=WorkOrderStatus.COMPLETED,
        linked_incident_id="INC-0000001",
        assigned_team="Field Maintenance Team",
        scheduled_at=started_at,
        started_at=started_at,
        completed_at=completed_at,
        estimated_labor_hours=2.5,
        actual_labor_hours=3.0,
        estimated_cost=1000.0,
        actual_cost=1200.0,
        completion_notes="Cooling fan replaced successfully.",
    )

    record = work_order.to_record()

    assert record["status"] == "completed"
    assert record["started_at"] == "2026-01-15T09:00:00+00:00"
    assert record["completed_at"] == "2026-01-15T12:00:00+00:00"
    assert record["cancelled_at"] is None
    assert record["is_open"] is False
    assert record["is_over_budget"] is True
    assert record["labor_variance_hours"] == 0.5
    assert record["cost_variance"] == 200.0
    assert record["completion_seconds"] == 10800.0


def test_to_record_serializes_cancelled_work_order() -> None:
    """Cancelled serialization should include cancellation information."""
    cancelled_at = _created_at() + timedelta(hours=1)

    work_order = _make_work_order(
        status=WorkOrderStatus.CANCELLED,
        cancelled_at=cancelled_at,
    )

    record = work_order.to_record()

    assert record["status"] == "cancelled"
    assert record["cancelled_at"] == "2026-01-15T09:00:00+00:00"
    assert record["completed_at"] is None
    assert record["is_open"] is False
    assert record["completion_seconds"] is None


def test_to_record_preserves_none_optional_fields() -> None:
    """Serialization should preserve None for unset optional fields."""
    work_order = _make_work_order(
        linked_incident_id=None,
        assigned_team=None,
        description=None,
        completion_notes=None,
    )

    record = work_order.to_record()

    assert record["linked_incident_id"] is None
    assert record["assigned_team"] is None
    assert record["scheduled_at"] is None
    assert record["started_at"] is None
    assert record["completed_at"] is None
    assert record["cancelled_at"] is None
    assert record["description"] is None
    assert record["completion_notes"] is None


def test_work_order_name_normalization_occurs_before_length_validation() -> None:
    """Whitespace should be removed before enforcing name length."""
    work_order_name = f" {'A' * 150} "

    work_order = _make_work_order(work_order_name=work_order_name)

    assert work_order.work_order_name == "A" * 150
    assert len(work_order.work_order_name) == 150


def test_assigned_team_normalization_occurs_before_length_validation() -> None:
    """Whitespace should be removed before enforcing team length."""
    assigned_team = f" {'A' * 100} "

    work_order = _make_work_order(assigned_team=assigned_team)

    assert work_order.assigned_team == "A" * 100
    assert len(work_order.assigned_team or "") == 100


def test_description_normalization_occurs_before_length_validation() -> None:
    """Whitespace should be removed before enforcing description length."""
    description = f" {'A' * 1000} "

    work_order = _make_work_order(description=description)

    assert work_order.description == "A" * 1000
    assert len(work_order.description or "") == 1000


def test_completion_notes_normalization_occurs_before_length_validation() -> None:
    """Whitespace should be removed before enforcing note length."""
    completion_notes = f" {'A' * 1000} "

    work_order = _make_work_order(completion_notes=completion_notes)

    assert work_order.completion_notes == "A" * 1000
    assert len(work_order.completion_notes or "") == 1000


def test_started_at_equal_to_scheduled_at_is_valid() -> None:
    """Work may start at the exact scheduled timestamp."""
    timestamp = _created_at() + timedelta(hours=1)

    work_order = _make_work_order(
        status=WorkOrderStatus.IN_PROGRESS,
        assigned_team="Field Maintenance Team",
        scheduled_at=timestamp,
        started_at=timestamp,
    )

    assert work_order.scheduled_at == timestamp
    assert work_order.started_at == timestamp


def test_completed_at_equal_to_started_at_is_valid() -> None:
    """Work may complete at the exact start timestamp."""
    timestamp = _created_at() + timedelta(hours=1)

    work_order = _make_work_order(
        status=WorkOrderStatus.COMPLETED,
        started_at=timestamp,
        completed_at=timestamp,
    )

    assert work_order.completion_seconds == 0.0


def test_optional_timestamp_equal_to_created_at_is_valid() -> None:
    """Optional lifecycle timestamps may equal the creation timestamp."""
    work_order = _make_work_order(
        status=WorkOrderStatus.CANCELLED,
        scheduled_at=_created_at(),
        cancelled_at=_created_at(),
    )

    assert work_order.scheduled_at == _created_at()
    assert work_order.cancelled_at == _created_at()


def test_labor_variance_rounding() -> None:
    """Labor variance should be rounded to three decimal places."""
    work_order = _make_work_order(
        estimated_labor_hours=1.1111,
        actual_labor_hours=2.2222,
    )

    assert work_order.labor_variance_hours == 1.111


def test_cost_variance_rounding() -> None:
    """Cost variance should be rounded to two decimal places."""
    work_order = _make_work_order(
        estimated_cost=100.111,
        actual_cost=200.999,
    )

    assert work_order.cost_variance == 100.89


def test_equal_estimated_and_actual_cost_is_not_over_budget() -> None:
    """Equal actual and estimated cost should not be over budget."""
    work_order = _make_work_order(
        estimated_cost=1000.0,
        actual_cost=1000.0,
    )

    assert work_order.is_over_budget is False


def test_actual_cost_below_estimate_is_not_over_budget() -> None:
    """Actual cost below estimate should not be over budget."""
    work_order = _make_work_order(
        estimated_cost=1000.0,
        actual_cost=900.0,
    )

    assert work_order.is_over_budget is False


def test_work_order_serialization_uses_enum_values() -> None:
    """Serialization must expose enum values rather than enum objects."""
    work_order = _make_work_order(
        work_order_type=WorkOrderType.PREDICTIVE,
        priority=WorkOrderPriority.CRITICAL,
    )

    record = work_order.to_record()

    assert record["work_order_type"] == "predictive"
    assert record["priority"] == "critical"
    assert record["status"] == "open"
    assert isinstance(record["work_order_type"], str)
    assert isinstance(record["priority"], str)
    assert isinstance(record["status"], str)


def test_work_order_serialization_uses_iso_8601_timestamps() -> None:
    """Serialization must use ISO 8601 text for all timestamps."""
    scheduled_at = _created_at() + timedelta(hours=1)
    started_at = scheduled_at
    completed_at = started_at + timedelta(hours=2)

    work_order = _make_work_order(
        status=WorkOrderStatus.COMPLETED,
        scheduled_at=scheduled_at,
        started_at=started_at,
        completed_at=completed_at,
    )

    record = work_order.to_record()

    assert record["created_at"] == _created_at().isoformat()
    assert record["scheduled_at"] == scheduled_at.isoformat()
    assert record["started_at"] == started_at.isoformat()
    assert record["completed_at"] == completed_at.isoformat()
    assert record["cancelled_at"] is None


def test_work_order_to_record_returns_new_dictionary_each_time() -> None:
    """Each serialization call should return an independent dictionary."""
    work_order = _make_work_order()

    first_record = work_order.to_record()
    second_record = work_order.to_record()

    assert first_record == second_record
    assert first_record is not second_record


def test_work_order_to_record_does_not_mutate_source_object() -> None:
    """Serialization should not change the immutable source object."""
    work_order = _make_work_order()
    original_created_at = work_order.created_at
    original_status = work_order.status
    original_type = work_order.work_order_type
    original_priority = work_order.priority

    work_order.to_record()

    assert work_order.created_at is original_created_at
    assert work_order.status is original_status
    assert work_order.work_order_type is original_type
    assert work_order.priority is original_priority
