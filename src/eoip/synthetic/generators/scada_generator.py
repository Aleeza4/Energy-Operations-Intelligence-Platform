"""
SCADA time-series generator for EOIP synthetic data generation.

This module creates deterministic, validated SCADAObservation records for
generation equipment in the synthetic solar-plant portfolio. It combines
plant capacity, equipment ratings, daylight behavior, weather conditions,
availability states, and bounded electrical measurements while preserving the
15-minute interval and operational-consistency rules enforced by the
SCADAObservation domain model.
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
from eoip.synthetic.generators.weather_generator import (
    WeatherGeneratorConfig,
    generate_weather,
)
from eoip.synthetic.models.equipment import Equipment, EquipmentType
from eoip.synthetic.models.scada import (
    SCADAObservation,
    SCADAOperatingState,
    SCADAQuality,
)

_DEFAULT_RANDOM_SEED: Final[int] = 42
_DEFAULT_INTERVAL_MINUTES: Final[int] = 15
_DEFAULT_DURATION_DAYS: Final[int] = 7
_DEFAULT_START_AT: Final[datetime] = datetime(2025, 1, 1, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class SCADAGeneratorConfig:
    """Configuration for deterministic synthetic SCADA generation."""

    start_at: datetime = _DEFAULT_START_AT
    duration_days: int = _DEFAULT_DURATION_DAYS
    interval_minutes: int = _DEFAULT_INTERVAL_MINUTES
    random_seed: int = _DEFAULT_RANDOM_SEED
    derating_probability: float = 0.015
    forced_outage_probability: float = 0.003
    maintenance_probability: float = 0.001
    estimated_probability: float = 0.01
    missing_probability: float = 0.001
    inverter_efficiency: float = 0.975
    nominal_ac_voltage_v: float = 400.0
    nominal_frequency_hz: float = 50.0
    nominal_power_factor: float = 0.99

    def __post_init__(self) -> None:
        """Validate generator configuration."""
        if not isinstance(self.start_at, datetime):
            raise TypeError("start_at must be a timezone-aware datetime value.")

        if self.start_at.tzinfo is None or self.start_at.utcoffset() is None:
            raise ValueError("start_at must be timezone-aware.")

        self._validate_positive_integer(
            field_name="duration_days",
            value=self.duration_days,
        )
        self._validate_positive_integer(
            field_name="interval_minutes",
            value=self.interval_minutes,
        )

        if self.interval_minutes != 15:
            raise ValueError(
                "interval_minutes must be 15 to match SCADAObservation "
                "alignment and EOIP Phase 2 requirements."
            )

        if isinstance(self.random_seed, bool) or not isinstance(
            self.random_seed,
            int,
        ):
            raise TypeError("random_seed must be an integer.")

        probability_fields = (
            "derating_probability",
            "forced_outage_probability",
            "maintenance_probability",
            "estimated_probability",
            "missing_probability",
        )
        for field_name in probability_fields:
            self._validate_probability(
                field_name=field_name,
                value=getattr(self, field_name),
            )

        state_probability_sum = (
            self.derating_probability
            + self.forced_outage_probability
            + self.maintenance_probability
        )
        if state_probability_sum > 1.0:
            raise ValueError(
                "derating_probability, forced_outage_probability, and "
                "maintenance_probability must not exceed 1.0 in total."
            )

        quality_probability_sum = self.estimated_probability + self.missing_probability
        if quality_probability_sum > 1.0:
            raise ValueError(
                "estimated_probability plus missing_probability " "must not exceed 1.0."
            )

        self._validate_bounded_number(
            field_name="inverter_efficiency",
            value=self.inverter_efficiency,
            minimum=0.0,
            maximum=1.0,
            strictly_positive=True,
        )
        self._validate_bounded_number(
            field_name="nominal_ac_voltage_v",
            value=self.nominal_ac_voltage_v,
            minimum=0.0,
            maximum=50_000.0,
            strictly_positive=True,
        )
        self._validate_bounded_number(
            field_name="nominal_frequency_hz",
            value=self.nominal_frequency_hz,
            minimum=0.0,
            maximum=70.0,
            strictly_positive=True,
        )
        self._validate_bounded_number(
            field_name="nominal_power_factor",
            value=self.nominal_power_factor,
            minimum=-1.0,
            maximum=1.0,
            strictly_positive=False,
        )

    @staticmethod
    def _validate_positive_integer(
        *,
        field_name: str,
        value: int,
    ) -> None:
        """Validate a strictly positive integer field."""
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
        """Validate a finite probability between zero and one."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{field_name} must be numeric.")

        if not math.isfinite(value):
            raise ValueError(f"{field_name} must be finite.")

        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{field_name} must be between 0.0 and 1.0.")

    @staticmethod
    def _validate_bounded_number(
        *,
        field_name: str,
        value: float,
        minimum: float,
        maximum: float,
        strictly_positive: bool,
    ) -> None:
        """Validate a finite numeric field inside inclusive bounds."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{field_name} must be numeric.")

        if not math.isfinite(value):
            raise ValueError(f"{field_name} must be finite.")

        if not minimum <= value <= maximum:
            raise ValueError(f"{field_name} must be between {minimum} and {maximum}.")

        if strictly_positive and value <= 0.0:
            raise ValueError(f"{field_name} must be greater than zero.")


def generate_scada(
    config: SCADAGeneratorConfig | None = None,
    *,
    plant_config: PlantGeneratorConfig | None = None,
    equipment_config: EquipmentGeneratorConfig | None = None,
    weather_config: WeatherGeneratorConfig | None = None,
) -> tuple[SCADAObservation, ...]:
    """
    Generate deterministic SCADA observations for generation equipment.

    Parameters
    ----------
    config:
        Optional SCADA-generator configuration.
    plant_config:
        Optional plant-generator configuration.
    equipment_config:
        Optional equipment-generator configuration.
    weather_config:
        Optional weather-generator configuration. Its start, duration, and
        interval must match the resolved SCADA configuration.

    Returns
    -------
    tuple[SCADAObservation, ...]
        Immutable collection of validated SCADA observations.
    """
    resolved_config = config or SCADAGeneratorConfig()
    resolved_weather_config = weather_config or WeatherGeneratorConfig(
        start_at=resolved_config.start_at,
        duration_days=resolved_config.duration_days,
        interval_minutes=resolved_config.interval_minutes,
        random_seed=resolved_config.random_seed,
        estimated_probability=resolved_config.estimated_probability,
        missing_probability=resolved_config.missing_probability,
    )

    _validate_time_config_compatibility(
        scada_config=resolved_config,
        weather_config=resolved_weather_config,
    )

    plants = generate_plants(plant_config)
    equipment = generate_equipment(
        equipment_config,
        plant_config=plant_config,
    )
    weather = generate_weather(
        resolved_weather_config,
        plant_config=plant_config,
        equipment_config=equipment_config,
    )

    plants_by_id = {plant.plant_id: plant for plant in plants}
    weather_by_plant_and_time = _weather_lookup(weather)
    generation_equipment = tuple(
        item
        for item in equipment
        if item.equipment_type
        in {
            EquipmentType.STRING_INVERTER,
            EquipmentType.CENTRAL_INVERTER,
        }
    )

    observations: list[SCADAObservation] = []

    for equipment_index, asset in enumerate(
        generation_equipment,
        start=1,
    ):
        plant = plants_by_id.get(asset.plant_id)
        if plant is None:
            raise ValueError(
                f"Equipment {asset.equipment_id} references unknown "
                f"plant_id '{asset.plant_id}'."
            )

        rng = random.Random(
            _equipment_seed(
                base_seed=resolved_config.random_seed,
                equipment_index=equipment_index,
            )
        )

        for timestamp in _timestamps(resolved_config):
            weather_observation = weather_by_plant_and_time.get(
                (asset.plant_id, timestamp)
            )
            if weather_observation is None:
                raise ValueError(
                    f"No weather observation found for plant "
                    f"{asset.plant_id} at {timestamp.isoformat()}."
                )

            observations.append(
                _generate_observation(
                    asset=asset,
                    plant_ac_capacity_mw=plant.ac_capacity_mw,
                    timestamp=timestamp,
                    ghi_wm2=weather_observation.ghi_wm2,
                    ambient_temperature_c=(weather_observation.ambient_temperature_c),
                    weather_quality=weather_observation.quality.value,
                    config=resolved_config,
                    rng=rng,
                )
            )

    return tuple(observations)


def generate_scada_records(
    config: SCADAGeneratorConfig | None = None,
    *,
    plant_config: PlantGeneratorConfig | None = None,
    equipment_config: EquipmentGeneratorConfig | None = None,
    weather_config: WeatherGeneratorConfig | None = None,
) -> tuple[dict[str, object], ...]:
    """Generate serialization-ready SCADA records."""
    return tuple(
        observation.to_record()
        for observation in generate_scada(
            config,
            plant_config=plant_config,
            equipment_config=equipment_config,
            weather_config=weather_config,
        )
    )


def _validate_time_config_compatibility(
    *,
    scada_config: SCADAGeneratorConfig,
    weather_config: WeatherGeneratorConfig,
) -> None:
    """Ensure weather and SCADA generators share one timeline."""
    if weather_config.start_at != scada_config.start_at:
        raise ValueError("weather_config.start_at must match SCADA start_at.")

    if weather_config.duration_days != scada_config.duration_days:
        raise ValueError("weather_config.duration_days must match SCADA duration_days.")

    if weather_config.interval_minutes != scada_config.interval_minutes:
        raise ValueError(
            "weather_config.interval_minutes must match SCADA " "interval_minutes."
        )


def _timestamps(
    config: SCADAGeneratorConfig,
) -> tuple[datetime, ...]:
    """Return the complete half-open SCADA timestamp sequence."""
    interval = timedelta(minutes=config.interval_minutes)
    total_intervals = config.duration_days * 1_440 // config.interval_minutes
    return tuple(config.start_at + index * interval for index in range(total_intervals))


def _weather_lookup(
    weather: tuple[object, ...],
) -> dict[tuple[str, datetime], object]:
    """Return one weather observation per plant and timestamp."""
    lookup: dict[tuple[str, datetime], object] = {}

    for observation in weather:
        plant_id = observation.plant_id
        timestamp = observation.timestamp
        key = (plant_id, timestamp)
        lookup.setdefault(key, observation)

    return lookup


def _generate_observation(
    *,
    asset: Equipment,
    plant_ac_capacity_mw: float,
    timestamp: datetime,
    ghi_wm2: float,
    ambient_temperature_c: float,
    weather_quality: str,
    config: SCADAGeneratorConfig,
    rng: random.Random,
) -> SCADAObservation:
    """Generate one validated SCADA observation."""
    quality = _sample_quality(
        config=config,
        weather_quality=weather_quality,
        rng=rng,
    )
    operating_state = _sample_operating_state(
        ghi_wm2=ghi_wm2,
        config=config,
        rng=rng,
    )

    equipment_available = operating_state not in {
        SCADAOperatingState.FAULT,
        SCADAOperatingState.MAINTENANCE,
    }
    grid_available = operating_state is not SCADAOperatingState.STOPPED

    if operating_state in {
        SCADAOperatingState.NIGHT,
        SCADAOperatingState.STOPPED,
        SCADAOperatingState.FAULT,
        SCADAOperatingState.MAINTENANCE,
    }:
        active_power_kw = 0.0
        interval_energy_kwh = 0.0
    else:
        rated_power_kw = asset.rated_power_kw or (plant_ac_capacity_mw * 1_000)
        irradiance_factor = _clamp(
            ghi_wm2 / 1_000.0,
            minimum=0.0,
            maximum=1.2,
        )
        temperature_factor = _temperature_derate(ambient_temperature_c)
        state_factor = (
            rng.uniform(0.55, 0.85)
            if operating_state is SCADAOperatingState.DERATED
            else rng.uniform(0.97, 1.01)
        )
        noise_factor = rng.uniform(0.985, 1.015)

        active_power_kw = _clamp(
            rated_power_kw
            * irradiance_factor
            * temperature_factor
            * state_factor
            * noise_factor
            * config.inverter_efficiency,
            minimum=0.0,
            maximum=min(50_000.0, rated_power_kw),
        )
        interval_energy_kwh = active_power_kw * (config.interval_minutes / 60.0)

    dc_voltage_v = _dc_voltage(
        active_power_kw=active_power_kw,
        operating_state=operating_state,
        rng=rng,
    )
    dc_current_a = _current(
        power_kw=active_power_kw,
        voltage_v=dc_voltage_v,
        multiplier=1_000.0,
    )

    ac_voltage_v = _ac_voltage(
        nominal_voltage_v=config.nominal_ac_voltage_v,
        operating_state=operating_state,
        rng=rng,
    )
    power_factor = _power_factor(
        nominal_power_factor=config.nominal_power_factor,
        operating_state=operating_state,
        rng=rng,
    )
    ac_current_a = _current(
        power_kw=active_power_kw,
        voltage_v=ac_voltage_v,
        multiplier=1_000.0 / max(power_factor, 0.01),
    )
    frequency_hz = _frequency(
        nominal_frequency_hz=config.nominal_frequency_hz,
        grid_available=grid_available,
        rng=rng,
    )

    if quality is SCADAQuality.MISSING:
        active_power_kw = 0.0
        interval_energy_kwh = 0.0
        dc_voltage_v = 0.0
        dc_current_a = 0.0
        ac_voltage_v = 0.0
        ac_current_a = 0.0
        frequency_hz = 0.0
        power_factor = 0.0
        operating_state = SCADAOperatingState.STOPPED
        equipment_available = False
        grid_available = False

    return SCADAObservation(
        plant_id=asset.plant_id,
        equipment_id=asset.equipment_id,
        timestamp=timestamp,
        active_power_kw=round(active_power_kw, 4),
        interval_energy_kwh=round(interval_energy_kwh, 4),
        dc_voltage_v=round(dc_voltage_v, 4),
        dc_current_a=round(dc_current_a, 4),
        ac_voltage_v=round(ac_voltage_v, 4),
        ac_current_a=round(ac_current_a, 4),
        frequency_hz=round(frequency_hz, 4),
        power_factor=round(power_factor, 4),
        equipment_available=equipment_available,
        grid_available=grid_available,
        operating_state=operating_state,
        quality=quality,
    )


def _sample_operating_state(
    *,
    ghi_wm2: float,
    config: SCADAGeneratorConfig,
    rng: random.Random,
) -> SCADAOperatingState:
    """Sample an operating state while preserving daylight behavior."""
    if ghi_wm2 <= 0.0:
        return SCADAOperatingState.NIGHT

    sample = rng.random()

    if sample < config.maintenance_probability:
        return SCADAOperatingState.MAINTENANCE

    if sample < (config.maintenance_probability + config.forced_outage_probability):
        return SCADAOperatingState.FAULT

    if sample < (
        config.maintenance_probability
        + config.forced_outage_probability
        + config.derating_probability
    ):
        return SCADAOperatingState.DERATED

    return SCADAOperatingState.NORMAL


def _sample_quality(
    *,
    config: SCADAGeneratorConfig,
    weather_quality: str,
    rng: random.Random,
) -> SCADAQuality:
    """Sample SCADA quality with weather quality as a lower bound."""
    if weather_quality == "missing":
        return SCADAQuality.MISSING

    sample = rng.random()

    if sample < config.missing_probability:
        return SCADAQuality.MISSING

    if (
        weather_quality == "estimated"
        or sample < config.missing_probability + config.estimated_probability
    ):
        return SCADAQuality.ESTIMATED

    return SCADAQuality.VALID


def _temperature_derate(ambient_temperature_c: float) -> float:
    """Return a bounded temperature derating factor."""
    if ambient_temperature_c <= 25.0:
        return 1.0

    derate = 1.0 - (ambient_temperature_c - 25.0) * 0.0035
    return _clamp(derate, minimum=0.75, maximum=1.0)


def _dc_voltage(
    *,
    active_power_kw: float,
    operating_state: SCADAOperatingState,
    rng: random.Random,
) -> float:
    """Generate bounded DC voltage."""
    if operating_state in {
        SCADAOperatingState.NIGHT,
        SCADAOperatingState.STOPPED,
        SCADAOperatingState.FAULT,
        SCADAOperatingState.MAINTENANCE,
    }:
        return 0.0

    base_voltage = 1_000.0 + rng.gauss(0.0, 18.0)
    load_adjustment = min(active_power_kw / 10_000.0, 1.0) * 20.0
    return _clamp(
        base_voltage - load_adjustment,
        minimum=0.0,
        maximum=2_000.0,
    )


def _ac_voltage(
    *,
    nominal_voltage_v: float,
    operating_state: SCADAOperatingState,
    rng: random.Random,
) -> float:
    """Generate bounded AC voltage."""
    if operating_state in {
        SCADAOperatingState.NIGHT,
        SCADAOperatingState.STOPPED,
        SCADAOperatingState.FAULT,
        SCADAOperatingState.MAINTENANCE,
    }:
        return 0.0

    return _clamp(
        nominal_voltage_v + rng.gauss(0.0, nominal_voltage_v * 0.01),
        minimum=0.0,
        maximum=50_000.0,
    )


def _power_factor(
    *,
    nominal_power_factor: float,
    operating_state: SCADAOperatingState,
    rng: random.Random,
) -> float:
    """Generate a bounded power factor."""
    if operating_state in {
        SCADAOperatingState.NIGHT,
        SCADAOperatingState.STOPPED,
        SCADAOperatingState.FAULT,
        SCADAOperatingState.MAINTENANCE,
    }:
        return 0.0

    return _clamp(
        nominal_power_factor + rng.gauss(0.0, 0.004),
        minimum=-1.0,
        maximum=1.0,
    )


def _frequency(
    *,
    nominal_frequency_hz: float,
    grid_available: bool,
    rng: random.Random,
) -> float:
    """Generate grid frequency."""
    if not grid_available:
        return 0.0

    return _clamp(
        nominal_frequency_hz + rng.gauss(0.0, 0.03),
        minimum=0.0,
        maximum=70.0,
    )


def _current(
    *,
    power_kw: float,
    voltage_v: float,
    multiplier: float,
) -> float:
    """Return bounded current derived from power and voltage."""
    if power_kw <= 0.0 or voltage_v <= 0.0:
        return 0.0

    current_a = power_kw * multiplier / voltage_v
    return _clamp(current_a, minimum=0.0, maximum=10_000.0)


def _equipment_seed(*, base_seed: int, equipment_index: int) -> int:
    """Return a stable independent seed for one equipment asset."""
    return base_seed * 100_000 + equipment_index


def _clamp(
    value: float,
    *,
    minimum: float,
    maximum: float,
) -> float:
    """Clamp a numeric value to inclusive bounds."""
    return max(minimum, min(value, maximum))
