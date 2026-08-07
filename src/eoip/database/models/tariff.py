"""
SQLAlchemy ORM model for EOIP energy tariffs.

This model mirrors the authoritative synthetic Tariff domain model while adding
relational persistence, database constraints, indexes, audit timestamps, and
conversion helpers for PostgreSQL.
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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from eoip.database.base import Base
from eoip.database.models.plant import PlantORM
from eoip.synthetic.models.tariff import (
    Tariff,
    TariffStatus,
    TariffType,
)


class TariffORM(Base):
    """PostgreSQL-backed energy tariff for one solar plant."""

    __tablename__ = "tariffs"

    __table_args__ = (
        CheckConstraint(
            "tariff_type IN ("
            "'fixed', "
            "'time_of_use', "
            "'feed_in', "
            "'power_purchase_agreement', "
            "'merchant'"
            ")",
            name="valid_tariff_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'expired', 'cancelled')",
            name="valid_status",
        ),
        CheckConstraint(
            "energy_rate_per_kwh >= 0",
            name="energy_rate_non_negative",
        ),
        CheckConstraint(
            "demand_rate_per_kw IS NULL OR demand_rate_per_kw >= 0",
            name="demand_rate_non_negative",
        ),
        CheckConstraint(
            "escalation_rate_pct >= 0 AND escalation_rate_pct <= 100",
            name="escalation_rate_range",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="effective_date_order",
        ),
        CheckConstraint(
            "status <> 'expired' OR effective_to IS NOT NULL",
            name="expired_status_requires_end_date",
        ),
        Index("ix_tariffs_plant_id", "plant_id"),
        Index("ix_tariffs_tariff_type", "tariff_type"),
        Index("ix_tariffs_status", "status"),
        Index("ix_tariffs_effective_from", "effective_from"),
        Index("ix_tariffs_effective_to", "effective_to"),
        Index("ix_tariffs_plant_status", "plant_id", "status"),
        Index(
            "ix_tariffs_plant_effective_from",
            "plant_id",
            "effective_from",
        ),
    )

    tariff_id: Mapped[str] = mapped_column(
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
    tariff_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    tariff_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )
    currency_code: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )
    energy_rate_per_kwh: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    effective_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    effective_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    demand_rate_per_kw: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    escalation_rate_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TariffStatus.ACTIVE.value,
        server_default=TariffStatus.ACTIVE.value,
    )
    contract_reference: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
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

    plant: Mapped[PlantORM] = relationship(
        PlantORM,
        lazy="selectin",
    )

    @property
    def is_current(self) -> bool:
        """Return whether the tariff is currently effective and active."""
        today = date.today()
        within_start = self.effective_from <= today
        within_end = self.effective_to is None or today <= self.effective_to
        return self.status == TariffStatus.ACTIVE.value and within_start and within_end

    @property
    def duration_days(self) -> int | None:
        """Return inclusive tariff duration when an end date exists."""
        if self.effective_to is None:
            return None

        return (self.effective_to - self.effective_from).days + 1

    def calculate_energy_revenue(self, energy_kwh: float) -> float:
        """Return energy revenue for exported energy."""
        self._validate_runtime_number("energy_kwh", energy_kwh)
        return round(energy_kwh * self.energy_rate_per_kwh, 2)

    def calculate_demand_charge(self, demand_kw: float) -> float:
        """Return the demand charge for the supplied demand."""
        self._validate_runtime_number("demand_kw", demand_kw)

        if self.demand_rate_per_kw is None:
            return 0.0

        return round(demand_kw * self.demand_rate_per_kw, 2)

    def calculate_total_value(
        self,
        *,
        energy_kwh: float,
        demand_kw: float = 0.0,
    ) -> float:
        """Return the combined energy and demand tariff value."""
        return round(
            self.calculate_energy_revenue(energy_kwh)
            + self.calculate_demand_charge(demand_kw),
            2,
        )

    @staticmethod
    def _validate_runtime_number(
        field_name: str,
        value: float,
    ) -> None:
        """Validate a finite, non-negative runtime calculation value."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(
                f"Invalid {field_name} '{value}'. "
                "Use a finite non-negative numeric value."
            )

        if value != value or value in {float("inf"), float("-inf")}:
            raise ValueError(
                f"Invalid {field_name} '{value}'. The value must be finite."
            )

        if value < 0:
            raise ValueError(
                f"Invalid {field_name} '{value}'. "
                "The value must be greater than or equal to zero."
            )

    def to_domain(self) -> Tariff:
        """Convert this ORM record to the authoritative Tariff model."""
        return Tariff(
            tariff_id=self.tariff_id,
            plant_id=self.plant_id,
            tariff_name=self.tariff_name,
            tariff_type=TariffType(self.tariff_type),
            currency_code=self.currency_code,
            energy_rate_per_kwh=self.energy_rate_per_kwh,
            effective_from=self.effective_from,
            effective_to=self.effective_to,
            demand_rate_per_kw=self.demand_rate_per_kw,
            escalation_rate_pct=self.escalation_rate_pct,
            status=TariffStatus(self.status),
            contract_reference=self.contract_reference,
            notes=self.notes,
        )

    @classmethod
    def from_domain(cls, tariff: Tariff) -> TariffORM:
        """Create an ORM record from a Tariff domain model."""
        if not isinstance(tariff, Tariff):
            raise TypeError("tariff must be a Tariff instance.")

        return cls(
            tariff_id=tariff.tariff_id,
            plant_id=tariff.plant_id,
            tariff_name=tariff.tariff_name,
            tariff_type=tariff.tariff_type.value,
            currency_code=tariff.currency_code,
            energy_rate_per_kwh=tariff.energy_rate_per_kwh,
            effective_from=tariff.effective_from,
            effective_to=tariff.effective_to,
            demand_rate_per_kw=tariff.demand_rate_per_kw,
            escalation_rate_pct=tariff.escalation_rate_pct,
            status=tariff.status.value,
            contract_reference=tariff.contract_reference,
            notes=tariff.notes,
        )

    def update_from_domain(self, tariff: Tariff) -> None:
        """Update mutable fields from a matching Tariff domain model."""
        if not isinstance(tariff, Tariff):
            raise TypeError("tariff must be a Tariff instance.")

        if tariff.tariff_id != self.tariff_id:
            raise ValueError("Cannot update TariffORM with a different tariff_id.")

        self.plant_id = tariff.plant_id
        self.tariff_name = tariff.tariff_name
        self.tariff_type = tariff.tariff_type.value
        self.currency_code = tariff.currency_code
        self.energy_rate_per_kwh = tariff.energy_rate_per_kwh
        self.effective_from = tariff.effective_from
        self.effective_to = tariff.effective_to
        self.demand_rate_per_kw = tariff.demand_rate_per_kw
        self.escalation_rate_pct = tariff.escalation_rate_pct
        self.status = tariff.status.value
        self.contract_reference = tariff.contract_reference
        self.notes = tariff.notes

    def to_record(self) -> dict[str, object]:
        """Return a serialization-ready database record."""
        return {
            "tariff_id": self.tariff_id,
            "plant_id": self.plant_id,
            "tariff_name": self.tariff_name,
            "tariff_type": self.tariff_type,
            "currency_code": self.currency_code,
            "energy_rate_per_kwh": self.energy_rate_per_kwh,
            "effective_from": self.effective_from.isoformat(),
            "effective_to": (
                self.effective_to.isoformat() if self.effective_to is not None else None
            ),
            "demand_rate_per_kw": self.demand_rate_per_kw,
            "escalation_rate_pct": self.escalation_rate_pct,
            "status": self.status,
            "contract_reference": self.contract_reference,
            "notes": self.notes,
            "is_current": self.is_current,
            "duration_days": self.duration_days,
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
            "TariffORM("
            f"tariff_id={self.tariff_id!r}, "
            f"plant_id={self.plant_id!r}, "
            f"tariff_type={self.tariff_type!r}, "
            f"status={self.status!r}"
            ")"
        )


__all__ = ["TariffORM"]
