"""
Unit tests for the EOIP Alarm domain model.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest

from eoip.synthetic.models.alarm import (
    Alarm,
    AlarmCategory,
    AlarmSeverity,
    AlarmStatus,
)


def _raised_at() -> datetime:
    """Return the default alarm timestamp."""
    return datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


def _make_alarm(**overrides: Any) -> Alarm:
    """Create a valid alarm with optional overrides."""
    data: dict[str, Any] = {
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
        "message": "Equipment temperature exceeded threshold.",
        "is_synthetic_ground_truth": False,
    }

    data.update(overrides)

    return Alarm(**data)


def test_alarm_construction() -> None:
    """A valid alarm should preserve supplied values."""
    alarm = _make_alarm()

    assert alarm.alarm_id == "ALM-0000001"
    assert alarm.plant_id == "PLANT-001"
    assert alarm.equipment_id == "EQP-00001"
    assert alarm.alarm_code == "INV_OVERTEMP"
    assert alarm.alarm_name == "Inverter Overtemperature"
    assert alarm.category is AlarmCategory.EQUIPMENT
    assert alarm.severity is AlarmSeverity.CRITICAL
    assert alarm.status is AlarmStatus.ACTIVE
    assert alarm.message == "Equipment temperature exceeded threshold."


def test_alarm_normalization() -> None:
    """Identifiers and text should be normalized."""
    alarm = _make_alarm(
        alarm_id=" alm-0000001 ",
        plant_id=" plant-001 ",
        equipment_id=" eqp-00001 ",
        alarm_code=" inv_overtemp ",
        alarm_name=" Inverter Overtemperature ",
        message=" Equipment temperature exceeded threshold. ",
    )

    assert alarm.alarm_id == "ALM-0000001"
    assert alarm.plant_id == "PLANT-001"
    assert alarm.equipment_id == "EQP-00001"
    assert alarm.alarm_code == "INV_OVERTEMP"
    assert alarm.alarm_name == "Inverter Overtemperature"
    assert alarm.message == "Equipment temperature exceeded threshold."


def test_default_values() -> None:
    """Optional fields should use documented defaults."""
    alarm = Alarm(
        alarm_id="ALM-0000001",
        plant_id="PLANT-001",
        equipment_id="EQP-00001",
        alarm_code="GRID_LOSS",
        alarm_name="Grid Loss",
        category=AlarmCategory.GRID,
        severity=AlarmSeverity.MAJOR,
        raised_at=_raised_at(),
    )

    assert alarm.status is AlarmStatus.ACTIVE
    assert alarm.acknowledged_at is None
    assert alarm.cleared_at is None
    assert alarm.message is None
    assert alarm.is_synthetic_ground_truth is False


def test_acknowledged_alarm() -> None:
    """Acknowledged alarms should preserve acknowledgement timestamp."""
    acknowledged_at = _raised_at() + timedelta(minutes=3)

    alarm = _make_alarm(
        status=AlarmStatus.ACKNOWLEDGED,
        acknowledged_at=acknowledged_at,
    )

    assert alarm.status is AlarmStatus.ACKNOWLEDGED
    assert alarm.acknowledged_at == acknowledged_at
    assert alarm.is_open is True


def test_cleared_alarm() -> None:
    """Cleared alarms should preserve cleared timestamp."""
    cleared_at = _raised_at() + timedelta(minutes=15)

    alarm = _make_alarm(
        status=AlarmStatus.CLEARED,
        cleared_at=cleared_at,
    )

    assert alarm.status is AlarmStatus.CLEARED
    assert alarm.cleared_at == cleared_at
    assert alarm.is_open is False


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (AlarmStatus.ACTIVE, True),
        (AlarmStatus.ACKNOWLEDGED, True),
        (AlarmStatus.CLEARED, False),
    ],
)
def test_is_open(
    status: AlarmStatus,
    expected: bool,
) -> None:
    """is_open should match lifecycle state."""
    kwargs: dict[str, Any] = {"status": status}

    if status is AlarmStatus.ACKNOWLEDGED:
        kwargs["acknowledged_at"] = _raised_at() + timedelta(minutes=2)

    if status is AlarmStatus.CLEARED:
        kwargs["cleared_at"] = _raised_at() + timedelta(minutes=5)

    alarm = _make_alarm(**kwargs)

    assert alarm.is_open is expected


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        (AlarmSeverity.INFORMATIONAL, False),
        (AlarmSeverity.WARNING, False),
        (AlarmSeverity.MAJOR, False),
        (AlarmSeverity.CRITICAL, True),
    ],
)
def test_is_critical(
    severity: AlarmSeverity,
    expected: bool,
) -> None:
    """Only critical alarms should return True."""
    alarm = _make_alarm(severity=severity)

    assert alarm.is_critical is expected


def test_acknowledgement_seconds_none() -> None:
    """Acknowledgement duration should be None before acknowledgement."""
    alarm = _make_alarm()

    assert alarm.acknowledgement_seconds is None


def test_resolution_seconds_none() -> None:
    """Resolution duration should be None before clearance."""
    alarm = _make_alarm()

    assert alarm.resolution_seconds is None


def test_acknowledgement_seconds() -> None:
    """Acknowledgement duration should be calculated correctly."""
    alarm = _make_alarm(
        status=AlarmStatus.ACKNOWLEDGED,
        acknowledged_at=_raised_at() + timedelta(seconds=90.1254),
    )

    assert alarm.acknowledgement_seconds == 90.125


def test_resolution_seconds() -> None:
    """Resolution duration should be calculated correctly."""
    alarm = _make_alarm(
        status=AlarmStatus.CLEARED,
        cleared_at=_raised_at() + timedelta(seconds=600.5678),
    )

    assert alarm.resolution_seconds == 600.568


def test_alarm_immutable() -> None:
    """Alarm dataclass should be frozen."""
    alarm = _make_alarm()

    with pytest.raises(FrozenInstanceError):
        alarm.alarm_name = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "alarm_id",
    [
        "",
        "   ",
        "ALM-1",
        "ALM-000001",
        "ALM-00000001",
        "ALARM-0000001",
        "ALM-ABCDEFG",
        "ALM_0000001",
    ],
)
def test_alarm_rejects_invalid_alarm_id(alarm_id: str) -> None:
    """Alarm IDs must follow the ALM-0000001 format."""
    with pytest.raises(ValueError, match="Invalid alarm_id"):
        _make_alarm(alarm_id=alarm_id)


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
def test_alarm_rejects_invalid_plant_id(plant_id: str) -> None:
    """Plant IDs must follow the PLANT-001 format."""
    with pytest.raises(ValueError, match="Invalid plant_id"):
        _make_alarm(plant_id=plant_id)


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
def test_alarm_rejects_invalid_equipment_id(equipment_id: str) -> None:
    """Equipment IDs must follow the EQP-00001 format."""
    with pytest.raises(ValueError, match="Invalid equipment_id"):
        _make_alarm(equipment_id=equipment_id)


@pytest.mark.parametrize(
    "alarm_code",
    [
        "",
        " ",
        "A",
        "_INVALID",
        "-INVALID",
        "INVALID CODE",
        "INV@FAULT",
        "A" * 51,
    ],
)
def test_alarm_rejects_invalid_alarm_code(alarm_code: str) -> None:
    """Alarm codes must follow the documented uppercase code format."""
    with pytest.raises(ValueError, match="Invalid alarm_code"):
        _make_alarm(alarm_code=alarm_code)


@pytest.mark.parametrize(
    "alarm_code",
    [
        "A1",
        "GRID_LOSS",
        "INV-OVERTEMP",
        "COMMUNICATION_FAILURE_01",
        "A" * 50,
    ],
)
def test_alarm_accepts_valid_alarm_codes(alarm_code: str) -> None:
    """Valid alarm codes should be normalized and accepted."""
    alarm = _make_alarm(alarm_code=alarm_code.lower())

    assert alarm.alarm_code == alarm_code


@pytest.mark.parametrize(
    "alarm_name",
    [
        "",
        "   ",
        "\t",
        "\n",
    ],
)
def test_alarm_rejects_empty_alarm_name(alarm_name: str) -> None:
    """Alarm names must contain visible text."""
    with pytest.raises(ValueError, match="alarm_name cannot be empty"):
        _make_alarm(alarm_name=alarm_name)


def test_alarm_rejects_alarm_name_longer_than_limit() -> None:
    """Alarm names must not exceed 150 characters."""
    with pytest.raises(ValueError, match="Use no more than 150"):
        _make_alarm(alarm_name="A" * 151)


def test_alarm_accepts_alarm_name_at_limit() -> None:
    """An alarm name containing exactly 150 characters should be accepted."""
    alarm = _make_alarm(alarm_name="A" * 150)

    assert len(alarm.alarm_name) == 150


@pytest.mark.parametrize(
    "message",
    [
        "",
        "   ",
        "\t",
        "\n",
    ],
)
def test_alarm_rejects_empty_optional_message(message: str) -> None:
    """Blank messages should be represented by None instead."""
    with pytest.raises(ValueError, match="message cannot be empty"):
        _make_alarm(message=message)


def test_alarm_accepts_none_message() -> None:
    """None should represent an unavailable alarm message."""
    alarm = _make_alarm(message=None)

    assert alarm.message is None


def test_alarm_rejects_message_longer_than_limit() -> None:
    """Alarm messages must not exceed 500 characters."""
    with pytest.raises(ValueError, match="Use no more than 500"):
        _make_alarm(message="A" * 501)


def test_alarm_accepts_message_at_limit() -> None:
    """A message containing exactly 500 characters should be accepted."""
    alarm = _make_alarm(message="A" * 500)

    assert len(alarm.message or "") == 500


@pytest.mark.parametrize("category", list(AlarmCategory))
def test_alarm_accepts_every_category(category: AlarmCategory) -> None:
    """Every documented alarm category should be accepted."""
    alarm = _make_alarm(category=category)

    assert alarm.category is category


@pytest.mark.parametrize(
    "category",
    [
        "equipment",
        "grid",
        1,
        None,
    ],
)
def test_alarm_rejects_invalid_category(category: object) -> None:
    """Raw strings and unsupported values must not replace AlarmCategory."""
    with pytest.raises(TypeError, match="Use an AlarmCategory value"):
        _make_alarm(category=category)


@pytest.mark.parametrize("severity", list(AlarmSeverity))
def test_alarm_accepts_every_severity(severity: AlarmSeverity) -> None:
    """Every documented alarm severity should be accepted."""
    alarm = _make_alarm(severity=severity)

    assert alarm.severity is severity


@pytest.mark.parametrize(
    "severity",
    [
        "critical",
        "warning",
        1,
        None,
    ],
)
def test_alarm_rejects_invalid_severity(severity: object) -> None:
    """Raw strings and unsupported values must not replace AlarmSeverity."""
    with pytest.raises(TypeError, match="Use an AlarmSeverity value"):
        _make_alarm(severity=severity)


@pytest.mark.parametrize(
    "status",
    [
        "active",
        "acknowledged",
        "cleared",
        1,
        None,
    ],
)
def test_alarm_rejects_invalid_status(status: object) -> None:
    """Raw strings and unsupported values must not replace AlarmStatus."""
    with pytest.raises(TypeError, match="Use an AlarmStatus value"):
        _make_alarm(status=status)


@pytest.mark.parametrize(
    "is_synthetic_ground_truth",
    [
        True,
        False,
    ],
)
def test_alarm_accepts_boolean_ground_truth_flag(
    is_synthetic_ground_truth: bool,
) -> None:
    """The synthetic ground-truth indicator should accept booleans."""
    alarm = _make_alarm(
        is_synthetic_ground_truth=is_synthetic_ground_truth,
    )

    assert alarm.is_synthetic_ground_truth is is_synthetic_ground_truth


@pytest.mark.parametrize(
    "is_synthetic_ground_truth",
    [
        1,
        0,
        "true",
        None,
    ],
)
def test_alarm_rejects_non_boolean_ground_truth_flag(
    is_synthetic_ground_truth: object,
) -> None:
    """The ground-truth indicator must be an actual boolean."""
    with pytest.raises(
        TypeError,
        match="Invalid is_synthetic_ground_truth value",
    ):
        _make_alarm(
            is_synthetic_ground_truth=is_synthetic_ground_truth,
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("raised_at", "2026-01-15T12:00:00+00:00"),
        ("raised_at", 20260115),
        ("raised_at", None),
        ("acknowledged_at", "2026-01-15T12:05:00+00:00"),
        ("acknowledged_at", 20260115),
        ("cleared_at", "2026-01-15T12:10:00+00:00"),
        ("cleared_at", 20260115),
    ],
)
def test_alarm_rejects_invalid_timestamp_types(
    field_name: str,
    value: object,
) -> None:
    """Alarm timestamps must be datetime values."""
    with pytest.raises(TypeError, match=f"Invalid {field_name}"):
        _make_alarm(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "raised_at",
        "acknowledged_at",
        "cleared_at",
    ],
)
def test_alarm_rejects_timezone_naive_timestamps(
    field_name: str,
) -> None:
    """Timezone-naive timestamps must be rejected."""
    naive_timestamp = datetime(2026, 1, 15, 12, 0)

    with pytest.raises(ValueError, match="timezone-naive"):
        _make_alarm(**{field_name: naive_timestamp})


def test_alarm_accepts_non_utc_timezone() -> None:
    """Timezone-aware timestamps outside UTC should be accepted."""
    local_timezone = timezone(timedelta(hours=5))

    raised_at = datetime(
        2026,
        1,
        15,
        12,
        0,
        tzinfo=local_timezone,
    )

    alarm = _make_alarm(raised_at=raised_at)

    assert alarm.raised_at == raised_at
    assert alarm.raised_at.utcoffset() == timedelta(hours=5)


def test_alarm_rejects_acknowledgement_before_raise() -> None:
    """Acknowledgement cannot occur before the alarm is raised."""
    acknowledged_at = _raised_at() - timedelta(seconds=1)

    with pytest.raises(
        ValueError,
        match="occurs before raised_at",
    ):
        _make_alarm(
            status=AlarmStatus.ACKNOWLEDGED,
            acknowledged_at=acknowledged_at,
        )


def test_alarm_rejects_clearance_before_raise() -> None:
    """Clearance cannot occur before the alarm is raised."""
    cleared_at = _raised_at() - timedelta(seconds=1)

    with pytest.raises(
        ValueError,
        match="occurs before raised_at",
    ):
        _make_alarm(
            status=AlarmStatus.CLEARED,
            cleared_at=cleared_at,
        )


def test_alarm_rejects_clearance_before_acknowledgement() -> None:
    """Clearance cannot occur before acknowledgement."""
    acknowledged_at = _raised_at() + timedelta(minutes=5)
    cleared_at = _raised_at() + timedelta(minutes=4)

    with pytest.raises(
        ValueError,
        match="occurs before acknowledged_at",
    ):
        _make_alarm(
            status=AlarmStatus.CLEARED,
            acknowledged_at=acknowledged_at,
            cleared_at=cleared_at,
        )


def test_active_alarm_rejects_cleared_timestamp() -> None:
    """ACTIVE alarms cannot already have a cleared timestamp."""
    with pytest.raises(
        ValueError,
        match="status 'active'",
    ):
        _make_alarm(
            cleared_at=_raised_at() + timedelta(minutes=5),
        )


def test_acknowledged_alarm_requires_acknowledged_at() -> None:
    """ACKNOWLEDGED alarms require acknowledged_at."""
    with pytest.raises(
        ValueError,
        match="acknowledged_at is missing",
    ):
        _make_alarm(
            status=AlarmStatus.ACKNOWLEDGED,
        )


def test_acknowledged_alarm_rejects_cleared_timestamp() -> None:
    """ACKNOWLEDGED alarms cannot also contain cleared_at."""
    with pytest.raises(
        ValueError,
        match="has cleared_at",
    ):
        _make_alarm(
            status=AlarmStatus.ACKNOWLEDGED,
            acknowledged_at=_raised_at() + timedelta(minutes=2),
            cleared_at=_raised_at() + timedelta(minutes=5),
        )


def test_cleared_alarm_requires_cleared_timestamp() -> None:
    """CLEARED alarms require cleared_at."""
    with pytest.raises(
        ValueError,
        match="cleared_at is missing",
    ):
        _make_alarm(
            status=AlarmStatus.CLEARED,
        )


def test_active_alarm_without_acknowledgement_is_valid() -> None:
    """A newly raised ACTIVE alarm is valid."""
    alarm = _make_alarm()

    assert alarm.status is AlarmStatus.ACTIVE
    assert alarm.acknowledged_at is None
    assert alarm.cleared_at is None


def test_acknowledged_alarm_with_timestamp_is_valid() -> None:
    """ACKNOWLEDGED alarms should preserve acknowledgement time."""
    acknowledged_at = _raised_at() + timedelta(minutes=3)

    alarm = _make_alarm(
        status=AlarmStatus.ACKNOWLEDGED,
        acknowledged_at=acknowledged_at,
    )

    assert alarm.acknowledged_at == acknowledged_at


def test_cleared_alarm_with_acknowledgement_is_valid() -> None:
    """CLEARED alarms may include acknowledgement and clearance."""
    acknowledged_at = _raised_at() + timedelta(minutes=2)
    cleared_at = _raised_at() + timedelta(minutes=8)

    alarm = _make_alarm(
        status=AlarmStatus.CLEARED,
        acknowledged_at=acknowledged_at,
        cleared_at=cleared_at,
    )

    assert alarm.acknowledged_at == acknowledged_at
    assert alarm.cleared_at == cleared_at


def test_cleared_alarm_without_acknowledgement_is_valid() -> None:
    """CLEARED alarms do not require acknowledgement."""
    cleared_at = _raised_at() + timedelta(minutes=7)

    alarm = _make_alarm(
        status=AlarmStatus.CLEARED,
        cleared_at=cleared_at,
    )

    assert alarm.cleared_at == cleared_at
    assert alarm.acknowledged_at is None


def test_to_record_returns_complete_active_alarm_record() -> None:
    """Active alarm serialization should return a complete record."""
    alarm = _make_alarm(is_synthetic_ground_truth=True)

    assert alarm.to_record() == {
        "alarm_id": "ALM-0000001",
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "alarm_code": "INV_OVERTEMP",
        "alarm_name": "Inverter Overtemperature",
        "category": "equipment",
        "severity": "critical",
        "raised_at": "2026-01-15T12:00:00+00:00",
        "status": "active",
        "acknowledged_at": None,
        "cleared_at": None,
        "message": "Equipment temperature exceeded threshold.",
        "is_synthetic_ground_truth": True,
        "is_open": True,
        "is_critical": True,
        "acknowledgement_seconds": None,
        "resolution_seconds": None,
    }


def test_to_record_serializes_acknowledged_alarm() -> None:
    """Acknowledged alarm serialization should include acknowledgement data."""
    acknowledged_at = _raised_at() + timedelta(minutes=3)

    alarm = _make_alarm(
        status=AlarmStatus.ACKNOWLEDGED,
        acknowledged_at=acknowledged_at,
    )

    record = alarm.to_record()

    assert record["status"] == "acknowledged"
    assert record["acknowledged_at"] == "2026-01-15T12:03:00+00:00"
    assert record["cleared_at"] is None
    assert record["is_open"] is True
    assert record["acknowledgement_seconds"] == 180.0
    assert record["resolution_seconds"] is None


def test_to_record_serializes_cleared_alarm() -> None:
    """Cleared alarm serialization should include lifecycle metrics."""
    acknowledged_at = _raised_at() + timedelta(minutes=2)
    cleared_at = _raised_at() + timedelta(minutes=17)

    alarm = _make_alarm(
        status=AlarmStatus.CLEARED,
        acknowledged_at=acknowledged_at,
        cleared_at=cleared_at,
    )

    record = alarm.to_record()

    assert record["status"] == "cleared"
    assert record["acknowledged_at"] == "2026-01-15T12:02:00+00:00"
    assert record["cleared_at"] == "2026-01-15T12:17:00+00:00"
    assert record["is_open"] is False
    assert record["is_critical"] is True
    assert record["acknowledgement_seconds"] == 120.0
    assert record["resolution_seconds"] == 1020.0


def test_to_record_preserves_none_message() -> None:
    """Serialization should preserve None when no message is available."""
    alarm = _make_alarm(message=None)

    record = alarm.to_record()

    assert record["message"] is None


def test_acknowledgement_at_equal_to_raised_at_is_valid() -> None:
    """Acknowledgement may occur at the same instant as alarm raise."""
    alarm = _make_alarm(
        status=AlarmStatus.ACKNOWLEDGED,
        acknowledged_at=_raised_at(),
    )

    assert alarm.acknowledgement_seconds == 0.0


def test_cleared_at_equal_to_raised_at_is_valid() -> None:
    """Clearance may occur at the same instant as alarm raise."""
    alarm = _make_alarm(
        status=AlarmStatus.CLEARED,
        cleared_at=_raised_at(),
    )

    assert alarm.resolution_seconds == 0.0


def test_cleared_at_equal_to_acknowledged_at_is_valid() -> None:
    """Clearance may occur at the same instant as acknowledgement."""
    timestamp = _raised_at() + timedelta(minutes=5)

    alarm = _make_alarm(
        status=AlarmStatus.CLEARED,
        acknowledged_at=timestamp,
        cleared_at=timestamp,
    )

    assert alarm.acknowledgement_seconds == 300.0
    assert alarm.resolution_seconds == 300.0


def test_alarm_code_normalization_occurs_before_validation() -> None:
    """Lowercase alarm codes should be normalized before validation."""
    alarm = _make_alarm(alarm_code=" grid_loss_01 ")

    assert alarm.alarm_code == "GRID_LOSS_01"


def test_alarm_message_normalization_occurs_before_length_validation() -> None:
    """Whitespace should be removed before enforcing message length."""
    message = f" {'A' * 500} "

    alarm = _make_alarm(message=message)

    assert alarm.message == "A" * 500
    assert len(alarm.message) == 500


def test_alarm_name_normalization_occurs_before_length_validation() -> None:
    """Whitespace should be removed before enforcing name length."""
    alarm_name = f" {'A' * 150} "

    alarm = _make_alarm(alarm_name=alarm_name)

    assert alarm.alarm_name == "A" * 150
    assert len(alarm.alarm_name) == 150


def test_alarm_serialization_uses_enum_values() -> None:
    """Serialization must expose enum values rather than enum objects."""
    alarm = _make_alarm(
        category=AlarmCategory.COMMUNICATION,
        severity=AlarmSeverity.WARNING,
    )

    record = alarm.to_record()

    assert record["category"] == "communication"
    assert record["severity"] == "warning"
    assert isinstance(record["category"], str)
    assert isinstance(record["severity"], str)
    assert isinstance(record["status"], str)


def test_alarm_serialization_uses_iso_8601_timestamps() -> None:
    """Serialization must use ISO 8601 text for every timestamp."""
    acknowledged_at = _raised_at() + timedelta(minutes=1)
    cleared_at = _raised_at() + timedelta(minutes=6)

    alarm = _make_alarm(
        status=AlarmStatus.CLEARED,
        acknowledged_at=acknowledged_at,
        cleared_at=cleared_at,
    )

    record = alarm.to_record()

    assert record["raised_at"] == _raised_at().isoformat()
    assert record["acknowledged_at"] == acknowledged_at.isoformat()
    assert record["cleared_at"] == cleared_at.isoformat()


def test_alarm_to_record_returns_new_dictionary_each_time() -> None:
    """Each serialization call should return an independent dictionary."""
    alarm = _make_alarm()

    first_record = alarm.to_record()
    second_record = alarm.to_record()

    assert first_record == second_record
    assert first_record is not second_record


def test_alarm_to_record_does_not_mutate_alarm() -> None:
    """Serializing an alarm should not change the immutable source object."""
    alarm = _make_alarm()
    original_raised_at = alarm.raised_at
    original_status = alarm.status
    original_category = alarm.category
    original_severity = alarm.severity

    alarm.to_record()

    assert alarm.raised_at is original_raised_at
    assert alarm.status is original_status
    assert alarm.category is original_category
    assert alarm.severity is original_severity
