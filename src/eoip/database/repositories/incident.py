"""Incident repository for EOIP."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from eoip.database.models.incident import IncidentORM
from eoip.database.repositories.base import BaseRepository


class IncidentRepository(BaseRepository[IncidentORM]):
    """Repository for incident persistence and operational queries."""

    def __init__(self, session: Session) -> None:
        """Initialize the incident repository."""
        super().__init__(
            session=session,
            model=IncidentORM,
        )

    def get_by_plant(
        self,
        plant_id: str,
    ) -> Sequence[IncidentORM]:
        """Return incidents belonging to a plant."""
        statement = (
            select(IncidentORM)
            .where(IncidentORM.plant_id == plant_id)
            .order_by(IncidentORM.occurred_at.desc())
        )

        return self.session.scalars(statement).all()

    def get_by_equipment(
        self,
        equipment_id: str,
    ) -> Sequence[IncidentORM]:
        """Return incidents belonging to equipment."""
        statement = (
            select(IncidentORM)
            .where(IncidentORM.equipment_id == equipment_id)
            .order_by(IncidentORM.occurred_at.desc())
        )

        return self.session.scalars(statement).all()

    def get_by_status(
        self,
        status: str,
    ) -> Sequence[IncidentORM]:
        """Return incidents matching a status."""
        statement = (
            select(IncidentORM)
            .where(IncidentORM.status == status)
            .order_by(IncidentORM.occurred_at.desc())
        )

        return self.session.scalars(statement).all()

    def get_by_severity(
        self,
        severity: str,
    ) -> Sequence[IncidentORM]:
        """Return incidents matching a severity."""
        statement = (
            select(IncidentORM)
            .where(IncidentORM.severity == severity)
            .order_by(IncidentORM.occurred_at.desc())
        )

        return self.session.scalars(statement).all()

    def get_open(
        self,
    ) -> Sequence[IncidentORM]:
        """Return unresolved incidents."""
        statement = (
            select(IncidentORM)
            .where(IncidentORM.resolved_at.is_(None))
            .order_by(IncidentORM.occurred_at.desc())
        )

        return self.session.scalars(statement).all()

    def get_open_by_plant(
        self,
        plant_id: str,
    ) -> Sequence[IncidentORM]:
        """Return unresolved incidents for a plant."""
        statement = (
            select(IncidentORM)
            .where(
                IncidentORM.plant_id == plant_id,
                IncidentORM.resolved_at.is_(None),
            )
            .order_by(IncidentORM.occurred_at.desc())
        )

        return self.session.scalars(statement).all()

    def get_by_linked_alarm(
        self,
        alarm_id: str,
    ) -> Sequence[IncidentORM]:
        """Return incidents linked to an alarm."""
        statement = (
            select(IncidentORM)
            .where(IncidentORM.linked_alarm_id == alarm_id)
            .order_by(IncidentORM.occurred_at.desc())
        )

        return self.session.scalars(statement).all()

    def get_occurred_between(
        self,
        start_at: datetime,
        end_at: datetime,
    ) -> Sequence[IncidentORM]:
        """Return incidents occurring within a time interval."""
        statement = (
            select(IncidentORM)
            .where(
                IncidentORM.occurred_at >= start_at,
                IncidentORM.occurred_at < end_at,
            )
            .order_by(IncidentORM.occurred_at)
        )

        return self.session.scalars(statement).all()
