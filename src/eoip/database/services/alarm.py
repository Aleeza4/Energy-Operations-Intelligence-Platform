"""Alarm CRUD service for EOIP."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from eoip.database.models.alarm import AlarmORM
from eoip.database.repositories.alarm import AlarmRepository


class AlarmService:
    """Application service for alarm CRUD operations."""

    def __init__(self, session: Session) -> None:
        """Initialize the alarm service."""
        self.session = session
        self.repository = AlarmRepository(session)

    def create(
        self,
        alarm: AlarmORM,
    ) -> AlarmORM:
        """Create an alarm within the current transaction."""
        if self.repository.exists(alarm.alarm_id):
            raise ValueError(f"Alarm already exists: {alarm.alarm_id}")

        return self.repository.add(alarm)

    def get(
        self,
        alarm_id: str,
    ) -> AlarmORM | None:
        """Return an alarm by identifier."""
        return self.repository.get(alarm_id)

    def get_required(
        self,
        alarm_id: str,
    ) -> AlarmORM:
        """Return an alarm or raise when it does not exist."""
        alarm = self.repository.get(alarm_id)

        if alarm is None:
            raise LookupError(f"Alarm does not exist: {alarm_id}")

        return alarm

    def acknowledge(
        self,
        alarm_id: str,
        *,
        acknowledged_at: datetime,
    ) -> AlarmORM:
        """Mark an alarm as acknowledged."""
        alarm = self.get_required(alarm_id)

        alarm.acknowledged_at = acknowledged_at
        alarm.status = "acknowledged"

        self.session.flush()

        return alarm

    def clear(
        self,
        alarm_id: str,
        *,
        cleared_at: datetime,
    ) -> AlarmORM:
        """Mark an alarm as cleared."""
        alarm = self.get_required(alarm_id)

        if alarm.acknowledged_at is not None and cleared_at < alarm.acknowledged_at:
            raise ValueError("cleared_at cannot be earlier than acknowledged_at.")

        alarm.cleared_at = cleared_at
        alarm.status = "cleared"

        self.session.flush()

        return alarm

    def update_message(
        self,
        alarm_id: str,
        *,
        message: str,
    ) -> AlarmORM:
        """Update the alarm message."""
        alarm = self.get_required(alarm_id)

        alarm.message = message

        self.session.flush()

        return alarm

    def delete(
        self,
        alarm_id: str,
    ) -> None:
        """Delete an alarm by identifier."""
        alarm = self.get_required(alarm_id)

        self.repository.delete(alarm)

    def list_all(self) -> list[AlarmORM]:
        """Return all alarms."""
        return list(self.repository.get_all())

    def list_by_plant(
        self,
        plant_id: str,
    ) -> list[AlarmORM]:
        """Return alarms belonging to a plant."""
        return list(self.repository.get_by_plant(plant_id))

    def list_by_equipment(
        self,
        equipment_id: str,
    ) -> list[AlarmORM]:
        """Return alarms belonging to equipment."""
        return list(self.repository.get_by_equipment(equipment_id))

    def list_open(self) -> list[AlarmORM]:
        """Return uncleared alarms."""
        return list(self.repository.get_open())

    def list_open_by_plant(
        self,
        plant_id: str,
    ) -> list[AlarmORM]:
        """Return uncleared alarms for a plant."""
        return list(self.repository.get_open_by_plant(plant_id))
