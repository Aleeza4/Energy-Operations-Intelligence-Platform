"""
Weather time-series generator for EOIP synthetic data generation.

This module creates deterministic, validated WeatherObservation records for
the weather-station assets generated for the synthetic solar-plant portfolio.
It models daylight, seasonal irradiance, cloud attenuation, temperature,
module heating, wind, humidity, and weather-data quality without introducing
dependencies beyond the Python standard library and existing EOIP models.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final

from eoip.synthetic.generators.equipment_generator import (
    EquipmentGeneratorConfig,
    generate_equipment,
)
from eoip.synthetic.generators.plant_generator import (
    PlantGeneratorConfig,
    generate_plants,
)
from eoip.synthetic.models.equipment import EquipmentType
from eoip.synthetic.models.weather import (
    WeatherObservation,
    WeatherQuality,
)

_DEFAULT_RANDOM_SEED: Final[int] = 42
_DEFAULT_INTERVAL_MINUTES: Final[int] = 15
_DEFAULT_DURATION_DAYS: Final[int] = 7
_DEFAULT_START_AT: Final[datetime] = datetime(2025, 1, 1, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class WeatherGeneratorConfig:
    """Configuration for deterministic synthetic weather generation."""

    start_at: datetime = _DEFAULT_START_AT
    duration_days: int = _DEFAULT_DURATION_DAYS
    interval_minutes: int = _DEFAULT_INTERVAL_MINUTES
    random_seed: int = _DEFAULT_RANDOM_SEED
    estimated_probability: float = 0.01
    missing_probability: float = 0.001
    minimum_night_temperature_c: float = 10.0
    maximum_day_temperature_c: float = 42.0
    maximum_clear_sky_ghi_wm2: float = 1_050.0

    def __post_init__(self) -> None:
        """Validate weather-generator configuration."""
        if not isinstance(self.start_at, datetime):
            raise TypeError("start_at must be a timezone-aware datetime value.")

        if self.start_at.tzinfo is None or self.start_at.utcoffset() is None:
            raise ValueError("start_at must be timezone-aware, preferably in UTC.")

        self._validate_positive_integer(
            field_name="duration_days",
            value=self.duration_days,
        )
        self._validate_positive_integer(
            field_name="interval_minutes",
            value=self.interval_minutes,
        )

        if 1_440 % self.interval_minutes != 0:
            raise ValueError("interval_minutes must divide evenly into 1440 minutes.")

        if isinstance(self.random_seed, bool) or not isinstance(
            self.random_seed,
            int,
        ):
            raise TypeError("random_seed must be an integer.")

        self._validate_probability(
            field_name="estimated_probability",
            value=self.estimated_probability,
        )
        self._validate_probability(
            field_name="missing_probability",
            value=self.missing_probability,
        )

        if self.estimated_probability + self.missing_probability > 1.0:
            raise ValueError(
                "estimated_probability plus missing_probability " "must not exceed 1.0."
            )

        self._validate_finite_number(
            field_name="minimum_night_temperature_c",
            value=self.minimum_night_temperature_c,
        )
        self._validate_finite_number(
            field_name="maximum_day_temperature_c",
            value=self.maximum_day_temperature_c,
        )
        self._validate_finite_number(
            field_name="maximum_clear_sky_ghi_wm2",
            value=self.maximum_clear_sky_ghi_wm2,
        )

        if self.maximum_day_temperature_c <= self.minimum_night_temperature_c:
            raise ValueError(
                "maximum_day_temperature_c must be greater than "
                "minimum_night_temperature_c."
            )

        if not 0.0 < self.maximum_clear_sky_ghi_wm2 <= 1_500.0:
            raise ValueError(
                "maximum_clear_sky_ghi_wm2 must be greater than zero "
                "and no greater than 1500."
            )

    @staticmethod
    def _validate_positive_integer(
        *,
        field_name: str,
        value: int,
    ) -> None:
        """Validate a strictly positive integer configuration value."""
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{field_name} must be an integer.")

        if value <= 0:
            raise ValueError(f"{field_name} must be greater than zero.")

    @staticmethod
    def _validate_probability(
        *,
        field_name: str,
        value: float,
    ) -> None:
        """Validate a probability between zero and one."""
        WeatherGeneratorConfig._validate_finite_number(
            field_name=field_name,
            value=value,
        )

        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{field_name} must be between 0.0 and 1.0.")

    @staticmethod
    def _validate_finite_number(
        *,
        field_name: str,
        value: float,
    ) -> None:
        """Validate a finite numeric configuration value."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{field_name} must be numeric.")

        if not math.isfinite(value):
            raise ValueError(f"{field_name} must be finite.")


