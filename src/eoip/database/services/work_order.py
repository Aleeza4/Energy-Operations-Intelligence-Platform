"""Work order CRUD service for EOIP."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from eoip.database.models.work_order import WorkOrderORM
from eoip.database.repositories.work_order import WorkOrderRepository


class WorkOrderService:
    """Application service for work order CRUD operations."""

    def __init__(self, session: Session) -> None:
        """Initialize the work order service."""
        self.session = session
        self.repository = WorkOrderRepository(session)

    def create(
        self,
        work_order: WorkOrderORM,
    ) -> WorkOrderORM:
        """Create a work order within the current transaction."""
        if self.repository.exists(work_order.work_order_id):
            raise ValueError(f"Work order already exists: {work_order.work_order_id}")

        return self.repository.add(work_order)

    def get(
        self,
        work_order_id: str,
    ) -> WorkOrderORM | None:
        """Return a work order by identifier."""
        return self.repository.get(work_order_id)

    def get_required(
        self,
        work_order_id: str,
    ) -> WorkOrderORM:
        """Return a work order or raise when it does not exist."""
        work_order = self.repository.get(work_order_id)

        if work_order is None:
            raise LookupError(f"Work order does not exist: {work_order_id}")

        return work_order

    def update_status(
        self,
        work_order_id: str,
        *,
        status: str,
    ) -> WorkOrderORM:
        """Update work order status."""
        work_order = self.get_required(work_order_id)

        work_order.status = status
        self.session.flush()

        return work_order

    def assign_team(
        self,
        work_order_id: str,
        *,
        assigned_team: str,
    ) -> WorkOrderORM:
        """Assign a team to a work order."""
        work_order = self.get_required(work_order_id)

        work_order.assigned_team = assigned_team
        self.session.flush()

        return work_order

    def schedule(
        self,
        work_order_id: str,
        *,
        scheduled_at: datetime,
    ) -> WorkOrderORM:
        """Schedule a work order."""
        work_order = self.get_required(work_order_id)

        work_order.scheduled_at = scheduled_at
        work_order.status = "scheduled"

        self.session.flush()

        return work_order

    def start(
        self,
        work_order_id: str,
        *,
        started_at: datetime,
    ) -> WorkOrderORM:
        """Mark a work order as started."""
        work_order = self.get_required(work_order_id)

        if work_order.scheduled_at is not None and started_at < work_order.scheduled_at:
            raise ValueError("started_at cannot be earlier than scheduled_at.")

        work_order.started_at = started_at
        work_order.status = "in_progress"

        self.session.flush()

        return work_order

    def complete(
        self,
        work_order_id: str,
        *,
        completed_at: datetime,
        actual_labor_hours: float | None = None,
        actual_cost: float | None = None,
        completion_notes: str | None = None,
    ) -> WorkOrderORM:
        """Mark a work order as completed."""
        work_order = self.get_required(work_order_id)

        if work_order.started_at is not None and completed_at < work_order.started_at:
            raise ValueError("completed_at cannot be earlier than started_at.")

        work_order.completed_at = completed_at
        work_order.status = "completed"

        if actual_labor_hours is not None:
            work_order.actual_labor_hours = actual_labor_hours

        if actual_cost is not None:
            work_order.actual_cost = actual_cost

        if completion_notes is not None:
            work_order.completion_notes = completion_notes

        self.session.flush()

        return work_order

    def cancel(
        self,
        work_order_id: str,
        *,
        cancelled_at: datetime,
    ) -> WorkOrderORM:
        """Cancel a work order."""
        work_order = self.get_required(work_order_id)

        work_order.cancelled_at = cancelled_at
        work_order.status = "cancelled"

        self.session.flush()

        return work_order

    def delete(
        self,
        work_order_id: str,
    ) -> None:
        """Delete a work order by identifier."""
        work_order = self.get_required(work_order_id)

        self.repository.delete(work_order)

    def list_all(self) -> list[WorkOrderORM]:
        """Return all work orders."""
        return list(self.repository.get_all())

    def list_by_plant(
        self,
        plant_id: str,
    ) -> list[WorkOrderORM]:
        """Return work orders belonging to a plant."""
        return list(self.repository.get_by_plant(plant_id))

    def list_by_equipment(
        self,
        equipment_id: str,
    ) -> list[WorkOrderORM]:
        """Return work orders belonging to equipment."""
        return list(self.repository.get_by_equipment(equipment_id))

    def list_open(self) -> list[WorkOrderORM]:
        """Return work orders not completed or cancelled."""
        return list(self.repository.get_open())

    def list_by_linked_incident(
        self,
        incident_id: str,
    ) -> list[WorkOrderORM]:
        """Return work orders linked to an incident."""
        return list(self.repository.get_by_linked_incident(incident_id))
