"""
Revenue-meter master-data domain model for EOIP synthetic generation.

This module defines the authoritative representation of one plant-level
settlement meter. Meter interval and cumulative readings are not stored here;
they belong to plant SCADA and must be derived from aggregated inverter SCADA.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum
from typing import Any

_METER_ID_PATTERN = re.compile(r"^MTR-\d{5}$")
_PLANT_ID_PATTERN = re.compile(r"^PLANT-\d{3}$")
_EQUIPMENT_ID_PATTERN = re.compile(r"^EQP-\d{5}$")


class MeterAccuracyClass(StrEnum):
    """Supported revenue-meter accuracy classes."""

    CLASS_02S = "0.2s"
    CLASS_05S = "0.5s"
    CLASS_1 = "1.0"


class MeterStatus(StrEnum):
    """Supported revenue-meter lifecycle states."""

    ACTIVE = "active"
    OUT_OF_SERVICE = "out_of_service"
    CALIBRATION_DUE = "calibration_due"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class RevenueMeter:
    """Immutable revenue-meter master-data record for one solar plant."""

    meter_id: str
    plant_id: str
    equipment_id: str
    meter_name: str
    manufacturer: str
    model_number: str
    serial_number: str
    accuracy_class: MeterAccuracyClass
    multiplier: float
    calibration_date: date
    status: MeterStatus = MeterStatus.ACTIVE
    is_primary: bool = True
    notes: str | None = None

    def __post_init__(self) -> None:
        """Normalize and validate the complete revenue-meter record."""
        normalized_meter_id = self.meter_id.strip().upper()
        normalized_plant_id = self.plant_id.strip().upper()
        normalized_equipment_id = self.equipment_id.strip().upper()
        normalized_meter_name = self.meter_name.strip()
        normalized_manufacturer = self.manufacturer.strip()
        normalized_model_number = self.model_number.strip().upper()
        normalized_serial_number = self.serial_number.strip().upper()
        normalized_notes = self.notes.strip() if self.notes is not None else None

        object.__setattr__(self, "meter_id", normalized_meter_id)
        object.__setattr__(self, "plant_id", normalized_plant_id)
        object.__setattr__(self, "equipment_id", normalized_equipment_id)
        object.__setattr__(self, "meter_name", normalized_meter_name)
        object.__setattr__(self, "manufacturer", normalized_manufacturer)
        object.__setattr__(self, "model_number", normalized_model_number)
        object.__setattr__(self, "serial_number", normalized_serial_number)
        object.__setattr__(self, "notes", normalized_notes)

        self._validate_identifiers()
        self._validate_text_fields()
        self._validate_enums()
        self._validate_multiplier()
        self._validate_calibration_date()
        self._validate_boolean_fields()

    def _validate_identifiers(self) -> None:
        """Validate meter, plant, and linked equipment identifiers."""
        if not _METER_ID_PATTERN.fullmatch(self.meter_id):
            raise ValueError(
                f"Invalid meter_id '{self.meter_id}'. " "Use the format 'MTR-00001'."
            )

        if not _PLANT_ID_PATTERN.fullmatch(self.plant_id):
            raise ValueError(
                f"Invalid plant_id '{self.plant_id}' for {self.meter_id}. "
                "Use the format 'PLANT-001'."
            )

        if not _EQUIPMENT_ID_PATTERN.fullmatch(self.equipment_id):
            raise ValueError(
                f"Invalid equipment_id '{self.equipment_id}' for "
                f"{self.meter_id}. Use the format 'EQP-00001'."
            )

    def _validate_text_fields(self) -> None:
        """Validate required and optional text fields."""
        required_fields = {
            "meter_name": (self.meter_name, 150),
            "manufacturer": (self.manufacturer, 100),
            "model_number": (self.model_number, 100),
            "serial_number": (self.serial_number, 100),
        }

        for field_name, (value, maximum_length) in required_fields.items():
            if not value:
                raise ValueError(f"{field_name} cannot be empty for {self.meter_id}.")
            if len(value) > maximum_length:
                raise ValueError(
                    f"{field_name} for {self.meter_id} contains "
                    f"{len(value)} characters. Use no more than "
                    f"{maximum_length}."
                )

        if self.notes is not None:
            if not self.notes:
                raise ValueError(
                    f"notes cannot be empty for {self.meter_id}. "
                    "Use None when no notes are available."
                )
            if len(self.notes) > 1_000:
                raise ValueError(
                    f"notes for {self.meter_id} contains "
                    f"{len(self.notes)} characters. Use no more than 1000."
                )

    def _validate_enums(self) -> None:
        """Validate meter accuracy class and lifecycle status."""
        if not isinstance(self.accuracy_class, MeterAccuracyClass):
            raise TypeError(
                f"accuracy_class must be MeterAccuracyClass for " f"{self.meter_id}."
            )

        if not isinstance(self.status, MeterStatus):
            raise TypeError(f"status must be MeterStatus for {self.meter_id}.")

    def _validate_multiplier(self) -> None:
        """Validate the positive finite meter multiplier."""
        value = self.multiplier

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("multiplier must be numeric.")

        if not math.isfinite(value):
            raise ValueError("multiplier must be finite.")

        if value <= 0:
            raise ValueError("multiplier must be greater than zero.")

    def _validate_calibration_date(self) -> None:
        """Validate the meter calibration date."""
        if not isinstance(self.calibration_date, date):
            raise TypeError("calibration_date must be a date value.")

    def _validate_boolean_fields(self) -> None:
        """Validate Boolean master-data flags."""
        if not isinstance(self.is_primary, bool):
            raise TypeError("is_primary must be a boolean.")

    @property
    def is_operational(self) -> bool:
        """Return whether the meter is available for settlement use."""
        return self.status in {
            MeterStatus.ACTIVE,
            MeterStatus.CALIBRATION_DUE,
        }

    @property
    def requires_attention(self) -> bool:
        """Return whether the meter requires operational attention."""
        return self.status in {
            MeterStatus.CALIBRATION_DUE,
            MeterStatus.OUT_OF_SERVICE,
        }

    def apply_multiplier(self, raw_register_value: float) -> float:
        """Return the engineering value for a raw meter register reading."""
        if isinstance(raw_register_value, bool) or not isinstance(
            raw_register_value,
            (int, float),
        ):
            raise TypeError("raw_register_value must be numeric.")

        if not math.isfinite(raw_register_value):
            raise ValueError("raw_register_value must be finite.")

        if raw_register_value < 0:
            raise ValueError(
                "raw_register_value must be greater than or equal to zero."
            )

        return round(raw_register_value * self.multiplier, 6)

    def to_record(self) -> dict[str, Any]:
        """Return a serialization-ready revenue-meter record."""
        record = asdict(self)
        record["accuracy_class"] = self.accuracy_class.value
        record["status"] = self.status.value
        record["calibration_date"] = self.calibration_date.isoformat()
        record["is_operational"] = self.is_operational
        record["requires_attention"] = self.requires_attention
        return record


__all__ = [
    "MeterAccuracyClass",
    "MeterStatus",
    "RevenueMeter",
]
