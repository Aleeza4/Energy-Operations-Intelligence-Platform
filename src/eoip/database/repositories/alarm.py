"""Alarm repository for EOIP."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from eoip.database.models.alarm import AlarmORM
from eoip.database.repositories.base import BaseRepository


class AlarmRepository(BaseRepository[AlarmORM]):
    """Repository for alarm persistence and operational queries."""

    def __init__(self, session: Session) -> None:
        """Initialize the alarm repository."""
        super().__init__(
            session=session,
            model=AlarmORM,
        )

    def get_by_plant(
        self,
        plant_id: str,
    ) -> Sequence[AlarmORM]:
        """Return alarms belonging to a plant."""
        statement = (
            select(AlarmORM)
            .where(AlarmORM.plant_id == plant_id)
            .order_by(AlarmORM.raised_at.desc())
        )

        return self.session.scalars(statement).all()

    def get_by_equipment(
        self,
        equipment_id: str,
    ) -> Sequence[AlarmORM]:
        """Return alarms belonging to equipment."""
        statement = (
            select(AlarmORM)
            .where(AlarmORM.equipment_id == equipment_id)
            .order_by(AlarmORM.raised_at.desc())
        )

        return self.session.scalars(statement).all()

    def get_by_status(
        self,
        status: str,
    ) -> Sequence[AlarmORM]:
        """Return alarms matching a status."""
        statement = (
            select(AlarmORM)
            .where(AlarmORM.status == status)
            .order_by(AlarmORM.raised_at.desc())
        )

        return self.session.scalars(statement).all()

    def get_by_severity(
        self,
        severity: str,
    ) -> Sequence[AlarmORM]:
        """Return alarms matching a severity."""
        statement = (
            select(AlarmORM)
            .where(AlarmORM.severity == severity)
            .order_by(AlarmORM.raised_at.desc())
        )

        return self.session.scalars(statement).all()

    def get_open(
        self,
    ) -> Sequence[AlarmORM]:
        """Return alarms that have not been cleared."""
        statement = (
            select(AlarmORM)
            .where(AlarmORM.cleared_at.is_(None))
            .order_by(AlarmORM.raised_at.desc())
        )

        return self.session.scalars(statement).all()

    def get_open_by_plant(
        self,
        plant_id: str,
    ) -> Sequence[AlarmORM]:
        """Return uncleared alarms for a plant."""
        statement = (
            select(AlarmORM)
            .where(
                AlarmORM.plant_id == plant_id,
                AlarmORM.cleared_at.is_(None),
            )
            .order_by(AlarmORM.raised_at.desc())
        )

        return self.session.scalars(statement).all()

    def get_raised_between(
        self,
        start_at: datetime,
        end_at: datetime,
    ) -> Sequence[AlarmORM]:
        """Return alarms raised within a time interval."""
        statement = (
            select(AlarmORM)
            .where(
                AlarmORM.raised_at >= start_at,
                AlarmORM.raised_at < end_at,
            )
            .order_by(AlarmORM.raised_at)
        )

        return self.session.scalars(statement).all()
