"""
Ground-truth event domain model for EOIP synthetic data generation.

This module defines the authoritative representation of a known synthetic event
injected into the EOIP dataset. Ground-truth events provide traceable labels
for anomaly detection, incident correlation, predictive maintenance, and model
evaluation without duplicating operational alarm or incident records.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

_GROUND_TRUTH_ID_PATTERN = re.compile(r"^GTE-\d{7}$")
_PLANT_ID_PATTERN = re.compile(r"^PLANT-\d{3}$")
_EQUIPMENT_ID_PATTERN = re.compile(r"^EQP-\d{5}$")


class GroundTruthEventType(StrEnum):
    """Supported synthetic ground-truth event types."""

    EQUIPMENT_FAILURE = "equipment_failure"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    GRID_OUTAGE = "grid_outage"
    COMMUNICATION_LOSS = "communication_loss"
    SENSOR_FAULT = "sensor_fault"
    CURTAILMENT = "curtailment"
    SOILING = "soiling"
    MAINTENANCE = "maintenance"


class GroundTruthSeverity(StrEnum):
    """Supported severity levels for synthetic ground-truth events."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class GroundTruthEvent:
    """Immutable synthetic event label for one plant or equipment asset."""

    ground_truth_id: str
    plant_id: str
    event_type: GroundTruthEventType
    severity: GroundTruthSeverity
    started_at: datetime
    ended_at: datetime
    equipment_id: str | None = None
    expected_power_loss_pct: float = 0.0
    expected_energy_loss_kwh: float = 0.0
    description: str | None = None

    def __post_init__(self) -> None:
        """Normalize and validate the complete ground-truth event."""
        normalized_ground_truth_id = self.ground_truth_id.strip().upper()
        normalized_plant_id = self.plant_id.strip().upper()
        normalized_equipment_id = (
            self.equipment_id.strip().upper() if self.equipment_id is not None else None
        )
        normalized_description = (
            self.description.strip() if self.description is not None else None
        )

        object.__setattr__(
            self,
            "ground_truth_id",
            normalized_ground_truth_id,
        )
        object.__setattr__(self, "plant_id", normalized_plant_id)
        object.__setattr__(self, "equipment_id", normalized_equipment_id)
        object.__setattr__(self, "description", normalized_description)

        self._validate_identifiers()
        self._validate_enums()
        self._validate_timestamps()
        self._validate_numeric_fields()
        self._validate_description()

    def _validate_identifiers(self) -> None:
        """Validate ground-truth, plant, and optional equipment identifiers."""
        if not _GROUND_TRUTH_ID_PATTERN.fullmatch(self.ground_truth_id):
            raise ValueError(
                f"Invalid ground_truth_id '{self.ground_truth_id}'. "
                "Use the format 'GTE-0000001'."
            )

        if not _PLANT_ID_PATTERN.fullmatch(self.plant_id):
            raise ValueError(
                f"Invalid plant_id '{self.plant_id}' for "
                f"{self.ground_truth_id}. Use the format 'PLANT-001'."
            )

        if self.equipment_id is not None and not _EQUIPMENT_ID_PATTERN.fullmatch(
            self.equipment_id
        ):
            raise ValueError(
                f"Invalid equipment_id '{self.equipment_id}' for "
                f"{self.ground_truth_id}. Use the format 'EQP-00001' or None."
            )

    def _validate_enums(self) -> None:
        """Validate event type and severity values."""
        if not isinstance(self.event_type, GroundTruthEventType):
            raise TypeError(
                f"Invalid event_type '{self.event_type}' for "
                f"{self.ground_truth_id}. Use a GroundTruthEventType value."
            )

        if not isinstance(self.severity, GroundTruthSeverity):
            raise TypeError(
                f"Invalid severity '{self.severity}' for "
                f"{self.ground_truth_id}. Use a GroundTruthSeverity value."
            )

    def _validate_timestamps(self) -> None:
        """Validate timezone awareness and event ordering."""
        timestamp_fields = (
            ("started_at", self.started_at),
            ("ended_at", self.ended_at),
        )

        for field_name, value in timestamp_fields:
            if not isinstance(value, datetime):
                raise TypeError(
                    f"Invalid {field_name} '{value}' for "
                    f"{self.ground_truth_id}. "
                    "Use a timezone-aware datetime value."
                )

            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(
                    f"{field_name} '{value}' for {self.ground_truth_id} is "
                    "timezone-naive. Use a timezone-aware datetime, preferably "
                    "in UTC."
                )

        if self.ended_at <= self.started_at:
            raise ValueError(
                f"ended_at '{self.ended_at.isoformat()}' for "
                f"{self.ground_truth_id} must occur after started_at "
                f"'{self.started_at.isoformat()}'."
            )

    def _validate_numeric_fields(self) -> None:
        """Validate expected power and energy loss values."""
        self._validate_number(
            field_name="expected_power_loss_pct",
            value=self.expected_power_loss_pct,
            minimum=0.0,
            maximum=100.0,
        )
        self._validate_number(
            field_name="expected_energy_loss_kwh",
            value=self.expected_energy_loss_kwh,
            minimum=0.0,
            maximum=None,
        )

    def _validate_description(self) -> None:
        """Validate optional event description."""
        if self.description is None:
            return

        if not self.description:
            raise ValueError(
                f"description cannot be empty for {self.ground_truth_id}. "
                "Use None when no description is available."
            )

        if len(self.description) > 1_000:
            raise ValueError(
                f"description for {self.ground_truth_id} contains "
                f"{len(self.description)} characters. Use no more than 1000."
            )

    def _validate_number(
        self,
        *,
        field_name: str,
        value: float,
        minimum: float,
        maximum: float | None,
    ) -> None:
        """Validate a finite numeric value against inclusive bounds."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(
                f"Invalid {field_name} '{value}' for "
                f"{self.ground_truth_id}. Use a finite numeric value."
            )

        if not math.isfinite(value):
            raise ValueError(
                f"Invalid {field_name} '{value}' for "
                f"{self.ground_truth_id}. The value must be finite."
            )

        if value < minimum:
            raise ValueError(
                f"Invalid {field_name} '{value}' for "
                f"{self.ground_truth_id}. The value must be at least "
                f"{minimum}."
            )

        if maximum is not None and value > maximum:
            raise ValueError(
                f"Invalid {field_name} '{value}' for "
                f"{self.ground_truth_id}. The value must not exceed "
                f"{maximum}."
            )

    @property
    def duration_seconds(self) -> float:
        """Return the total event duration in seconds."""
        elapsed = self.ended_at - self.started_at
        return round(elapsed.total_seconds(), 3)

    @property
    def is_equipment_specific(self) -> bool:
        """Return whether the event targets a specific equipment asset."""
        return self.equipment_id is not None

    @property
    def is_critical(self) -> bool:
        """Return whether the event has critical severity."""
        return self.severity is GroundTruthSeverity.CRITICAL

    def to_record(self) -> dict[str, Any]:
        """Return a serialization-ready ground-truth event record."""
        record = asdict(self)
        record["event_type"] = self.event_type.value
        record["severity"] = self.severity.value
        record["started_at"] = self.started_at.isoformat()
        record["ended_at"] = self.ended_at.isoformat()
        record["duration_seconds"] = self.duration_seconds
        record["is_equipment_specific"] = self.is_equipment_specific
        record["is_critical"] = self.is_critical
        return record
