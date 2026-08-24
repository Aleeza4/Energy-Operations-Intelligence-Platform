"""Unit tests for the EOIP work order service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from eoip.database.models.work_order import WorkOrderORM
from eoip.database.services.work_order import WorkOrderService


def _mock_session() -> MagicMock:
    """Return a Session-compatible mock."""
    return MagicMock(spec=Session)


def _work_order() -> MagicMock:
    """Return a WorkOrderORM-compatible mock."""
    work_order = MagicMock(spec=WorkOrderORM)
    work_order.work_order_id = "WO000001"
    work_order.plant_id = "PLANT001"
    work_order.equipment_id = "INV000001"
    work_order.status = "open"
    work_order.assigned_team = None
    work_order.scheduled_at = None
    work_order.started_at = None
    work_order.completed_at = None
    work_order.cancelled_at = None
    work_order.actual_labor_hours = None
    work_order.actual_cost = None
    work_order.completion_notes = None
    return work_order


class TestWorkOrderServiceConstruction:
    """Tests for work order service construction."""

    def test_service_exposes_session_and_repository(self) -> None:
        session = _mock_session()

        service = WorkOrderService(session)

        assert service.session is session
        assert service.repository.session is session
        assert service.repository.model is WorkOrderORM


class TestWorkOrderServiceCreate:
    """Tests for work order creation."""

    def test_create_adds_new_work_order(self) -> None:
        session = _mock_session()
        work_order = _work_order()

        service = WorkOrderService(session)
        service.repository.exists = MagicMock(return_value=False)
        service.repository.add = MagicMock(return_value=work_order)

        result = service.create(work_order)

        assert result is work_order
        service.repository.exists.assert_called_once_with("WO000001")
        service.repository.add.assert_called_once_with(work_order)

    def test_create_rejects_duplicate_work_order(self) -> None:
        session = _mock_session()
        work_order = _work_order()

        service = WorkOrderService(session)
        service.repository.exists = MagicMock(return_value=True)
        service.repository.add = MagicMock()

        with pytest.raises(
            ValueError,
            match="Work order already exists: WO000001",
        ):
            service.create(work_order)

        service.repository.exists.assert_called_once_with("WO000001")
        service.repository.add.assert_not_called()


class TestWorkOrderServiceGet:
    """Tests for work order retrieval."""

    def test_get_returns_work_order(self) -> None:
        session = _mock_session()
        work_order = _work_order()

        service = WorkOrderService(session)
        service.repository.get = MagicMock(return_value=work_order)

        result = service.get("WO000001")

        assert result is work_order
        service.repository.get.assert_called_once_with("WO000001")

    def test_get_returns_none_when_missing(self) -> None:
        session = _mock_session()

        service = WorkOrderService(session)
        service.repository.get = MagicMock(return_value=None)

        result = service.get("WO000001")

        assert result is None

    def test_get_required_returns_work_order(self) -> None:
        session = _mock_session()
        work_order = _work_order()

        service = WorkOrderService(session)
        service.repository.get = MagicMock(return_value=work_order)

        result = service.get_required("WO000001")

        assert result is work_order

    def test_get_required_raises_when_missing(self) -> None:
        session = _mock_session()

        service = WorkOrderService(session)
        service.repository.get = MagicMock(return_value=None)

        with pytest.raises(
            LookupError,
            match="Work order does not exist: WO000001",
        ):
            service.get_required("WO000001")


class TestWorkOrderServiceUpdateStatus:
    """Tests for work order status updates."""

    def test_update_status_changes_status(self) -> None:
        session = _mock_session()
        work_order = _work_order()

        service = WorkOrderService(session)
        service.get_required = MagicMock(return_value=work_order)

        result = service.update_status(
            "WO000001",
            status="scheduled",
        )

        assert result is work_order
        assert work_order.status == "scheduled"

        service.get_required.assert_called_once_with("WO000001")
        session.flush.assert_called_once_with()


class TestWorkOrderServiceAssignment:
    """Tests for work order assignment."""

    def test_assign_team_updates_team(self) -> None:
        session = _mock_session()
        work_order = _work_order()

        service = WorkOrderService(session)
        service.get_required = MagicMock(return_value=work_order)

        result = service.assign_team(
            "WO000001",
            assigned_team="Electrical Maintenance",
        )

        assert result is work_order
        assert work_order.assigned_team == "Electrical Maintenance"

        service.get_required.assert_called_once_with("WO000001")
        session.flush.assert_called_once_with()


class TestWorkOrderServiceSchedule:
    """Tests for work order scheduling."""

    def test_schedule_updates_work_order(self) -> None:
        session = _mock_session()
        work_order = _work_order()

        service = WorkOrderService(session)
        service.get_required = MagicMock(return_value=work_order)

        scheduled_at = datetime(
            2026,
            8,
            17,
            10,
            0,
            tzinfo=UTC,
        )

        result = service.schedule(
            "WO000001",
            scheduled_at=scheduled_at,
        )

        assert result is work_order
        assert work_order.scheduled_at == scheduled_at
        assert work_order.status == "scheduled"

        session.flush.assert_called_once_with()


class TestWorkOrderServiceStart:
    """Tests for starting work orders."""

    def test_start_updates_work_order(self) -> None:
        session = _mock_session()
        work_order = _work_order()

        scheduled_at = datetime(
            2026,
            8,
            17,
            10,
            0,
            tzinfo=UTC,
        )
        started_at = datetime(
            2026,
            8,
            17,
            11,
            0,
            tzinfo=UTC,
        )

        work_order.scheduled_at = scheduled_at

        service = WorkOrderService(session)
        service.get_required = MagicMock(return_value=work_order)

        result = service.start(
            "WO000001",
            started_at=started_at,
        )

        assert result is work_order
        assert work_order.started_at == started_at
        assert work_order.status == "in_progress"

        session.flush.assert_called_once_with()

    def test_start_rejects_time_before_schedule(self) -> None:
        session = _mock_session()
        work_order = _work_order()

        work_order.scheduled_at = datetime(
            2026,
            8,
            17,
            11,
            0,
            tzinfo=UTC,
        )

        service = WorkOrderService(session)
        service.get_required = MagicMock(return_value=work_order)

        with pytest.raises(
            ValueError,
            match="started_at cannot be earlier than scheduled_at",
        ):
            service.start(
                "WO000001",
                started_at=datetime(
                    2026,
                    8,
                    17,
                    10,
                    0,
                    tzinfo=UTC,
                ),
            )

        session.flush.assert_not_called()


class TestWorkOrderServiceComplete:
    """Tests for completing work orders."""

    def test_complete_updates_work_order(self) -> None:
        session = _mock_session()
        work_order = _work_order()

        work_order.started_at = datetime(
            2026,
            8,
            17,
            11,
            0,
            tzinfo=UTC,
        )

        completed_at = datetime(
            2026,
            8,
            17,
            13,
            0,
            tzinfo=UTC,
        )

        service = WorkOrderService(session)
        service.get_required = MagicMock(return_value=work_order)

        result = service.complete(
            "WO000001",
            completed_at=completed_at,
            actual_labor_hours=2.0,
            actual_cost=5000.0,
            completion_notes="Repair completed successfully.",
        )

        assert result is work_order
        assert work_order.completed_at == completed_at
        assert work_order.status == "completed"
        assert work_order.actual_labor_hours == 2.0
        assert work_order.actual_cost == 5000.0
        assert work_order.completion_notes == "Repair completed successfully."

        session.flush.assert_called_once_with()

    def test_complete_rejects_time_before_start(self) -> None:
        session = _mock_session()
        work_order = _work_order()

        work_order.started_at = datetime(
            2026,
            8,
            17,
            12,
            0,
            tzinfo=UTC,
        )

        service = WorkOrderService(session)
        service.get_required = MagicMock(return_value=work_order)

        with pytest.raises(
            ValueError,
            match="completed_at cannot be earlier than started_at",
        ):
            service.complete(
                "WO000001",
                completed_at=datetime(
                    2026,
                    8,
                    17,
                    11,
                    0,
                    tzinfo=UTC,
                ),
            )

        session.flush.assert_not_called()


class TestWorkOrderServiceCancel:
    """Tests for cancelling work orders."""

    def test_cancel_updates_work_order(self) -> None:
        session = _mock_session()
        work_order = _work_order()

        service = WorkOrderService(session)
        service.get_required = MagicMock(return_value=work_order)

        cancelled_at = datetime(
            2026,
            8,
            17,
            12,
            0,
            tzinfo=UTC,
        )

        result = service.cancel(
            "WO000001",
            cancelled_at=cancelled_at,
        )

        assert result is work_order
        assert work_order.cancelled_at == cancelled_at
        assert work_order.status == "cancelled"

        session.flush.assert_called_once_with()


class TestWorkOrderServiceDelete:
    """Tests for work order deletion."""

    def test_delete_removes_existing_work_order(self) -> None:
        session = _mock_session()
        work_order = _work_order()

        service = WorkOrderService(session)
        service.get_required = MagicMock(return_value=work_order)
        service.repository.delete = MagicMock()

        result = service.delete("WO000001")

        assert result is None
        service.repository.delete.assert_called_once_with(work_order)


class TestWorkOrderServiceListing:
    """Tests for work order listing helpers."""

    def test_list_all_returns_work_orders(self) -> None:
        session = _mock_session()
        work_order_one = _work_order()
        work_order_two = _work_order()

        service = WorkOrderService(session)
        service.repository.get_all = MagicMock(
            return_value=(work_order_one, work_order_two)
        )

        result = service.list_all()

        assert result == [work_order_one, work_order_two]

    def test_list_by_plant_returns_matching_work_orders(self) -> None:
        session = _mock_session()
        work_order = _work_order()

        service = WorkOrderService(session)
        service.repository.get_by_plant = MagicMock(return_value=(work_order,))

        result = service.list_by_plant("PLANT001")

        assert result == [work_order]
        service.repository.get_by_plant.assert_called_once_with("PLANT001")

    def test_list_by_equipment_returns_matching_work_orders(self) -> None:
        session = _mock_session()
        work_order = _work_order()

        service = WorkOrderService(session)
        service.repository.get_by_equipment = MagicMock(return_value=(work_order,))

        result = service.list_by_equipment("INV000001")

        assert result == [work_order]
        service.repository.get_by_equipment.assert_called_once_with("INV000001")

    def test_list_open_returns_open_work_orders(self) -> None:
        session = _mock_session()
        work_order = _work_order()

        service = WorkOrderService(session)
        service.repository.get_open = MagicMock(return_value=(work_order,))

        result = service.list_open()

        assert result == [work_order]
        service.repository.get_open.assert_called_once_with()

    def test_list_by_linked_incident_returns_matching_work_orders(
        self,
    ) -> None:
        session = _mock_session()
        work_order = _work_order()

        service = WorkOrderService(session)
        service.repository.get_by_linked_incident = MagicMock(
            return_value=(work_order,)
        )

        result = service.list_by_linked_incident("INCIDENT1")

        assert result == [work_order]
        service.repository.get_by_linked_incident.assert_called_once_with("INCIDENT1")
