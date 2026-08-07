"""
SQLAlchemy ORM model for EOIP SCADA telemetry.

This model mirrors the authoritative synthetic SCADAObservation domain model
while adding relational persistence, database constraints, indexes, audit
timestamps, and conversion helpers for PostgreSQL and TimescaleDB.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from eoip.core.constants import SCADA_SAMPLE_INTERVAL_MINUTES
from eoip.database.base import Base
from eoip.database.models.equipment import EquipmentORM
from eoip.database.models.plant import PlantORM
from eoip.synthetic.models.scada import (
    SCADAObservation,
    SCADAOperatingState,
    SCADAQuality,
)


class SCADAObservationORM(Base):
    """PostgreSQL-backed 15-minute SCADA telemetry observation."""

    __tablename__ = "scada_observations"

    __table_args__ = (
        CheckConstraint(
            "active_power_kw >= 0 AND active_power_kw <= 50000",
            name="active_power_range",
        ),
        CheckConstraint(
            "interval_energy_kwh >= 0 AND interval_energy_kwh <= 12500",
            name="interval_energy_range",
        ),
        CheckConstraint(
            "dc_voltage_v >= 0 AND dc_voltage_v <= 2000",
            name="dc_voltage_range",
        ),
        CheckConstraint(
            "dc_current_a >= 0 AND dc_current_a <= 10000",
            name="dc_current_range",
        ),
        CheckConstraint(
            "ac_voltage_v >= 0 AND ac_voltage_v <= 50000",
            name="ac_voltage_range",
        ),
        CheckConstraint(
            "ac_current_a >= 0 AND ac_current_a <= 10000",
            name="ac_current_range",
        ),
        CheckConstraint(
            "frequency_hz >= 0 AND frequency_hz <= 70",
            name="frequency_range",
        ),
        CheckConstraint(
            "power_factor >= -1 AND power_factor <= 1",
            name="power_factor_range",
        ),
        CheckConstraint(
            "operating_state IN ("
            "'normal', "
            "'derated', "
            "'stopped', "
            "'fault', "
            "'maintenance', "
            "'night'"
            ")",
            name="valid_operating_state",
        ),
        CheckConstraint(
            "quality IN ('valid', 'estimated', 'missing')",
            name="valid_quality",
        ),
        CheckConstraint(
            "equipment_available "
            "OR (active_power_kw = 0 AND interval_energy_kwh = 0)",
            name="unavailable_equipment_has_no_generation",
        ),
        CheckConstraint(
            "grid_available " "OR (active_power_kw = 0 AND interval_energy_kwh = 0)",
            name="unavailable_grid_has_no_generation",
        ),
        CheckConstraint(
            "operating_state NOT IN "
            "('stopped', 'fault', 'maintenance', 'night') "
            "OR (active_power_kw = 0 AND interval_energy_kwh = 0)",
            name="non_generating_state_has_no_generation",
        ),
        CheckConstraint(
            "operating_state <> 'normal' "
            "OR (equipment_available AND grid_available)",
            name="normal_state_requires_availability",
        ),
        CheckConstraint(
            "EXTRACT(SECOND FROM timestamp) = 0",
            name="timestamp_zero_seconds",
        ),
        CheckConstraint(
            "MOD(EXTRACT(MINUTE FROM timestamp)::integer, "
            f"{SCADA_SAMPLE_INTERVAL_MINUTES}) = 0",
            name="timestamp_interval_aligned",
        ),
        Index("ix_scada_observations_plant_id", "plant_id"),
        Index("ix_scada_observations_timestamp", "timestamp"),
        Index(
            "ix_scada_observations_plant_timestamp",
            "plant_id",
            "timestamp",
        ),
        Index(
            "ix_scada_observations_equipment_timestamp",
            "equipment_id",
            "timestamp",
        ),
        Index(
            "ix_scada_observations_state_timestamp",
            "operating_state",
            "timestamp",
        ),
        Index(
            "ix_scada_observations_quality_timestamp",
            "quality",
            "timestamp",
        ),
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
    equipment_id: Mapped[str] = mapped_column(
        String(9),
        ForeignKey(
            "equipment.equipment_id",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        primary_key=True,
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
    )
    active_power_kw: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    interval_energy_kwh: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    dc_voltage_v: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    dc_current_a: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    ac_voltage_v: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    ac_current_a: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    frequency_hz: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    power_factor: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    equipment_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    grid_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    operating_state: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    quality: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SCADAQuality.VALID.value,
        server_default=SCADAQuality.VALID.value,
    )
    inserted_at: Mapped[datetime] = mapped_column(
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
    equipment: Mapped[EquipmentORM] = relationship(
        EquipmentORM,
        lazy="selectin",
    )

    @property
    def is_exporting(self) -> bool:
        """Return whether the asset is producing exportable active power."""
        return (
            self.active_power_kw > 0
            and self.equipment_available
            and self.grid_available
        )

    @property
    def calculated_interval_energy_kwh(self) -> float:
        """Return expected interval energy derived from active power."""
        interval_hours = SCADA_SAMPLE_INTERVAL_MINUTES / 60
        return round(self.active_power_kw * interval_hours, 4)

    @property
    def energy_deviation_kwh(self) -> float:
        """Return reported minus power-derived interval energy."""
        return round(
            self.interval_energy_kwh - self.calculated_interval_energy_kwh,
            4,
        )

    def to_domain(self) -> SCADAObservation:
        """Convert this ORM record to the authoritative domain model."""
        return SCADAObservation(
            plant_id=self.plant_id,
            equipment_id=self.equipment_id,
            timestamp=self.timestamp,
            active_power_kw=self.active_power_kw,
            interval_energy_kwh=self.interval_energy_kwh,
            dc_voltage_v=self.dc_voltage_v,
            dc_current_a=self.dc_current_a,
            ac_voltage_v=self.ac_voltage_v,
            ac_current_a=self.ac_current_a,
            frequency_hz=self.frequency_hz,
            power_factor=self.power_factor,
            equipment_available=self.equipment_available,
            grid_available=self.grid_available,
            operating_state=SCADAOperatingState(self.operating_state),
            quality=SCADAQuality(self.quality),
        )

    @classmethod
    def from_domain(
        cls,
        observation: SCADAObservation,
    ) -> SCADAObservationORM:
        """Create an ORM record from a SCADA domain observation."""
        if not isinstance(observation, SCADAObservation):
            raise TypeError("observation must be a SCADAObservation instance.")

        return cls(
            plant_id=observation.plant_id,
            equipment_id=observation.equipment_id,
            timestamp=observation.timestamp,
            active_power_kw=observation.active_power_kw,
            interval_energy_kwh=observation.interval_energy_kwh,
            dc_voltage_v=observation.dc_voltage_v,
            dc_current_a=observation.dc_current_a,
            ac_voltage_v=observation.ac_voltage_v,
            ac_current_a=observation.ac_current_a,
            frequency_hz=observation.frequency_hz,
            power_factor=observation.power_factor,
            equipment_available=observation.equipment_available,
            grid_available=observation.grid_available,
            operating_state=observation.operating_state.value,
            quality=observation.quality.value,
        )

    def update_from_domain(
        self,
        observation: SCADAObservation,
    ) -> None:
        """Update mutable fields from a matching domain observation."""
        if not isinstance(observation, SCADAObservation):
            raise TypeError("observation must be a SCADAObservation instance.")

        if (
            observation.equipment_id != self.equipment_id
            or observation.timestamp != self.timestamp
        ):
            raise ValueError(
                "Cannot update SCADAObservationORM with a different "
                "equipment_id or timestamp."
            )

        self.plant_id = observation.plant_id
        self.active_power_kw = observation.active_power_kw
        self.interval_energy_kwh = observation.interval_energy_kwh
        self.dc_voltage_v = observation.dc_voltage_v
        self.dc_current_a = observation.dc_current_a
        self.ac_voltage_v = observation.ac_voltage_v
        self.ac_current_a = observation.ac_current_a
        self.frequency_hz = observation.frequency_hz
        self.power_factor = observation.power_factor
        self.equipment_available = observation.equipment_available
        self.grid_available = observation.grid_available
        self.operating_state = observation.operating_state.value
        self.quality = observation.quality.value

    def to_record(self) -> dict[str, object]:
        """Return a serialization-ready database record."""
        return {
            "plant_id": self.plant_id,
            "equipment_id": self.equipment_id,
            "timestamp": self.timestamp.isoformat(),
            "active_power_kw": self.active_power_kw,
            "interval_energy_kwh": self.interval_energy_kwh,
            "dc_voltage_v": self.dc_voltage_v,
            "dc_current_a": self.dc_current_a,
            "ac_voltage_v": self.ac_voltage_v,
            "ac_current_a": self.ac_current_a,
            "frequency_hz": self.frequency_hz,
            "power_factor": self.power_factor,
            "equipment_available": self.equipment_available,
            "grid_available": self.grid_available,
            "operating_state": self.operating_state,
            "quality": self.quality,
            "is_exporting": self.is_exporting,
            "calculated_interval_energy_kwh": (self.calculated_interval_energy_kwh),
            "energy_deviation_kwh": self.energy_deviation_kwh,
            "inserted_at": (
                self.inserted_at.isoformat() if self.inserted_at is not None else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at is not None else None
            ),
        }

    def __repr__(self) -> str:
        """Return a concise developer representation."""
        return (
            "SCADAObservationORM("
            f"equipment_id={self.equipment_id!r}, "
            f"timestamp={self.timestamp!r}, "
            f"operating_state={self.operating_state!r}, "
            f"quality={self.quality!r}"
            ")"
        )


__all__ = ["SCADAObservationORM"]
