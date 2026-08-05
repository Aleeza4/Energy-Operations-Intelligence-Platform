"""
Tariff domain model for EOIP synthetic data generation.

This module defines the authoritative representation of an energy tariff
applied to a solar plant. Synthetic tariff generators, financial analytics,
ETL pipelines, recommendation calculations, and dashboards must use this
model instead of creating independent tariff dictionaries.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum
from typing import Any

_TARIFF_ID_PATTERN = re.compile(r"^TAR-\d{5}$")
_PLANT_ID_PATTERN = re.compile(r"^PLANT-\d{3}$")
_CURRENCY_CODE_PATTERN = re.compile(r"^[A-Z]{3}$")


class TariffType(StrEnum):
    """Supported tariff structures for solar-energy settlements."""

    FIXED = "fixed"
    TIME_OF_USE = "time_of_use"
    FEED_IN = "feed_in"
    POWER_PURCHASE_AGREEMENT = "power_purchase_agreement"
    MERCHANT = "merchant"


class TariffStatus(StrEnum):
    """Supported lifecycle states for tariffs."""

    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class Tariff:
    """Immutable energy-tariff record for one solar plant."""

    tariff_id: str
    plant_id: str
    tariff_name: str
    tariff_type: TariffType
    currency_code: str
    energy_rate_per_kwh: float
    effective_from: date
    effective_to: date | None = None
    demand_rate_per_kw: float | None = None
    escalation_rate_pct: float = 0.0
    status: TariffStatus = TariffStatus.ACTIVE
    contract_reference: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        """Normalize and validate the complete tariff record."""
        normalized_tariff_id = self.tariff_id.strip().upper()
        normalized_plant_id = self.plant_id.strip().upper()
        normalized_tariff_name = self.tariff_name.strip()
        normalized_currency_code = self.currency_code.strip().upper()
        normalized_contract_reference = (
            self.contract_reference.strip().upper()
            if self.contract_reference is not None
            else None
        )
        normalized_notes = self.notes.strip() if self.notes is not None else None

        object.__setattr__(self, "tariff_id", normalized_tariff_id)
        object.__setattr__(self, "plant_id", normalized_plant_id)
        object.__setattr__(self, "tariff_name", normalized_tariff_name)
        object.__setattr__(self, "currency_code", normalized_currency_code)
        object.__setattr__(
            self,
            "contract_reference",
            normalized_contract_reference,
        )
        object.__setattr__(self, "notes", normalized_notes)

        self._validate_identifiers()
        self._validate_text_fields()
        self._validate_enums()
        self._validate_dates()
        self._validate_numeric_fields()

    def _validate_identifiers(self) -> None:
        """Validate tariff, plant, and currency identifiers."""
        if not _TARIFF_ID_PATTERN.fullmatch(self.tariff_id):
            raise ValueError(
                f"Invalid tariff_id '{self.tariff_id}'. " "Use the format 'TAR-00001'."
            )

        if not _PLANT_ID_PATTERN.fullmatch(self.plant_id):
            raise ValueError(
                f"Invalid plant_id '{self.plant_id}' for {self.tariff_id}. "
                "Use the format 'PLANT-001'."
            )

        if not _CURRENCY_CODE_PATTERN.fullmatch(self.currency_code):
            raise ValueError(
                f"Invalid currency_code '{self.currency_code}' for "
                f"{self.tariff_id}. Use a three-letter ISO-style code such "
                "as 'USD', 'EUR', or 'PKR'."
            )

    def _validate_text_fields(self) -> None:
        """Validate required and optional tariff text fields."""
        if not self.tariff_name:
            raise ValueError(
                f"tariff_name cannot be empty for {self.tariff_id}. "
                "Provide a descriptive tariff name."
            )

        if len(self.tariff_name) > 150:
            raise ValueError(
                f"tariff_name for {self.tariff_id} contains "
                f"{len(self.tariff_name)} characters. Use no more than 150."
            )

        self._validate_optional_text(
            field_name="contract_reference",
            value=self.contract_reference,
            maximum_length=100,
        )
        self._validate_optional_text(
            field_name="notes",
            value=self.notes,
            maximum_length=1_000,
        )

    def _validate_optional_text(
        self,
        field_name: str,
        value: str | None,
        maximum_length: int,
    ) -> None:
        """Validate an optional normalized text value."""
        if value is None:
            return

        if not value:
            raise ValueError(
                f"{field_name} cannot be empty for {self.tariff_id}. "
                f"Use None when no {field_name} is available."
            )

        if len(value) > maximum_length:
            raise ValueError(
                f"{field_name} for {self.tariff_id} contains "
                f"{len(value)} characters. Use no more than {maximum_length}."
            )

    def _validate_enums(self) -> None:
        """Validate tariff type and lifecycle status."""
        if not isinstance(self.tariff_type, TariffType):
            raise TypeError(
                f"Invalid tariff_type '{self.tariff_type}' for "
                f"{self.tariff_id}. Use a TariffType value."
            )

        if not isinstance(self.status, TariffStatus):
            raise TypeError(
                f"Invalid status '{self.status}' for {self.tariff_id}. "
                "Use a TariffStatus value."
            )

    def _validate_dates(self) -> None:
        """Validate tariff effective dates and lifecycle consistency."""
        if not isinstance(self.effective_from, date):
            raise TypeError(
                f"Invalid effective_from '{self.effective_from}' for "
                f"{self.tariff_id}. Use a datetime.date value."
            )

        if self.effective_to is not None and not isinstance(self.effective_to, date):
            raise TypeError(
                f"Invalid effective_to '{self.effective_to}' for "
                f"{self.tariff_id}. Use a datetime.date value or None."
            )

        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError(
                f"effective_to '{self.effective_to}' for {self.tariff_id} "
                f"occurs before effective_from '{self.effective_from}'."
            )

        if self.status is TariffStatus.EXPIRED and self.effective_to is None:
            raise ValueError(
                f"Tariff {self.tariff_id} has status 'expired' but "
                "effective_to is missing."
            )

        if self.status is TariffStatus.ACTIVE:
            if self.effective_from > date.today():
                raise ValueError(
                    f"Tariff {self.tariff_id} has status 'active' but "
                    f"effective_from '{self.effective_from}' is in the future."
                )

            if self.effective_to is not None and self.effective_to < date.today():
                raise ValueError(
                    f"Tariff {self.tariff_id} has status 'active' but "
                    f"effective_to '{self.effective_to}' is in the past."
                )

    def _validate_numeric_fields(self) -> None:
        """Validate tariff rates and escalation percentage."""
        self._validate_non_negative_number(
            field_name="energy_rate_per_kwh",
            value=self.energy_rate_per_kwh,
        )
        self._validate_non_negative_number(
            field_name="demand_rate_per_kw",
            value=self.demand_rate_per_kw,
            allow_none=True,
        )
        self._validate_non_negative_number(
            field_name="escalation_rate_pct",
            value=self.escalation_rate_pct,
        )

        if self.escalation_rate_pct > 100.0:
            raise ValueError(
                f"Invalid escalation_rate_pct '{self.escalation_rate_pct}' "
                f"for {self.tariff_id}. Use a value between 0 and 100."
            )

    def _validate_non_negative_number(
        self,
        field_name: str,
        value: float | None,
        *,
        allow_none: bool = False,
    ) -> None:
        """Validate a finite non-negative numeric field."""
        if value is None:
            if allow_none:
                return
            raise TypeError(
                f"Invalid {field_name} 'None' for {self.tariff_id}. "
                "Use a finite non-negative numeric value."
            )

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(
                f"Invalid {field_name} '{value}' for {self.tariff_id}. "
                "Use a finite non-negative numeric value."
            )

        if not math.isfinite(value):
            raise ValueError(
                f"Invalid {field_name} '{value}' for {self.tariff_id}. "
                "The value must be finite."
            )

        if value < 0:
            raise ValueError(
                f"Invalid {field_name} '{value}' for {self.tariff_id}. "
                "The value must be greater than or equal to zero."
            )

    @property
    def is_current(self) -> bool:
        """Return whether the tariff is currently effective and active."""
        today = date.today()
        within_start = self.effective_from <= today
        within_end = self.effective_to is None or today <= self.effective_to
        return self.status is TariffStatus.ACTIVE and within_start and within_end

    @property
    def duration_days(self) -> int | None:
        """Return the inclusive tariff duration in days when bounded."""
        if self.effective_to is None:
            return None

        return (self.effective_to - self.effective_from).days + 1

    def calculate_energy_revenue(self, energy_kwh: float) -> float:
        """Return energy revenue for the supplied exported energy."""
        self._validate_runtime_number(
            field_name="energy_kwh",
            value=energy_kwh,
        )
        return round(energy_kwh * self.energy_rate_per_kwh, 2)

    def calculate_demand_charge(self, demand_kw: float) -> float:
        """Return demand charge for the supplied demand value."""
        self._validate_runtime_number(
            field_name="demand_kw",
            value=demand_kw,
        )

        if self.demand_rate_per_kw is None:
            return 0.0

        return round(demand_kw * self.demand_rate_per_kw, 2)

    def calculate_total_value(
        self,
        *,
        energy_kwh: float,
        demand_kw: float = 0.0,
    ) -> float:
        """Return total tariff value from energy and demand components."""
        return round(
            self.calculate_energy_revenue(energy_kwh)
            + self.calculate_demand_charge(demand_kw),
            2,
        )

    @staticmethod
    def _validate_runtime_number(field_name: str, value: float) -> None:
        """Validate a finite non-negative runtime calculation input."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(
                f"Invalid {field_name} '{value}'. "
                "Use a finite non-negative numeric value."
            )

        if not math.isfinite(value):
            raise ValueError(
                f"Invalid {field_name} '{value}'. The value must be finite."
            )

        if value < 0:
            raise ValueError(
                f"Invalid {field_name} '{value}'. "
                "The value must be greater than or equal to zero."
            )

    def to_record(self) -> dict[str, Any]:
        """Return a serialization-ready tariff record."""
        record = asdict(self)
        record["tariff_type"] = self.tariff_type.value
        record["status"] = self.status.value
        record["effective_from"] = self.effective_from.isoformat()
        record["effective_to"] = (
            self.effective_to.isoformat() if self.effective_to is not None else None
        )
        record["is_current"] = self.is_current
        record["duration_days"] = self.duration_days
        return record
