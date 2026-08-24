"""Equipment CRUD service for EOIP."""

from __future__ import annotations

from sqlalchemy.orm import Session

from eoip.database.models.equipment import EquipmentORM
from eoip.database.repositories.equipment import EquipmentRepository


class EquipmentService:
    """Application service for equipment CRUD operations."""

    def __init__(self, session: Session) -> None:
        """Initialize the equipment service."""
        self.session = session
        self.repository = EquipmentRepository(session)

    def create(
        self,
        equipment: EquipmentORM,
    ) -> EquipmentORM:
        """Create equipment within the current transaction."""
        if self.repository.exists(equipment.equipment_id):
            raise ValueError(f"Equipment already exists: {equipment.equipment_id}")

        return self.repository.add(equipment)

    def get(
        self,
        equipment_id: str,
    ) -> EquipmentORM | None:
        """Return equipment by identifier."""
        return self.repository.get(equipment_id)

    def get_required(
        self,
        equipment_id: str,
    ) -> EquipmentORM:
        """Return equipment or raise when it does not exist."""
        equipment = self.repository.get(equipment_id)

        if equipment is None:
            raise LookupError(f"Equipment does not exist: {equipment_id}")

        return equipment

    def update(
        self,
        equipment_id: str,
        *,
        equipment_name: str | None = None,
        manufacturer: str | None = None,
        model_number: str | None = None,
        rated_power_kw: float | None = None,
        status: str | None = None,
    ) -> EquipmentORM:
        """Update supported mutable equipment fields."""
        equipment = self.get_required(equipment_id)

        if equipment_name is not None:
            equipment.equipment_name = equipment_name

        if manufacturer is not None:
            equipment.manufacturer = manufacturer

        if model_number is not None:
            equipment.model_number = model_number

        if rated_power_kw is not None:
            equipment.rated_power_kw = rated_power_kw

        if status is not None:
            equipment.status = status

        self.session.flush()

        return equipment

    def delete(
        self,
        equipment_id: str,
    ) -> None:
        """Delete equipment by identifier."""
        equipment = self.get_required(equipment_id)

        self.repository.delete(equipment)

    def list_all(self) -> list[EquipmentORM]:
        """Return all equipment."""
        return list(self.repository.get_all())

    def list_by_plant(
        self,
        plant_id: str,
    ) -> list[EquipmentORM]:
        """Return equipment belonging to a plant."""
        return list(self.repository.get_by_plant(plant_id))

    def list_by_status(
        self,
        status: str,
    ) -> list[EquipmentORM]:
        """Return equipment matching a status."""
        return list(self.repository.get_by_status(status))

    def list_by_type(
        self,
        equipment_type: str,
    ) -> list[EquipmentORM]:
        """Return equipment matching a type."""
        return list(self.repository.get_by_type(equipment_type))

    def list_operational_by_plant(
        self,
        plant_id: str,
    ) -> list[EquipmentORM]:
        """Return operational equipment belonging to a plant."""
        return list(self.repository.get_operational_by_plant(plant_id))
