"""Unit tests for the EOIP plant repository."""

from __future__ import annotations

from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from eoip.database.models.plant import PlantORM
from eoip.database.repositories.plant import PlantRepository


def _mock_session() -> MagicMock:
    """Return a Session-compatible mock."""
    return MagicMock(spec=Session)


def _scalar_result(*entities: PlantORM) -> MagicMock:
    """Return a mocked SQLAlchemy scalar result."""
    result = MagicMock()
    result.all.return_value = list(entities)
    return result


class TestPlantRepositoryConstruction:
    """Tests for plant repository construction."""

    def test_repository_uses_plant_model(self) -> None:
        session = _mock_session()

        repository = PlantRepository(session)

        assert repository.session is session
        assert repository.model is PlantORM


class TestPlantRepositoryByStatus:
    """Tests for status-based plant queries."""

    def test_get_by_status_returns_matching_plants(self) -> None:
        session = _mock_session()

        plant_one = MagicMock(spec=PlantORM)
        plant_two = MagicMock(spec=PlantORM)

        session.scalars.return_value = _scalar_result(
            plant_one,
            plant_two,
        )

        repository = PlantRepository(session)

        result = repository.get_by_status("operational")

        assert result == [
            plant_one,
            plant_two,
        ]

        session.scalars.assert_called_once()

    def test_get_operational_delegates_to_operational_status(
        self,
    ) -> None:
        session = _mock_session()

        repository = PlantRepository(session)
        repository.get_by_status = MagicMock(return_value=[])

        result = repository.get_operational()

        assert result == []

        repository.get_by_status.assert_called_once_with("operational")


class TestPlantRepositoryByRegion:
    """Tests for region-based plant queries."""

    def test_get_by_region_returns_matching_plants(self) -> None:
        session = _mock_session()

        plant = MagicMock(spec=PlantORM)

        session.scalars.return_value = _scalar_result(plant)

        repository = PlantRepository(session)

        result = repository.get_by_region("Punjab")

        assert result == [plant]

        session.scalars.assert_called_once()

    def test_get_by_region_returns_empty_sequence_when_no_match(
        self,
    ) -> None:
        session = _mock_session()

        session.scalars.return_value = _scalar_result()

        repository = PlantRepository(session)

        result = repository.get_by_region("Missing Region")

        assert result == []
