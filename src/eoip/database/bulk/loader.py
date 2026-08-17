"""PostgreSQL bulk-loading utilities for EOIP."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from sqlalchemy import Table, insert
from sqlalchemy.orm import Session

from eoip.database.bulk.base import chunked, normalize_records


class BulkLoader:
    """Perform batched bulk inserts using an existing SQLAlchemy session."""

    def __init__(
        self,
        session: Session,
        *,
        batch_size: int = 1000,
    ) -> None:
        """Initialize the bulk loader."""
        if batch_size < 1:
            raise ValueError("batch_size must be greater than zero")

        self.session = session
        self.batch_size = batch_size

    def insert_records(
        self,
        table: Table,
        records: Iterable[Mapping[str, object]],
    ) -> int:
        """Insert records into a table in batches.

        The loader does not commit the transaction. Transaction ownership
        remains with the caller or surrounding session scope.

        Parameters
        ----------
        table:
            SQLAlchemy table receiving the records.
        records:
            Mapping-like rows to insert.

        Returns
        -------
        int
            Number of records submitted for insertion.
        """
        normalized = normalize_records(dict(record) for record in records)

        if not normalized:
            return 0

        inserted_count = 0

        for batch in chunked(
            normalized,
            self.batch_size,
        ):
            self.session.execute(
                insert(table),
                batch,
            )
            inserted_count += len(batch)

        self.session.flush()

        return inserted_count

    def insert_orm_records(
        self,
        model: type[object],
        records: Iterable[Mapping[str, object]],
    ) -> int:
        """Insert mapping records using an ORM model.

        Parameters
        ----------
        model:
            SQLAlchemy ORM mapped class.
        records:
            Mapping-like rows matching the model's mapped columns.

        Returns
        -------
        int
            Number of records submitted for insertion.
        """
        table = getattr(model, "__table__", None)

        if table is None:
            raise TypeError(
                "model must be a SQLAlchemy ORM mapped class "
                "with a __table__ attribute"
            )

        return self.insert_records(
            table,
            records,
        )
