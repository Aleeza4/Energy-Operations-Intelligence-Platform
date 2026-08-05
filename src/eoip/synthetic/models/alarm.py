"""
Alarm domain model for EOIP synthetic data generation.

This module defines the authoritative representation of an operational alarm
raised by plant equipment. Synthetic alarm generators, incident correlation,
ETL pipelines, alarm analytics, and dashboard components must use this model
instead of creating independent alarm dictionaries.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

_PLANT_ID_PATTERN = re.compile(r"^PLANT-\d{3}$")
_EQUIPMENT_ID_PATTERN = re.compile(r"^EQP-\d{5}$")
_ALARM_ID_PATTERN = re.compile(r"^ALM-\d{7}$")
_ALARM_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_-]{1,49}$")


class AlarmSeverity(StrEnum):
    """Supported operational severity levels for alarms."""

    INFORMATIONAL = "informational"
    WARNING = "warning"
    MAJOR = "major"
    CRITICAL = "critical"


class AlarmStatus(StrEnum):
    """Supported lifecycle states for alarms."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    CLEARED = "cleared"


class AlarmCategory(StrEnum):
    """Supported alarm categories used by EOIP operations analytics."""

    EQUIPMENT = "equipment"
    GRID = "grid"
    COMMUNICATION = "communication"
    ENVIRONMENTAL = "environmental"
    PERFORMANCE = "performance"
    SAFETY = "safety"


