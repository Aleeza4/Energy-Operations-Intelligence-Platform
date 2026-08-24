"""
SQLAlchemy ORM model for EOIP maintenance work orders.

This model mirrors the authoritative synthetic WorkOrder domain model while
adding relational persistence, database constraints, indexes, audit timestamps,
and conversion helpers for PostgreSQL.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from eoip.database.base import Base
from eoip.database.models.equipment import EquipmentORM
from eoip.database.models.incident import IncidentORM
from eoip.database.models.plant import PlantORM
from eoip.synthetic.models.work_order import (
    WorkOrder,
    WorkOrderPriority,
    WorkOrderStatus,
    WorkOrderType,
)


class WorkOrderORM(Base):
    """PostgreSQL-backed maintenance work-order record."""

    __tablename__ = "work_orders"

    __table_args__ = (
        CheckConstraint(
            "work_order_type IN ("
            "'corrective', "
            "'preventive', "
            "'predictive', "
            "'inspection', "
            "'emergency'"
            ")",
            name="valid_work_order_type",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'critical')",
            name="valid_priority",
        ),
        CheckConstraint(
            "status IN ("
            "'open', "
            "'assigned', "
            "'in_progress', "
            "'completed', "
            "'cancelled'"
            ")",
            name="valid_status",
        ),
        CheckConstraint(
            "scheduled_at IS NULL OR scheduled_at >= created_at",
            name="scheduled_not_before_created",
        ),
        CheckConstraint(
            "started_at IS NULL OR started_at >= created_at",
            name="started_not_before_created",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= created_at",
            name="completed_not_before_created",
        ),
        CheckConstraint(
            "cancelled_at IS NULL OR cancelled_at >= created_at",
            name="cancelled_not_before_created",
        ),
        CheckConstraint(
            "started_at IS NULL "
            "OR scheduled_at IS NULL "
            "OR started_at >= scheduled_at",
            name="started_not_before_scheduled",
        ),
        CheckConstraint(
            "completed_at IS NULL "
            "OR started_at IS NULL "
            "OR completed_at >= started_at",
            name="completed_not_before_started",
        ),
        CheckConstraint(
            "estimated_labor_hours IS NULL " "OR estimated_labor_hours >= 0",
            name="estimated_labor_non_negative",
        ),
        CheckConstraint(
            "actual_labor_hours IS NULL OR actual_labor_hours >= 0",
            name="actual_labor_non_negative",
        ),
        CheckConstraint(
            "estimated_cost IS NULL OR estimated_cost >= 0",
            name="estimated_cost_non_negative",
        ),
        CheckConstraint(
            "actual_cost IS NULL OR actual_cost >= 0",
            name="actual_cost_non_negative",
        ),
        CheckConstraint(
            "NOT (status = 'open' AND started_at IS NOT NULL)",
            name="open_has_no_started_at",
        ),
        CheckConstraint(
            "NOT (status = 'open' AND completed_at IS NOT NULL)",
            name="open_has_no_completed_at",
        ),
        CheckConstraint(
            "NOT (status = 'open' AND cancelled_at IS NOT NULL)",
            name="open_has_no_cancelled_at",
        ),
        CheckConstraint(
            "NOT (status = 'assigned' AND assigned_team IS NULL)",
            name="assigned_has_team",
        ),
        CheckConstraint(
            "NOT (status = 'assigned' AND started_at IS NOT NULL)",
            name="assigned_has_no_started_at",
        ),
        CheckConstraint(
            "NOT (status = 'in_progress' AND assigned_team IS NULL)",
            name="in_progress_has_team",
        ),
        CheckConstraint(
            "NOT (status = 'in_progress' AND started_at IS NULL)",
            name="in_progress_has_started_at",
        ),
        CheckConstraint(
            "NOT (status = 'in_progress' AND completed_at IS NOT NULL)",
            name="in_progress_has_no_completed_at",
        ),
        CheckConstraint(
            "NOT (status = 'in_progress' AND cancelled_at IS NOT NULL)",
            name="in_progress_has_no_cancelled_at",
        ),
        CheckConstraint(
            "NOT (status = 'completed' AND started_at IS NULL)",
            name="completed_has_started_at",
        ),
        CheckConstraint(
            "NOT (status = 'completed' AND completed_at IS NULL)",
            name="completed_has_completed_at",
        ),
        CheckConstraint(
            "NOT (status = 'completed' AND cancelled_at IS NOT NULL)",
            name="completed_has_no_cancelled_at",
        ),
        CheckConstraint(
            "NOT (status = 'cancelled' AND cancelled_at IS NULL)",
            name="cancelled_has_cancelled_at",
        ),
        CheckConstraint(
            "NOT (status = 'cancelled' AND completed_at IS NOT NULL)",
            name="cancelled_has_no_completed_at",
        ),
        Index("ix_work_orders_plant_id", "plant_id"),
        Index("ix_work_orders_equipment_id", "equipment_id"),
        Index("ix_work_orders_linked_incident_id", "linked_incident_id"),
        Index("ix_work_orders_work_order_type", "work_order_type"),
        Index("ix_work_orders_priority", "priority"),
        Index("ix_work_orders_status", "status"),
        Index("ix_work_orders_created_at", "created_at"),
        Index("ix_work_orders_scheduled_at", "scheduled_at"),
        Index(
            "ix_work_orders_plant_equipment_created_at",
            "plant_id",
            "equipment_id",
            "created_at",
        ),
    )

    work_order_id: Mapped[str] = mapped_column(
        String(10),
        primary_key=True,
        nullable=False,
    )
    plant_id: Mapped[str] = mapped_column(
        String(9),
        ForeignKey(
            "plants.plant_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    equipment_id: Mapped[str] = mapped_column(
        String(9),
        ForeignKey(
            "equipment.equipment_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    work_order_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    work_order_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=WorkOrderStatus.OPEN.value,
        server_default=WorkOrderStatus.OPEN.value,
    )
    linked_incident_id: Mapped[str | None] = mapped_column(
        String(11),
        ForeignKey(
            "incidents.incident_id",
            onupdate="CASCADE",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    assigned_team: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    estimated_labor_hours: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    actual_labor_hours: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    estimated_cost: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    actual_cost: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        String(1_000),
        nullable=True,
    )
    completion_notes: Mapped[str | None] = mapped_column(
        String(1_000),
        nullable=True,
    )
    is_synthetic_ground_truth: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    inserted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    plant: Mapped[PlantORM] = relationship(
        PlantORM,
        lazy="selectin",
    )
    equipment: Mapped[EquipmentORM] = relationship(
        EquipmentORM,
        lazy="selectin",
    )
    linked_incident: Mapped[IncidentORM | None] = relationship(
        IncidentORM,
        lazy="selectin",
    )

    @property
    def is_open(self) -> bool:
        """Return whether the work order still requires action."""
        return self.status in {
            WorkOrderStatus.OPEN.value,
            WorkOrderStatus.ASSIGNED.value,
            WorkOrderStatus.IN_PROGRESS.value,
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

    def to_domain(self) -> WorkOrder:
        """Convert this ORM record to the authoritative WorkOrder model."""
        return WorkOrder(
            work_order_id=self.work_order_id,
            plant_id=self.plant_id,
            equipment_id=self.equipment_id,
            work_order_name=self.work_order_name,
            work_order_type=WorkOrderType(self.work_order_type),
            priority=WorkOrderPriority(self.priority),
            created_at=self.created_at,
            status=WorkOrderStatus(self.status),
            linked_incident_id=self.linked_incident_id,
            assigned_team=self.assigned_team,
            scheduled_at=self.scheduled_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            cancelled_at=self.cancelled_at,
            estimated_labor_hours=self.estimated_labor_hours,
            actual_labor_hours=self.actual_labor_hours,
            estimated_cost=self.estimated_cost,
            actual_cost=self.actual_cost,
            description=self.description,
            completion_notes=self.completion_notes,
            is_synthetic_ground_truth=self.is_synthetic_ground_truth,
        )

    @classmethod
    def from_domain(cls, work_order: WorkOrder) -> WorkOrderORM:
        """Create an ORM record from a WorkOrder domain model."""
        if not isinstance(work_order, WorkOrder):
            raise TypeError("work_order must be a WorkOrder instance.")

        return cls(
            work_order_id=work_order.work_order_id,
            plant_id=work_order.plant_id,
            equipment_id=work_order.equipment_id,
            work_order_name=work_order.work_order_name,
            work_order_type=work_order.work_order_type.value,
            priority=work_order.priority.value,
            created_at=work_order.created_at,
            status=work_order.status.value,
            linked_incident_id=work_order.linked_incident_id,
            assigned_team=work_order.assigned_team,
            scheduled_at=work_order.scheduled_at,
            started_at=work_order.started_at,
            completed_at=work_order.completed_at,
            cancelled_at=work_order.cancelled_at,
            estimated_labor_hours=work_order.estimated_labor_hours,
            actual_labor_hours=work_order.actual_labor_hours,
            estimated_cost=work_order.estimated_cost,
            actual_cost=work_order.actual_cost,
            description=work_order.description,
            completion_notes=work_order.completion_notes,
            is_synthetic_ground_truth=(work_order.is_synthetic_ground_truth),
        )

    def update_from_domain(self, work_order: WorkOrder) -> None:
        """Update mutable fields from a matching WorkOrder model."""
        if not isinstance(work_order, WorkOrder):
            raise TypeError("work_order must be a WorkOrder instance.")

        if work_order.work_order_id != self.work_order_id:
            raise ValueError(
                "Cannot update WorkOrderORM with a different work_order_id."
            )

        self.plant_id = work_order.plant_id
        self.equipment_id = work_order.equipment_id
        self.work_order_name = work_order.work_order_name
        self.work_order_type = work_order.work_order_type.value
        self.priority = work_order.priority.value
        self.created_at = work_order.created_at
        self.status = work_order.status.value
        self.linked_incident_id = work_order.linked_incident_id
        self.assigned_team = work_order.assigned_team
        self.scheduled_at = work_order.scheduled_at
        self.started_at = work_order.started_at
        self.completed_at = work_order.completed_at
        self.cancelled_at = work_order.cancelled_at
        self.estimated_labor_hours = work_order.estimated_labor_hours
        self.actual_labor_hours = work_order.actual_labor_hours
        self.estimated_cost = work_order.estimated_cost
        self.actual_cost = work_order.actual_cost
        self.description = work_order.description
        self.completion_notes = work_order.completion_notes
        self.is_synthetic_ground_truth = work_order.is_synthetic_ground_truth

    def to_record(self) -> dict[str, object]:
        """Return a serialization-ready database record."""
        return {
            "work_order_id": self.work_order_id,
            "plant_id": self.plant_id,
            "equipment_id": self.equipment_id,
            "work_order_name": self.work_order_name,
            "work_order_type": self.work_order_type,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "linked_incident_id": self.linked_incident_id,
            "assigned_team": self.assigned_team,
            "scheduled_at": self._serialize_timestamp(self.scheduled_at),
            "started_at": self._serialize_timestamp(self.started_at),
            "completed_at": self._serialize_timestamp(self.completed_at),
            "cancelled_at": self._serialize_timestamp(self.cancelled_at),
            "estimated_labor_hours": self.estimated_labor_hours,
            "actual_labor_hours": self.actual_labor_hours,
            "estimated_cost": self.estimated_cost,
            "actual_cost": self.actual_cost,
            "description": self.description,
            "completion_notes": self.completion_notes,
            "is_synthetic_ground_truth": self.is_synthetic_ground_truth,
            "is_open": self.is_open,
            "is_over_budget": self.is_over_budget,
            "labor_variance_hours": self.labor_variance_hours,
            "cost_variance": self.cost_variance,
            "completion_seconds": self.completion_seconds,
            "inserted_at": (
                self.inserted_at.isoformat() if self.inserted_at is not None else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at is not None else None
            ),
        }

    @staticmethod
    def _serialize_timestamp(value: datetime | None) -> str | None:
        """Serialize an optional timestamp as ISO 8601 text."""
        return value.isoformat() if value is not None else None

    def __repr__(self) -> str:
        """Return a concise developer representation."""
        return (
            "WorkOrderORM("
            f"work_order_id={self.work_order_id!r}, "
            f"equipment_id={self.equipment_id!r}, "
            f"priority={self.priority!r}, "
            f"status={self.status!r}"
            ")"
        )


__all__ = ["WorkOrderORM"]
