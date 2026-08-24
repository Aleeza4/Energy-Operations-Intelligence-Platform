"""
SQLAlchemy ORM model for EOIP plant equipment.

This model mirrors the authoritative synthetic Equipment domain model while
adding relational persistence, database constraints, indexes, audit timestamps,
and conversion helpers for PostgreSQL.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from eoip.database.base import Base
from eoip.database.models.plant import PlantORM
from eoip.synthetic.models.equipment import (
    Equipment,
    EquipmentStatus,
    EquipmentType,
)


class EquipmentORM(Base):
    """PostgreSQL-backed equipment master-data record."""

    __tablename__ = "equipment"

    __table_args__ = (
        UniqueConstraint(
            "serial_number",
            name="uq_equipment_serial_number",
        ),
        CheckConstraint(
            "rated_power_kw IS NULL OR rated_power_kw > 0",
            name="rated_power_positive",
        ),
        CheckConstraint(
            "parent_equipment_id IS NULL " "OR parent_equipment_id <> equipment_id",
            name="not_own_parent",
        ),
        CheckConstraint(
            "equipment_type IN ("
            "'string_inverter', "
            "'central_inverter', "
            "'transformer', "
            "'feeder', "
            "'weather_station', "
            "'revenue_meter', "
            "'protection_relay'"
            ")",
            name="valid_equipment_type",
        ),
        CheckConstraint(
            "status IN ("
            "'operational', "
            "'planned_outage', "
            "'forced_outage', "
            "'maintenance', "
            "'decommissioned'"
            ")",
            name="valid_status",
        ),
        Index("ix_equipment_plant_id", "plant_id"),
        Index("ix_equipment_equipment_type", "equipment_type"),
        Index("ix_equipment_status", "status"),
        Index("ix_equipment_parent_equipment_id", "parent_equipment_id"),
        Index("ix_equipment_commissioning_date", "commissioning_date"),
    )

    equipment_id: Mapped[str] = mapped_column(
        String(9),
        primary_key=True,
        nullable=False,
    )
    plant_id: Mapped[str] = mapped_column(
        String(9),
        ForeignKey(
            "plants.plant_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    equipment_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    equipment_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )
    manufacturer: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    model_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    serial_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    commissioning_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    rated_power_kw: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    parent_equipment_id: Mapped[str | None] = mapped_column(
        String(9),
        ForeignKey(
            "equipment.equipment_id",
            onupdate="CASCADE",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=EquipmentStatus.OPERATIONAL.value,
        server_default=EquipmentStatus.OPERATIONAL.value,
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

    plant: Mapped[PlantORM] = relationship(
        PlantORM,
        lazy="selectin",
    )
    parent: Mapped[EquipmentORM | None] = relationship(
        "EquipmentORM",
        remote_side=lambda: EquipmentORM.equipment_id,
        foreign_keys=lambda: [EquipmentORM.parent_equipment_id],
        back_populates="children",
        lazy="selectin",
    )
    children: Mapped[list[EquipmentORM]] = relationship(
        "EquipmentORM",
        foreign_keys=lambda: [EquipmentORM.parent_equipment_id],
        back_populates="parent",
        lazy="selectin",
    )

    @property
    def is_generation_equipment(self) -> bool:
        """Return whether the asset converts solar DC power to AC power."""
        return self.equipment_type in {
            EquipmentType.STRING_INVERTER.value,
            EquipmentType.CENTRAL_INVERTER.value,
        }

    @property
    def is_available(self) -> bool:
        """Return whether the equipment is operational."""
        return self.status == EquipmentStatus.OPERATIONAL.value

    def to_domain(self) -> Equipment:
        """Convert this ORM record to the authoritative Equipment model."""
        return Equipment(
            equipment_id=self.equipment_id,
            plant_id=self.plant_id,
            equipment_name=self.equipment_name,
            equipment_type=EquipmentType(self.equipment_type),
            manufacturer=self.manufacturer,
            model_number=self.model_number,
            serial_number=self.serial_number,
            commissioning_date=self.commissioning_date,
            rated_power_kw=self.rated_power_kw,
            parent_equipment_id=self.parent_equipment_id,
            status=EquipmentStatus(self.status),
        )

    @classmethod
    def from_domain(cls, equipment: Equipment) -> EquipmentORM:
        """Create an ORM record from an Equipment domain model."""
        if not isinstance(equipment, Equipment):
            raise TypeError("equipment must be an Equipment instance.")

        return cls(
            equipment_id=equipment.equipment_id,
            plant_id=equipment.plant_id,
            equipment_name=equipment.equipment_name,
            equipment_type=equipment.equipment_type.value,
            manufacturer=equipment.manufacturer,
            model_number=equipment.model_number,
            serial_number=equipment.serial_number,
            commissioning_date=equipment.commissioning_date,
            rated_power_kw=equipment.rated_power_kw,
            parent_equipment_id=equipment.parent_equipment_id,
            status=equipment.status.value,
        )

    def update_from_domain(self, equipment: Equipment) -> None:
        """Update mutable fields from a matching Equipment domain model."""
        if not isinstance(equipment, Equipment):
            raise TypeError("equipment must be an Equipment instance.")

        if equipment.equipment_id != self.equipment_id:
            raise ValueError(
                "Cannot update EquipmentORM with a different equipment_id."
            )

        self.plant_id = equipment.plant_id
        self.equipment_name = equipment.equipment_name
        self.equipment_type = equipment.equipment_type.value
        self.manufacturer = equipment.manufacturer
        self.model_number = equipment.model_number
        self.serial_number = equipment.serial_number
        self.commissioning_date = equipment.commissioning_date
        self.rated_power_kw = equipment.rated_power_kw
        self.parent_equipment_id = equipment.parent_equipment_id
        self.status = equipment.status.value

    def to_record(self) -> dict[str, object]:
        """Return a serialization-ready database record."""
        return {
            "equipment_id": self.equipment_id,
            "plant_id": self.plant_id,
            "equipment_name": self.equipment_name,
            "equipment_type": self.equipment_type,
            "manufacturer": self.manufacturer,
            "model_number": self.model_number,
            "serial_number": self.serial_number,
            "commissioning_date": self.commissioning_date.isoformat(),
            "rated_power_kw": self.rated_power_kw,
            "parent_equipment_id": self.parent_equipment_id,
            "status": self.status,
            "is_generation_equipment": self.is_generation_equipment,
            "is_available": self.is_available,
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
            "EquipmentORM("
            f"equipment_id={self.equipment_id!r}, "
            f"equipment_name={self.equipment_name!r}, "
            f"equipment_type={self.equipment_type!r}, "
            f"status={self.status!r}"
            ")"
        )


__all__ = ["EquipmentORM"]
