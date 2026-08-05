"""
Budget domain model for EOIP synthetic data generation.

Represents an annual or project budget allocated to a solar plant.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum
from typing import Any

_BUDGET_ID = re.compile(r"^BUD-\d{5}$")
_PLANT_ID = re.compile(r"^PLANT-\d{3}$")


class BudgetCategory(StrEnum):
    OPERATIONS = "operations"
    MAINTENANCE = "maintenance"
    CAPEX = "capex"
    OPEX = "opex"
    OTHER = "other"


class BudgetStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class Budget:
    budget_id: str
    plant_id: str
    budget_name: str
    category: BudgetCategory
    fiscal_year: int
    allocated_amount: float
    spent_amount: float = 0.0
    currency_code: str = "PKR"
    approved_on: date | None = None
    status: BudgetStatus = BudgetStatus.DRAFT

    def __post_init__(self) -> None:
        bid = self.budget_id.strip().upper()
        pid = self.plant_id.strip().upper()
        name = self.budget_name.strip()
        cur = self.currency_code.strip().upper()

        object.__setattr__(self, "budget_id", bid)
        object.__setattr__(self, "plant_id", pid)
        object.__setattr__(self, "budget_name", name)
        object.__setattr__(self, "currency_code", cur)

        if not _BUDGET_ID.fullmatch(bid):
            raise ValueError("Invalid budget_id.")
        if not _PLANT_ID.fullmatch(pid):
            raise ValueError("Invalid plant_id.")
        if not name:
            raise ValueError("budget_name cannot be empty.")
        if not isinstance(self.category, BudgetCategory):
            raise TypeError("category must be BudgetCategory.")
        if not isinstance(self.status, BudgetStatus):
            raise TypeError("status must be BudgetStatus.")
        if not (2000 <= self.fiscal_year <= 2100):
            raise ValueError("Invalid fiscal_year.")
        for field in ("allocated_amount", "spent_amount"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{field} must be numeric.")
            if not math.isfinite(value):
                raise ValueError(f"{field} must be finite.")
            if value < 0:
                raise ValueError(f"{field} must be non-negative.")
        if self.spent_amount > self.allocated_amount:
            raise ValueError("spent_amount cannot exceed allocated_amount.")
        if self.status is BudgetStatus.APPROVED and self.approved_on is None:
            raise ValueError("approved_on required for approved budgets.")

    @property
    def remaining_amount(self) -> float:
        return round(self.allocated_amount - self.spent_amount, 2)

    @property
    def utilization_pct(self) -> float:
        if self.allocated_amount == 0:
            return 0.0
        return round(self.spent_amount / self.allocated_amount * 100, 2)

    @property
    def is_over_budget(self) -> bool:
        return self.spent_amount > self.allocated_amount

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["category"] = self.category.value
        record["status"] = self.status.value
        record["approved_on"] = (
            self.approved_on.isoformat() if self.approved_on else None
        )
        record["remaining_amount"] = self.remaining_amount
        record["utilization_pct"] = self.utilization_pct
        record["is_over_budget"] = self.is_over_budget
        return record
