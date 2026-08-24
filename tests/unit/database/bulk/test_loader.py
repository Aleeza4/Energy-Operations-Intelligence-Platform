"""Unit tests for the EOIP PostgreSQL bulk loader."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table
from sqlalchemy.orm import Session

from eoip.database.bulk.loader import BulkLoader


def _mock_session() -> MagicMock:
    """Return a Session-compatible mock."""
    return MagicMock(spec=Session)


def _table() -> Table:
    """Return a simple SQLAlchemy table for bulk-loader tests."""
    metadata = MetaData()

    return Table(
        "test_bulk_table",
        metadata,
        Column(
            "id",
            Integer,
            primary_key=True,
        ),
        Column(
            "name",
            String(100),
            nullable=False,
        ),
    )


class TestBulkLoaderConstruction:
    """Tests for bulk loader construction."""

    def test_constructor_stores_session_and_batch_size(self) -> None:
        session = _mock_session()

        loader = BulkLoader(
            session,
            batch_size=500,
        )

        assert loader.session is session
        assert loader.batch_size == 500

    def test_constructor_uses_default_batch_size(self) -> None:
        session = _mock_session()

        loader = BulkLoader(session)

        assert loader.batch_size == 1000

    @pytest.mark.parametrize(
        "batch_size",
        [
            0,
            -1,
            -100,
        ],
    )
    def test_constructor_rejects_invalid_batch_size(
        self,
        batch_size: int,
    ) -> None:
        session = _mock_session()

        with pytest.raises(
            ValueError,
            match="batch_size must be greater than zero",
        ):
            BulkLoader(
                session,
                batch_size=batch_size,
            )


class TestBulkLoaderInsertRecords:
    """Tests for bulk record insertion."""

    def test_insert_records_returns_zero_for_empty_input(self) -> None:
        session = _mock_session()
        loader = BulkLoader(session)

        result = loader.insert_records(
            _table(),
            [],
        )

        assert result == 0
        session.execute.assert_not_called()
        session.flush.assert_not_called()

    def test_insert_records_inserts_single_batch(self) -> None:
        session = _mock_session()

        loader = BulkLoader(
            session,
            batch_size=10,
        )

        records = [
            {
                "id": 1,
                "name": "Alpha",
            },
            {
                "id": 2,
                "name": "Beta",
            },
        ]

        result = loader.insert_records(
            _table(),
            records,
        )

        assert result == 2
        assert session.execute.call_count == 1
        session.flush.assert_called_once_with()

    def test_insert_records_splits_large_input_into_batches(self) -> None:
        session = _mock_session()

        loader = BulkLoader(
            session,
            batch_size=2,
        )

        records = [
            {
                "id": 1,
                "name": "Alpha",
            },
            {
                "id": 2,
                "name": "Beta",
            },
            {
                "id": 3,
                "name": "Gamma",
            },
            {
                "id": 4,
                "name": "Delta",
            },
            {
                "id": 5,
                "name": "Epsilon",
            },
        ]

        result = loader.insert_records(
            _table(),
            records,
        )

        assert result == 5
        assert session.execute.call_count == 3
        session.flush.assert_called_once_with()

    def test_insert_records_does_not_commit_transaction(self) -> None:
        session = _mock_session()

        loader = BulkLoader(session)

        loader.insert_records(
            _table(),
            [
                {
                    "id": 1,
                    "name": "Alpha",
                }
            ],
        )

        session.commit.assert_not_called()

    def test_insert_records_accepts_generator_input(self) -> None:
        session = _mock_session()

        loader = BulkLoader(
            session,
            batch_size=2,
        )

        records = (
            {
                "id": number,
                "name": f"Record {number}",
            }
            for number in range(1, 4)
        )

        result = loader.insert_records(
            _table(),
            records,
        )

        assert result == 3
        assert session.execute.call_count == 2
        session.flush.assert_called_once_with()


class TestBulkLoaderInsertOrmRecords:
    """Tests for ORM-model bulk insertion."""

    def test_insert_orm_records_uses_model_table(self) -> None:
        session = _mock_session()
        table = _table()

        class TestModel:
            __table__ = table

        loader = BulkLoader(session)
        loader.insert_records = MagicMock(return_value=2)

        records = [
            {
                "id": 1,
                "name": "Alpha",
            },
            {
                "id": 2,
                "name": "Beta",
            },
        ]

        result = loader.insert_orm_records(
            TestModel,
            records,
        )

        assert result == 2

        loader.insert_records.assert_called_once_with(
            table,
            records,
        )

    def test_insert_orm_records_rejects_unmapped_class(self) -> None:
        session = _mock_session()

        class InvalidModel:
            pass

        loader = BulkLoader(session)

        with pytest.raises(
            TypeError,
            match=(
                "model must be a SQLAlchemy ORM mapped class "
                "with a __table__ attribute"
            ),
        ):
            loader.insert_orm_records(
                InvalidModel,
                [],
            )
