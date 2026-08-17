"""Unit tests for the EOIP incident service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from eoip.database.models.incident import IncidentORM
from eoip.database.services.incident import IncidentService


def _mock_session() -> MagicMock:
    """Return a Session-compatible mock."""
    return MagicMock(spec=Session)


def _incident() -> MagicMock:
    """Return an IncidentORM-compatible mock."""
    incident = MagicMock(spec=IncidentORM)
    incident.incident_id = "INCIDENT1"
    incident.plant_id = "PLANT001"
    incident.equipment_id = "INV000001"
    incident.status = "open"
    incident.root_cause = None
    incident.description = "Test incident"
    incident.occurred_at = datetime(
        2026,
        8,
        17,
        10,
        0,
        tzinfo=UTC,
    )
    incident.resolved_at = None
    return incident


class TestIncidentServiceConstruction:
    """Tests for incident service construction."""

    def test_service_exposes_session_and_repository(self) -> None:
        session = _mock_session()

        service = IncidentService(session)

        assert service.session is session
        assert service.repository.session is session
        assert service.repository.model is IncidentORM


class TestIncidentServiceCreate:
    """Tests for incident creation."""

    def test_create_adds_new_incident(self) -> None:
        session = _mock_session()
        incident = _incident()

        service = IncidentService(session)
        service.repository.exists = MagicMock(return_value=False)
        service.repository.add = MagicMock(return_value=incident)

        result = service.create(incident)

        assert result is incident
        service.repository.exists.assert_called_once_with("INCIDENT1")
        service.repository.add.assert_called_once_with(incident)

    def test_create_rejects_duplicate_incident(self) -> None:
        session = _mock_session()
        incident = _incident()

        service = IncidentService(session)
        service.repository.exists = MagicMock(return_value=True)
        service.repository.add = MagicMock()

        with pytest.raises(
            ValueError,
            match="Incident already exists: INCIDENT1",
        ):
            service.create(incident)

        service.repository.exists.assert_called_once_with("INCIDENT1")
        service.repository.add.assert_not_called()


class TestIncidentServiceGet:
    """Tests for incident retrieval."""

    def test_get_returns_incident(self) -> None:
        session = _mock_session()
        incident = _incident()

        service = IncidentService(session)
        service.repository.get = MagicMock(return_value=incident)

        result = service.get("INCIDENT1")

        assert result is incident
        service.repository.get.assert_called_once_with("INCIDENT1")

    def test_get_returns_none_when_missing(self) -> None:
        session = _mock_session()

        service = IncidentService(session)
        service.repository.get = MagicMock(return_value=None)

        result = service.get("INCIDENT1")

        assert result is None

    def test_get_required_returns_incident(self) -> None:
        session = _mock_session()
        incident = _incident()

        service = IncidentService(session)
        service.repository.get = MagicMock(return_value=incident)

        result = service.get_required("INCIDENT1")

        assert result is incident

    def test_get_required_raises_when_missing(self) -> None:
        session = _mock_session()

        service = IncidentService(session)
        service.repository.get = MagicMock(return_value=None)

        with pytest.raises(
            LookupError,
            match="Incident does not exist: INCIDENT1",
        ):
            service.get_required("INCIDENT1")


class TestIncidentServiceUpdateStatus:
    """Tests for incident status updates."""

    def test_update_status_changes_status(self) -> None:
        session = _mock_session()
        incident = _incident()

        service = IncidentService(session)
        service.get_required = MagicMock(return_value=incident)

        result = service.update_status(
            "INCIDENT1",
            status="investigating",
        )

        assert result is incident
        assert incident.status == "investigating"

        service.get_required.assert_called_once_with("INCIDENT1")
        session.flush.assert_called_once_with()


class TestIncidentServiceResolve:
    """Tests for incident resolution."""

    def test_resolve_updates_incident(self) -> None:
        session = _mock_session()
        incident = _incident()

        service = IncidentService(session)
        service.get_required = MagicMock(return_value=incident)

        resolved_at = datetime(
            2026,
            8,
            17,
            12,
            0,
            tzinfo=UTC,
        )

        result = service.resolve(
            "INCIDENT1",
            resolved_at=resolved_at,
            root_cause="Communication failure",
        )

        assert result is incident
        assert incident.resolved_at == resolved_at
        assert incident.status == "resolved"
        assert incident.root_cause == "Communication failure"

        session.flush.assert_called_once_with()

    def test_resolve_rejects_time_before_occurrence(self) -> None:
        session = _mock_session()
        incident = _incident()

        service = IncidentService(session)
        service.get_required = MagicMock(return_value=incident)

        with pytest.raises(
            ValueError,
            match="resolved_at cannot be earlier than occurred_at",
        ):
            service.resolve(
                "INCIDENT1",
                resolved_at=datetime(
                    2026,
                    8,
                    17,
                    9,
                    0,
                    tzinfo=UTC,
                ),
            )

        session.flush.assert_not_called()


class TestIncidentServiceUpdates:
    """Tests for incident field updates."""

    def test_update_root_cause_changes_root_cause(self) -> None:
        session = _mock_session()
        incident = _incident()

        service = IncidentService(session)
        service.get_required = MagicMock(return_value=incident)

        result = service.update_root_cause(
            "INCIDENT1",
            root_cause="Grid disturbance",
        )

        assert result is incident
        assert incident.root_cause == "Grid disturbance"

        session.flush.assert_called_once_with()

    def test_update_description_changes_description(self) -> None:
        session = _mock_session()
        incident = _incident()

        service = IncidentService(session)
        service.get_required = MagicMock(return_value=incident)

        result = service.update_description(
            "INCIDENT1",
            description="Updated incident description",
        )

        assert result is incident
        assert incident.description == "Updated incident description"

        session.flush.assert_called_once_with()


class TestIncidentServiceDelete:
    """Tests for incident deletion."""

    def test_delete_removes_existing_incident(self) -> None:
        session = _mock_session()
        incident = _incident()

        service = IncidentService(session)
        service.get_required = MagicMock(return_value=incident)
        service.repository.delete = MagicMock()

        result = service.delete("INCIDENT1")

        assert result is None
        service.repository.delete.assert_called_once_with(incident)


class TestIncidentServiceListing:
    """Tests for incident listing helpers."""

    def test_list_all_returns_incidents(self) -> None:
        session = _mock_session()
        incident_one = _incident()
        incident_two = _incident()

        service = IncidentService(session)
        service.repository.get_all = MagicMock(
            return_value=(incident_one, incident_two)
        )

        result = service.list_all()

        assert result == [incident_one, incident_two]

    def test_list_by_plant_returns_matching_incidents(self) -> None:
        session = _mock_session()
        incident = _incident()

        service = IncidentService(session)
        service.repository.get_by_plant = MagicMock(return_value=(incident,))

        result = service.list_by_plant("PLANT001")

        assert result == [incident]
        service.repository.get_by_plant.assert_called_once_with("PLANT001")

    def test_list_by_equipment_returns_matching_incidents(self) -> None:
        session = _mock_session()
        incident = _incident()

        service = IncidentService(session)
        service.repository.get_by_equipment = MagicMock(return_value=(incident,))

        result = service.list_by_equipment("INV000001")

        assert result == [incident]
        service.repository.get_by_equipment.assert_called_once_with("INV000001")

    def test_list_open_returns_open_incidents(self) -> None:
        session = _mock_session()
        incident = _incident()

        service = IncidentService(session)
        service.repository.get_open = MagicMock(return_value=(incident,))

        result = service.list_open()

        assert result == [incident]
        service.repository.get_open.assert_called_once_with()

    def test_list_open_by_plant_returns_matching_incidents(self) -> None:
        session = _mock_session()
        incident = _incident()

        service = IncidentService(session)
        service.repository.get_open_by_plant = MagicMock(return_value=(incident,))

        result = service.list_open_by_plant("PLANT001")

        assert result == [incident]
        service.repository.get_open_by_plant.assert_called_once_with("PLANT001")

    def test_list_by_linked_alarm_returns_matching_incidents(self) -> None:
        session = _mock_session()
        incident = _incident()

        service = IncidentService(session)
        service.repository.get_by_linked_alarm = MagicMock(return_value=(incident,))

        result = service.list_by_linked_alarm("ALARM001")

        assert result == [incident]
        service.repository.get_by_linked_alarm.assert_called_once_with("ALARM001")
