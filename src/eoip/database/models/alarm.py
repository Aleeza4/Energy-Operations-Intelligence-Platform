"""
SQLAlchemy ORM model for EOIP operational alarms.

This model mirrors the authoritative synthetic Alarm domain model while adding
relational persistence, database constraints, indexes, audit timestamps, and
conversion helpers for PostgreSQL.
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
from eoip.database.models.equipment import EquipmentORM
from eoip.database.models.plant import PlantORM
from eoip.synthetic.models.alarm import (
    Alarm,
    AlarmCategory,
    AlarmSeverity,
    AlarmStatus,
)


class AlarmORM(Base):
    """PostgreSQL-backed operational alarm record."""

    __tablename__ = "alarms"

    __table_args__ = (
        CheckConstraint(
            "category IN ("
            "'equipment', "
            "'grid', "
            "'communication', "
            "'environmental', "
            "'performance', "
            "'safety'"
            ")",
            name="valid_category",
        ),
        CheckConstraint(
            "severity IN ("
            "'informational', "
            "'warning', "
            "'major', "
            "'critical'"
            ")",
            name="valid_severity",
        ),
        CheckConstraint(
            "status IN ('active', 'acknowledged', 'cleared')",
            name="valid_status",
        ),
        CheckConstraint(
            "acknowledged_at IS NULL OR acknowledged_at >= raised_at",
            name="acknowledged_not_before_raised",
        ),
        CheckConstraint(
            "cleared_at IS NULL OR cleared_at >= raised_at",
            name="cleared_not_before_raised",
        ),
        CheckConstraint(
            "cleared_at IS NULL "
            "OR acknowledged_at IS NULL "
            "OR cleared_at >= acknowledged_at",
            name="cleared_not_before_acknowledged",
        ),
        CheckConstraint(
            "NOT (status = 'active' AND cleared_at IS NOT NULL)",
            name="active_has_no_cleared_at",
        ),
        CheckConstraint(
            "NOT (status = 'acknowledged' AND acknowledged_at IS NULL)",
            name="acknowledged_has_timestamp",
        ),
        CheckConstraint(
            "NOT (status = 'acknowledged' AND cleared_at IS NOT NULL)",
            name="acknowledged_has_no_cleared_at",
        ),
        CheckConstraint(
            "NOT (status = 'cleared' AND cleared_at IS NULL)",
            name="cleared_has_timestamp",
        ),
        Index("ix_alarms_plant_id", "plant_id"),
        Index("ix_alarms_equipment_id", "equipment_id"),
        Index("ix_alarms_alarm_code", "alarm_code"),
        Index("ix_alarms_category", "category"),
        Index("ix_alarms_severity", "severity"),
        Index("ix_alarms_status", "status"),
        Index("ix_alarms_raised_at", "raised_at"),
        Index(
            "ix_alarms_plant_equipment_raised_at",
            "plant_id",
            "equipment_id",
            "raised_at",
        ),
    )

    alarm_id: Mapped[str] = mapped_column(
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
    equipment_id: Mapped[str] = mapped_column(
        String(9),
        ForeignKey(
            "equipment.equipment_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    alarm_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    alarm_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    raised_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AlarmStatus.ACTIVE.value,
        server_default=AlarmStatus.ACTIVE.value,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cleared_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    message: Mapped[str | None] = mapped_column(
        String(500),
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

    plant: Mapped[PlantORM] = relationship(
        PlantORM,
        lazy="selectin",
    )
    equipment: Mapped[EquipmentORM] = relationship(
        EquipmentORM,
        lazy="selectin",
    )

    @property
    def is_open(self) -> bool:
        """Return whether the alarm remains active or acknowledged."""
        return self.status in {
            AlarmStatus.ACTIVE.value,
            AlarmStatus.ACKNOWLEDGED.value,
        }

    @property
    def is_critical(self) -> bool:
        """Return whether the alarm has critical severity."""
        return self.severity == AlarmSeverity.CRITICAL.value

    @property
    def acknowledgement_seconds(self) -> float | None:
        """Return elapsed seconds from raise to acknowledgement."""
        if self.acknowledged_at is None:
            return None

        elapsed = self.acknowledged_at - self.raised_at
        return round(elapsed.total_seconds(), 3)

    @property
    def resolution_seconds(self) -> float | None:
        """Return elapsed seconds from raise to clearance."""
        if self.cleared_at is None:
            return None

        elapsed = self.cleared_at - self.raised_at
        return round(elapsed.total_seconds(), 3)

    def to_domain(self) -> Alarm:
        """Convert this ORM record to the authoritative Alarm model."""
        return Alarm(
            alarm_id=self.alarm_id,
            plant_id=self.plant_id,
            equipment_id=self.equipment_id,
            alarm_code=self.alarm_code,
            alarm_name=self.alarm_name,
            category=AlarmCategory(self.category),
            severity=AlarmSeverity(self.severity),
            raised_at=self.raised_at,
            status=AlarmStatus(self.status),
            acknowledged_at=self.acknowledged_at,
            cleared_at=self.cleared_at,
            message=self.message,
            is_synthetic_ground_truth=self.is_synthetic_ground_truth,
        )

    @classmethod
    @classmethod
    def from_domain(cls, alarm: Alarm) -> AlarmORM:
        """Create an ORM record from an Alarm domain model."""
        if not isinstance(alarm, Alarm):
            raise TypeError("alarm must be an Alarm instance.")

        return cls(
            alarm_id=alarm.alarm_id,
            plant_id=alarm.plant_id,
            equipment_id=alarm.equipment_id,
            alarm_code=alarm.alarm_code,
            alarm_name=alarm.alarm_name,
            category=alarm.category.value,
            severity=alarm.severity.value,
            raised_at=alarm.raised_at,
            status=alarm.status.value,
            acknowledged_at=alarm.acknowledged_at,
            cleared_at=alarm.cleared_at,
            message=alarm.message,
            is_synthetic_ground_truth=alarm.is_synthetic_ground_truth,
        )

    def update_from_domain(self, alarm: Alarm) -> None:
        """Update mutable fields from a matching Alarm domain model."""
        if not isinstance(alarm, Alarm):
            raise TypeError("alarm must be an Alarm instance.")

        if alarm.alarm_id != self.alarm_id:
            raise ValueError(
                "Cannot update AlarmORM with a different alarm_id."
            )

        self.plant_id = alarm.plant_id
        self.equipment_id = alarm.equipment_id
        self.alarm_code = alarm.alarm_code
        self.alarm_name = alarm.alarm_name
        self.category = alarm.category.value
        self.severity = alarm.severity.value
        self.raised_at = alarm.raised_at
        self.status = alarm.status.value
        self.acknowledged_at = alarm.acknowledged_at
        self.cleared_at = alarm.cleared_at
        self.message = alarm.message
        self.is_synthetic_ground_truth = alarm.is_synthetic_ground_truth

    def to_record(self) -> dict[str, object]:
        """Return a serialization-ready database record."""
        return {
            "alarm_id": self.alarm_id,
            "plant_id": self.plant_id,
            "equipment_id": self.equipment_id,
            "alarm_code": self.alarm_code,
            "alarm_name": self.alarm_name,
            "category": self.category,
            "severity": self.severity,
            "raised_at": self.raised_at.isoformat(),
            "status": self.status,
            "acknowledged_at": (
                self.acknowledged_at.isoformat()
                if self.acknowledged_at is not None
                else None
            ),
            "cleared_at": (
                self.cleared_at.isoformat()
                if self.cleared_at is not None
                else None
            ),
            "message": self.message,
            "is_synthetic_ground_truth": self.is_synthetic_ground_truth,
            "is_open": self.is_open,
            "is_critical": self.is_critical,
            "acknowledgement_seconds": self.acknowledgement_seconds,
            "resolution_seconds": self.resolution_seconds,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at is not None
                else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at is not None
                else None
            ),
        }

    def __repr__(self) -> str:
        """Return a concise developer representation."""
        return (
            "AlarmORM("
            f"alarm_id={self.alarm_id!r}, "
            f"equipment_id={self.equipment_id!r}, "
            f"severity={self.severity!r}, "
            f"status={self.status!r}"
            ")"
        )


__all__ = ["AlarmORM"]