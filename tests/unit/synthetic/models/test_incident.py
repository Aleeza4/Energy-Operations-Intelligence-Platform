"""
Unit tests for the EOIP Incident domain model.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest

from eoip.synthetic.models.incident import (
    Incident,
    IncidentCategory,
    IncidentSeverity,
    IncidentStatus,
)


def _occurred_at() -> datetime:
    """Return the default incident timestamp."""
    return datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


def _make_incident(**overrides: Any) -> Incident:
    """Create a valid incident with optional overrides."""
    data: dict[str, Any] = {
        "incident_id": "INC-0000001",
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "incident_name": "Inverter Failure",
        "category": IncidentCategory.EQUIPMENT_FAILURE,
        "severity": IncidentSeverity.CRITICAL,
        "occurred_at": _occurred_at(),
        "status": IncidentStatus.OPEN,
        "detected_at": None,
        "resolved_at": None,
        "description": "Inverter stopped producing power.",
        "root_cause": None,
        "linked_alarm_id": None,
        "is_synthetic_ground_truth": False,
    }

    data.update(overrides)

    return Incident(**data)


def test_incident_construction() -> None:
    """A valid incident should preserve supplied values."""
    incident = _make_incident()

    assert incident.incident_id == "INC-0000001"
    assert incident.plant_id == "PLANT-001"
    assert incident.equipment_id == "EQP-00001"
    assert incident.incident_name == "Inverter Failure"
    assert incident.category is IncidentCategory.EQUIPMENT_FAILURE
    assert incident.severity is IncidentSeverity.CRITICAL
    assert incident.status is IncidentStatus.OPEN
    assert incident.description == "Inverter stopped producing power."
    assert incident.root_cause is None
    assert incident.linked_alarm_id is None


def test_incident_normalization() -> None:
    """Identifiers and text should be normalized."""
    incident = _make_incident(
        incident_id=" inc-0000001 ",
        plant_id=" plant-001 ",
        equipment_id=" eqp-00001 ",
        incident_name=" Inverter Failure ",
        description=" Inverter stopped producing power. ",
        root_cause=" Cooling Fan Failure ",
        linked_alarm_id=" alm-0000001 ",
    )

    assert incident.incident_id == "INC-0000001"
    assert incident.plant_id == "PLANT-001"
    assert incident.equipment_id == "EQP-00001"
    assert incident.incident_name == "Inverter Failure"
    assert incident.description == "Inverter stopped producing power."
    assert incident.root_cause == "Cooling Fan Failure"
    assert incident.linked_alarm_id == "ALM-0000001"


def test_default_values() -> None:
    """Optional fields should use documented defaults."""
    incident = Incident(
        incident_id="INC-0000001",
        plant_id="PLANT-001",
        equipment_id="EQP-00001",
        incident_name="Grid Event",
        category=IncidentCategory.GRID_EVENT,
        severity=IncidentSeverity.MODERATE,
        occurred_at=_occurred_at(),
    )

    assert incident.status is IncidentStatus.OPEN
    assert incident.detected_at is None
    assert incident.resolved_at is None
    assert incident.description is None
    assert incident.root_cause is None
    assert incident.linked_alarm_id is None
    assert incident.is_synthetic_ground_truth is False


def test_investigating_incident() -> None:
    """Investigating incidents should preserve detection timestamp."""
    detected_at = _occurred_at() + timedelta(minutes=3)

    incident = _make_incident(
        status=IncidentStatus.INVESTIGATING,
        detected_at=detected_at,
    )

    assert incident.status is IncidentStatus.INVESTIGATING
    assert incident.detected_at == detected_at
    assert incident.is_open is True


def test_resolved_incident() -> None:
    """Resolved incidents should preserve resolution timestamp."""
    resolved_at = _occurred_at() + timedelta(minutes=30)

    incident = _make_incident(
        status=IncidentStatus.RESOLVED,
        resolved_at=resolved_at,
    )

    assert incident.status is IncidentStatus.RESOLVED
    assert incident.resolved_at == resolved_at
    assert incident.is_open is False


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (IncidentStatus.OPEN, True),
        (IncidentStatus.INVESTIGATING, True),
        (IncidentStatus.RESOLVED, False),
    ],
)
def test_is_open(
    status: IncidentStatus,
    expected: bool,
) -> None:
    """is_open should match lifecycle state."""
    kwargs: dict[str, Any] = {
        "status": status,
    }

    if status is IncidentStatus.INVESTIGATING:
        kwargs["detected_at"] = _occurred_at() + timedelta(minutes=2)

    if status is IncidentStatus.RESOLVED:
        kwargs["resolved_at"] = _occurred_at() + timedelta(minutes=5)

    incident = _make_incident(**kwargs)

    assert incident.is_open is expected


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        (IncidentSeverity.LOW, False),
        (IncidentSeverity.MODERATE, False),
        (IncidentSeverity.HIGH, False),
        (IncidentSeverity.CRITICAL, True),
    ],
)
def test_is_critical(
    severity: IncidentSeverity,
    expected: bool,
) -> None:
    """Only critical incidents should return True."""
    incident = _make_incident(severity=severity)

    assert incident.is_critical is expected


def test_detection_seconds_none() -> None:
    """Detection duration should be None before detection."""
    incident = _make_incident()

    assert incident.detection_seconds is None


def test_resolution_seconds_none() -> None:
    """Resolution duration should be None before resolution."""
    incident = _make_incident()

    assert incident.resolution_seconds is None


def test_detection_seconds() -> None:
    """Detection duration should be calculated correctly."""
    incident = _make_incident(
        status=IncidentStatus.INVESTIGATING,
        detected_at=_occurred_at() + timedelta(seconds=90.1254),
    )

    assert incident.detection_seconds == 90.125


def test_resolution_seconds() -> None:
    """Resolution duration should be calculated correctly."""
    incident = _make_incident(
        status=IncidentStatus.RESOLVED,
        resolved_at=_occurred_at() + timedelta(seconds=600.5678),
    )

    assert incident.resolution_seconds == 600.568


def test_incident_immutable() -> None:
    """Incident dataclass should be frozen."""
    incident = _make_incident()

    with pytest.raises(FrozenInstanceError):
        incident.incident_name = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "incident_id",
    [
        "",
        "   ",
        "INC-1",
        "INC-000001",
        "INC-00000001",
        "INCIDENT-0000001",
        "INC-ABCDEFG",
        "INC_0000001",
    ],
)
def test_incident_rejects_invalid_incident_id(
    incident_id: str,
) -> None:
    """Incident IDs must follow the INC-0000001 format."""
    with pytest.raises(ValueError, match="Invalid incident_id"):
        _make_incident(incident_id=incident_id)


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
def test_incident_rejects_invalid_plant_id(
    plant_id: str,
) -> None:
    """Plant IDs must follow the PLANT-001 format."""
    with pytest.raises(ValueError, match="Invalid plant_id"):
        _make_incident(plant_id=plant_id)


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
def test_incident_rejects_invalid_equipment_id(
    equipment_id: str,
) -> None:
    """Equipment IDs must follow the EQP-00001 format."""
    with pytest.raises(ValueError, match="Invalid equipment_id"):
        _make_incident(equipment_id=equipment_id)


@pytest.mark.parametrize(
    "linked_alarm_id",
    [
        "",
        " ",
        "ALM-1",
        "ALM-000001",
        "ALM-00000001",
        "ALARM-0000001",
        "ALM-ABCDEFG",
        "ALM_0000001",
    ],
)
def test_incident_rejects_invalid_linked_alarm_id(
    linked_alarm_id: str,
) -> None:
    """Linked alarm IDs must follow the ALM-0000001 format."""
    with pytest.raises(ValueError, match="Invalid linked_alarm_id"):
        _make_incident(linked_alarm_id=linked_alarm_id)


def test_incident_accepts_valid_linked_alarm_id() -> None:
    """A correctly formatted linked alarm ID should be accepted."""
    incident = _make_incident(
        linked_alarm_id="alm-0000001",
    )

    assert incident.linked_alarm_id == "ALM-0000001"


@pytest.mark.parametrize(
    "incident_name",
    [
        "",
        "   ",
        "\t",
        "\n",
    ],
)
def test_incident_rejects_empty_incident_name(
    incident_name: str,
) -> None:
    """Incident names must contain visible text."""
    with pytest.raises(
        ValueError,
        match="incident_name cannot be empty",
    ):
        _make_incident(incident_name=incident_name)


def test_incident_rejects_long_incident_name() -> None:
    """Incident names must not exceed 150 characters."""
    with pytest.raises(
        ValueError,
        match="Use no more than 150",
    ):
        _make_incident(
            incident_name="A" * 151,
        )


def test_incident_accepts_incident_name_at_limit() -> None:
    """Exactly 150 characters should be accepted."""
    incident = _make_incident(
        incident_name="A" * 150,
    )

    assert len(incident.incident_name) == 150


@pytest.mark.parametrize(
    "description",
    [
        "",
        "   ",
        "\t",
        "\n",
    ],
)
def test_incident_rejects_empty_description(
    description: str,
) -> None:
    """Blank descriptions should use None."""
    with pytest.raises(
        ValueError,
        match="description cannot be empty",
    ):
        _make_incident(description=description)


def test_incident_accepts_none_description() -> None:
    """None is valid for description."""
    incident = _make_incident(description=None)

    assert incident.description is None


def test_incident_rejects_long_description() -> None:
    """Descriptions must not exceed 1000 characters."""
    with pytest.raises(
        ValueError,
        match="Use no more than 1000",
    ):
        _make_incident(
            description="A" * 1001,
        )


def test_incident_accepts_description_at_limit() -> None:
    """Exactly 1000 characters should be accepted."""
    incident = _make_incident(
        description="A" * 1000,
    )

    assert len(incident.description or "") == 1000


@pytest.mark.parametrize(
    "root_cause",
    [
        "",
        "   ",
        "\t",
        "\n",
    ],
)
def test_incident_rejects_empty_root_cause(
    root_cause: str,
) -> None:
    """Blank root causes should use None."""
    with pytest.raises(
        ValueError,
        match="root_cause cannot be empty",
    ):
        _make_incident(root_cause=root_cause)


def test_incident_accepts_none_root_cause() -> None:
    """None is valid until RCA is complete."""
    incident = _make_incident(root_cause=None)

    assert incident.root_cause is None


def test_incident_rejects_long_root_cause() -> None:
    """Root cause must not exceed 500 characters."""
    with pytest.raises(
        ValueError,
        match="Use no more than 500",
    ):
        _make_incident(
            root_cause="A" * 501,
        )


def test_incident_accepts_root_cause_at_limit() -> None:
    """Exactly 500 characters should be accepted."""
    incident = _make_incident(
        root_cause="A" * 500,
    )

    assert len(incident.root_cause or "") == 500


@pytest.mark.parametrize(
    "category",
    list(IncidentCategory),
)
def test_incident_accepts_every_category(
    category: IncidentCategory,
) -> None:
    """Every IncidentCategory should be accepted."""
    incident = _make_incident(category=category)

    assert incident.category is category


@pytest.mark.parametrize(
    "category",
    [
        "equipment_failure",
        "grid_event",
        1,
        None,
    ],
)
def test_incident_rejects_invalid_category(
    category: object,
) -> None:
    """Only IncidentCategory enum values are valid."""
    with pytest.raises(
        TypeError,
        match="Use an IncidentCategory value",
    ):
        _make_incident(category=category)


@pytest.mark.parametrize(
    "severity",
    list(IncidentSeverity),
)
def test_incident_accepts_every_severity(
    severity: IncidentSeverity,
) -> None:
    """Every IncidentSeverity should be accepted."""
    incident = _make_incident(
        severity=severity,
    )

    assert incident.severity is severity


@pytest.mark.parametrize(
    "severity",
    [
        "critical",
        "high",
        1,
        None,
    ],
)
def test_incident_rejects_invalid_severity(
    severity: object,
) -> None:
    """Only IncidentSeverity enum values are valid."""
    with pytest.raises(
        TypeError,
        match="Use an IncidentSeverity value",
    ):
        _make_incident(severity=severity)


@pytest.mark.parametrize(
    "status",
    [
        "open",
        "investigating",
        "resolved",
        1,
        None,
    ],
)
def test_incident_rejects_invalid_status(
    status: object,
) -> None:
    """Only IncidentStatus enum values are valid."""
    with pytest.raises(
        TypeError,
        match="Use an IncidentStatus value",
    ):
        _make_incident(status=status)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("occurred_at", "2026-01-15T12:00:00+00:00"),
        ("occurred_at", 20260115),
        ("occurred_at", None),
        ("detected_at", "2026-01-15T12:05:00+00:00"),
        ("detected_at", 20260115),
        ("resolved_at", "2026-01-15T12:10:00+00:00"),
        ("resolved_at", 20260115),
    ],
)
def test_incident_rejects_invalid_timestamp_types(
    field_name: str,
    value: object,
) -> None:
    """Incident timestamps must be datetime values."""
    with pytest.raises(TypeError, match=f"Invalid {field_name}"):
        _make_incident(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "occurred_at",
        "detected_at",
        "resolved_at",
    ],
)
def test_incident_rejects_timezone_naive_timestamps(
    field_name: str,
) -> None:
    """Timezone-naive timestamps must be rejected."""
    naive_timestamp = datetime(2026, 1, 15, 12, 0)

    with pytest.raises(ValueError, match="timezone-naive"):
        _make_incident(**{field_name: naive_timestamp})


def test_incident_accepts_non_utc_timezone() -> None:
    """Timezone-aware timestamps outside UTC should be accepted."""
    local_timezone = timezone(timedelta(hours=5))

    occurred_at = datetime(
        2026,
        1,
        15,
        12,
        0,
        tzinfo=local_timezone,
    )

    incident = _make_incident(
        occurred_at=occurred_at,
    )

    assert incident.occurred_at == occurred_at
    assert incident.occurred_at.utcoffset() == timedelta(hours=5)


def test_incident_rejects_detection_before_occurrence() -> None:
    """Detection cannot occur before occurrence."""
    detected_at = _occurred_at() - timedelta(seconds=1)

    with pytest.raises(
        ValueError,
        match="occurs before occurred_at",
    ):
        _make_incident(
            status=IncidentStatus.INVESTIGATING,
            detected_at=detected_at,
        )


def test_incident_rejects_resolution_before_occurrence() -> None:
    """Resolution cannot occur before occurrence."""
    resolved_at = _occurred_at() - timedelta(seconds=1)

    with pytest.raises(
        ValueError,
        match="occurs before occurred_at",
    ):
        _make_incident(
            status=IncidentStatus.RESOLVED,
            resolved_at=resolved_at,
        )


def test_incident_rejects_resolution_before_detection() -> None:
    """Resolution cannot occur before detection."""
    detected_at = _occurred_at() + timedelta(minutes=5)
    resolved_at = _occurred_at() + timedelta(minutes=4)

    with pytest.raises(
        ValueError,
        match="occurs before detected_at",
    ):
        _make_incident(
            status=IncidentStatus.RESOLVED,
            detected_at=detected_at,
            resolved_at=resolved_at,
        )


@pytest.mark.parametrize(
    "is_synthetic_ground_truth",
    [
        True,
        False,
    ],
)
def test_incident_accepts_boolean_ground_truth_flag(
    is_synthetic_ground_truth: bool,
) -> None:
    """Boolean values should be accepted."""
    incident = _make_incident(
        is_synthetic_ground_truth=is_synthetic_ground_truth,
    )

    assert incident.is_synthetic_ground_truth is is_synthetic_ground_truth


@pytest.mark.parametrize(
    "is_synthetic_ground_truth",
    [
        1,
        0,
        "true",
        None,
    ],
)
def test_incident_rejects_non_boolean_ground_truth_flag(
    is_synthetic_ground_truth: object,
) -> None:
    """Only bool values are valid."""
    with pytest.raises(
        TypeError,
        match="Invalid is_synthetic_ground_truth",
    ):
        _make_incident(
            is_synthetic_ground_truth=is_synthetic_ground_truth,
        )


def test_open_incident_rejects_resolved_timestamp() -> None:
    """OPEN incidents cannot have resolved_at."""
    with pytest.raises(
        ValueError,
        match="status 'open'",
    ):
        _make_incident(
            resolved_at=_occurred_at() + timedelta(minutes=10),
        )


def test_investigating_incident_requires_detected_at() -> None:
    """INVESTIGATING incidents require detected_at."""
    with pytest.raises(
        ValueError,
        match="detected_at is missing",
    ):
        _make_incident(
            status=IncidentStatus.INVESTIGATING,
        )


def test_investigating_incident_rejects_resolved_at() -> None:
    """INVESTIGATING incidents cannot already be resolved."""
    with pytest.raises(
        ValueError,
        match="also has resolved_at",
    ):
        _make_incident(
            status=IncidentStatus.INVESTIGATING,
            detected_at=_occurred_at() + timedelta(minutes=2),
            resolved_at=_occurred_at() + timedelta(minutes=20),
        )


def test_resolved_incident_requires_resolved_at() -> None:
    """RESOLVED incidents require resolved_at."""
    with pytest.raises(
        ValueError,
        match="resolved_at is missing",
    ):
        _make_incident(
            status=IncidentStatus.RESOLVED,
        )


def test_open_incident_is_valid() -> None:
    """A newly opened incident is valid."""
    incident = _make_incident()

    assert incident.status is IncidentStatus.OPEN
    assert incident.detected_at is None
    assert incident.resolved_at is None


def test_investigating_incident_is_valid() -> None:
    """A valid investigating incident should be accepted."""
    detected_at = _occurred_at() + timedelta(minutes=3)

    incident = _make_incident(
        status=IncidentStatus.INVESTIGATING,
        detected_at=detected_at,
    )

    assert incident.detected_at == detected_at


def test_resolved_incident_is_valid() -> None:
    """A valid resolved incident should be accepted."""
    detected_at = _occurred_at() + timedelta(minutes=2)
    resolved_at = _occurred_at() + timedelta(minutes=30)

    incident = _make_incident(
        status=IncidentStatus.RESOLVED,
        detected_at=detected_at,
        resolved_at=resolved_at,
    )

    assert incident.detected_at == detected_at
    assert incident.resolved_at == resolved_at


def test_to_record_returns_complete_open_incident_record() -> None:
    """Open incident serialization should return a complete record."""
    incident = _make_incident(is_synthetic_ground_truth=True)

    assert incident.to_record() == {
        "incident_id": "INC-0000001",
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "incident_name": "Inverter Failure",
        "category": "equipment_failure",
        "severity": "critical",
        "occurred_at": "2026-01-15T12:00:00+00:00",
        "status": "open",
        "detected_at": None,
        "resolved_at": None,
        "description": "Inverter stopped producing power.",
        "root_cause": None,
        "linked_alarm_id": None,
        "is_synthetic_ground_truth": True,
        "is_open": True,
        "is_critical": True,
        "detection_seconds": None,
        "resolution_seconds": None,
    }


def test_to_record_serializes_investigating_incident() -> None:
    """Investigating incident serialization should include detection data."""
    detected_at = _occurred_at() + timedelta(minutes=3)

    incident = _make_incident(
        status=IncidentStatus.INVESTIGATING,
        detected_at=detected_at,
    )

    record = incident.to_record()

    assert record["status"] == "investigating"
    assert record["detected_at"] == "2026-01-15T12:03:00+00:00"
    assert record["resolved_at"] is None
    assert record["is_open"] is True
    assert record["detection_seconds"] == 180.0
    assert record["resolution_seconds"] is None


def test_to_record_serializes_resolved_incident() -> None:
    """Resolved incident serialization should include lifecycle metrics."""
    detected_at = _occurred_at() + timedelta(minutes=2)
    resolved_at = _occurred_at() + timedelta(minutes=45)

    incident = _make_incident(
        status=IncidentStatus.RESOLVED,
        detected_at=detected_at,
        resolved_at=resolved_at,
        root_cause="Cooling fan failure.",
        linked_alarm_id="ALM-0000001",
    )

    record = incident.to_record()

    assert record["status"] == "resolved"
    assert record["detected_at"] == "2026-01-15T12:02:00+00:00"
    assert record["resolved_at"] == "2026-01-15T12:45:00+00:00"
    assert record["root_cause"] == "Cooling fan failure."
    assert record["linked_alarm_id"] == "ALM-0000001"
    assert record["is_open"] is False
    assert record["is_critical"] is True
    assert record["detection_seconds"] == 120.0
    assert record["resolution_seconds"] == 2700.0


def test_to_record_preserves_none_optional_fields() -> None:
    """Serialization should preserve None for optional fields."""
    incident = _make_incident(
        description=None,
        root_cause=None,
        linked_alarm_id=None,
    )

    record = incident.to_record()

    assert record["description"] is None
    assert record["root_cause"] is None
    assert record["linked_alarm_id"] is None
    assert record["detected_at"] is None
    assert record["resolved_at"] is None


def test_detection_at_equal_to_occurred_at_is_valid() -> None:
    """Detection may occur at the same instant as occurrence."""
    incident = _make_incident(
        status=IncidentStatus.INVESTIGATING,
        detected_at=_occurred_at(),
    )

    assert incident.detection_seconds == 0.0


def test_resolved_at_equal_to_occurred_at_is_valid() -> None:
    """Resolution may occur at the same instant as occurrence."""
    incident = _make_incident(
        status=IncidentStatus.RESOLVED,
        resolved_at=_occurred_at(),
    )

    assert incident.resolution_seconds == 0.0


def test_resolved_at_equal_to_detected_at_is_valid() -> None:
    """Resolution may occur at the same instant as detection."""
    timestamp = _occurred_at() + timedelta(minutes=5)

    incident = _make_incident(
        status=IncidentStatus.RESOLVED,
        detected_at=timestamp,
        resolved_at=timestamp,
    )

    assert incident.detection_seconds == 300.0
    assert incident.resolution_seconds == 300.0


def test_incident_name_normalization_occurs_before_length_validation() -> None:
    """Whitespace should be removed before enforcing name length."""
    incident_name = f" {'A' * 150} "

    incident = _make_incident(incident_name=incident_name)

    assert incident.incident_name == "A" * 150
    assert len(incident.incident_name) == 150


def test_description_normalization_occurs_before_length_validation() -> None:
    """Whitespace should be removed before enforcing description length."""
    description = f" {'A' * 1000} "

    incident = _make_incident(description=description)

    assert incident.description == "A" * 1000
    assert len(incident.description or "") == 1000


def test_root_cause_normalization_occurs_before_length_validation() -> None:
    """Whitespace should be removed before enforcing root-cause length."""
    root_cause = f" {'A' * 500} "

    incident = _make_incident(root_cause=root_cause)

    assert incident.root_cause == "A" * 500
    assert len(incident.root_cause or "") == 500


def test_incident_serialization_uses_enum_values() -> None:
    """Serialization must expose enum values rather than enum objects."""
    incident = _make_incident(
        category=IncidentCategory.COMMUNICATION_FAILURE,
        severity=IncidentSeverity.HIGH,
    )

    record = incident.to_record()

    assert record["category"] == "communication_failure"
    assert record["severity"] == "high"
    assert record["status"] == "open"
    assert isinstance(record["category"], str)
    assert isinstance(record["severity"], str)
    assert isinstance(record["status"], str)


def test_incident_serialization_uses_iso_8601_timestamps() -> None:
    """Serialization must use ISO 8601 text for every timestamp."""
    detected_at = _occurred_at() + timedelta(minutes=1)
    resolved_at = _occurred_at() + timedelta(minutes=6)

    incident = _make_incident(
        status=IncidentStatus.RESOLVED,
        detected_at=detected_at,
        resolved_at=resolved_at,
    )

    record = incident.to_record()

    assert record["occurred_at"] == _occurred_at().isoformat()
    assert record["detected_at"] == detected_at.isoformat()
    assert record["resolved_at"] == resolved_at.isoformat()


def test_incident_to_record_returns_new_dictionary_each_time() -> None:
    """Each serialization call should return an independent dictionary."""
    incident = _make_incident()

    first_record = incident.to_record()
    second_record = incident.to_record()

    assert first_record == second_record
    assert first_record is not second_record


def test_incident_to_record_does_not_mutate_incident() -> None:
    """Serializing an incident should not change the source object."""
    incident = _make_incident()
    original_occurred_at = incident.occurred_at
    original_status = incident.status
    original_category = incident.category
    original_severity = incident.severity

    incident.to_record()

    assert incident.occurred_at is original_occurred_at
    assert incident.status is original_status
    assert incident.category is original_category
    assert incident.severity is original_severity
