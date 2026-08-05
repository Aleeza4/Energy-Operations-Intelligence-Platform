"""
Weather observation domain model for EOIP synthetic data generation.

This module defines the authoritative representation of one weather
measurement recorded for a solar plant at a specific timezone-aware timestamp.
Synthetic weather generators, SCADA generation, forecasting, and analytical
components must use this model instead of creating independent weather records.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

_PLANT_ID_PATTERN = re.compile(r"^PLANT-\d{3}$")
_WEATHER_STATION_ID_PATTERN = re.compile(r"^WS-\d{3}$")


class WeatherQuality(StrEnum):
    """Supported data-quality states for weather observations."""

    VALID = "valid"
    ESTIMATED = "estimated"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class WeatherObservation:
    """Immutable weather measurement for one plant and weather station."""

    plant_id: str
    weather_station_id: str
    timestamp: datetime
    ghi_wm2: float
    dni_wm2: float
    dhi_wm2: float
    ambient_temperature_c: float
    module_temperature_c: float
    wind_speed_ms: float
    relative_humidity_pct: float
    quality: WeatherQuality = WeatherQuality.VALID

    def __post_init__(self) -> None:
        """Normalize identifiers and validate the complete observation."""
        normalized_plant_id = self.plant_id.strip().upper()
        normalized_weather_station_id = self.weather_station_id.strip().upper()

        object.__setattr__(self, "plant_id", normalized_plant_id)
        object.__setattr__(
            self,
            "weather_station_id",
            normalized_weather_station_id,
        )

        if not _PLANT_ID_PATTERN.fullmatch(normalized_plant_id):
            raise ValueError(
                f"Invalid plant_id '{self.plant_id}'. "
                "Use the format 'PLANT-001'."
            )

        if not _WEATHER_STATION_ID_PATTERN.fullmatch(
            normalized_weather_station_id
        ):
            raise ValueError(
                f"Invalid weather_station_id '{self.weather_station_id}'. "
                "Use the format 'WS-001'."
            )

        if not isinstance(self.timestamp, datetime):
            raise TypeError(
                f"Invalid timestamp '{self.timestamp}' for "
                f"{self.weather_station_id}. Use a datetime value."
            )

        if (
            self.timestamp.tzinfo is None
            or self.timestamp.utcoffset() is None
        ):
            raise ValueError(
                f"Timestamp '{self.timestamp}' for "
                f"{self.weather_station_id} is timezone-naive. "
                "Use a timezone-aware datetime, preferably in UTC."
            )

        self._validate_numeric_range(
            field_name="ghi_wm2",
            value=self.ghi_wm2,
            minimum=0.0,
            maximum=1500.0,
        )
        self._validate_numeric_range(
            field_name="dni_wm2",
            value=self.dni_wm2,
            minimum=0.0,
            maximum=1500.0,
        )
        self._validate_numeric_range(
            field_name="dhi_wm2",
            value=self.dhi_wm2,
            minimum=0.0,
            maximum=1500.0,
        )
        self._validate_numeric_range(
            field_name="ambient_temperature_c",
            value=self.ambient_temperature_c,
            minimum=-40.0,
            maximum=70.0,
        )
        self._validate_numeric_range(
            field_name="module_temperature_c",
            value=self.module_temperature_c,
            minimum=-40.0,
            maximum=120.0,
        )
        self._validate_numeric_range(
            field_name="wind_speed_ms",
            value=self.wind_speed_ms,
            minimum=0.0,
            maximum=70.0,
        )
        self._validate_numeric_range(
            field_name="relative_humidity_pct",
            value=self.relative_humidity_pct,
            minimum=0.0,
            maximum=100.0,
        )

        if not isinstance(self.quality, WeatherQuality):
            raise TypeError(
                f"Invalid quality '{self.quality}' for "
                f"{self.weather_station_id}. "
                "Use a WeatherQuality value."
            )

    @staticmethod
    def _validate_numeric_range(
        field_name: str,
        value: float,
        minimum: float,
        maximum: float,
    ) -> None:
        """
        Validate that a weather measurement is numeric and within range.

        Parameters
        ----------
        field_name:
            Name of the field being validated.
        value:
            Measurement value.
        minimum:
            Inclusive minimum permitted value.
        maximum:
            Inclusive maximum permitted value.

        Raises
        ------
        TypeError
            If the value is not numeric or is a boolean.
        ValueError
            If the value is outside the accepted range.
        """
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(
                f"Invalid {field_name} value '{value}'. "
                f"Use a numeric value between {minimum} and {maximum}."
            )

        if not minimum <= value <= maximum:
            raise ValueError(
                f"Invalid {field_name} value '{value}'. "
                f"Expected a value between {minimum} and {maximum}, "
                "inclusive."
            )

    @property
    def total_horizontal_irradiance(self) -> float:
        """Return the combined global and diffuse horizontal irradiance."""
        return round(self.ghi_wm2 + self.dhi_wm2, 4)

    @property
    def is_daylight(self) -> bool:
        """Return whether the observation represents daylight conditions."""
        return self.ghi_wm2 > 0

    def to_record(self) -> dict[str, Any]:
        """Return a serialization-ready weather observation record."""
        record = asdict(self)
        record["timestamp"] = self.timestamp.isoformat()
        record["quality"] = self.quality.value
        record["total_horizontal_irradiance"] = (
            self.total_horizontal_irradiance
        )
        record["is_daylight"] = self.is_daylight
        return record