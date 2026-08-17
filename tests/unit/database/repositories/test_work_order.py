"""Unit tests for the EOIP work order repository."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from eoip.database.models.work_order import WorkOrderORM
from eoip.database.repositories.work_order import WorkOrderRepository


def _mock_session() -> MagicMock:
    """Return a Session-compatible mock."""
    return MagicMock(spec=Session)


def _scalar_result(*entities: WorkOrderORM) -> MagicMock:
    """Return a mocked SQLAlchemy scalar result."""
    result = MagicMock()
    result.all.return_value = list(entities)
    return result


class TestWorkOrderRepositoryConstruction:
    """Tests for work order repository construction."""

    def test_repository_uses_work_order_model(self) -> None:
        session = _mock_session()

        repository = WorkOrderRepository(session)

        assert repository.session is session
        assert repository.model is WorkOrderORM


class TestWorkOrderRepositoryByPlant:
    """Tests for plant-based work order queries."""

    def test_get_by_plant_returns_matching_work_orders(self) -> None:
        session = _mock_session()

        work_order_one = MagicMock(spec=WorkOrderORM)
        work_order_two = MagicMock(spec=WorkOrderORM)

        session.scalars.return_value = _scalar_result(
            work_order_one,
            work_order_two,
        )

        repository = WorkOrderRepository(session)

        result = repository.get_by_plant("PLANT001")

        assert result == [
            work_order_one,
            work_order_two,
        ]

        session.scalars.assert_called_once()


class TestWorkOrderRepositoryByEquipment:
    """Tests for equipment-based work order queries."""

    def test_get_by_equipment_returns_matching_work_orders(
        self,
    ) -> None:
        session = _mock_session()

        work_order = MagicMock(spec=WorkOrderORM)

        session.scalars.return_value = _scalar_result(work_order)

        repository = WorkOrderRepository(session)

        result = repository.get_by_equipment("INV000001")

        assert result == [work_order]

        session.scalars.assert_called_once()


class TestWorkOrderRepositoryByStatus:
    """Tests for status-based work order queries."""

    def test_get_by_status_returns_matching_work_orders(self) -> None:
        session = _mock_session()

        work_order = MagicMock(spec=WorkOrderORM)

        session.scalars.return_value = _scalar_result(work_order)

        repository = WorkOrderRepository(session)

        result = repository.get_by_status("open")

        assert result == [work_order]

        session.scalars.assert_called_once()


class TestWorkOrderRepositoryByPriority:
    """Tests for priority-based work order queries."""

    def test_get_by_priority_returns_matching_work_orders(
        self,
    ) -> None:
        session = _mock_session()

        work_order = MagicMock(spec=WorkOrderORM)

        session.scalars.return_value = _scalar_result(work_order)

        repository = WorkOrderRepository(session)

        result = repository.get_by_priority("high")

        assert result == [work_order]

        session.scalars.assert_called_once()


class TestWorkOrderRepositoryByType:
    """Tests for work-order-type queries."""

    def test_get_by_type_returns_matching_work_orders(self) -> None:
        session = _mock_session()

        work_order = MagicMock(spec=WorkOrderORM)

        session.scalars.return_value = _scalar_result(work_order)

        repository = WorkOrderRepository(session)

        result = repository.get_by_type("corrective")

        assert result == [work_order]

        session.scalars.assert_called_once()


class TestWorkOrderRepositoryIncidentLink:
    """Tests for linked-incident work order queries."""

    def test_get_by_linked_incident_returns_matching_work_orders(
        self,
    ) -> None:
        session = _mock_session()

        work_order = MagicMock(spec=WorkOrderORM)

        session.scalars.return_value = _scalar_result(work_order)

        repository = WorkOrderRepository(session)

        result = repository.get_by_linked_incident("INCIDENT1")

        assert result == [work_order]

        session.scalars.assert_called_once()

    def test_get_by_linked_incident_returns_empty_sequence(
        self,
    ) -> None:
        session = _mock_session()

        session.scalars.return_value = _scalar_result()

        repository = WorkOrderRepository(session)

        result = repository.get_by_linked_incident("INCIDENT1")

        assert result == []


class TestWorkOrderRepositoryOpenQueries:
    """Tests for open work order queries."""

    def test_get_open_returns_matching_work_orders(self) -> None:
        session = _mock_session()

        work_order_one = MagicMock(spec=WorkOrderORM)
        work_order_two = MagicMock(spec=WorkOrderORM)

        session.scalars.return_value = _scalar_result(
            work_order_one,
            work_order_two,
        )

        repository = WorkOrderRepository(session)

        result = repository.get_open()

        assert result == [
            work_order_one,
            work_order_two,
        ]

        session.scalars.assert_called_once()

    def test_get_open_returns_empty_sequence(self) -> None:
        session = _mock_session()

        session.scalars.return_value = _scalar_result()

        repository = WorkOrderRepository(session)

        result = repository.get_open()

        assert result == []


class TestWorkOrderRepositoryScheduleRange:
    """Tests for scheduled work order queries."""

    def test_get_scheduled_between_returns_matching_work_orders(
        self,
    ) -> None:
        session = _mock_session()

        work_order_one = MagicMock(spec=WorkOrderORM)
        work_order_two = MagicMock(spec=WorkOrderORM)

        session.scalars.return_value = _scalar_result(
            work_order_one,
            work_order_two,
        )

        repository = WorkOrderRepository(session)

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

        result = repository.get_scheduled_between(
            start_at,
            end_at,
        )

        assert result == [
            work_order_one,
            work_order_two,
        ]

        session.scalars.assert_called_once()

    def test_get_scheduled_between_returns_empty_sequence(
        self,
    ) -> None:
        session = _mock_session()

        session.scalars.return_value = _scalar_result()

        repository = WorkOrderRepository(session)

        result = repository.get_scheduled_between(
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
