"""Plant CRUD service for EOIP."""

from __future__ import annotations

from sqlalchemy.orm import Session

from eoip.database.models.plant import PlantORM
from eoip.database.repositories.plant import PlantRepository


class PlantService:
    """Application service for plant CRUD operations."""

    def __init__(self, session: Session) -> None:
        """Initialize the plant service."""
        self.session = session
        self.repository = PlantRepository(session)

    def create(
        self,
        plant: PlantORM,
    ) -> PlantORM:
        """Create a plant within the current transaction."""
        if self.repository.exists(plant.plant_id):
            raise ValueError(f"Plant already exists: {plant.plant_id}")

        return self.repository.add(plant)

    def get(
        self,
        plant_id: str,
    ) -> PlantORM | None:
        """Return a plant by identifier."""
        return self.repository.get(plant_id)

    def get_required(
        self,
        plant_id: str,
    ) -> PlantORM:
        """Return a plant or raise when it does not exist."""
        plant = self.repository.get(plant_id)

        if plant is None:
            raise LookupError(f"Plant does not exist: {plant_id}")

        return plant

    def update(
        self,
        plant_id: str,
        *,
        plant_name: str | None = None,
        region: str | None = None,
        status: str | None = None,
    ) -> PlantORM:
        """Update supported mutable plant fields."""
        plant = self.get_required(plant_id)

        if plant_name is not None:
            plant.plant_name = plant_name

        if region is not None:
            plant.region = region

        if status is not None:
            plant.status = status

        self.session.flush()

        return plant

    def delete(
        self,
        plant_id: str,
    ) -> None:
        """Delete a plant by identifier."""
        plant = self.get_required(plant_id)

        self.repository.delete(plant)

    def list_all(self) -> list[PlantORM]:
        """Return all plants."""
        return list(self.repository.get_all())

    def list_operational(self) -> list[PlantORM]:
        """Return all operational plants."""
        return list(self.repository.get_operational())

    def list_by_region(
        self,
        region: str,
    ) -> list[PlantORM]:
        """Return plants in a region."""
        return list(self.repository.get_by_region(region))
