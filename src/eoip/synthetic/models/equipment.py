"""
Common equipment domain model for EOIP synthetic data generation.

This module owns the authoritative Phase 2 master-data representation shared
by solar-plant equipment. Synthetic generators must use this model instead of
creating independent equipment dictionaries or duplicating common validation.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Any

_EQUIPMENT_ID_PATTERN = re.compile(r"^EQP-\d{5}$")
_PLANT_ID_PATTERN = re.compile(r"^PLANT-\d{3}$")


class EquipmentType(StrEnum):
    """Supported categories of solar-plant equipment."""

    STRING_INVERTER = "string_inverter"
    CENTRAL_INVERTER = "central_inverter"
    TRANSFORMER = "transformer"
    FEEDER = "feeder"
    WEATHER_STATION = "weather_station"
    REVENUE_METER = "revenue_meter"
    PROTECTION_RELAY = "protection_relay"


class EquipmentStatus(StrEnum):
    """Supported operational states for equipment."""

    OPERATIONAL = "operational"
    PLANNED_OUTAGE = "planned_outage"
    FORCED_OUTAGE = "forced_outage"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


@dataclass(frozen=True, slots=True)
class Equipment:
    """Immutable common master-data record for one plant asset."""

    equipment_id: str
    plant_id: str
    equipment_name: str
    equipment_type: EquipmentType
    manufacturer: str
    model_number: str
    serial_number: str
    commissioning_date: date
    rated_power_kw: float | None = None
    parent_equipment_id: str | None = None
    status: EquipmentStatus = EquipmentStatus.OPERATIONAL

    def __post_init__(self) -> None:
        """Normalize and validate equipment master data."""
        normalized_equipment_id = self.equipment_id.strip().upper()
        normalized_plant_id = self.plant_id.strip().upper()
        normalized_equipment_name = self.equipment_name.strip()
        normalized_manufacturer = self.manufacturer.strip()
        normalized_model_number = self.model_number.strip().upper()
        normalized_serial_number = self.serial_number.strip().upper()
        normalized_parent_id = (
            self.parent_equipment_id.strip().upper()
            if self.parent_equipment_id is not None
            else None
        )

        object.__setattr__(self, "equipment_id", normalized_equipment_id)
        object.__setattr__(self, "plant_id", normalized_plant_id)
        object.__setattr__(self, "equipment_name", normalized_equipment_name)
        object.__setattr__(self, "manufacturer", normalized_manufacturer)
        object.__setattr__(self, "model_number", normalized_model_number)
        object.__setattr__(self, "serial_number", normalized_serial_number)
        object.__setattr__(self, "parent_equipment_id", normalized_parent_id)

        if not _EQUIPMENT_ID_PATTERN.fullmatch(normalized_equipment_id):
            raise ValueError(
                f"Invalid equipment_id '{self.equipment_id}'. "
                "Use the format 'EQP-00001'."
            )

        if not _PLANT_ID_PATTERN.fullmatch(normalized_plant_id):
            raise ValueError(
                f"Invalid plant_id '{self.plant_id}' for {self.equipment_id}. "
                "Use the format 'PLANT-001'."
            )

        if not normalized_equipment_name:
            raise ValueError(
                f"equipment_name cannot be empty for {self.equipment_id}. "
                "Provide a descriptive equipment name."
            )

        if not isinstance(self.equipment_type, EquipmentType):
            raise TypeError(
                f"Invalid equipment_type '{self.equipment_type}' for "
                f"{self.equipment_id}. Use an EquipmentType value."
            )

        if not normalized_manufacturer:
            raise ValueError(
                f"manufacturer cannot be empty for {self.equipment_id}. "
                "Provide the equipment manufacturer."
            )

        if not normalized_model_number:
            raise ValueError(
                f"model_number cannot be empty for {self.equipment_id}. "
                "Provide the manufacturer's model number."
            )

        if not normalized_serial_number:
            raise ValueError(
                f"serial_number cannot be empty for {self.equipment_id}. "
                "Provide the equipment serial number."
            )

        if not isinstance(self.commissioning_date, date) or isinstance(
            self.commissioning_date,
            datetime,
        ):
            raise TypeError(
                f"Invalid commissioning_date '{self.commissioning_date}' for "
                f"{self.equipment_id}. Use a datetime.date value."
            )

        if self.commissioning_date > date.today():
            raise ValueError(
                f"Commissioning date '{self.commissioning_date}' for "
                f"{self.equipment_id} is in the future. Use a date on or "
                f"before '{date.today()}'."
            )

        if self.rated_power_kw is not None:
            if isinstance(self.rated_power_kw, bool) or not isinstance(
                self.rated_power_kw,
                (int, float),
            ):
                raise TypeError(
                    f"Invalid rated_power_kw '{self.rated_power_kw}' for "
                    f"{self.equipment_id}. Use a positive numeric value or None."
                )
            if not self.rated_power_kw > 0:
                raise ValueError(
                    f"Invalid rated_power_kw '{self.rated_power_kw}' for "
                    f"{self.equipment_id}. Rated power must be greater than zero."
                )

        if normalized_parent_id is not None:
            if not _EQUIPMENT_ID_PATTERN.fullmatch(normalized_parent_id):
                raise ValueError(
                    f"Invalid parent_equipment_id '{self.parent_equipment_id}' "
                    f"for {self.equipment_id}. Use the format 'EQP-00001'."
                )
            if normalized_parent_id == normalized_equipment_id:
                raise ValueError(
                    f"Invalid parent_equipment_id '{self.parent_equipment_id}' "
                    f"for {self.equipment_id}. Equipment cannot be its own parent."
                )

        if not isinstance(self.status, EquipmentStatus):
            raise TypeError(
                f"Invalid status '{self.status}' for {self.equipment_id}. "
                "Use an EquipmentStatus value."
            )

    @property
    def is_generation_equipment(self) -> bool:
        """Return whether the equipment converts solar DC power to AC power."""
        return self.equipment_type in {
            EquipmentType.STRING_INVERTER,
            EquipmentType.CENTRAL_INVERTER,
        }

    @property
    def is_available(self) -> bool:
        """Return whether the equipment is currently operational."""
        return self.status is EquipmentStatus.OPERATIONAL

    def to_record(self) -> dict[str, Any]:
        """Return a serialization-ready equipment master-data record."""
        record = asdict(self)
        record["commissioning_date"] = self.commissioning_date.isoformat()
        record["equipment_type"] = self.equipment_type.value
        record["status"] = self.status.value
        record["is_generation_equipment"] = self.is_generation_equipment
        record["is_available"] = self.is_available
        return record
