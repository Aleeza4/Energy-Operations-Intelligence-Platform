"""Unit tests for the EOIP incident repository."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from eoip.database.models.incident import IncidentORM
from eoip.database.repositories.incident import IncidentRepository


def _mock_session() -> MagicMock:
    """Return a Session-compatible mock."""
    return MagicMock(spec=Session)


def _scalar_result(*entities: IncidentORM) -> MagicMock:
    """Return a mocked SQLAlchemy scalar result."""
    result = MagicMock()
    result.all.return_value = list(entities)
    return result


class TestIncidentRepositoryConstruction:
    """Tests for incident repository construction."""

    def test_repository_uses_incident_model(self) -> None:
        session = _mock_session()

        repository = IncidentRepository(session)

        assert repository.session is session
        assert repository.model is IncidentORM


class TestIncidentRepositoryByPlant:
    """Tests for plant-based incident queries."""

    def test_get_by_plant_returns_matching_incidents(self) -> None:
        session = _mock_session()

        incident_one = MagicMock(spec=IncidentORM)
        incident_two = MagicMock(spec=IncidentORM)

        session.scalars.return_value = _scalar_result(
            incident_one,
            incident_two,
        )

        repository = IncidentRepository(session)

        result = repository.get_by_plant("PLANT001")

        assert result == [
            incident_one,
            incident_two,
        ]

        session.scalars.assert_called_once()


class TestIncidentRepositoryByEquipment:
    """Tests for equipment-based incident queries."""

    def test_get_by_equipment_returns_matching_incidents(self) -> None:
        session = _mock_session()

        incident = MagicMock(spec=IncidentORM)

        session.scalars.return_value = _scalar_result(incident)

        repository = IncidentRepository(session)

        result = repository.get_by_equipment("INV000001")

        assert result == [incident]

        session.scalars.assert_called_once()


class TestIncidentRepositoryByStatus:
    """Tests for status-based incident queries."""

    def test_get_by_status_returns_matching_incidents(self) -> None:
        session = _mock_session()

        incident = MagicMock(spec=IncidentORM)

        session.scalars.return_value = _scalar_result(incident)

        repository = IncidentRepository(session)

        result = repository.get_by_status("open")

        assert result == [incident]

        session.scalars.assert_called_once()


class TestIncidentRepositoryBySeverity:
    """Tests for severity-based incident queries."""

    def test_get_by_severity_returns_matching_incidents(self) -> None:
        session = _mock_session()

        incident = MagicMock(spec=IncidentORM)

        session.scalars.return_value = _scalar_result(incident)

        repository = IncidentRepository(session)

        result = repository.get_by_severity("critical")

        assert result == [incident]

        session.scalars.assert_called_once()


class TestIncidentRepositoryOpenQueries:
    """Tests for unresolved incident queries."""

    def test_get_open_returns_unresolved_incidents(self) -> None:
        session = _mock_session()

        incident_one = MagicMock(spec=IncidentORM)
        incident_two = MagicMock(spec=IncidentORM)

        session.scalars.return_value = _scalar_result(
            incident_one,
            incident_two,
        )

        repository = IncidentRepository(session)

        result = repository.get_open()

        assert result == [
            incident_one,
            incident_two,
        ]

        session.scalars.assert_called_once()

    def test_get_open_by_plant_returns_unresolved_incidents(
        self,
    ) -> None:
        session = _mock_session()

        incident = MagicMock(spec=IncidentORM)

        session.scalars.return_value = _scalar_result(incident)

        repository = IncidentRepository(session)

        result = repository.get_open_by_plant("PLANT001")

        assert result == [incident]

        session.scalars.assert_called_once()


class TestIncidentRepositoryAlarmLink:
    """Tests for linked-alarm incident queries."""

    def test_get_by_linked_alarm_returns_matching_incidents(
        self,
    ) -> None:
        session = _mock_session()

        incident = MagicMock(spec=IncidentORM)

        session.scalars.return_value = _scalar_result(incident)

        repository = IncidentRepository(session)

        result = repository.get_by_linked_alarm("ALARM001")

        assert result == [incident]

        session.scalars.assert_called_once()

    def test_get_by_linked_alarm_returns_empty_sequence(
        self,
    ) -> None:
        session = _mock_session()

        session.scalars.return_value = _scalar_result()

        repository = IncidentRepository(session)

        result = repository.get_by_linked_alarm("ALARM001")

        assert result == []


class TestIncidentRepositoryTimeRange:
    """Tests for incident time-range queries."""

    def test_get_occurred_between_returns_matching_incidents(
        self,
    ) -> None:
        session = _mock_session()

        incident_one = MagicMock(spec=IncidentORM)
        incident_two = MagicMock(spec=IncidentORM)

        session.scalars.return_value = _scalar_result(
            incident_one,
            incident_two,
        )

        repository = IncidentRepository(session)

        start_at = datetime(
            2026,
            8,
            1,
            tzinfo=UTC,
        )

        end_at = datetime(
            2026,
            8,
            2,
            tzinfo=UTC,
        )

        result = repository.get_occurred_between(
            start_at,
            end_at,
        )

        assert result == [
            incident_one,
            incident_two,
        ]

        session.scalars.assert_called_once()

    def test_get_occurred_between_returns_empty_sequence(
        self,
    ) -> None:
        session = _mock_session()

        session.scalars.return_value = _scalar_result()

        repository = IncidentRepository(session)

        result = repository.get_occurred_between(
            datetime(
                2026,
                8,
                1,
                tzinfo=UTC,
            ),
            datetime(
                2026,
                8,
                2,
                tzinfo=UTC,
            ),
        )

        assert result == []
