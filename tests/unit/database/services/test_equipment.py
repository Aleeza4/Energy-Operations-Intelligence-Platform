"""Unit tests for the EOIP equipment service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from eoip.database.models.equipment import EquipmentORM
from eoip.database.services.equipment import EquipmentService


def _mock_session() -> MagicMock:
    """Return a Session-compatible mock."""
    return MagicMock(spec=Session)


def _equipment() -> MagicMock:
    """Return an EquipmentORM-compatible mock."""
    equipment = MagicMock(spec=EquipmentORM)
    equipment.equipment_id = "INV000001"
    equipment.equipment_name = "Test Inverter"
    equipment.manufacturer = "Test Manufacturer"
    equipment.model_number = "MODEL-001"
    equipment.rated_power_kw = 1000.0
    equipment.status = "operational"
    return equipment


class TestEquipmentServiceConstruction:
    """Tests for equipment service construction."""

    def test_service_exposes_session_and_repository(self) -> None:
        session = _mock_session()

        service = EquipmentService(session)

        assert service.session is session
        assert service.repository.session is session
        assert service.repository.model is EquipmentORM


class TestEquipmentServiceCreate:
    """Tests for equipment creation."""

    def test_create_adds_new_equipment(self) -> None:
        session = _mock_session()
        equipment = _equipment()

        service = EquipmentService(session)
        service.repository.exists = MagicMock(return_value=False)
        service.repository.add = MagicMock(return_value=equipment)

        result = service.create(equipment)

        assert result is equipment
        service.repository.exists.assert_called_once_with("INV000001")
        service.repository.add.assert_called_once_with(equipment)

    def test_create_rejects_duplicate_equipment(self) -> None:
        session = _mock_session()
        equipment = _equipment()

        service = EquipmentService(session)
        service.repository.exists = MagicMock(return_value=True)
        service.repository.add = MagicMock()

        with pytest.raises(
            ValueError,
            match="Equipment already exists: INV000001",
        ):
            service.create(equipment)

        service.repository.exists.assert_called_once_with("INV000001")
        service.repository.add.assert_not_called()


class TestEquipmentServiceGet:
    """Tests for equipment retrieval."""

    def test_get_returns_equipment(self) -> None:
        session = _mock_session()
        equipment = _equipment()

        service = EquipmentService(session)
        service.repository.get = MagicMock(return_value=equipment)

        result = service.get("INV000001")

        assert result is equipment
        service.repository.get.assert_called_once_with("INV000001")

    def test_get_returns_none_when_missing(self) -> None:
        session = _mock_session()

        service = EquipmentService(session)
        service.repository.get = MagicMock(return_value=None)

        result = service.get("INV000001")

        assert result is None
        service.repository.get.assert_called_once_with("INV000001")

    def test_get_required_returns_equipment(self) -> None:
        session = _mock_session()
        equipment = _equipment()

        service = EquipmentService(session)
        service.repository.get = MagicMock(return_value=equipment)

        result = service.get_required("INV000001")

        assert result is equipment
        service.repository.get.assert_called_once_with("INV000001")

    def test_get_required_raises_when_missing(self) -> None:
        session = _mock_session()

        service = EquipmentService(session)
        service.repository.get = MagicMock(return_value=None)

        with pytest.raises(
            LookupError,
            match="Equipment does not exist: INV000001",
        ):
            service.get_required("INV000001")

        service.repository.get.assert_called_once_with("INV000001")


class TestEquipmentServiceUpdate:
    """Tests for equipment updates."""

    def test_update_changes_supported_fields(self) -> None:
        session = _mock_session()
        equipment = _equipment()

        service = EquipmentService(session)
        service.get_required = MagicMock(return_value=equipment)

        result = service.update(
            "INV000001",
            equipment_name="Updated Inverter",
            manufacturer="Updated Manufacturer",
            model_number="MODEL-002",
            rated_power_kw=1200.0,
            status="maintenance",
        )

        assert result is equipment
        assert equipment.equipment_name == "Updated Inverter"
        assert equipment.manufacturer == "Updated Manufacturer"
        assert equipment.model_number == "MODEL-002"
        assert equipment.rated_power_kw == 1200.0
        assert equipment.status == "maintenance"

        service.get_required.assert_called_once_with("INV000001")
        session.flush.assert_called_once_with()

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        session = _mock_session()
        equipment = _equipment()

        service = EquipmentService(session)
        service.get_required = MagicMock(return_value=equipment)

        result = service.update(
            "INV000001",
            status="maintenance",
        )

        assert result is equipment
        assert equipment.equipment_name == "Test Inverter"
        assert equipment.manufacturer == "Test Manufacturer"
        assert equipment.model_number == "MODEL-001"
        assert equipment.rated_power_kw == 1000.0
        assert equipment.status == "maintenance"

        service.get_required.assert_called_once_with("INV000001")
        session.flush.assert_called_once_with()


class TestEquipmentServiceDelete:
    """Tests for equipment deletion."""

    def test_delete_removes_existing_equipment(self) -> None:
        session = _mock_session()
        equipment = _equipment()

        service = EquipmentService(session)
        service.get_required = MagicMock(return_value=equipment)
        service.repository.delete = MagicMock()

        result = service.delete("INV000001")

        assert result is None

        service.get_required.assert_called_once_with("INV000001")
        service.repository.delete.assert_called_once_with(equipment)


class TestEquipmentServiceListing:
    """Tests for equipment listing helpers."""

    def test_list_all_returns_equipment(self) -> None:
        session = _mock_session()
        equipment_one = _equipment()
        equipment_two = _equipment()

        service = EquipmentService(session)
        service.repository.get_all = MagicMock(
            return_value=(
                equipment_one,
                equipment_two,
            )
        )

        result = service.list_all()

        assert result == [
            equipment_one,
            equipment_two,
        ]
        service.repository.get_all.assert_called_once_with()

    def test_list_by_plant_returns_matching_equipment(self) -> None:
        session = _mock_session()
        equipment = _equipment()

        service = EquipmentService(session)
        service.repository.get_by_plant = MagicMock(return_value=(equipment,))

        result = service.list_by_plant("PLANT001")

        assert result == [equipment]
        service.repository.get_by_plant.assert_called_once_with("PLANT001")

    def test_list_by_status_returns_matching_equipment(self) -> None:
        session = _mock_session()
        equipment = _equipment()

        service = EquipmentService(session)
        service.repository.get_by_status = MagicMock(return_value=(equipment,))

        result = service.list_by_status("operational")

        assert result == [equipment]
        service.repository.get_by_status.assert_called_once_with("operational")

    def test_list_by_type_returns_matching_equipment(self) -> None:
        session = _mock_session()
        equipment = _equipment()

        service = EquipmentService(session)
        service.repository.get_by_type = MagicMock(return_value=(equipment,))

        result = service.list_by_type("string_inverter")

        assert result == [equipment]
        service.repository.get_by_type.assert_called_once_with("string_inverter")

    def test_list_operational_by_plant_returns_matching_equipment(
        self,
    ) -> None:
        session = _mock_session()
        equipment = _equipment()

        service = EquipmentService(session)
        service.repository.get_operational_by_plant = MagicMock(
            return_value=(equipment,)
        )

        result = service.list_operational_by_plant("PLANT001")

        assert result == [equipment]
        service.repository.get_operational_by_plant.assert_called_once_with("PLANT001")
