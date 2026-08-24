"""Unit tests for the EOIP plant service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from eoip.database.models.plant import PlantORM
from eoip.database.services.plant import PlantService


def _mock_session() -> MagicMock:
    """Return a Session-compatible mock."""
    return MagicMock(spec=Session)


def _plant() -> MagicMock:
    """Return a PlantORM-compatible mock."""
    plant = MagicMock(spec=PlantORM)
    plant.plant_id = "PLANT001"
    plant.plant_name = "Test Plant"
    plant.region = "Punjab"
    plant.status = "operational"
    return plant


class TestPlantServiceConstruction:
    """Tests for plant service construction."""

    def test_service_exposes_session_and_repository(self) -> None:
        session = _mock_session()

        service = PlantService(session)

        assert service.session is session
        assert service.repository.session is session
        assert service.repository.model is PlantORM


class TestPlantServiceCreate:
    """Tests for plant creation."""

    def test_create_adds_new_plant(self) -> None:
        session = _mock_session()
        plant = _plant()

        service = PlantService(session)
        service.repository.exists = MagicMock(return_value=False)
        service.repository.add = MagicMock(return_value=plant)

        result = service.create(plant)

        assert result is plant
        service.repository.exists.assert_called_once_with("PLANT001")
        service.repository.add.assert_called_once_with(plant)

    def test_create_rejects_duplicate_plant(self) -> None:
        session = _mock_session()
        plant = _plant()

        service = PlantService(session)
        service.repository.exists = MagicMock(return_value=True)
        service.repository.add = MagicMock()

        with pytest.raises(
            ValueError,
            match="Plant already exists: PLANT001",
        ):
            service.create(plant)

        service.repository.exists.assert_called_once_with("PLANT001")
        service.repository.add.assert_not_called()


class TestPlantServiceGet:
    """Tests for plant retrieval."""

    def test_get_returns_plant(self) -> None:
        session = _mock_session()
        plant = _plant()

        service = PlantService(session)
        service.repository.get = MagicMock(return_value=plant)

        result = service.get("PLANT001")

        assert result is plant
        service.repository.get.assert_called_once_with("PLANT001")

    def test_get_returns_none_when_missing(self) -> None:
        session = _mock_session()

        service = PlantService(session)
        service.repository.get = MagicMock(return_value=None)

        result = service.get("PLANT001")

        assert result is None
        service.repository.get.assert_called_once_with("PLANT001")

    def test_get_required_returns_plant(self) -> None:
        session = _mock_session()
        plant = _plant()

        service = PlantService(session)
        service.repository.get = MagicMock(return_value=plant)

        result = service.get_required("PLANT001")

        assert result is plant
        service.repository.get.assert_called_once_with("PLANT001")

    def test_get_required_raises_when_missing(self) -> None:
        session = _mock_session()

        service = PlantService(session)
        service.repository.get = MagicMock(return_value=None)

        with pytest.raises(
            LookupError,
            match="Plant does not exist: PLANT001",
        ):
            service.get_required("PLANT001")

        service.repository.get.assert_called_once_with("PLANT001")


class TestPlantServiceUpdate:
    """Tests for plant updates."""

    def test_update_changes_supported_fields(self) -> None:
        session = _mock_session()
        plant = _plant()

        service = PlantService(session)
        service.get_required = MagicMock(return_value=plant)

        result = service.update(
            "PLANT001",
            plant_name="Updated Plant",
            region="Islamabad",
            status="planned_outage",
        )

        assert result is plant
        assert plant.plant_name == "Updated Plant"
        assert plant.region == "Islamabad"
        assert plant.status == "planned_outage"

        service.get_required.assert_called_once_with("PLANT001")
        session.flush.assert_called_once_with()

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        session = _mock_session()
        plant = _plant()

        service = PlantService(session)
        service.get_required = MagicMock(return_value=plant)

        result = service.update(
            "PLANT001",
            region="KPK",
        )

        assert result is plant
        assert plant.plant_name == "Test Plant"
        assert plant.region == "KPK"
        assert plant.status == "operational"

        service.get_required.assert_called_once_with("PLANT001")
        session.flush.assert_called_once_with()


class TestPlantServiceDelete:
    """Tests for plant deletion."""

    def test_delete_removes_existing_plant(self) -> None:
        session = _mock_session()
        plant = _plant()

        service = PlantService(session)
        service.get_required = MagicMock(return_value=plant)
        service.repository.delete = MagicMock()

        result = service.delete("PLANT001")

        assert result is None

        service.get_required.assert_called_once_with("PLANT001")
        service.repository.delete.assert_called_once_with(plant)


class TestPlantServiceListing:
    """Tests for plant listing helpers."""

    def test_list_all_returns_plants(self) -> None:
        session = _mock_session()
        plant_one = _plant()
        plant_two = _plant()

        service = PlantService(session)
        service.repository.get_all = MagicMock(
            return_value=(
                plant_one,
                plant_two,
            )
        )

        result = service.list_all()

        assert result == [
            plant_one,
            plant_two,
        ]

        service.repository.get_all.assert_called_once_with()

    def test_list_operational_returns_operational_plants(self) -> None:
        session = _mock_session()
        plant = _plant()

        service = PlantService(session)
        service.repository.get_operational = MagicMock(return_value=(plant,))

        result = service.list_operational()

        assert result == [plant]
        service.repository.get_operational.assert_called_once_with()

    def test_list_by_region_returns_matching_plants(self) -> None:
        session = _mock_session()
        plant = _plant()

        service = PlantService(session)
        service.repository.get_by_region = MagicMock(return_value=(plant,))

        result = service.list_by_region("Punjab")

        assert result == [plant]
        service.repository.get_by_region.assert_called_once_with("Punjab")