def generate_weather(
    config: WeatherGeneratorConfig | None = None,
    *,
    plant_config: PlantGeneratorConfig | None = None,
    equipment_config: EquipmentGeneratorConfig | None = None,
) -> tuple[WeatherObservation, ...]:
    """
    Generate deterministic weather observations for all weather stations.

    Parameters
    ----------
    config:
        Optional weather-generator configuration.
    plant_config:
        Optional plant-generator configuration.
    equipment_config:
        Optional equipment-generator configuration.

    Returns
    -------
    tuple[WeatherObservation, ...]
        Immutable collection of validated weather observations.
    """
    resolved_config = config or WeatherGeneratorConfig()
    plants = generate_plants(plant_config)
    equipment = generate_equipment(
        equipment_config,
        plant_config=plant_config,
    )

    plants_by_id = {plant.plant_id: plant for plant in plants}
    station_equipment = tuple(
        item
        for item in equipment
        if item.equipment_type is EquipmentType.WEATHER_STATION
    )

    if len(station_equipment) > 999:
        raise ValueError(
            "WeatherObservation supports at most 999 weather-station IDs "
            "in the WS-001 format."
        )

    observations: list[WeatherObservation] = []

    for station_index, station in enumerate(station_equipment, start=1):
        plant = plants_by_id.get(station.plant_id)

        if plant is None:
            raise ValueError(
                f"Weather-station equipment {station.equipment_id} "
                f"references unknown plant_id '{station.plant_id}'."
            )

        station_rng = random.Random(
            _station_seed(
                base_seed=resolved_config.random_seed,
                station_index=station_index,
            )
        )
        weather_station_id = f"WS-{station_index:03d}"

        for timestamp in _timestamps(resolved_config):
            observations.append(
                _generate_observation(
                    plant_id=plant.plant_id,
                    weather_station_id=weather_station_id,
                    latitude=plant.latitude,
                    longitude=plant.longitude,
                    timestamp=timestamp,
                    config=resolved_config,
                    rng=station_rng,
                )
            )

    return tuple(observations)


def generate_weather_records(
    config: WeatherGeneratorConfig | None = None,
    *,
    plant_config: PlantGeneratorConfig | None = None,
    equipment_config: EquipmentGeneratorConfig | None = None,
) -> tuple[dict[str, object], ...]:
    """Generate serialization-ready weather observation records."""
    return tuple(
        observation.to_record()
        for observation in generate_weather(
            config,
            plant_config=plant_config,
            equipment_config=equipment_config,
        )
    )


def _timestamps(
    config: WeatherGeneratorConfig,
) -> tuple[datetime, ...]:
    """Return all timestamps in the configured half-open time range."""
    interval = timedelta(minutes=config.interval_minutes)
    total_intervals = config.duration_days * 1_440 // config.interval_minutes

    return tuple(config.start_at + index * interval for index in range(total_intervals))


def _generate_observation(
    *,
    plant_id: str,
    weather_station_id: str,
    latitude: float,
    longitude: float,
    timestamp: datetime,
    config: WeatherGeneratorConfig,
    rng: random.Random,
) -> WeatherObservation:
    """Generate one validated weather observation."""
    quality = _sample_quality(config=config, rng=rng)

    if quality is WeatherQuality.MISSING:
        return WeatherObservation(
            plant_id=plant_id,
            weather_station_id=weather_station_id,
            timestamp=timestamp,
            ghi_wm2=0.0,
            dni_wm2=0.0,
            dhi_wm2=0.0,
            ambient_temperature_c=0.0,
            module_temperature_c=0.0,
            wind_speed_ms=0.0,
            relative_humidity_pct=0.0,
            quality=quality,
        )

    solar_factor = _solar_factor(
        timestamp=timestamp,
        latitude=latitude,
        longitude=longitude,
    )
    seasonal_factor = _seasonal_irradiance_factor(timestamp)
    cloud_factor = _cloud_attenuation(rng)

    clear_sky_ghi = config.maximum_clear_sky_ghi_wm2 * solar_factor * seasonal_factor
    ghi_wm2 = _clamp(
        clear_sky_ghi * cloud_factor + rng.gauss(0.0, 10.0),
        minimum=0.0,
        maximum=1_500.0,
    )

    if solar_factor <= 0.0:
        ghi_wm2 = 0.0
        dni_wm2 = 0.0
        dhi_wm2 = 0.0
    else:
        diffuse_fraction = _clamp(
            0.12 + (1.0 - cloud_factor) * 0.65,
            minimum=0.08,
            maximum=0.85,
        )
        dhi_wm2 = _clamp(
            ghi_wm2 * diffuse_fraction,
            minimum=0.0,
            maximum=1_500.0,
        )
        dni_wm2 = _clamp(
            (ghi_wm2 - dhi_wm2) / max(solar_factor, 0.12),
            minimum=0.0,
            maximum=1_500.0,
        )

    ambient_temperature_c = _ambient_temperature(
        timestamp=timestamp,
        solar_factor=solar_factor,
        config=config,
        rng=rng,
    )
    module_temperature_c = _clamp(
        ambient_temperature_c + ghi_wm2 * 0.028 - rng.uniform(0.0, 2.0),
        minimum=-40.0,
        maximum=120.0,
    )
    wind_speed_ms = _clamp(
        rng.weibullvariate(4.0, 2.0),
        minimum=0.0,
        maximum=70.0,
    )
    relative_humidity_pct = _clamp(
        78.0
        - solar_factor * 35.0
        - (ambient_temperature_c - 25.0) * 0.45
        + rng.gauss(0.0, 5.0),
        minimum=5.0,
        maximum=100.0,
    )

    if quality is WeatherQuality.ESTIMATED:
        ghi_wm2 *= 0.985
        dni_wm2 *= 0.985
        dhi_wm2 *= 0.985

    return WeatherObservation(
        plant_id=plant_id,
        weather_station_id=weather_station_id,
        timestamp=timestamp,
        ghi_wm2=round(ghi_wm2, 3),
        dni_wm2=round(dni_wm2, 3),
        dhi_wm2=round(dhi_wm2, 3),
        ambient_temperature_c=round(ambient_temperature_c, 3),
        module_temperature_c=round(module_temperature_c, 3),
        wind_speed_ms=round(wind_speed_ms, 3),
        relative_humidity_pct=round(relative_humidity_pct, 3),
        quality=quality,
    )


