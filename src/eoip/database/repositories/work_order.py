"""Work order repository for EOIP."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from eoip.database.models.work_order import WorkOrderORM
from eoip.database.repositories.base import BaseRepository


class WorkOrderRepository(BaseRepository[WorkOrderORM]):
    """Repository for work order persistence and operational queries."""

    def __init__(self, session: Session) -> None:
        """Initialize the work order repository."""
        super().__init__(
            session=session,
            model=WorkOrderORM,
        )

    def get_by_plant(
        self,
        plant_id: str,
    ) -> Sequence[WorkOrderORM]:
        """Return work orders belonging to a plant."""
        statement = (
            select(WorkOrderORM)
            .where(WorkOrderORM.plant_id == plant_id)
            .order_by(WorkOrderORM.created_at.desc())
        )

        return self.session.scalars(statement).all()

    def get_by_equipment(
        self,
        equipment_id: str,
    ) -> Sequence[WorkOrderORM]:
        """Return work orders belonging to equipment."""
        statement = (
            select(WorkOrderORM)
            .where(WorkOrderORM.equipment_id == equipment_id)
            .order_by(WorkOrderORM.created_at.desc())
        )

        return self.session.scalars(statement).all()

    def get_by_status(
        self,
        status: str,
    ) -> Sequence[WorkOrderORM]:
        """Return work orders matching a status."""
        statement = (
            select(WorkOrderORM)
            .where(WorkOrderORM.status == status)
            .order_by(WorkOrderORM.created_at.desc())
        )

        return self.session.scalars(statement).all()

    def get_by_priority(
        self,
        priority: str,
    ) -> Sequence[WorkOrderORM]:
        """Return work orders matching a priority."""
        statement = (
            select(WorkOrderORM)
            .where(WorkOrderORM.priority == priority)
            .order_by(WorkOrderORM.created_at.desc())
        )

        return self.session.scalars(statement).all()

    def get_by_type(
        self,
        work_order_type: str,
    ) -> Sequence[WorkOrderORM]:
        """Return work orders matching a work order type."""
        statement = (
            select(WorkOrderORM)
            .where(WorkOrderORM.work_order_type == work_order_type)
            .order_by(WorkOrderORM.created_at.desc())
        )

        return self.session.scalars(statement).all()

    def get_by_linked_incident(
        self,
        incident_id: str,
    ) -> Sequence[WorkOrderORM]:
        """Return work orders linked to an incident."""
        statement = (
            select(WorkOrderORM)
            .where(WorkOrderORM.linked_incident_id == incident_id)
            .order_by(WorkOrderORM.created_at.desc())
        )

        return self.session.scalars(statement).all()

    def get_open(
        self,
    ) -> Sequence[WorkOrderORM]:
        """Return work orders that are not completed or cancelled."""
        statement = (
            select(WorkOrderORM)
            .where(WorkOrderORM.status.notin_(("completed", "cancelled")))
            .order_by(WorkOrderORM.created_at.desc())
        )

        return self.session.scalars(statement).all()

    def get_scheduled_between(
        self,
        start_at: datetime,
        end_at: datetime,
    ) -> Sequence[WorkOrderORM]:
        """Return work orders scheduled within a time interval."""
        statement = (
            select(WorkOrderORM)
            .where(
                WorkOrderORM.scheduled_at.is_not(None),
                WorkOrderORM.scheduled_at >= start_at,
                WorkOrderORM.scheduled_at < end_at,
            )
            .order_by(WorkOrderORM.scheduled_at)
        )

        return self.session.scalars(statement).all()
