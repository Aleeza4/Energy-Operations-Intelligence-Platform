"""
SQLAlchemy ORM model for EOIP operational incidents.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from eoip.database.base import Base
from eoip.database.models.alarm import AlarmORM
from eoip.database.models.equipment import EquipmentORM
from eoip.database.models.plant import PlantORM
from eoip.synthetic.models.incident import (
    Incident,
    IncidentCategory,
    IncidentSeverity,
    IncidentStatus,
)


class IncidentORM(Base):
    """PostgreSQL-backed operational incident record."""

    __tablename__ = "incidents"

    __table_args__ = (
        CheckConstraint(
            "category IN ("
            "'equipment_failure', 'grid_event', "
            "'communication_failure', 'performance_degradation', "
            "'environmental_event', 'safety_event', "
            "'planned_maintenance')",
            name="valid_category",
        ),
        CheckConstraint(
            "severity IN ('low', 'moderate', 'high', 'critical')",
            name="valid_severity",
        ),
        CheckConstraint(
            "status IN ('open', 'investigating', 'resolved')",
            name="valid_status",
        ),
        CheckConstraint(
            "detected_at IS NULL OR detected_at >= occurred_at",
            name="detected_not_before_occurred",
        ),
        CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= occurred_at",
            name="resolved_not_before_occurred",
        ),
        CheckConstraint(
            "resolved_at IS NULL OR detected_at IS NULL "
            "OR resolved_at >= detected_at",
            name="resolved_not_before_detected",
        ),
        CheckConstraint(
            "NOT (status = 'open' AND resolved_at IS NOT NULL)",
            name="open_has_no_resolved_at",
        ),
        CheckConstraint(
            "NOT (status = 'investigating' AND detected_at IS NULL)",
            name="investigating_has_detected_at",
        ),
        CheckConstraint(
            "NOT (status = 'investigating' AND resolved_at IS NOT NULL)",
            name="investigating_has_no_resolved_at",
        ),
        CheckConstraint(
            "NOT (status = 'resolved' AND resolved_at IS NULL)",
            name="resolved_has_timestamp",
        ),
        Index("ix_incidents_plant_id", "plant_id"),
        Index("ix_incidents_equipment_id", "equipment_id"),
        Index("ix_incidents_linked_alarm_id", "linked_alarm_id"),
        Index("ix_incidents_category", "category"),
        Index("ix_incidents_severity", "severity"),
        Index("ix_incidents_status", "status"),
        Index("ix_incidents_occurred_at", "occurred_at"),
        Index(
            "ix_incidents_plant_equipment_occurred_at",
            "plant_id",
            "equipment_id",
            "occurred_at",
        ),
    )

    incident_id: Mapped[str] = mapped_column(
        String(11), primary_key=True, nullable=False
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
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    incident_name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=IncidentStatus.OPEN.value,
        server_default=IncidentStatus.OPEN.value,
    )
    detected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    description: Mapped[str | None] = mapped_column(String(1_000), nullable=True)
    root_cause: Mapped[str | None] = mapped_column(String(500), nullable=True)
    linked_alarm_id: Mapped[str | None] = mapped_column(
        String(11),
        ForeignKey(
            "alarms.alarm_id",
            onupdate="CASCADE",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    is_synthetic_ground_truth: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
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

    plant: Mapped[PlantORM] = relationship(PlantORM, lazy="selectin")
    equipment: Mapped[EquipmentORM] = relationship(EquipmentORM, lazy="selectin")
    linked_alarm: Mapped[AlarmORM | None] = relationship(AlarmORM, lazy="selectin")

    @property
    def is_open(self) -> bool:
        return self.status in {
            IncidentStatus.OPEN.value,
            IncidentStatus.INVESTIGATING.value,
        }

    @property
    def is_critical(self) -> bool:
        return self.severity == IncidentSeverity.CRITICAL.value

    @property
    def detection_seconds(self) -> float | None:
        if self.detected_at is None:
            return None
        return round(
            (self.detected_at - self.occurred_at).total_seconds(),
            3,
        )

    @property
    def resolution_seconds(self) -> float | None:
        if self.resolved_at is None:
            return None
        return round(
            (self.resolved_at - self.occurred_at).total_seconds(),
            3,
        )

    def to_domain(self) -> Incident:
        return Incident(
            incident_id=self.incident_id,
            plant_id=self.plant_id,
            equipment_id=self.equipment_id,
            incident_name=self.incident_name,
            category=IncidentCategory(self.category),
            severity=IncidentSeverity(self.severity),
            occurred_at=self.occurred_at,
            status=IncidentStatus(self.status),
            detected_at=self.detected_at,
            resolved_at=self.resolved_at,
            description=self.description,
            root_cause=self.root_cause,
            linked_alarm_id=self.linked_alarm_id,
            is_synthetic_ground_truth=self.is_synthetic_ground_truth,
        )

    @classmethod
    def from_domain(cls, incident: Incident) -> IncidentORM:
        if not isinstance(incident, Incident):
            raise TypeError("incident must be an Incident instance.")

        return cls(
            incident_id=incident.incident_id,
            plant_id=incident.plant_id,
            equipment_id=incident.equipment_id,
            incident_name=incident.incident_name,
            category=incident.category.value,
            severity=incident.severity.value,
            occurred_at=incident.occurred_at,
            status=incident.status.value,
            detected_at=incident.detected_at,
            resolved_at=incident.resolved_at,
            description=incident.description,
            root_cause=incident.root_cause,
            linked_alarm_id=incident.linked_alarm_id,
            is_synthetic_ground_truth=incident.is_synthetic_ground_truth,
        )

    def update_from_domain(self, incident: Incident) -> None:
        if not isinstance(incident, Incident):
            raise TypeError("incident must be an Incident instance.")
        if incident.incident_id != self.incident_id:
            raise ValueError("Cannot update IncidentORM with a different incident_id.")

        self.plant_id = incident.plant_id
        self.equipment_id = incident.equipment_id
        self.incident_name = incident.incident_name
        self.category = incident.category.value
        self.severity = incident.severity.value
        self.occurred_at = incident.occurred_at
        self.status = incident.status.value
        self.detected_at = incident.detected_at
        self.resolved_at = incident.resolved_at
        self.description = incident.description
        self.root_cause = incident.root_cause
        self.linked_alarm_id = incident.linked_alarm_id
        self.is_synthetic_ground_truth = incident.is_synthetic_ground_truth

    def to_record(self) -> dict[str, object]:
        return {
            "incident_id": self.incident_id,
            "plant_id": self.plant_id,
            "equipment_id": self.equipment_id,
            "incident_name": self.incident_name,
            "category": self.category,
            "severity": self.severity,
            "occurred_at": self.occurred_at.isoformat(),
            "status": self.status,
            "detected_at": (
                self.detected_at.isoformat() if self.detected_at is not None else None
            ),
            "resolved_at": (
                self.resolved_at.isoformat() if self.resolved_at is not None else None
            ),
            "description": self.description,
            "root_cause": self.root_cause,
            "linked_alarm_id": self.linked_alarm_id,
            "is_synthetic_ground_truth": self.is_synthetic_ground_truth,
            "is_open": self.is_open,
            "is_critical": self.is_critical,
            "detection_seconds": self.detection_seconds,
            "resolution_seconds": self.resolution_seconds,
            "created_at": (
                self.created_at.isoformat() if self.created_at is not None else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at is not None else None
            ),
        }

    def __repr__(self) -> str:
        return (
            "IncidentORM("
            f"incident_id={self.incident_id!r}, "
            f"equipment_id={self.equipment_id!r}, "
            f"severity={self.severity!r}, "
            f"status={self.status!r}"
            ")"
        )


__all__ = ["IncidentORM"]
