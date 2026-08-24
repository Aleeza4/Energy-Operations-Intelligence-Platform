"""Unit tests for the EOIP alarm service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from eoip.database.models.alarm import AlarmORM
from eoip.database.services.alarm import AlarmService


def _mock_session() -> MagicMock:
    """Return a Session-compatible mock."""
    return MagicMock(spec=Session)


def _alarm() -> MagicMock:
    """Return an AlarmORM-compatible mock."""
    alarm = MagicMock(spec=AlarmORM)
    alarm.alarm_id = "ALARM001"
    alarm.plant_id = "PLANT001"
    alarm.equipment_id = "INV000001"
    alarm.status = "active"
    alarm.message = "Test alarm"
    alarm.acknowledged_at = None
    alarm.cleared_at = None
    return alarm


class TestAlarmServiceConstruction:
    """Tests for alarm service construction."""

    def test_service_exposes_session_and_repository(self) -> None:
        session = _mock_session()

        service = AlarmService(session)

        assert service.session is session
        assert service.repository.session is session
        assert service.repository.model is AlarmORM


class TestAlarmServiceCreate:
    """Tests for alarm creation."""

    def test_create_adds_new_alarm(self) -> None:
        session = _mock_session()
        alarm = _alarm()

        service = AlarmService(session)
        service.repository.exists = MagicMock(return_value=False)
        service.repository.add = MagicMock(return_value=alarm)

        result = service.create(alarm)

        assert result is alarm
        service.repository.exists.assert_called_once_with("ALARM001")
        service.repository.add.assert_called_once_with(alarm)

    def test_create_rejects_duplicate_alarm(self) -> None:
        session = _mock_session()
        alarm = _alarm()

        service = AlarmService(session)
        service.repository.exists = MagicMock(return_value=True)
        service.repository.add = MagicMock()

        with pytest.raises(
            ValueError,
            match="Alarm already exists: ALARM001",
        ):
            service.create(alarm)

        service.repository.exists.assert_called_once_with("ALARM001")
        service.repository.add.assert_not_called()


class TestAlarmServiceGet:
    """Tests for alarm retrieval."""

    def test_get_returns_alarm(self) -> None:
        session = _mock_session()
        alarm = _alarm()

        service = AlarmService(session)
        service.repository.get = MagicMock(return_value=alarm)

        result = service.get("ALARM001")

        assert result is alarm
        service.repository.get.assert_called_once_with("ALARM001")

    def test_get_returns_none_when_missing(self) -> None:
        session = _mock_session()

        service = AlarmService(session)
        service.repository.get = MagicMock(return_value=None)

        result = service.get("ALARM001")

        assert result is None

    def test_get_required_returns_alarm(self) -> None:
        session = _mock_session()
        alarm = _alarm()

        service = AlarmService(session)
        service.repository.get = MagicMock(return_value=alarm)

        result = service.get_required("ALARM001")

        assert result is alarm

    def test_get_required_raises_when_missing(self) -> None:
        session = _mock_session()

        service = AlarmService(session)
        service.repository.get = MagicMock(return_value=None)

        with pytest.raises(
            LookupError,
            match="Alarm does not exist: ALARM001",
        ):
            service.get_required("ALARM001")


class TestAlarmServiceAcknowledge:
    """Tests for alarm acknowledgement."""

    def test_acknowledge_updates_alarm(self) -> None:
        session = _mock_session()
        alarm = _alarm()

        service = AlarmService(session)
        service.get_required = MagicMock(return_value=alarm)

        acknowledged_at = datetime(
            2026,
            8,
            17,
            10,
            0,
            tzinfo=UTC,
        )

        result = service.acknowledge(
            "ALARM001",
            acknowledged_at=acknowledged_at,
        )

        assert result is alarm
        assert alarm.acknowledged_at == acknowledged_at
        assert alarm.status == "acknowledged"

        service.get_required.assert_called_once_with("ALARM001")
        session.flush.assert_called_once_with()


class TestAlarmServiceClear:
    """Tests for alarm clearing."""

    def test_clear_updates_alarm(self) -> None:
        session = _mock_session()
        alarm = _alarm()

        acknowledged_at = datetime(
            2026,
            8,
            17,
            10,
            0,
            tzinfo=UTC,
        )
        cleared_at = datetime(
            2026,
            8,
            17,
            11,
            0,
            tzinfo=UTC,
        )

        alarm.acknowledged_at = acknowledged_at

        service = AlarmService(session)
        service.get_required = MagicMock(return_value=alarm)

        result = service.clear(
            "ALARM001",
            cleared_at=cleared_at,
        )

        assert result is alarm
        assert alarm.cleared_at == cleared_at
        assert alarm.status == "cleared"

        session.flush.assert_called_once_with()

    def test_clear_rejects_time_before_acknowledgement(self) -> None:
        session = _mock_session()
        alarm = _alarm()

        alarm.acknowledged_at = datetime(
            2026,
            8,
            17,
            11,
            0,
            tzinfo=UTC,
        )

        service = AlarmService(session)
        service.get_required = MagicMock(return_value=alarm)

        with pytest.raises(
            ValueError,
            match=("cleared_at cannot be earlier than " "acknowledged_at"),
        ):
            service.clear(
                "ALARM001",
                cleared_at=datetime(
                    2026,
                    8,
                    17,
                    10,
                    0,
                    tzinfo=UTC,
                ),
            )

        session.flush.assert_not_called()


class TestAlarmServiceUpdateMessage:
    """Tests for alarm message updates."""

    def test_update_message_changes_message(self) -> None:
        session = _mock_session()
        alarm = _alarm()

        service = AlarmService(session)
        service.get_required = MagicMock(return_value=alarm)

        result = service.update_message(
            "ALARM001",
            message="Updated alarm message",
        )

        assert result is alarm
        assert alarm.message == "Updated alarm message"

        session.flush.assert_called_once_with()


class TestAlarmServiceDelete:
    """Tests for alarm deletion."""

    def test_delete_removes_existing_alarm(self) -> None:
        session = _mock_session()
        alarm = _alarm()

        service = AlarmService(session)
        service.get_required = MagicMock(return_value=alarm)
        service.repository.delete = MagicMock()

        result = service.delete("ALARM001")

        assert result is None
        service.repository.delete.assert_called_once_with(alarm)


class TestAlarmServiceListing:
    """Tests for alarm listing helpers."""

    def test_list_all_returns_alarms(self) -> None:
        session = _mock_session()
        alarm_one = _alarm()
        alarm_two = _alarm()

        service = AlarmService(session)
        service.repository.get_all = MagicMock(return_value=(alarm_one, alarm_two))

        result = service.list_all()

        assert result == [alarm_one, alarm_two]

    def test_list_by_plant_returns_matching_alarms(self) -> None:
        session = _mock_session()
        alarm = _alarm()

        service = AlarmService(session)
        service.repository.get_by_plant = MagicMock(return_value=(alarm,))

        result = service.list_by_plant("PLANT001")

        assert result == [alarm]
        service.repository.get_by_plant.assert_called_once_with("PLANT001")

    def test_list_by_equipment_returns_matching_alarms(self) -> None:
        session = _mock_session()
        alarm = _alarm()

        service = AlarmService(session)
        service.repository.get_by_equipment = MagicMock(return_value=(alarm,))

        result = service.list_by_equipment("INV000001")

        assert result == [alarm]
        service.repository.get_by_equipment.assert_called_once_with("INV000001")

    def test_list_open_returns_open_alarms(self) -> None:
        session = _mock_session()
        alarm = _alarm()

        service = AlarmService(session)
        service.repository.get_open = MagicMock(return_value=(alarm,))

        result = service.list_open()

        assert result == [alarm]
        service.repository.get_open.assert_called_once_with()

    def test_list_open_by_plant_returns_matching_alarms(self) -> None:
        session = _mock_session()
        alarm = _alarm()

        service = AlarmService(session)
        service.repository.get_open_by_plant = MagicMock(return_value=(alarm,))

        result = service.list_open_by_plant("PLANT001")

        assert result == [alarm]
        service.repository.get_open_by_plant.assert_called_once_with("PLANT001")
