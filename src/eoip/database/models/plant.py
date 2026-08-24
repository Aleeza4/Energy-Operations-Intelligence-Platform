"""
SQLAlchemy ORM model for EOIP solar plants.

This model mirrors the authoritative synthetic Plant domain model while adding
database persistence fields, constraints, indexes, and conversion helpers.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from eoip.database.base import Base
from eoip.synthetic.models.plant import Plant, PlantStatus


class PlantORM(Base):
    """PostgreSQL-backed plant master-data record."""

    __tablename__ = "plants"

    __table_args__ = (
        CheckConstraint(
            "latitude >= -90.0 AND latitude <= 90.0",
            name="latitude_range",
        ),
        CheckConstraint(
            "longitude >= -180.0 AND longitude <= 180.0",
            name="longitude_range",
        ),
        CheckConstraint(
            "dc_capacity_mw > 0",
            name="dc_capacity_positive",
        ),
        CheckConstraint(
            "ac_capacity_mw > 0",
            name="ac_capacity_positive",
        ),
        CheckConstraint(
            "ac_capacity_mw <= dc_capacity_mw",
            name="ac_not_greater_than_dc",
        ),
        CheckConstraint(
            "status IN ('operational', 'planned_outage', 'decommissioned')",
            name="valid_status",
        ),
        Index("ix_plants_region", "region"),
        Index("ix_plants_status", "status"),
        Index("ix_plants_commissioning_date", "commissioning_date"),
    )

    plant_id: Mapped[str] = mapped_column(
        String(9),
        primary_key=True,
        nullable=False,
    )
    plant_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    region: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    dc_capacity_mw: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    ac_capacity_mw: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    commissioning_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=PlantStatus.OPERATIONAL.value,
        server_default=PlantStatus.OPERATIONAL.value,
    )
    timezone_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="UTC",
        server_default="UTC",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    @property
    def dc_ac_ratio(self) -> float:
        """Return the installed DC-to-AC capacity ratio."""
        return round(self.dc_capacity_mw / self.ac_capacity_mw, 4)

    def to_domain(self) -> Plant:
        """Convert this ORM record to the authoritative Plant domain model."""
        return Plant(
            plant_id=self.plant_id,
            plant_name=self.plant_name,
            region=self.region,
            latitude=self.latitude,
            longitude=self.longitude,
            dc_capacity_mw=self.dc_capacity_mw,
            ac_capacity_mw=self.ac_capacity_mw,
            commissioning_date=self.commissioning_date,
            status=PlantStatus(self.status),
            timezone_name=self.timezone_name,
        )

    @classmethod
    def from_domain(cls, plant: Plant) -> PlantORM:
        """Create an ORM record from the authoritative Plant domain model."""
        if not isinstance(plant, Plant):
            raise TypeError("plant must be a Plant instance.")

        return cls(
            plant_id=plant.plant_id,
            plant_name=plant.plant_name,
            region=plant.region,
            latitude=plant.latitude,
            longitude=plant.longitude,
            dc_capacity_mw=plant.dc_capacity_mw,
            ac_capacity_mw=plant.ac_capacity_mw,
            commissioning_date=plant.commissioning_date,
            status=plant.status.value,
            timezone_name=plant.timezone_name,
        )

    def update_from_domain(self, plant: Plant) -> None:
        """Update mutable fields from a matching Plant domain model."""
        if not isinstance(plant, Plant):
            raise TypeError("plant must be a Plant instance.")

        if plant.plant_id != self.plant_id:
            raise ValueError("Cannot update PlantORM with a different plant_id.")

        self.plant_name = plant.plant_name
        self.region = plant.region
        self.latitude = plant.latitude
        self.longitude = plant.longitude
        self.dc_capacity_mw = plant.dc_capacity_mw
        self.ac_capacity_mw = plant.ac_capacity_mw
        self.commissioning_date = plant.commissioning_date
        self.status = plant.status.value
        self.timezone_name = plant.timezone_name

    def to_record(self) -> dict[str, object]:
        """Return a serialization-ready database record."""
        return {
            "plant_id": self.plant_id,
            "plant_name": self.plant_name,
            "region": self.region,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "dc_capacity_mw": self.dc_capacity_mw,
            "ac_capacity_mw": self.ac_capacity_mw,
            "commissioning_date": self.commissioning_date.isoformat(),
            "status": self.status,
            "timezone_name": self.timezone_name,
            "dc_ac_ratio": self.dc_ac_ratio,
            "created_at": (
                self.created_at.isoformat() if self.created_at is not None else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at is not None else None
            ),
        }

    def __repr__(self) -> str:
        """Return a concise developer representation."""
        return (
            "PlantORM("
            f"plant_id={self.plant_id!r}, "
            f"plant_name={self.plant_name!r}, "
            f"status={self.status!r}"
            ")"
        )


__all__ = ["PlantORM"]
