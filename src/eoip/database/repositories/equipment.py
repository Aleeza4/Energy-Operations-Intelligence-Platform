"""Equipment repository for EOIP."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from eoip.database.models.equipment import EquipmentORM
from eoip.database.repositories.base import BaseRepository


class EquipmentRepository(BaseRepository[EquipmentORM]):
    """Repository for equipment persistence and queries."""

    def __init__(self, session: Session) -> None:
        """Initialize the equipment repository."""
        super().__init__(
            session=session,
            model=EquipmentORM,
        )

    def get_by_plant(
        self,
        plant_id: str,
    ) -> Sequence[EquipmentORM]:
        """Return equipment belonging to a plant."""
        statement = (
            select(EquipmentORM)
            .where(EquipmentORM.plant_id == plant_id)
            .order_by(EquipmentORM.equipment_id)
        )

        return self.session.scalars(statement).all()

    def get_by_status(
        self,
        status: str,
    ) -> Sequence[EquipmentORM]:
        """Return equipment matching a status."""
        statement = (
            select(EquipmentORM)
            .where(EquipmentORM.status == status)
            .order_by(EquipmentORM.equipment_id)
        )

        return self.session.scalars(statement).all()

    def get_by_type(
        self,
        equipment_type: str,
    ) -> Sequence[EquipmentORM]:
        """Return equipment matching a type."""
        statement = (
            select(EquipmentORM)
            .where(EquipmentORM.equipment_type == equipment_type)
            .order_by(EquipmentORM.equipment_id)
        )

        return self.session.scalars(statement).all()

    def get_operational_by_plant(
        self,
        plant_id: str,
    ) -> Sequence[EquipmentORM]:
        """Return operational equipment belonging to a plant."""
        statement = (
            select(EquipmentORM)
            .where(
                EquipmentORM.plant_id == plant_id,
                EquipmentORM.status == "operational",
            )
            .order_by(EquipmentORM.equipment_id)
        )

        return self.session.scalars(statement).all()
