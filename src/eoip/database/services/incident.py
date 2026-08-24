"""Incident CRUD service for EOIP."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from eoip.database.models.incident import IncidentORM
from eoip.database.repositories.incident import IncidentRepository


class IncidentService:
    """Application service for incident CRUD operations."""

    def __init__(self, session: Session) -> None:
        """Initialize the incident service."""
        self.session = session
        self.repository = IncidentRepository(session)

    def create(
        self,
        incident: IncidentORM,
    ) -> IncidentORM:
        """Create an incident within the current transaction."""
        if self.repository.exists(incident.incident_id):
            raise ValueError(f"Incident already exists: {incident.incident_id}")

        return self.repository.add(incident)

    def get(
        self,
        incident_id: str,
    ) -> IncidentORM | None:
        """Return an incident by identifier."""
        return self.repository.get(incident_id)

    def get_required(
        self,
        incident_id: str,
    ) -> IncidentORM:
        """Return an incident or raise when it does not exist."""
        incident = self.repository.get(incident_id)

        if incident is None:
            raise LookupError(f"Incident does not exist: {incident_id}")

        return incident

    def update_status(
        self,
        incident_id: str,
        *,
        status: str,
    ) -> IncidentORM:
        """Update the incident status."""
        incident = self.get_required(incident_id)

        incident.status = status

        self.session.flush()

        return incident

    def resolve(
        self,
        incident_id: str,
        *,
        resolved_at: datetime,
        root_cause: str | None = None,
    ) -> IncidentORM:
        """Resolve an incident."""
        incident = self.get_required(incident_id)

        if resolved_at < incident.occurred_at:
            raise ValueError("resolved_at cannot be earlier than occurred_at.")

        incident.resolved_at = resolved_at
        incident.status = "resolved"

        if root_cause is not None:
            incident.root_cause = root_cause

        self.session.flush()

        return incident

    def update_root_cause(
        self,
        incident_id: str,
        *,
        root_cause: str,
    ) -> IncidentORM:
        """Update the incident root cause."""
        incident = self.get_required(incident_id)

        incident.root_cause = root_cause

        self.session.flush()

        return incident

    def update_description(
        self,
        incident_id: str,
        *,
        description: str,
    ) -> IncidentORM:
        """Update the incident description."""
        incident = self.get_required(incident_id)

        incident.description = description

        self.session.flush()

        return incident

    def delete(
        self,
        incident_id: str,
    ) -> None:
        """Delete an incident by identifier."""
        incident = self.get_required(incident_id)

        self.repository.delete(incident)

    def list_all(self) -> list[IncidentORM]:
        """Return all incidents."""
        return list(self.repository.get_all())

    def list_by_plant(
        self,
        plant_id: str,
    ) -> list[IncidentORM]:
        """Return incidents belonging to a plant."""
        return list(self.repository.get_by_plant(plant_id))

    def list_by_equipment(
        self,
        equipment_id: str,
    ) -> list[IncidentORM]:
        """Return incidents belonging to equipment."""
        return list(self.repository.get_by_equipment(equipment_id))

    def list_open(self) -> list[IncidentORM]:
        """Return unresolved incidents."""
        return list(self.repository.get_open())

    def list_open_by_plant(
        self,
        plant_id: str,
    ) -> list[IncidentORM]:
        """Return unresolved incidents for a plant."""
        return list(self.repository.get_open_by_plant(plant_id))

    def list_by_linked_alarm(
        self,
        alarm_id: str,
    ) -> list[IncidentORM]:
        """Return incidents linked to an alarm."""
        return list(self.repository.get_by_linked_alarm(alarm_id))
