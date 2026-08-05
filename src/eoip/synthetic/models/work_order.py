"""
Maintenance work-order domain model for EOIP synthetic data generation.

This module defines the authoritative representation of a maintenance work
order associated with solar-plant equipment. Synthetic generators, maintenance
analytics, reliability calculations, ETL pipelines, and dashboards must use
this model instead of creating independent work-order dictionaries.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

_WORK_ORDER_ID_PATTERN = re.compile(r"^WO-\d{7}$")
_PLANT_ID_PATTERN = re.compile(r"^PLANT-\d{3}$")
_EQUIPMENT_ID_PATTERN = re.compile(r"^EQP-\d{5}$")
_INCIDENT_ID_PATTERN = re.compile(r"^INC-\d{7}$")


class WorkOrderType(StrEnum):
    """Supported maintenance work-order types."""

    CORRECTIVE = "corrective"
    PREVENTIVE = "preventive"
    PREDICTIVE = "predictive"
    INSPECTION = "inspection"
    EMERGENCY = "emergency"


class WorkOrderPriority(StrEnum):
    """Supported operational priorities for work orders."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkOrderStatus(StrEnum):
    """Supported lifecycle states for maintenance work orders."""

    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class WorkOrder:
    """Immutable maintenance work-order record for one plant asset."""

    work_order_id: str
    plant_id: str
    equipment_id: str
    work_order_name: str
    work_order_type: WorkOrderType
    priority: WorkOrderPriority
    created_at: datetime
    status: WorkOrderStatus = WorkOrderStatus.OPEN
    linked_incident_id: str | None = None
    assigned_team: str | None = None
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    estimated_labor_hours: float | None = None
    actual_labor_hours: float | None = None
    estimated_cost: float | None = None
    actual_cost: float | None = None
    description: str | None = None
    completion_notes: str | None = None
    is_synthetic_ground_truth: bool = False

    def __post_init__(self) -> None:
        """Normalize and validate the complete work-order record."""
        normalized_work_order_id = self.work_order_id.strip().upper()
        normalized_plant_id = self.plant_id.strip().upper()
        normalized_equipment_id = self.equipment_id.strip().upper()
        normalized_work_order_name = self.work_order_name.strip()
        normalized_linked_incident_id = (
            self.linked_incident_id.strip().upper()
            if self.linked_incident_id is not None
            else None
        )
        normalized_assigned_team = (
            self.assigned_team.strip() if self.assigned_team is not None else None
        )
        normalized_description = (
            self.description.strip() if self.description is not None else None
        )
        normalized_completion_notes = (
            self.completion_notes.strip() if self.completion_notes is not None else None
        )

        object.__setattr__(
            self,
            "work_order_id",
            normalized_work_order_id,
        )
        object.__setattr__(self, "plant_id", normalized_plant_id)
        object.__setattr__(self, "equipment_id", normalized_equipment_id)
        object.__setattr__(
            self,
            "work_order_name",
            normalized_work_order_name,
        )
        object.__setattr__(
            self,
            "linked_incident_id",
            normalized_linked_incident_id,
        )
        object.__setattr__(
            self,
            "assigned_team",
            normalized_assigned_team,
        )
        object.__setattr__(self, "description", normalized_description)
        object.__setattr__(
            self,
            "completion_notes",
            normalized_completion_notes,
        )

        self._validate_identifiers()
        self._validate_text_fields()
        self._validate_enums()
        self._validate_timestamps()
        self._validate_numeric_fields()
        self._validate_boolean_fields()
        self._validate_lifecycle_consistency()

    def _validate_identifiers(self) -> None:
        """Validate work-order, plant, equipment, and incident identifiers."""
        if not _WORK_ORDER_ID_PATTERN.fullmatch(self.work_order_id):
            raise ValueError(
                f"Invalid work_order_id '{self.work_order_id}'. "
                "Use the format 'WO-0000001'."
            )

        if not _PLANT_ID_PATTERN.fullmatch(self.plant_id):
            raise ValueError(
                f"Invalid plant_id '{self.plant_id}' for "
                f"{self.work_order_id}. Use the format 'PLANT-001'."
            )

        if not _EQUIPMENT_ID_PATTERN.fullmatch(self.equipment_id):
            raise ValueError(
                f"Invalid equipment_id '{self.equipment_id}' for "
                f"{self.work_order_id}. Use the format 'EQP-00001'."
            )

        if self.linked_incident_id is not None and not _INCIDENT_ID_PATTERN.fullmatch(
            self.linked_incident_id
        ):
            raise ValueError(
                f"Invalid linked_incident_id "
                f"'{self.linked_incident_id}' for {self.work_order_id}. "
                "Use the format 'INC-0000001' or None."
            )

    def _validate_text_fields(self) -> None:
        """Validate work-order name and optional descriptive fields."""
        if not self.work_order_name:
            raise ValueError(
                f"work_order_name cannot be empty for "
                f"{self.work_order_id}. Provide a descriptive name."
            )

        if len(self.work_order_name) > 150:
            raise ValueError(
                f"work_order_name for {self.work_order_id} contains "
                f"{len(self.work_order_name)} characters. "
                "Use no more than 150."
            )

        self._validate_optional_text(
            field_name="assigned_team",
            value=self.assigned_team,
            maximum_length=100,
        )
        self._validate_optional_text(
            field_name="description",
            value=self.description,
            maximum_length=1_000,
        )
        self._validate_optional_text(
            field_name="completion_notes",
            value=self.completion_notes,
            maximum_length=1_000,
        )

    def _validate_optional_text(
        self,
        field_name: str,
        value: str | None,
        maximum_length: int,
    ) -> None:
        """Validate an optional normalized text field."""
        if value is None:
            return

        if not value:
            raise ValueError(
                f"{field_name} cannot be empty for {self.work_order_id}. "
                f"Use None when no {field_name} is available."
            )

        if len(value) > maximum_length:
            raise ValueError(
                f"{field_name} for {self.work_order_id} contains "
                f"{len(value)} characters. Use no more than "
                f"{maximum_length}."
            )

    def _validate_enums(self) -> None:
        """Validate work-order type, priority, and lifecycle status."""
        if not isinstance(self.work_order_type, WorkOrderType):
            raise TypeError(
                f"Invalid work_order_type '{self.work_order_type}' for "
                f"{self.work_order_id}. Use a WorkOrderType value."
            )

        if not isinstance(self.priority, WorkOrderPriority):
            raise TypeError(
                f"Invalid priority '{self.priority}' for "
                f"{self.work_order_id}. Use a WorkOrderPriority value."
            )

        if not isinstance(self.status, WorkOrderStatus):
            raise TypeError(
                f"Invalid status '{self.status}' for "
                f"{self.work_order_id}. Use a WorkOrderStatus value."
            )

    def _validate_timestamps(self) -> None:
        """Validate work-order timestamps, timezone awareness, and ordering."""
        if not isinstance(self.created_at, datetime):
            raise TypeError(
                f"Invalid created_at '{self.created_at}' for "
                f"{self.work_order_id}. "
                "Use a timezone-aware datetime value."
            )

        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError(
                f"created_at '{self.created_at}' for "
                f"{self.work_order_id} is timezone-naive. "
                "Use a timezone-aware datetime, preferably UTC."
            )

        optional_timestamps: tuple[
            tuple[str, datetime | None],
            ...,
        ] = (
            ("scheduled_at", self.scheduled_at),
            ("started_at", self.started_at),
            ("completed_at", self.completed_at),
            ("cancelled_at", self.cancelled_at),
        )

        for field_name, value in optional_timestamps:
            if value is None:
                continue

            if not isinstance(value, datetime):
                raise TypeError(
                    f"Invalid {field_name} '{value}' for "
                    f"{self.work_order_id}. "
                    "Use a timezone-aware datetime value or None."
                )

            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(
                    f"{field_name} '{value}' for "
                    f"{self.work_order_id} is timezone-naive. "
                    "Use a timezone-aware datetime, preferably UTC."
                )

            if value < self.created_at:
                raise ValueError(
                    f"{field_name} '{value.isoformat()}' for "
                    f"{self.work_order_id} occurs before created_at "
                    f"'{self.created_at.isoformat()}'."
                )

        if (
            self.scheduled_at is not None
            and self.started_at is not None
            and self.started_at < self.scheduled_at
        ):
            raise ValueError(
                f"started_at '{self.started_at.isoformat()}' for "
                f"{self.work_order_id} occurs before scheduled_at "
                f"'{self.scheduled_at.isoformat()}'."
            )

        if (
            self.started_at is not None
            and self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            raise ValueError(
                f"completed_at '{self.completed_at.isoformat()}' for "
                f"{self.work_order_id} occurs before started_at "
                f"'{self.started_at.isoformat()}'."
            )

    def _validate_numeric_fields(self) -> None:
        """Validate labor-hour and cost values."""
        numeric_fields: tuple[
            tuple[str, float | None],
            ...,
        ] = (
            ("estimated_labor_hours", self.estimated_labor_hours),
            ("actual_labor_hours", self.actual_labor_hours),
            ("estimated_cost", self.estimated_cost),
            ("actual_cost", self.actual_cost),
        )

        for field_name, value in numeric_fields:
            if value is None:
                continue

            if isinstance(value, bool) or not isinstance(
                value,
                (int, float),
            ):
                raise TypeError(
                    f"Invalid {field_name} '{value}' for "
                    f"{self.work_order_id}. "
                    "Use a non-negative finite numeric value or None."
                )

            if not math.isfinite(value):
                raise ValueError(
                    f"Invalid {field_name} '{value}' for "
                    f"{self.work_order_id}. "
                    "The value must be finite."
                )

            if value < 0:
                raise ValueError(
                    f"Invalid {field_name} '{value}' for "
                    f"{self.work_order_id}. "
                    "The value must be greater than or equal to zero."
                )

    def _validate_boolean_fields(self) -> None:
        """Validate the synthetic ground-truth indicator."""
        if not isinstance(self.is_synthetic_ground_truth, bool):
            raise TypeError(
                f"Invalid is_synthetic_ground_truth value "
                f"'{self.is_synthetic_ground_truth}' for "
                f"{self.work_order_id}. Use True or False."
            )

    def _validate_lifecycle_consistency(self) -> None:
        """Validate consistency between work-order status and lifecycle data."""
        if self.status is WorkOrderStatus.OPEN:
            if self.started_at is not None:
                raise ValueError(
                    f"Work order {self.work_order_id} has status 'open' "
                    "but also has started_at."
                )

            if self.completed_at is not None:
                raise ValueError(
                    f"Work order {self.work_order_id} has status 'open' "
                    "but also has completed_at."
                )

            if self.cancelled_at is not None:
                raise ValueError(
                    f"Work order {self.work_order_id} has status 'open' "
                    "but also has cancelled_at."
                )

        if self.status is WorkOrderStatus.ASSIGNED:
            if self.assigned_team is None:
                raise ValueError(
                    f"Work order {self.work_order_id} has status "
                    "'assigned' but assigned_team is missing."
                )

            if self.started_at is not None:
                raise ValueError(
                    f"Work order {self.work_order_id} has status "
                    "'assigned' but also has started_at."
                )

        if self.status is WorkOrderStatus.IN_PROGRESS:
            if self.assigned_team is None:
                raise ValueError(
                    f"Work order {self.work_order_id} has status "
                    "'in_progress' but assigned_team is missing."
                )

            if self.started_at is None:
                raise ValueError(
                    f"Work order {self.work_order_id} has status "
                    "'in_progress' but started_at is missing."
                )

            if self.completed_at is not None:
                raise ValueError(
                    f"Work order {self.work_order_id} has status "
                    "'in_progress' but also has completed_at."
                )

            if self.cancelled_at is not None:
                raise ValueError(
                    f"Work order {self.work_order_id} has status "
                    "'in_progress' but also has cancelled_at."
                )

        if self.status is WorkOrderStatus.COMPLETED:
            if self.started_at is None:
                raise ValueError(
                    f"Work order {self.work_order_id} has status "
                    "'completed' but started_at is missing."
                )

            if self.completed_at is None:
                raise ValueError(
                    f"Work order {self.work_order_id} has status "
                    "'completed' but completed_at is missing."
                )

            if self.cancelled_at is not None:
                raise ValueError(
                    f"Work order {self.work_order_id} has status "
                    "'completed' but also has cancelled_at."
                )

        if self.status is WorkOrderStatus.CANCELLED:
            if self.cancelled_at is None:
                raise ValueError(
                    f"Work order {self.work_order_id} has status "
                    "'cancelled' but cancelled_at is missing."
                )

            if self.completed_at is not None:
                raise ValueError(
                    f"Work order {self.work_order_id} has status "
                    "'cancelled' but also has completed_at."
                )

    @property
    def is_open(self) -> bool:
        """Return whether the work order still requires operational action."""
        return self.status in {
            WorkOrderStatus.OPEN,
            WorkOrderStatus.ASSIGNED,
            WorkOrderStatus.IN_PROGRESS,
        }

    @property
    def is_over_budget(self) -> bool | None:
        """Return whether actual cost exceeds estimated cost."""
        if self.estimated_cost is None or self.actual_cost is None:
            return None

        return self.actual_cost > self.estimated_cost

    @property
    def labor_variance_hours(self) -> float | None:
        """Return actual labor hours minus estimated labor hours."""
        if self.estimated_labor_hours is None or self.actual_labor_hours is None:
            return None

        return round(
            self.actual_labor_hours - self.estimated_labor_hours,
            3,
        )

    @property
    def cost_variance(self) -> float | None:
        """Return actual cost minus estimated cost."""
        if self.estimated_cost is None or self.actual_cost is None:
            return None

        return round(self.actual_cost - self.estimated_cost, 2)

    @property
    def completion_seconds(self) -> float | None:
        """Return elapsed seconds from work start to completion."""
        if self.started_at is None or self.completed_at is None:
            return None

        elapsed = self.completed_at - self.started_at
        return round(elapsed.total_seconds(), 3)

    def to_record(self) -> dict[str, Any]:
        """Return a serialization-ready maintenance work-order record."""
        record = asdict(self)
        record["work_order_type"] = self.work_order_type.value
        record["priority"] = self.priority.value
        record["status"] = self.status.value
        record["created_at"] = self.created_at.isoformat()
        record["scheduled_at"] = self._serialize_timestamp(self.scheduled_at)
        record["started_at"] = self._serialize_timestamp(self.started_at)
        record["completed_at"] = self._serialize_timestamp(self.completed_at)
        record["cancelled_at"] = self._serialize_timestamp(self.cancelled_at)
        record["is_open"] = self.is_open
        record["is_over_budget"] = self.is_over_budget
        record["labor_variance_hours"] = self.labor_variance_hours
        record["cost_variance"] = self.cost_variance
        record["completion_seconds"] = self.completion_seconds
        return record

    @staticmethod
    def _serialize_timestamp(value: datetime | None) -> str | None:
        """Serialize an optional timestamp as ISO 8601 text."""
        return value.isoformat() if value is not None else None
