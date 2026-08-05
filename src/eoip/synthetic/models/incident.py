"""
Incident domain model for EOIP synthetic data generation.

This module defines the authoritative representation of an operational
incident affecting a solar plant asset. Synthetic incident generators,
maintenance workflows, reliability analytics, ETL pipelines, and dashboards
must use this model instead of creating independent incident dictionaries.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

_INCIDENT_ID_PATTERN = re.compile(r"^INC-\d{7}$")
_PLANT_ID_PATTERN = re.compile(r"^PLANT-\d{3}$")
_EQUIPMENT_ID_PATTERN = re.compile(r"^EQP-\d{5}$")
_ALARM_ID_PATTERN = re.compile(r"^ALM-\d{7}$")


class IncidentCategory(StrEnum):
    """Supported categories for operational incidents."""

    EQUIPMENT_FAILURE = "equipment_failure"
    GRID_EVENT = "grid_event"
    COMMUNICATION_FAILURE = "communication_failure"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    ENVIRONMENTAL_EVENT = "environmental_event"
    SAFETY_EVENT = "safety_event"
    PLANNED_MAINTENANCE = "planned_maintenance"


class IncidentSeverity(StrEnum):
    """Supported operational severity levels for incidents."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(StrEnum):
    """Supported lifecycle states for operational incidents."""

    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"


