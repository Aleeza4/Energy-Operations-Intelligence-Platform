"""Unit tests for the EOIP alarm repository."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from eoip.database.models.alarm import AlarmORM
from eoip.database.repositories.alarm import AlarmRepository


def _mock_session() -> MagicMock:
    """Return a Session-compatible mock."""
    return MagicMock(spec=Session)


def _scalar_result(*entities: AlarmORM) -> MagicMock:
    """Return a mocked SQLAlchemy scalar result."""
    result = MagicMock()
    result.all.return_value = list(entities)
    return result


class TestAlarmRepositoryConstruction:
    """Tests for alarm repository construction."""

    def test_repository_uses_alarm_model(self) -> None:
        session = _mock_session()

        repository = AlarmRepository(session)

        assert repository.session is session
        assert repository.model is AlarmORM


class TestAlarmRepositoryByPlant:
    """Tests for plant-based alarm queries."""

    def test_get_by_plant_returns_matching_alarms(self) -> None:
        session = _mock_session()

        alarm_one = MagicMock(spec=AlarmORM)
        alarm_two = MagicMock(spec=AlarmORM)

        session.scalars.return_value = _scalar_result(
            alarm_one,
            alarm_two,
        )

        repository = AlarmRepository(session)

        result = repository.get_by_plant("PLANT001")

        assert result == [
            alarm_one,
            alarm_two,
        ]

        session.scalars.assert_called_once()


class TestAlarmRepositoryByEquipment:
    """Tests for equipment-based alarm queries."""

    def test_get_by_equipment_returns_matching_alarms(self) -> None:
        session = _mock_session()

        alarm = MagicMock(spec=AlarmORM)

        session.scalars.return_value = _scalar_result(alarm)

        repository = AlarmRepository(session)

        result = repository.get_by_equipment("INV000001")

        assert result == [alarm]

        session.scalars.assert_called_once()


class TestAlarmRepositoryByStatus:
    """Tests for status-based alarm queries."""

    def test_get_by_status_returns_matching_alarms(self) -> None:
        session = _mock_session()

        alarm = MagicMock(spec=AlarmORM)

        session.scalars.return_value = _scalar_result(alarm)

        repository = AlarmRepository(session)

        result = repository.get_by_status("active")

        assert result == [alarm]

        session.scalars.assert_called_once()


class TestAlarmRepositoryBySeverity:
    """Tests for severity-based alarm queries."""

    def test_get_by_severity_returns_matching_alarms(self) -> None:
        session = _mock_session()

        alarm = MagicMock(spec=AlarmORM)

        session.scalars.return_value = _scalar_result(alarm)

        repository = AlarmRepository(session)

        result = repository.get_by_severity("critical")

        assert result == [alarm]

        session.scalars.assert_called_once()


class TestAlarmRepositoryOpenQueries:
    """Tests for open alarm queries."""

    def test_get_open_returns_uncleared_alarms(self) -> None:
        session = _mock_session()

        alarm_one = MagicMock(spec=AlarmORM)
        alarm_two = MagicMock(spec=AlarmORM)

        session.scalars.return_value = _scalar_result(
            alarm_one,
            alarm_two,
        )

        repository = AlarmRepository(session)

        result = repository.get_open()

        assert result == [
            alarm_one,
            alarm_two,
        ]

        session.scalars.assert_called_once()

    def test_get_open_by_plant_returns_uncleared_plant_alarms(
        self,
    ) -> None:
        session = _mock_session()

        alarm = MagicMock(spec=AlarmORM)

        session.scalars.return_value = _scalar_result(alarm)

        repository = AlarmRepository(session)

        result = repository.get_open_by_plant("PLANT001")

        assert result == [alarm]

        session.scalars.assert_called_once()


class TestAlarmRepositoryTimeRange:
    """Tests for alarm time-range queries."""

    def test_get_raised_between_returns_matching_alarms(
        self,
    ) -> None:
        session = _mock_session()

        alarm_one = MagicMock(spec=AlarmORM)
        alarm_two = MagicMock(spec=AlarmORM)

        session.scalars.return_value = _scalar_result(
            alarm_one,
            alarm_two,
        )

        repository = AlarmRepository(session)

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

        result = repository.get_raised_between(
            start_at,
            end_at,
        )

        assert result == [
            alarm_one,
            alarm_two,
        ]

        session.scalars.assert_called_once()

    def test_get_raised_between_returns_empty_sequence(
        self,
    ) -> None:
        session = _mock_session()

        session.scalars.return_value = _scalar_result()

        repository = AlarmRepository(session)

        result = repository.get_raised_between(
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