def _sample_quality(
    *,
    config: WeatherGeneratorConfig,
    rng: random.Random,
) -> WeatherQuality:
    """Sample deterministic weather-data quality."""
    sample = rng.random()

    if sample < config.missing_probability:
        return WeatherQuality.MISSING

    if sample < (config.missing_probability + config.estimated_probability):
        return WeatherQuality.ESTIMATED

    return WeatherQuality.VALID


def _solar_factor(
    *,
    timestamp: datetime,
    latitude: float,
    longitude: float,
) -> float:
    """Approximate normalized solar elevation from time and location."""
    day_of_year = timestamp.timetuple().tm_yday
    latitude_radians = math.radians(latitude)
    declination = math.radians(
        23.44 * math.sin(math.radians((360.0 / 365.0) * (day_of_year - 81)))
    )

    solar_time = timestamp.hour + timestamp.minute / 60.0 + longitude / 15.0
    hour_angle = math.radians(15.0 * (solar_time - 12.0))

    elevation_sine = math.sin(latitude_radians) * math.sin(declination) + math.cos(
        latitude_radians
    ) * math.cos(declination) * math.cos(hour_angle)

    return _clamp(
        elevation_sine,
        minimum=0.0,
        maximum=1.0,
    )


def _seasonal_irradiance_factor(timestamp: datetime) -> float:
    """Return a smooth annual irradiance multiplier."""
    day_of_year = timestamp.timetuple().tm_yday
    return 0.82 + 0.18 * math.sin(2.0 * math.pi * (day_of_year - 80) / 365.0)


def _cloud_attenuation(rng: random.Random) -> float:
    """Return a bounded cloud attenuation factor."""
    if rng.random() < 0.18:
        return rng.uniform(0.25, 0.75)

    return rng.uniform(0.82, 1.0)


def _ambient_temperature(
    *,
    timestamp: datetime,
    solar_factor: float,
    config: WeatherGeneratorConfig,
    rng: random.Random,
) -> float:
    """Generate ambient temperature from seasonal and diurnal effects."""
    day_of_year = timestamp.timetuple().tm_yday
    seasonal_offset = 7.0 * math.sin(2.0 * math.pi * (day_of_year - 120) / 365.0)
    temperature_span = (
        config.maximum_day_temperature_c - config.minimum_night_temperature_c
    )
    base_temperature = (
        config.minimum_night_temperature_c
        + temperature_span * solar_factor
        + seasonal_offset
    )

    return _clamp(
        base_temperature + rng.gauss(0.0, 1.2),
        minimum=-40.0,
        maximum=70.0,
    )


def _station_seed(*, base_seed: int, station_index: int) -> int:
    """Return a stable independent random seed for one weather station."""
    return base_seed * 10_000 + station_index


def _clamp(
    value: float,
    *,
    minimum: float,
    maximum: float,
) -> float:
    """Clamp a numeric value to inclusive bounds."""
    return max(minimum, min(value, maximum))
