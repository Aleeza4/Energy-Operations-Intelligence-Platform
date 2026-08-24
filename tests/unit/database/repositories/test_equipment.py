"""Unit tests for the EOIP equipment repository."""

from __future__ import annotations

from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from eoip.database.models.equipment import EquipmentORM
from eoip.database.repositories.equipment import EquipmentRepository


def _mock_session() -> MagicMock:
    """Return a Session-compatible mock."""
    return MagicMock(spec=Session)


def _scalar_result(*entities: EquipmentORM) -> MagicMock:
    """Return a mocked SQLAlchemy scalar result."""
    result = MagicMock()
    result.all.return_value = list(entities)
    return result


class TestEquipmentRepositoryConstruction:
    """Tests for equipment repository construction."""

    def test_repository_uses_equipment_model(self) -> None:
        session = _mock_session()

        repository = EquipmentRepository(session)

        assert repository.session is session
        assert repository.model is EquipmentORM


class TestEquipmentRepositoryByPlant:
    """Tests for plant-based equipment queries."""

    def test_get_by_plant_returns_matching_equipment(self) -> None:
        session = _mock_session()

        equipment_one = MagicMock(spec=EquipmentORM)
        equipment_two = MagicMock(spec=EquipmentORM)

        session.scalars.return_value = _scalar_result(
            equipment_one,
            equipment_two,
        )

        repository = EquipmentRepository(session)

        result = repository.get_by_plant("PLANT001")

        assert result == [
            equipment_one,
            equipment_two,
        ]

        session.scalars.assert_called_once()

    def test_get_by_plant_returns_empty_sequence_when_no_match(
        self,
    ) -> None:
        session = _mock_session()

        session.scalars.return_value = _scalar_result()

        repository = EquipmentRepository(session)

        result = repository.get_by_plant("MISSING01")

        assert result == []


class TestEquipmentRepositoryByStatus:
    """Tests for status-based equipment queries."""

    def test_get_by_status_returns_matching_equipment(self) -> None:
        session = _mock_session()

        equipment = MagicMock(spec=EquipmentORM)

        session.scalars.return_value = _scalar_result(equipment)

        repository = EquipmentRepository(session)

        result = repository.get_by_status("operational")

        assert result == [equipment]

        session.scalars.assert_called_once()


class TestEquipmentRepositoryByType:
    """Tests for equipment-type queries."""

    def test_get_by_type_returns_matching_equipment(self) -> None:
        session = _mock_session()

        equipment = MagicMock(spec=EquipmentORM)

        session.scalars.return_value = _scalar_result(equipment)

        repository = EquipmentRepository(session)

        result = repository.get_by_type("string_inverter")

        assert result == [equipment]

        session.scalars.assert_called_once()


class TestEquipmentRepositoryOperationalByPlant:
    """Tests for operational equipment queries."""

    def test_get_operational_by_plant_returns_matching_equipment(
        self,
    ) -> None:
        session = _mock_session()

        equipment_one = MagicMock(spec=EquipmentORM)
        equipment_two = MagicMock(spec=EquipmentORM)

        session.scalars.return_value = _scalar_result(
            equipment_one,
            equipment_two,
        )

        repository = EquipmentRepository(session)

        result = repository.get_operational_by_plant("PLANT001")

        assert result == [
            equipment_one,
            equipment_two,
        ]

        session.scalars.assert_called_once()

    def test_get_operational_by_plant_returns_empty_sequence(
        self,
    ) -> None:
        session = _mock_session()

        session.scalars.return_value = _scalar_result()

        repository = EquipmentRepository(session)

        result = repository.get_operational_by_plant("PLANT001")

        assert result == []
