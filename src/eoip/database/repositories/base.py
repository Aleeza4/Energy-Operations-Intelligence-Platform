"""Generic repository primitives for EOIP database access."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from eoip.database.base import Base


class BaseRepository[ModelT: Base]:
    """Provide common database operations for an EOIP ORM model."""

    def __init__(
        self,
        session: Session,
        model: type[ModelT],
    ) -> None:
        """Initialize the repository."""
        self.session = session
        self.model = model

    def get(
        self,
        primary_key: object,
    ) -> ModelT | None:
        """Return one entity by primary key."""
        return self.session.get(
            self.model,
            primary_key,
        )

    def get_all(self) -> Sequence[ModelT]:
        """Return all entities for the repository model."""
        statement = select(self.model)

        return self.session.scalars(statement).all()

    def add(
        self,
        entity: ModelT,
    ) -> ModelT:
        """Add one entity to the current transaction."""
        self.session.add(entity)
        self.session.flush()

        return entity

    def add_all(
        self,
        entities: Sequence[ModelT],
    ) -> Sequence[ModelT]:
        """Add multiple entities to the current transaction."""
        self.session.add_all(list(entities))
        self.session.flush()

        return entities

    def delete(
        self,
        entity: ModelT,
    ) -> None:
        """Delete one entity from the current transaction."""
        self.session.delete(entity)
        self.session.flush()

    def exists(
        self,
        primary_key: object,
    ) -> bool:
        """Return whether an entity exists for a primary key."""
        return (
            self.session.get(
                self.model,
                primary_key,
            )
            is not None
        )

    def count(self) -> int:
        """Return the total number of model rows."""
        statement = select(func.count()).select_from(self.model)

        return self.session.scalar(statement) or 0
