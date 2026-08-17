"""Unit tests for the generic EOIP base repository."""

from __future__ import annotations

from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from eoip.database.models.plant import PlantORM
from eoip.database.repositories.base import BaseRepository


def _mock_session() -> MagicMock:
    """Return a Session-compatible mock."""
    return MagicMock(spec=Session)


class TestBaseRepositoryConstruction:
    """Tests for base repository construction."""

    def test_repository_exposes_session_and_model(self) -> None:
        session = _mock_session()

        repository = BaseRepository(
            session=session,
            model=PlantORM,
        )

        assert repository.session is session
        assert repository.model is PlantORM


class TestBaseRepositoryGet:
    """Tests for retrieving entities by primary key."""

    def test_get_returns_entity(self) -> None:
        session = _mock_session()
        entity = MagicMock(spec=PlantORM)

        session.get.return_value = entity

        repository = BaseRepository(
            session=session,
            model=PlantORM,
        )

        result = repository.get("PLANT001")

        assert result is entity

        session.get.assert_called_once_with(
            PlantORM,
            "PLANT001",
        )

    def test_get_returns_none_when_entity_does_not_exist(self) -> None:
        session = _mock_session()

        session.get.return_value = None

        repository = BaseRepository(
            session=session,
            model=PlantORM,
        )

        result = repository.get("MISSING01")

        assert result is None


class TestBaseRepositoryGetAll:
    """Tests for retrieving all repository entities."""

    def test_get_all_returns_scalar_results(self) -> None:
        session = _mock_session()

        entity_one = MagicMock(spec=PlantORM)
        entity_two = MagicMock(spec=PlantORM)

        scalar_result = MagicMock()
        scalar_result.all.return_value = [
            entity_one,
            entity_two,
        ]

        session.scalars.return_value = scalar_result

        repository = BaseRepository(
            session=session,
            model=PlantORM,
        )

        result = repository.get_all()

        assert result == [
            entity_one,
            entity_two,
        ]

        session.scalars.assert_called_once()


class TestBaseRepositoryAdd:
    """Tests for adding entities."""

    def test_add_adds_flushes_and_returns_entity(self) -> None:
        session = _mock_session()
        entity = MagicMock(spec=PlantORM)

        repository = BaseRepository(
            session=session,
            model=PlantORM,
        )

        result = repository.add(entity)

        assert result is entity

        session.add.assert_called_once_with(entity)
        session.flush.assert_called_once_with()

    def test_add_does_not_commit_transaction(self) -> None:
        session = _mock_session()
        entity = MagicMock(spec=PlantORM)

        repository = BaseRepository(
            session=session,
            model=PlantORM,
        )

        repository.add(entity)

        session.commit.assert_not_called()


class TestBaseRepositoryAddAll:
    """Tests for adding multiple entities."""

    def test_add_all_adds_flushes_and_returns_entities(self) -> None:
        session = _mock_session()

        entity_one = MagicMock(spec=PlantORM)
        entity_two = MagicMock(spec=PlantORM)

        entities = (
            entity_one,
            entity_two,
        )

        repository = BaseRepository(
            session=session,
            model=PlantORM,
        )

        result = repository.add_all(entities)

        assert result is entities

        session.add_all.assert_called_once_with(
            [
                entity_one,
                entity_two,
            ]
        )

        session.flush.assert_called_once_with()

    def test_add_all_does_not_commit_transaction(self) -> None:
        session = _mock_session()

        repository = BaseRepository(
            session=session,
            model=PlantORM,
        )

        repository.add_all(())

        session.commit.assert_not_called()


class TestBaseRepositoryDelete:
    """Tests for deleting entities."""

    def test_delete_deletes_and_flushes_entity(self) -> None:
        session = _mock_session()
        entity = MagicMock(spec=PlantORM)

        repository = BaseRepository(
            session=session,
            model=PlantORM,
        )

        result = repository.delete(entity)

        assert result is None

        session.delete.assert_called_once_with(entity)
        session.flush.assert_called_once_with()

    def test_delete_does_not_commit_transaction(self) -> None:
        session = _mock_session()
        entity = MagicMock(spec=PlantORM)

        repository = BaseRepository(
            session=session,
            model=PlantORM,
        )

        repository.delete(entity)

        session.commit.assert_not_called()


class TestBaseRepositoryExists:
    """Tests for entity existence checks."""

    def test_exists_returns_true_when_entity_exists(self) -> None:
        session = _mock_session()

        session.get.return_value = MagicMock(spec=PlantORM)

        repository = BaseRepository(
            session=session,
            model=PlantORM,
        )

        assert repository.exists("PLANT001") is True

    def test_exists_returns_false_when_entity_does_not_exist(
        self,
    ) -> None:
        session = _mock_session()

        session.get.return_value = None

        repository = BaseRepository(
            session=session,
            model=PlantORM,
        )

        assert repository.exists("PLANT001") is False


class TestBaseRepositoryCount:
    """Tests for repository row counts."""

    def test_count_returns_database_count(self) -> None:
        session = _mock_session()

        session.scalar.return_value = 12

        repository = BaseRepository(
            session=session,
            model=PlantORM,
        )

        result = repository.count()

        assert result == 12

        session.scalar.assert_called_once()

    def test_count_returns_zero_when_scalar_is_none(self) -> None:
        session = _mock_session()

        session.scalar.return_value = None

        repository = BaseRepository(
            session=session,
            model=PlantORM,
        )

        result = repository.count()

        assert result == 0