@dataclass(frozen=True, slots=True)
class Incident:
    """Immutable operational incident record for one plant asset."""

    incident_id: str
    plant_id: str
    equipment_id: str
    incident_name: str
    category: IncidentCategory
    severity: IncidentSeverity
    occurred_at: datetime
    status: IncidentStatus = IncidentStatus.OPEN
    detected_at: datetime | None = None
    resolved_at: datetime | None = None
    description: str | None = None
    root_cause: str | None = None
    linked_alarm_id: str | None = None
    is_synthetic_ground_truth: bool = False

    def __post_init__(self) -> None:
        """Normalize and validate the complete operational incident."""
        normalized_incident_id = self.incident_id.strip().upper()
        normalized_plant_id = self.plant_id.strip().upper()
        normalized_equipment_id = self.equipment_id.strip().upper()
        normalized_incident_name = self.incident_name.strip()
        normalized_description = (
            self.description.strip() if self.description is not None else None
        )
        normalized_root_cause = (
            self.root_cause.strip() if self.root_cause is not None else None
        )
        normalized_linked_alarm_id = (
            self.linked_alarm_id.strip().upper()
            if self.linked_alarm_id is not None
            else None
        )

        object.__setattr__(self, "incident_id", normalized_incident_id)
        object.__setattr__(self, "plant_id", normalized_plant_id)
        object.__setattr__(self, "equipment_id", normalized_equipment_id)
        object.__setattr__(self, "incident_name", normalized_incident_name)
        object.__setattr__(self, "description", normalized_description)
        object.__setattr__(self, "root_cause", normalized_root_cause)
        object.__setattr__(
            self,
            "linked_alarm_id",
            normalized_linked_alarm_id,
        )

        self._validate_identifiers()
        self._validate_text_fields()
        self._validate_enums()
        self._validate_timestamps()
        self._validate_boolean_fields()
        self._validate_lifecycle_consistency()

    def _validate_identifiers(self) -> None:
        """Validate incident, plant, equipment, and linked alarm identifiers."""
        if not _INCIDENT_ID_PATTERN.fullmatch(self.incident_id):
            raise ValueError(
                f"Invalid incident_id '{self.incident_id}'. "
                "Use the format 'INC-0000001'."
            )

        if not _PLANT_ID_PATTERN.fullmatch(self.plant_id):
            raise ValueError(
                f"Invalid plant_id '{self.plant_id}' for {self.incident_id}. "
                "Use the format 'PLANT-001'."
            )

        if not _EQUIPMENT_ID_PATTERN.fullmatch(self.equipment_id):
            raise ValueError(
                f"Invalid equipment_id '{self.equipment_id}' for "
                f"{self.incident_id}. Use the format 'EQP-00001'."
            )

        if self.linked_alarm_id is not None and not _ALARM_ID_PATTERN.fullmatch(
            self.linked_alarm_id
        ):
            raise ValueError(
                f"Invalid linked_alarm_id '{self.linked_alarm_id}' for "
                f"{self.incident_id}. Use the format 'ALM-0000001' or None."
            )

    def _validate_text_fields(self) -> None:
        """Validate incident name, description, and root-cause text."""
        if not self.incident_name:
            raise ValueError(
                f"incident_name cannot be empty for {self.incident_id}. "
                "Provide a descriptive incident name."
            )

        if len(self.incident_name) > 150:
            raise ValueError(
                f"incident_name for {self.incident_id} contains "
                f"{len(self.incident_name)} characters. Use no more than 150."
            )

        if self.description is not None and not self.description:
            raise ValueError(
                f"description cannot be empty for {self.incident_id}. "
                "Use None when no description is available."
            )

        if self.description is not None and len(self.description) > 1_000:
            raise ValueError(
                f"description for {self.incident_id} contains "
                f"{len(self.description)} characters. Use no more than 1000."
            )

        if self.root_cause is not None and not self.root_cause:
            raise ValueError(
                f"root_cause cannot be empty for {self.incident_id}. "
                "Use None until the root cause has been identified."
            )

        if self.root_cause is not None and len(self.root_cause) > 500:
            raise ValueError(
                f"root_cause for {self.incident_id} contains "
                f"{len(self.root_cause)} characters. Use no more than 500."
            )

    def _validate_enums(self) -> None:
        """Validate incident category, severity, and status values."""
        if not isinstance(self.category, IncidentCategory):
            raise TypeError(
                f"Invalid category '{self.category}' for {self.incident_id}. "
                "Use an IncidentCategory value."
            )

        if not isinstance(self.severity, IncidentSeverity):
            raise TypeError(
                f"Invalid severity '{self.severity}' for {self.incident_id}. "
                "Use an IncidentSeverity value."
            )

        if not isinstance(self.status, IncidentStatus):
            raise TypeError(
                f"Invalid status '{self.status}' for {self.incident_id}. "
                "Use an IncidentStatus value."
            )

    def _validate_timestamps(self) -> None:
        """Validate incident timestamps, timezone awareness, and ordering."""
        if not isinstance(self.occurred_at, datetime):
            raise TypeError(
                f"Invalid occurred_at '{self.occurred_at}' for "
                f"{self.incident_id}. Use a timezone-aware datetime value."
            )

        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError(
                f"occurred_at '{self.occurred_at}' for {self.incident_id} is "
                "timezone-naive. Use a timezone-aware datetime, preferably UTC."
            )

        optional_timestamps: tuple[
            tuple[str, datetime | None],
            ...,
        ] = (
            ("detected_at", self.detected_at),
            ("resolved_at", self.resolved_at),
        )

        for field_name, value in optional_timestamps:
            if value is None:
                continue

            if not isinstance(value, datetime):
                raise TypeError(
                    f"Invalid {field_name} '{value}' for {self.incident_id}. "
                    "Use a timezone-aware datetime value or None."
                )

            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(
                    f"{field_name} '{value}' for {self.incident_id} is "
                    "timezone-naive. Use a timezone-aware datetime, preferably "
                    "UTC."
                )

        if self.detected_at is not None and self.detected_at < self.occurred_at:
            raise ValueError(
                f"detected_at '{self.detected_at.isoformat()}' for "
                f"{self.incident_id} occurs before occurred_at "
                f"'{self.occurred_at.isoformat()}'."
            )

        if self.resolved_at is not None and self.resolved_at < self.occurred_at:
            raise ValueError(
                f"resolved_at '{self.resolved_at.isoformat()}' for "
                f"{self.incident_id} occurs before occurred_at "
                f"'{self.occurred_at.isoformat()}'."
            )

        if (
            self.resolved_at is not None
            and self.detected_at is not None
            and self.resolved_at < self.detected_at
        ):
            raise ValueError(
                f"resolved_at '{self.resolved_at.isoformat()}' for "
                f"{self.incident_id} occurs before detected_at "
                f"'{self.detected_at.isoformat()}'."
            )

    def _validate_boolean_fields(self) -> None:
        """Validate the synthetic ground-truth indicator."""
        if not isinstance(self.is_synthetic_ground_truth, bool):
            raise TypeError(
                f"Invalid is_synthetic_ground_truth value "
                f"'{self.is_synthetic_ground_truth}' for {self.incident_id}. "
                "Use True or False."
            )

    def _validate_lifecycle_consistency(self) -> None:
        """Validate consistency between incident status and resolution data."""
        if self.status is IncidentStatus.OPEN and self.resolved_at is not None:
            raise ValueError(
                f"Incident {self.incident_id} has status 'open' but also has "
                "resolved_at. Remove resolved_at or use status 'resolved'."
            )

        if self.status is IncidentStatus.INVESTIGATING and self.detected_at is None:
            raise ValueError(
                f"Incident {self.incident_id} has status 'investigating' but "
                "detected_at is missing."
            )

        if self.status is IncidentStatus.INVESTIGATING and self.resolved_at is not None:
            raise ValueError(
                f"Incident {self.incident_id} has status 'investigating' but "
                "also has resolved_at. Use status 'resolved' after resolution."
            )

        if self.status is IncidentStatus.RESOLVED and self.resolved_at is None:
            raise ValueError(
                f"Incident {self.incident_id} has status 'resolved' but "
                "resolved_at is missing."
            )

    @property
    def is_open(self) -> bool:
        """Return whether the incident remains open or under investigation."""
        return self.status in {
            IncidentStatus.OPEN,
            IncidentStatus.INVESTIGATING,
        }

    @property
    def is_critical(self) -> bool:
        """Return whether the incident has critical severity."""
        return self.severity is IncidentSeverity.CRITICAL

    @property
    def detection_seconds(self) -> float | None:
        """Return elapsed seconds from occurrence to incident detection."""
        if self.detected_at is None:
            return None

        elapsed = self.detected_at - self.occurred_at
        return round(elapsed.total_seconds(), 3)

    @property
    def resolution_seconds(self) -> float | None:
        """Return elapsed seconds from occurrence to incident resolution."""
        if self.resolved_at is None:
            return None

        elapsed = self.resolved_at - self.occurred_at
        return round(elapsed.total_seconds(), 3)

    def to_record(self) -> dict[str, Any]:
        """Return a serialization-ready operational incident record."""
        record = asdict(self)
        record["category"] = self.category.value
        record["severity"] = self.severity.value
        record["status"] = self.status.value
        record["occurred_at"] = self.occurred_at.isoformat()
        record["detected_at"] = (
            self.detected_at.isoformat() if self.detected_at is not None else None
        )
        record["resolved_at"] = (
            self.resolved_at.isoformat() if self.resolved_at is not None else None
        )
        record["is_open"] = self.is_open
        record["is_critical"] = self.is_critical
        record["detection_seconds"] = self.detection_seconds
        record["resolution_seconds"] = self.resolution_seconds
        return record