@dataclass(frozen=True, slots=True)
class Alarm:
    """Immutable operational alarm record for one plant asset."""

    alarm_id: str
    plant_id: str
    equipment_id: str
    alarm_code: str
    alarm_name: str
    category: AlarmCategory
    severity: AlarmSeverity
    raised_at: datetime
    status: AlarmStatus = AlarmStatus.ACTIVE
    acknowledged_at: datetime | None = None
    cleared_at: datetime | None = None
    message: str | None = None
    is_synthetic_ground_truth: bool = False

    def __post_init__(self) -> None:
        """Normalize and validate the complete alarm record."""
        normalized_alarm_id = self.alarm_id.strip().upper()
        normalized_plant_id = self.plant_id.strip().upper()
        normalized_equipment_id = self.equipment_id.strip().upper()
        normalized_alarm_code = self.alarm_code.strip().upper()
        normalized_alarm_name = self.alarm_name.strip()
        normalized_message = self.message.strip() if self.message is not None else None

        object.__setattr__(self, "alarm_id", normalized_alarm_id)
        object.__setattr__(self, "plant_id", normalized_plant_id)
        object.__setattr__(self, "equipment_id", normalized_equipment_id)
        object.__setattr__(self, "alarm_code", normalized_alarm_code)
        object.__setattr__(self, "alarm_name", normalized_alarm_name)
        object.__setattr__(self, "message", normalized_message)

        self._validate_identifiers()
        self._validate_text_fields()
        self._validate_enums()
        self._validate_timestamps()
        self._validate_boolean_fields()
        self._validate_lifecycle_consistency()

    def _validate_identifiers(self) -> None:
        """Validate alarm, plant, equipment, and alarm-code identifiers."""
        if not _ALARM_ID_PATTERN.fullmatch(self.alarm_id):
            raise ValueError(
                f"Invalid alarm_id '{self.alarm_id}'. " "Use the format 'ALM-0000001'."
            )

        if not _PLANT_ID_PATTERN.fullmatch(self.plant_id):
            raise ValueError(
                f"Invalid plant_id '{self.plant_id}' for {self.alarm_id}. "
                "Use the format 'PLANT-001'."
            )

        if not _EQUIPMENT_ID_PATTERN.fullmatch(self.equipment_id):
            raise ValueError(
                f"Invalid equipment_id '{self.equipment_id}' for "
                f"{self.alarm_id}. Use the format 'EQP-00001'."
            )

        if not _ALARM_CODE_PATTERN.fullmatch(self.alarm_code):
            raise ValueError(
                f"Invalid alarm_code '{self.alarm_code}' for {self.alarm_id}. "
                "Use 2 to 50 uppercase letters, digits, underscores, or hyphens, "
                "starting with a letter or digit."
            )

    def _validate_text_fields(self) -> None:
        """Validate human-readable alarm fields."""
        if not self.alarm_name:
            raise ValueError(
                f"alarm_name cannot be empty for {self.alarm_id}. "
                "Provide a descriptive alarm name."
            )

        if self.message is not None and not self.message:
            raise ValueError(
                f"message cannot be empty for {self.alarm_id}. "
                "Use None when no alarm message is available."
            )

        if len(self.alarm_name) > 150:
            raise ValueError(
                f"alarm_name for {self.alarm_id} contains "
                f"{len(self.alarm_name)} characters. Use no more than 150."
            )

        if self.message is not None and len(self.message) > 500:
            raise ValueError(
                f"message for {self.alarm_id} contains "
                f"{len(self.message)} characters. Use no more than 500."
            )

    def _validate_enums(self) -> None:
        """Validate alarm category, severity, and lifecycle status."""
        if not isinstance(self.category, AlarmCategory):
            raise TypeError(
                f"Invalid category '{self.category}' for {self.alarm_id}. "
                "Use an AlarmCategory value."
            )

        if not isinstance(self.severity, AlarmSeverity):
            raise TypeError(
                f"Invalid severity '{self.severity}' for {self.alarm_id}. "
                "Use an AlarmSeverity value."
            )

        if not isinstance(self.status, AlarmStatus):
            raise TypeError(
                f"Invalid status '{self.status}' for {self.alarm_id}. "
                "Use an AlarmStatus value."
            )

    def _validate_timestamps(self) -> None:
        """Validate alarm timestamps, ordering, and timezone awareness."""
        if not isinstance(self.raised_at, datetime):
            raise TypeError(
                f"Invalid raised_at '{self.raised_at}' for {self.alarm_id}. "
                "Use a timezone-aware datetime value."
            )

        if self.raised_at.tzinfo is None or self.raised_at.utcoffset() is None:
            raise ValueError(
                f"raised_at '{self.raised_at}' for {self.alarm_id} is "
                "timezone-naive. Use a timezone-aware datetime, preferably "
                "in UTC."
            )

        optional_timestamp_fields: tuple[
            tuple[str, datetime | None],
            ...,
        ] = (
            ("acknowledged_at", self.acknowledged_at),
            ("cleared_at", self.cleared_at),
        )

        for field_name, value in optional_timestamp_fields:
            if value is None:
                continue

            if not isinstance(value, datetime):
                raise TypeError(
                    f"Invalid {field_name} '{value}' for {self.alarm_id}. "
                    "Use a timezone-aware datetime value or None."
                )

            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(
                    f"{field_name} '{value}' for {self.alarm_id} is "
                    "timezone-naive. Use a timezone-aware datetime, preferably "
                    "in UTC."
                )

        if self.acknowledged_at is not None and self.acknowledged_at < self.raised_at:
            raise ValueError(
                f"acknowledged_at '{self.acknowledged_at.isoformat()}' for "
                f"{self.alarm_id} occurs before raised_at "
                f"'{self.raised_at.isoformat()}'."
            )

        if self.cleared_at is not None and self.cleared_at < self.raised_at:
            raise ValueError(
                f"cleared_at '{self.cleared_at.isoformat()}' for "
                f"{self.alarm_id} occurs before raised_at "
                f"'{self.raised_at.isoformat()}'."
            )

        if (
            self.cleared_at is not None
            and self.acknowledged_at is not None
            and self.cleared_at < self.acknowledged_at
        ):
            raise ValueError(
                f"cleared_at '{self.cleared_at.isoformat()}' for "
                f"{self.alarm_id} occurs before acknowledged_at "
                f"'{self.acknowledged_at.isoformat()}'."
            )

    def _validate_boolean_fields(self) -> None:
        """Validate the synthetic ground-truth indicator."""
        if not isinstance(self.is_synthetic_ground_truth, bool):
            raise TypeError(
                f"Invalid is_synthetic_ground_truth value "
                f"'{self.is_synthetic_ground_truth}' for {self.alarm_id}. "
                "Use True or False."
            )

    def _validate_lifecycle_consistency(self) -> None:
        """Validate consistency between alarm status and lifecycle timestamps."""
        if self.status is AlarmStatus.ACTIVE and self.cleared_at is not None:
            raise ValueError(
                f"Alarm {self.alarm_id} has status 'active' but also has "
                "cleared_at. Remove cleared_at or use status 'cleared'."
            )

        if self.status is AlarmStatus.ACKNOWLEDGED:
            if self.acknowledged_at is None:
                raise ValueError(
                    f"Alarm {self.alarm_id} has status 'acknowledged' but "
                    "acknowledged_at is missing."
                )

            if self.cleared_at is not None:
                raise ValueError(
                    f"Alarm {self.alarm_id} has status 'acknowledged' but also "
                    "has cleared_at. Use status 'cleared' when the alarm has "
                    "been cleared."
                )

        if self.status is AlarmStatus.CLEARED and self.cleared_at is None:
            raise ValueError(
                f"Alarm {self.alarm_id} has status 'cleared' but cleared_at "
                "is missing."
            )

    @property
    def is_open(self) -> bool:
        """Return whether the alarm remains active or acknowledged."""
        return self.status in {
            AlarmStatus.ACTIVE,
            AlarmStatus.ACKNOWLEDGED,
        }

    @property
    def is_critical(self) -> bool:
        """Return whether the alarm has critical severity."""
        return self.severity is AlarmSeverity.CRITICAL

    @property
    def acknowledgement_seconds(self) -> float | None:
        """Return elapsed seconds from alarm raise to acknowledgement."""
        if self.acknowledged_at is None:
            return None

        elapsed = self.acknowledged_at - self.raised_at
        return round(elapsed.total_seconds(), 3)

    @property
    def resolution_seconds(self) -> float | None:
        """Return elapsed seconds from alarm raise to clearance."""
        if self.cleared_at is None:
            return None

        elapsed = self.cleared_at - self.raised_at
        return round(elapsed.total_seconds(), 3)

    def to_record(self) -> dict[str, Any]:
        """Return a serialization-ready operational alarm record."""
        record = asdict(self)
        record["category"] = self.category.value
        record["severity"] = self.severity.value
        record["status"] = self.status.value
        record["raised_at"] = self.raised_at.isoformat()
        record["acknowledged_at"] = (
            self.acknowledged_at.isoformat()
            if self.acknowledged_at is not None
            else None
        )
        record["cleared_at"] = (
            self.cleared_at.isoformat() if self.cleared_at is not None else None
        )
        record["is_open"] = self.is_open
        record["is_critical"] = self.is_critical
        record["acknowledgement_seconds"] = self.acknowledgement_seconds
        record["resolution_seconds"] = self.resolution_seconds
        return record
