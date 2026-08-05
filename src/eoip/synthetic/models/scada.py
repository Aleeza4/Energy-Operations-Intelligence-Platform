"""
SCADA telemetry domain model for EOIP synthetic data generation.

This module defines the authoritative representation of one 15-minute
equipment telemetry observation. Synthetic SCADA generators, ETL pipelines,
analytics, anomaly detection, and predictive-maintenance components must use
this model instead of creating independent telemetry dictionaries.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from eoip.core.constants import SCADA_SAMPLE_INTERVAL_MINUTES

_PLANT_ID_PATTERN = re.compile(r"^PLANT-\d{3}$")
_EQUIPMENT_ID_PATTERN = re.compile(r"^EQP-\d{5}$")


class SCADAOperatingState(StrEnum):
    """Supported operating states for a SCADA telemetry observation."""

    NORMAL = "normal"
    DERATED = "derated"
    STOPPED = "stopped"
    FAULT = "fault"
    MAINTENANCE = "maintenance"
    NIGHT = "night"


class SCADAQuality(StrEnum):
    """Supported data-quality states for SCADA telemetry."""

    VALID = "valid"
    ESTIMATED = "estimated"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class SCADAObservation:
    """Immutable 15-minute telemetry observation for one plant asset."""

    plant_id: str
    equipment_id: str
    timestamp: datetime
    active_power_kw: float
    interval_energy_kwh: float
    dc_voltage_v: float
    dc_current_a: float
    ac_voltage_v: float
    ac_current_a: float
    frequency_hz: float
    power_factor: float
    equipment_available: bool
    grid_available: bool
    operating_state: SCADAOperatingState
    quality: SCADAQuality = SCADAQuality.VALID

    def __post_init__(self) -> None:
        """Normalize identifiers and validate the telemetry observation."""
        normalized_plant_id = self.plant_id.strip().upper()
        normalized_equipment_id = self.equipment_id.strip().upper()

        object.__setattr__(self, "plant_id", normalized_plant_id)
        object.__setattr__(self, "equipment_id", normalized_equipment_id)

        if not _PLANT_ID_PATTERN.fullmatch(normalized_plant_id):
            raise ValueError(
                f"Invalid plant_id '{self.plant_id}'. "
                "Use the format 'PLANT-001'."
            )

        if not _EQUIPMENT_ID_PATTERN.fullmatch(normalized_equipment_id):
            raise ValueError(
                f"Invalid equipment_id '{self.equipment_id}'. "
                "Use the format 'EQP-00001'."
            )

        self._validate_timestamp()
        self._validate_numeric_measurements()
        self._validate_boolean_fields()
        self._validate_enums()
        self._validate_operational_consistency()

    def _validate_timestamp(self) -> None:
        """
        Validate the timestamp type, timezone awareness, and interval alignment.

        Raises
        ------
        TypeError
            If the timestamp is not a datetime value.
        ValueError
            If the timestamp is timezone-naive or is not aligned to a
            15-minute SCADA interval.
        """
        if not isinstance(self.timestamp, datetime):
            raise TypeError(
                f"Invalid timestamp '{self.timestamp}' for "
                f"{self.equipment_id}. Use a datetime value."
            )

        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError(
                f"Timestamp '{self.timestamp}' for {self.equipment_id} is "
                "timezone-naive. Use a timezone-aware datetime, preferably UTC."
            )

        is_interval_aligned = (
            self.timestamp.minute % SCADA_SAMPLE_INTERVAL_MINUTES == 0
            and self.timestamp.second == 0
            and self.timestamp.microsecond == 0
        )

        if not is_interval_aligned:
            raise ValueError(
                f"Timestamp '{self.timestamp.isoformat()}' for "
                f"{self.equipment_id} is not aligned to the required "
                f"{SCADA_SAMPLE_INTERVAL_MINUTES}-minute SCADA interval. "
                "Use minutes 00, 15, 30, or 45 with zero seconds and "
                "microseconds."
            )

    def _validate_numeric_measurements(self) -> None:
        """Validate all numeric SCADA measurements and accepted ranges."""
        measurements: tuple[tuple[str, float, float, float], ...] = (
            ("active_power_kw", self.active_power_kw, 0.0, 50_000.0),
            (
                "interval_energy_kwh",
                self.interval_energy_kwh,
                0.0,
                12_500.0,
            ),
            ("dc_voltage_v", self.dc_voltage_v, 0.0, 2_000.0),
            ("dc_current_a", self.dc_current_a, 0.0, 10_000.0),
            ("ac_voltage_v", self.ac_voltage_v, 0.0, 50_000.0),
            ("ac_current_a", self.ac_current_a, 0.0, 10_000.0),
            ("frequency_hz", self.frequency_hz, 0.0, 70.0),
            ("power_factor", self.power_factor, -1.0, 1.0),
        )

        for field_name, value, minimum, maximum in measurements:
            self._validate_numeric_range(
                field_name=field_name,
                value=value,
                minimum=minimum,
                maximum=maximum,
            )

    def _validate_boolean_fields(self) -> None:
        """
        Validate availability fields.

        Raises
        ------
        TypeError
            If either availability field is not a boolean value.
        """
        if not isinstance(self.equipment_available, bool):
            raise TypeError(
                f"Invalid equipment_available value "
                f"'{self.equipment_available}' for {self.equipment_id}. "
                "Use True or False."
            )

        if not isinstance(self.grid_available, bool):
            raise TypeError(
                f"Invalid grid_available value '{self.grid_available}' for "
                f"{self.equipment_id}. Use True or False."
            )

    def _validate_enums(self) -> None:
        """
        Validate SCADA operating state and data quality.

        Raises
        ------
        TypeError
            If an enum field is not an instance of its required enum.
        """
        if not isinstance(self.operating_state, SCADAOperatingState):
            raise TypeError(
                f"Invalid operating_state '{self.operating_state}' for "
                f"{self.equipment_id}. Use a SCADAOperatingState value."
            )

        if not isinstance(self.quality, SCADAQuality):
            raise TypeError(
                f"Invalid quality '{self.quality}' for {self.equipment_id}. "
                "Use a SCADAQuality value."
            )

    def _validate_operational_consistency(self) -> None:
        """
        Validate relationships between power, availability, and operating state.

        Raises
        ------
        ValueError
            If measurements conflict with availability or operating state.
        """
        if not self.equipment_available and (
            self.active_power_kw > 0 or self.interval_energy_kwh > 0
        ):
            raise ValueError(
                f"SCADA observation for {self.equipment_id} reports "
                "equipment_available=False but contains positive active power "
                "or interval energy. Set both generation values to zero."
            )

        if not self.grid_available and (
            self.active_power_kw > 0 or self.interval_energy_kwh > 0
        ):
            raise ValueError(
                f"SCADA observation for {self.equipment_id} reports "
                "grid_available=False but contains positive active power or "
                "interval energy. Set both generation values to zero."
            )

        non_generating_states = {
            SCADAOperatingState.STOPPED,
            SCADAOperatingState.FAULT,
            SCADAOperatingState.MAINTENANCE,
            SCADAOperatingState.NIGHT,
        }

        if self.operating_state in non_generating_states and (
            self.active_power_kw > 0 or self.interval_energy_kwh > 0
        ):
            raise ValueError(
                f"Operating state '{self.operating_state.value}' for "
                f"{self.equipment_id} requires active_power_kw and "
                "interval_energy_kwh to both be zero."
            )

        if self.operating_state is SCADAOperatingState.NORMAL and (
            not self.equipment_available or not self.grid_available
        ):
            raise ValueError(
                f"Operating state 'normal' for {self.equipment_id} requires "
                "equipment_available=True and grid_available=True."
            )

    @staticmethod
    def _validate_numeric_range(
        field_name: str,
        value: float,
        minimum: float,
        maximum: float,
    ) -> None:
        """
        Validate that a measurement is finite, numeric, and within range.

        Parameters
        ----------
        field_name:
            Measurement field being validated.
        value:
            Measurement value.
        minimum:
            Inclusive minimum accepted value.
        maximum:
            Inclusive maximum accepted value.

        Raises
        ------
        TypeError
            If the value is not numeric or is a boolean.
        ValueError
            If the value is non-finite or outside the accepted range.
        """
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(
                f"Invalid {field_name} value '{value}'. Use a numeric value "
                f"between {minimum} and {maximum}."
            )

        if not math.isfinite(value):
            raise ValueError(
                f"Invalid {field_name} value '{value}'. "
                "SCADA measurements must be finite numeric values."
            )

        if not minimum <= value <= maximum:
            raise ValueError(
                f"Invalid {field_name} value '{value}'. Expected a value "
                f"between {minimum} and {maximum}, inclusive."
            )

    @property
    def is_exporting(self) -> bool:
        """Return whether the asset is producing exportable active power."""
        return (
            self.active_power_kw > 0
            and self.equipment_available
            and self.grid_available
        )

    @property
    def calculated_interval_energy_kwh(self) -> float:
        """Return expected 15-minute energy derived from active power."""
        interval_hours = SCADA_SAMPLE_INTERVAL_MINUTES / 60
        return round(self.active_power_kw * interval_hours, 4)

    @property
    def energy_deviation_kwh(self) -> float:
        """Return reported minus power-derived interval energy."""
        return round(
            self.interval_energy_kwh - self.calculated_interval_energy_kwh,
            4,
        )

    def to_record(self) -> dict[str, Any]:
        """Return a serialization-ready SCADA telemetry record."""
        record = asdict(self)
        record["timestamp"] = self.timestamp.isoformat()
        record["operating_state"] = self.operating_state.value
        record["quality"] = self.quality.value
        record["is_exporting"] = self.is_exporting
        record["calculated_interval_energy_kwh"] = (
            self.calculated_interval_energy_kwh
        )
        record["energy_deviation_kwh"] = self.energy_deviation_kwh
        return record