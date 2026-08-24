"""
SQLAlchemy ORM model for EOIP synthetic ground-truth events.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from eoip.database.base import Base
from eoip.database.models.equipment import EquipmentORM
from eoip.database.models.plant import PlantORM
from eoip.synthetic.models.ground_truth import (
    GroundTruthEvent,
    GroundTruthEventType,
    GroundTruthSeverity,
)


class GroundTruthEventORM(Base):
    """PostgreSQL-backed synthetic ground-truth event."""

    __tablename__ = "ground_truth_events"

    __table_args__ = (
        CheckConstraint(
            "event_type IN ("
            "'equipment_failure', 'performance_degradation', "
            "'grid_outage', 'communication_loss', 'sensor_fault', "
            "'curtailment', 'soiling', 'maintenance')",
            name="valid_event_type",
        ),
        CheckConstraint(
            "severity IN ('low', 'moderate', 'high', 'critical')",
            name="valid_severity",
        ),
        CheckConstraint(
            "ended_at > started_at",
            name="ended_after_started",
        ),
        CheckConstraint(
            "expected_power_loss_pct >= 0 " "AND expected_power_loss_pct <= 100",
            name="power_loss_pct_range",
        ),
        CheckConstraint(
            "expected_energy_loss_kwh >= 0",
            name="energy_loss_non_negative",
        ),
        Index("ix_ground_truth_events_plant_id", "plant_id"),
        Index("ix_ground_truth_events_equipment_id", "equipment_id"),
        Index("ix_ground_truth_events_event_type", "event_type"),
        Index("ix_ground_truth_events_severity", "severity"),
        Index("ix_ground_truth_events_started_at", "started_at"),
        Index("ix_ground_truth_events_ended_at", "ended_at"),
        Index(
            "ix_ground_truth_events_plant_started_at",
            "plant_id",
            "started_at",
        ),
        Index(
            "ix_ground_truth_events_plant_severity",
            "plant_id",
            "severity",
        ),
        Index(
            "ix_ground_truth_events_equipment_started_at",
            "equipment_id",
            "started_at",
        ),
    )

    ground_truth_id: Mapped[str] = mapped_column(
        String(11),
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
    equipment_id: Mapped[str | None] = mapped_column(
        String(9),
        ForeignKey(
            "equipment.equipment_id",
            onupdate="CASCADE",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    ended_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    expected_power_loss_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0",
    )
    expected_energy_loss_kwh: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0",
    )
    description: Mapped[str | None] = mapped_column(
        String(1_000),
        nullable=True,
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

    plant: Mapped[PlantORM] = relationship(PlantORM, lazy="selectin")
    equipment: Mapped[EquipmentORM | None] = relationship(
        EquipmentORM,
        lazy="selectin",
    )

    @property
    def duration_seconds(self) -> float:
        """Return total event duration in seconds."""
        return round((self.ended_at - self.started_at).total_seconds(), 3)

    @property
    def is_equipment_specific(self) -> bool:
        """Return whether the event targets one equipment asset."""
        return self.equipment_id is not None

    @property
    def is_critical(self) -> bool:
        """Return whether the event has critical severity."""
        return self.severity == GroundTruthSeverity.CRITICAL.value

    def to_domain(self) -> GroundTruthEvent:
        """Convert this ORM record to the authoritative domain model."""
        return GroundTruthEvent(
            ground_truth_id=self.ground_truth_id,
            plant_id=self.plant_id,
            event_type=GroundTruthEventType(self.event_type),
            severity=GroundTruthSeverity(self.severity),
            started_at=self.started_at,
            ended_at=self.ended_at,
            equipment_id=self.equipment_id,
            expected_power_loss_pct=self.expected_power_loss_pct,
            expected_energy_loss_kwh=self.expected_energy_loss_kwh,
            description=self.description,
        )

    @classmethod
    def from_domain(
        cls,
        event: GroundTruthEvent,
    ) -> GroundTruthEventORM:
        """Create an ORM record from a ground-truth domain event."""
        if not isinstance(event, GroundTruthEvent):
            raise TypeError("event must be a GroundTruthEvent instance.")

        return cls(
            ground_truth_id=event.ground_truth_id,
            plant_id=event.plant_id,
            equipment_id=event.equipment_id,
            event_type=event.event_type.value,
            severity=event.severity.value,
            started_at=event.started_at,
            ended_at=event.ended_at,
            expected_power_loss_pct=event.expected_power_loss_pct,
            expected_energy_loss_kwh=event.expected_energy_loss_kwh,
            description=event.description,
        )

    def update_from_domain(self, event: GroundTruthEvent) -> None:
        """Update mutable fields from a matching ground-truth event."""
        if not isinstance(event, GroundTruthEvent):
            raise TypeError("event must be a GroundTruthEvent instance.")

        if event.ground_truth_id != self.ground_truth_id:
            raise ValueError(
                "Cannot update GroundTruthEventORM with a different " "ground_truth_id."
            )

        self.plant_id = event.plant_id
        self.equipment_id = event.equipment_id
        self.event_type = event.event_type.value
        self.severity = event.severity.value
        self.started_at = event.started_at
        self.ended_at = event.ended_at
        self.expected_power_loss_pct = event.expected_power_loss_pct
        self.expected_energy_loss_kwh = event.expected_energy_loss_kwh
        self.description = event.description

    def to_record(self) -> dict[str, object]:
        """Return a serialization-ready database record."""
        return {
            "ground_truth_id": self.ground_truth_id,
            "plant_id": self.plant_id,
            "equipment_id": self.equipment_id,
            "event_type": self.event_type,
            "severity": self.severity,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat(),
            "expected_power_loss_pct": self.expected_power_loss_pct,
            "expected_energy_loss_kwh": self.expected_energy_loss_kwh,
            "description": self.description,
            "duration_seconds": self.duration_seconds,
            "is_equipment_specific": self.is_equipment_specific,
            "is_critical": self.is_critical,
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
            "GroundTruthEventORM("
            f"ground_truth_id={self.ground_truth_id!r}, "
            f"plant_id={self.plant_id!r}, "
            f"event_type={self.event_type!r}, "
            f"severity={self.severity!r}"
            ")"
        )


__all__ = ["GroundTruthEventORM"]
