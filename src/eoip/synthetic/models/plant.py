"""
Plant domain model for EOIP synthetic data generation.

This module defines the authoritative representation of a utility-scale solar
plant. All Phase 2 generators that require plant information must use this
model rather than creating independent plant dictionaries or duplicate
validation logic.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum
from typing import Any

from eoip.core.constants import UTC_TIMEZONE_NAME

_PLANT_ID_PATTERN = re.compile(r"^PLANT-\d{3}$")


class PlantStatus(StrEnum):
    """Supported operational states for a solar plant."""

    OPERATIONAL = "operational"
    PLANNED_OUTAGE = "planned_outage"
    DECOMMISSIONED = "decommissioned"


@dataclass(frozen=True, slots=True)
class Plant:
    """Immutable master-data record for one utility-scale solar plant."""

    plant_id: str
    plant_name: str
    region: str
    latitude: float
    longitude: float
    dc_capacity_mw: float
    ac_capacity_mw: float
    commissioning_date: date
    status: PlantStatus = PlantStatus.OPERATIONAL
    timezone_name: str = UTC_TIMEZONE_NAME

    def __post_init__(self) -> None:
        """Validate plant master data immediately after initialization."""
        normalized_plant_id = self.plant_id.strip().upper()
        normalized_plant_name = self.plant_name.strip()
        normalized_region = self.region.strip()
        normalized_timezone = self.timezone_name.strip()

        object.__setattr__(self, "plant_id", normalized_plant_id)
        object.__setattr__(self, "plant_name", normalized_plant_name)
        object.__setattr__(self, "region", normalized_region)
        object.__setattr__(self, "timezone_name", normalized_timezone)

        if not _PLANT_ID_PATTERN.fullmatch(normalized_plant_id):
            raise ValueError(
                f"Invalid plant_id '{self.plant_id}'. "
                "Use the format 'PLANT-001', 'PLANT-002', and so on."
            )

        if not normalized_plant_name:
            raise ValueError(
                "plant_name cannot be empty. Provide a descriptive plant name."
            )

        if not normalized_region:
            raise ValueError(
                "region cannot be empty. Provide the plant's operational region."
            )

        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError(
                f"Invalid latitude '{self.latitude}' for {self.plant_id}. "
                "Latitude must be between -90 and 90 degrees."
            )

        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError(
                f"Invalid longitude '{self.longitude}' for {self.plant_id}. "
                "Longitude must be between -180 and 180 degrees."
            )

        if self.dc_capacity_mw <= 0:
            raise ValueError(
                f"Invalid dc_capacity_mw '{self.dc_capacity_mw}' for "
                f"{self.plant_id}. DC capacity must be greater than zero."
            )

        if self.ac_capacity_mw <= 0:
            raise ValueError(
                f"Invalid ac_capacity_mw '{self.ac_capacity_mw}' for "
                f"{self.plant_id}. AC capacity must be greater than zero."
            )

        if self.ac_capacity_mw > self.dc_capacity_mw:
            raise ValueError(
                f"AC capacity '{self.ac_capacity_mw} MW' exceeds DC capacity "
                f"'{self.dc_capacity_mw} MW' for {self.plant_id}. "
                "For the EOIP solar portfolio, AC capacity must not exceed "
                "installed DC capacity."
            )

        if self.commissioning_date > date.today():
            raise ValueError(
                f"Commissioning date '{self.commissioning_date}' for "
                f"{self.plant_id} is in the future. Use a date on or before "
                f"'{date.today()}'."
            )

        if not isinstance(self.status, PlantStatus):
            raise TypeError(
                f"Invalid status '{self.status}' for {self.plant_id}. "
                "Use a PlantStatus value."
            )

        if not normalized_timezone:
            raise ValueError(
                f"timezone_name cannot be empty for {self.plant_id}. "
                f"Use '{UTC_TIMEZONE_NAME}' unless another approved timezone "
                "is required."
            )

    @property
    def dc_ac_ratio(self) -> float:
        """Return the installed DC-to-AC capacity ratio."""
        return round(self.dc_capacity_mw / self.ac_capacity_mw, 4)

    def to_record(self) -> dict[str, Any]:
        """Return a serialization-ready plant master-data record."""
        record = asdict(self)
        record["commissioning_date"] = self.commissioning_date.isoformat()
        record["status"] = self.status.value
        record["dc_ac_ratio"] = self.dc_ac_ratio
        return record