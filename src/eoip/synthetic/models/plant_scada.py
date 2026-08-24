"""
Plant-level SCADA domain model for EOIP synthetic data generation.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

_PLANT_ID_PATTERN = re.compile(r"^PLANT-\d{3}$")
_METER_ID_PATTERN = re.compile(r"^MTR-\d{5}$")
_INTERVAL_HOURS = 0.25


class PlantSCADAQuality(StrEnum):
    """Supported plant-level SCADA data-quality states."""

    VALID = "valid"
    ESTIMATED = "estimated"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class PlantSCADAObservation:
    """Immutable plant-level observation for one 15-minute interval."""

    plant_id: str
    meter_id: str
    timestamp: datetime
    gross_inverter_power_kw: float
    transformer_loss_kw: float
    collection_loss_kw: float
    export_power_kw: float
    import_power_kw: float
    interval_export_energy_kwh: float
    interval_import_energy_kwh: float
    cumulative_export_energy_kwh: float
    cumulative_import_energy_kwh: float
    grid_available: bool
    plant_available: bool
    quality: PlantSCADAQuality = PlantSCADAQuality.VALID

    def __post_init__(self) -> None:
        """Normalize identifiers and validate the observation."""
        object.__setattr__(self, "plant_id", self.plant_id.strip().upper())
        object.__setattr__(self, "meter_id", self.meter_id.strip().upper())

        self._validate_identifiers()
        self._validate_timestamp()
        self._validate_flags_and_quality()
        self._validate_numeric_fields()
        self._validate_energy_reconciliation()
        self._validate_operational_consistency()

    def _validate_identifiers(self) -> None:
        if not _PLANT_ID_PATTERN.fullmatch(self.plant_id):
            raise ValueError(
                f"Invalid plant_id '{self.plant_id}'. " "Use the format 'PLANT-001'."
            )
        if not _METER_ID_PATTERN.fullmatch(self.meter_id):
            raise ValueError(
                f"Invalid meter_id '{self.meter_id}'. " "Use the format 'MTR-00001'."
            )

    def _validate_timestamp(self) -> None:
        if not isinstance(self.timestamp, datetime):
            raise TypeError("timestamp must be a datetime value.")
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware.")
        if self.timestamp.second != 0 or self.timestamp.microsecond != 0:
            raise ValueError("timestamp seconds and microseconds must both be zero.")
        if self.timestamp.minute % 15 != 0:
            raise ValueError("timestamp must align to a 15-minute interval.")

    def _validate_flags_and_quality(self) -> None:
        if not isinstance(self.grid_available, bool):
            raise TypeError("grid_available must be a boolean.")
        if not isinstance(self.plant_available, bool):
            raise TypeError("plant_available must be a boolean.")
        if not isinstance(self.quality, PlantSCADAQuality):
            raise TypeError("quality must be a PlantSCADAQuality instance.")

    def _validate_numeric_fields(self) -> None:
        fields = {
            "gross_inverter_power_kw": self.gross_inverter_power_kw,
            "transformer_loss_kw": self.transformer_loss_kw,
            "collection_loss_kw": self.collection_loss_kw,
            "export_power_kw": self.export_power_kw,
            "import_power_kw": self.import_power_kw,
            "interval_export_energy_kwh": self.interval_export_energy_kwh,
            "interval_import_energy_kwh": self.interval_import_energy_kwh,
            "cumulative_export_energy_kwh": self.cumulative_export_energy_kwh,
            "cumulative_import_energy_kwh": self.cumulative_import_energy_kwh,
        }
        for name, value in fields.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be numeric.")
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite.")
            if value < 0:
                raise ValueError(f"{name} must be greater than or equal to zero.")

    def _validate_energy_reconciliation(self) -> None:
        if not math.isclose(
            self.interval_export_energy_kwh,
            self.export_power_kw * _INTERVAL_HOURS,
            rel_tol=1e-6,
            abs_tol=1e-4,
        ):
            raise ValueError(
                "interval_export_energy_kwh must equal export_power_kw "
                "multiplied by 0.25 hours."
            )
        if not math.isclose(
            self.interval_import_energy_kwh,
            self.import_power_kw * _INTERVAL_HOURS,
            rel_tol=1e-6,
            abs_tol=1e-4,
        ):
            raise ValueError(
                "interval_import_energy_kwh must equal import_power_kw "
                "multiplied by 0.25 hours."
            )

    def _validate_operational_consistency(self) -> None:
        maximum_export = max(
            self.gross_inverter_power_kw
            - self.transformer_loss_kw
            - self.collection_loss_kw,
            0.0,
        )
        if self.export_power_kw > maximum_export + 1e-4:
            raise ValueError(
                "export_power_kw cannot exceed gross inverter power "
                "after transformer and collection losses."
            )
        if self.export_power_kw > 0 and self.import_power_kw > 0:
            raise ValueError(
                "export_power_kw and import_power_kw cannot both be positive."
            )
        if not self.grid_available and self.export_power_kw > 0:
            raise ValueError(
                "Grid-unavailable intervals cannot contain exported power."
            )
        if not self.plant_available and (
            self.gross_inverter_power_kw > 0 or self.export_power_kw > 0
        ):
            raise ValueError("Plant-unavailable intervals cannot contain generation.")
        if self.quality is PlantSCADAQuality.MISSING:
            interval_values = (
                self.gross_inverter_power_kw,
                self.transformer_loss_kw,
                self.collection_loss_kw,
                self.export_power_kw,
                self.import_power_kw,
                self.interval_export_energy_kwh,
                self.interval_import_energy_kwh,
            )
            if any(value != 0 for value in interval_values):
                raise ValueError(
                    "Missing-quality observations must use zero interval "
                    "measurement values."
                )

    @property
    def total_loss_kw(self) -> float:
        """Return total transformer and collection losses."""
        return round(
            self.transformer_loss_kw + self.collection_loss_kw,
            6,
        )

    @property
    def delivered_power_before_grid_kw(self) -> float:
        """Return power remaining after electrical losses."""
        return round(
            max(self.gross_inverter_power_kw - self.total_loss_kw, 0.0),
            6,
        )

    @property
    def net_power_kw(self) -> float:
        """Return signed settlement-boundary power."""
        return round(self.export_power_kw - self.import_power_kw, 6)

    @property
    def is_exporting(self) -> bool:
        """Return whether the plant exports power."""
        return self.export_power_kw > 0

    @property
    def is_importing(self) -> bool:
        """Return whether the plant imports auxiliary power."""
        return self.import_power_kw > 0

    def to_record(self) -> dict[str, Any]:
        """Return a serialization-ready plant-SCADA record."""
        record = asdict(self)
        record["timestamp"] = self.timestamp.isoformat()
        record["quality"] = self.quality.value
        record["total_loss_kw"] = self.total_loss_kw
        record["delivered_power_before_grid_kw"] = self.delivered_power_before_grid_kw
        record["net_power_kw"] = self.net_power_kw
        record["is_exporting"] = self.is_exporting
        record["is_importing"] = self.is_importing
        return record


__all__ = ["PlantSCADAObservation", "PlantSCADAQuality"]
