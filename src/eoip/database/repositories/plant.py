"""Plant repository for EOIP."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from eoip.database.models.plant import PlantORM
from eoip.database.repositories.base import BaseRepository


class PlantRepository(BaseRepository[PlantORM]):
    """Repository for plant persistence and queries."""

    def __init__(self, session: Session) -> None:
        """Initialize the plant repository."""
        super().__init__(
            session=session,
            model=PlantORM,
        )

    def get_by_status(
        self,
        status: str,
    ) -> Sequence[PlantORM]:
        """Return plants matching a status."""
        statement = (
            select(PlantORM)
            .where(PlantORM.status == status)
            .order_by(PlantORM.plant_id)
        )

        return self.session.scalars(statement).all()

    def get_by_region(
        self,
        region: str,
    ) -> Sequence[PlantORM]:
        """Return plants matching a region."""
        statement = (
            select(PlantORM)
            .where(PlantORM.region == region)
            .order_by(PlantORM.plant_id)
        )

        return self.session.scalars(statement).all()

    def get_operational(
        self,
    ) -> Sequence[PlantORM]:
        """Return all operational plants."""
        return self.get_by_status("operational")
