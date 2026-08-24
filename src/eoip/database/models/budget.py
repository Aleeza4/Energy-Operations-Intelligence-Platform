"""
SQLAlchemy ORM model for EOIP plant budgets.

This model mirrors the authoritative synthetic Budget domain model while adding
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
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from eoip.database.base import Base
from eoip.database.models.plant import PlantORM
from eoip.synthetic.models.budget import (
    Budget,
    BudgetCategory,
    BudgetStatus,
)


class BudgetORM(Base):
    """PostgreSQL-backed budget record for one solar plant."""

    __tablename__ = "budgets"

    __table_args__ = (
        CheckConstraint(
            "category IN ("
            "'operations', "
            "'maintenance', "
            "'capex', "
            "'opex', "
            "'other'"
            ")",
            name="valid_category",
        ),
        CheckConstraint(
            "status IN ('draft', 'approved', 'closed')",
            name="valid_status",
        ),
        CheckConstraint(
            "fiscal_year >= 2000 AND fiscal_year <= 2100",
            name="fiscal_year_range",
        ),
        CheckConstraint(
            "allocated_amount >= 0",
            name="allocated_amount_non_negative",
        ),
        CheckConstraint(
            "spent_amount >= 0",
            name="spent_amount_non_negative",
        ),
        CheckConstraint(
            "spent_amount <= allocated_amount",
            name="spent_not_above_allocated",
        ),
        CheckConstraint(
            "status <> 'approved' OR approved_on IS NOT NULL",
            name="approved_status_requires_date",
        ),
        Index("ix_budgets_plant_id", "plant_id"),
        Index("ix_budgets_category", "category"),
        Index("ix_budgets_status", "status"),
        Index("ix_budgets_fiscal_year", "fiscal_year"),
        Index("ix_budgets_approved_on", "approved_on"),
        Index(
            "ix_budgets_plant_fiscal_year",
            "plant_id",
            "fiscal_year",
        ),
    )

    budget_id: Mapped[str] = mapped_column(
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
    budget_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    fiscal_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    allocated_amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    spent_amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0",
    )
    currency_code: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="PKR",
        server_default="PKR",
    )
    approved_on: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=BudgetStatus.DRAFT.value,
        server_default=BudgetStatus.DRAFT.value,
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
    def remaining_amount(self) -> float:
        """Return unspent budget amount."""
        return round(self.allocated_amount - self.spent_amount, 2)

    @property
    def utilization_pct(self) -> float:
        """Return percentage of the allocated amount already spent."""
        if self.allocated_amount == 0:
            return 0.0

        return round(
            self.spent_amount / self.allocated_amount * 100,
            2,
        )

    @property
    def is_over_budget(self) -> bool:
        """Return whether spending exceeds allocation."""
        return self.spent_amount > self.allocated_amount

    def to_domain(self) -> Budget:
        """Convert this ORM record to the authoritative Budget model."""
        return Budget(
            budget_id=self.budget_id,
            plant_id=self.plant_id,
            budget_name=self.budget_name,
            category=BudgetCategory(self.category),
            fiscal_year=self.fiscal_year,
            allocated_amount=self.allocated_amount,
            spent_amount=self.spent_amount,
            currency_code=self.currency_code,
            approved_on=self.approved_on,
            status=BudgetStatus(self.status),
        )

    @classmethod
    def from_domain(cls, budget: Budget) -> BudgetORM:
        """Create an ORM record from a Budget domain model."""
        if not isinstance(budget, Budget):
            raise TypeError("budget must be a Budget instance.")

        return cls(
            budget_id=budget.budget_id,
            plant_id=budget.plant_id,
            budget_name=budget.budget_name,
            category=budget.category.value,
            fiscal_year=budget.fiscal_year,
            allocated_amount=budget.allocated_amount,
            spent_amount=budget.spent_amount,
            currency_code=budget.currency_code,
            approved_on=budget.approved_on,
            status=budget.status.value,
        )

    def update_from_domain(self, budget: Budget) -> None:
        """Update mutable fields from a matching Budget domain model."""
        if not isinstance(budget, Budget):
            raise TypeError("budget must be a Budget instance.")

        if budget.budget_id != self.budget_id:
            raise ValueError("Cannot update BudgetORM with a different budget_id.")

        self.plant_id = budget.plant_id
        self.budget_name = budget.budget_name
        self.category = budget.category.value
        self.fiscal_year = budget.fiscal_year
        self.allocated_amount = budget.allocated_amount
        self.spent_amount = budget.spent_amount
        self.currency_code = budget.currency_code
        self.approved_on = budget.approved_on
        self.status = budget.status.value

    def to_record(self) -> dict[str, object]:
        """Return a serialization-ready database record."""
        return {
            "budget_id": self.budget_id,
            "plant_id": self.plant_id,
            "budget_name": self.budget_name,
            "category": self.category,
            "fiscal_year": self.fiscal_year,
            "allocated_amount": self.allocated_amount,
            "spent_amount": self.spent_amount,
            "currency_code": self.currency_code,
            "approved_on": (
                self.approved_on.isoformat() if self.approved_on is not None else None
            ),
            "status": self.status,
            "remaining_amount": self.remaining_amount,
            "utilization_pct": self.utilization_pct,
            "is_over_budget": self.is_over_budget,
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
            "BudgetORM("
            f"budget_id={self.budget_id!r}, "
            f"plant_id={self.plant_id!r}, "
            f"fiscal_year={self.fiscal_year!r}, "
            f"status={self.status!r}"
            ")"
        )


__all__ = ["BudgetORM"]
