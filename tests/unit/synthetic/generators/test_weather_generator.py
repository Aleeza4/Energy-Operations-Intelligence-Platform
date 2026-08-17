"""
Unit tests for the EOIP synthetic weather generator.

These tests verify deterministic weather generation, configuration validation,
time-series length and alignment, station coverage, daylight behavior, quality
sampling, physical bounds, serialization, and WeatherObservation integrity.
"""

from __future__ import annotations

import math
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from eoip.synthetic.generators.equipment_generator import (
    EquipmentGeneratorConfig,
)
from eoip.synthetic.generators.plant_generator import (
    PlantGeneratorConfig,
)
from eoip.synthetic.generators.weather_generator import (
    WeatherGeneratorConfig,
    generate_weather,
    generate_weather_records,
)
from eoip.synthetic.models.weather import (
    WeatherObservation,
    WeatherQuality,
)


def _plant_config() -> PlantGeneratorConfig:
    """Return a compact deterministic plant configuration."""
    return PlantGeneratorConfig(
        plant_count=2,
        random_seed=11,
    )


def _equipment_config(
    *,
    weather_stations_per_plant: int = 1,
) -> EquipmentGeneratorConfig:
    """Return a compact deterministic equipment configuration."""
    return EquipmentGeneratorConfig(
        random_seed=22,
        string_inverters_per_plant=2,
        transformers_per_plant=1,
        feeders_per_plant=1,
        weather_stations_per_plant=weather_stations_per_plant,
        revenue_meters_per_plant=1,
        protection_relays_per_plant=1,
    )


def _weather_config(**overrides: Any) -> WeatherGeneratorConfig:
    """Return a compact deterministic weather configuration."""
    data: dict[str, Any] = {
        "start_at": datetime(2025, 1, 1, tzinfo=UTC),
        "duration_days": 1,
        "interval_minutes": 15,
        "random_seed": 33,
        "estimated_probability": 0.0,
        "missing_probability": 0.0,
    }
    data.update(overrides)
    return WeatherGeneratorConfig(**data)


def test_generate_weather_returns_tuple_of_observations() -> None:
    """The generator should return immutable WeatherObservation objects."""
    weather = generate_weather(
        _weather_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
    )

    assert isinstance(weather, tuple)
    assert weather
    assert all(isinstance(observation, WeatherObservation) for observation in weather)


def test_generate_weather_returns_expected_observation_count() -> None:
    """Observation count should equal stations multiplied by intervals."""
    plant_config = _plant_config()
    equipment_config = _equipment_config(weather_stations_per_plant=2)
    weather_config = _weather_config(
        duration_days=2,
        interval_minutes=30,
    )

    weather = generate_weather(
        weather_config,
        plant_config=plant_config,
        equipment_config=equipment_config,
    )

    intervals_per_station = 2 * 1_440 // 30
    station_count = (
        plant_config.plant_count * equipment_config.weather_stations_per_plant
    )

    assert len(weather) == station_count * intervals_per_station


def test_generate_weather_is_deterministic_for_same_configuration() -> None:
    """The same inputs should generate identical weather time series."""
    weather_config = _weather_config()
    plant_config = _plant_config()
    equipment_config = _equipment_config()

    first_result = generate_weather(
        weather_config,
        plant_config=plant_config,
        equipment_config=equipment_config,
    )
    second_result = generate_weather(
        weather_config,
        plant_config=plant_config,
        equipment_config=equipment_config,
    )

    assert first_result == second_result


def test_different_weather_seeds_change_generated_values() -> None:
    """Different weather seeds should change simulated measurements."""
    plant_config = _plant_config()
    equipment_config = _equipment_config()

    first_result = generate_weather(
        _weather_config(random_seed=1),
        plant_config=plant_config,
        equipment_config=equipment_config,
    )
    second_result = generate_weather(
        _weather_config(random_seed=2),
        plant_config=plant_config,
        equipment_config=equipment_config,
    )

    assert first_result != second_result
    assert tuple(item.timestamp for item in first_result) == tuple(
        item.timestamp for item in second_result
    )


def test_weather_station_ids_are_unique_and_sequential() -> None:
    """Weather stations should use sequential WS-001 identifiers."""
    weather = generate_weather(
        _weather_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(weather_stations_per_plant=2),
    )

    station_ids = tuple(
        sorted({observation.weather_station_id for observation in weather})
    )

    assert station_ids == (
        "WS-001",
        "WS-002",
        "WS-003",
        "WS-004",
    )


def test_every_station_has_same_number_of_observations() -> None:
    """Each weather station should receive a complete time series."""
    weather = generate_weather(
        _weather_config(
            duration_days=2,
            interval_minutes=60,
        ),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(weather_stations_per_plant=2),
    )

    counts: dict[str, int] = {}

    for observation in weather:
        counts[observation.weather_station_id] = (
            counts.get(observation.weather_station_id, 0) + 1
        )

    assert set(counts.values()) == {48}


def test_timestamps_begin_at_configured_start() -> None:
    """Every station should begin at the configured start timestamp."""
    start_at = datetime(2025, 3, 1, 6, 0, tzinfo=UTC)
    weather = generate_weather(
        _weather_config(start_at=start_at),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
    )

    first_by_station: dict[str, datetime] = {}

    for observation in weather:
        first_by_station.setdefault(
            observation.weather_station_id,
            observation.timestamp,
        )

    assert set(first_by_station.values()) == {start_at}


def test_timestamps_follow_configured_interval() -> None:
    """Consecutive station timestamps should use the configured interval."""
    weather = generate_weather(
        _weather_config(interval_minutes=30),
        plant_config=PlantGeneratorConfig(
            plant_count=1,
            random_seed=11,
        ),
        equipment_config=_equipment_config(),
    )

    timestamps = [
        observation.timestamp
        for observation in weather
        if observation.weather_station_id == "WS-001"
    ]

    assert all(
        later - earlier == timedelta(minutes=30)
        for earlier, later in zip(timestamps, timestamps[1:], strict=False)
    )


def test_time_range_is_half_open() -> None:
    """The final timestamp should be one interval before the end boundary."""
    config = _weather_config(
        duration_days=1,
        interval_minutes=60,
    )
    weather = generate_weather(
        config,
        plant_config=PlantGeneratorConfig(
            plant_count=1,
            random_seed=11,
        ),
        equipment_config=_equipment_config(),
    )

    station_weather = [
        observation
        for observation in weather
        if observation.weather_station_id == "WS-001"
    ]

    assert station_weather[0].timestamp == config.start_at
    assert station_weather[-1].timestamp == (config.start_at + timedelta(hours=23))


def test_generated_measurements_respect_model_bounds() -> None:
    """Every generated value should remain within WeatherObservation bounds."""
    weather = generate_weather(
        _weather_config(duration_days=3),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
    )

    for observation in weather:
        assert 0.0 <= observation.ghi_wm2 <= 1_500.0
        assert 0.0 <= observation.dni_wm2 <= 1_500.0
        assert 0.0 <= observation.dhi_wm2 <= 1_500.0
        assert -40.0 <= observation.ambient_temperature_c <= 70.0
        assert -40.0 <= observation.module_temperature_c <= 120.0
        assert 0.0 <= observation.wind_speed_ms <= 70.0
        assert 0.0 <= observation.relative_humidity_pct <= 100.0


def test_night_observations_have_zero_irradiance() -> None:
    """Night observations should report zero GHI, DNI, and DHI."""
    weather = generate_weather(
        _weather_config(
            start_at=datetime(2025, 6, 1, tzinfo=UTC),
            duration_days=2,
        ),
        plant_config=PlantGeneratorConfig(
            plant_count=1,
            random_seed=11,
        ),
        equipment_config=_equipment_config(),
    )

    night_observations = [
        observation for observation in weather if observation.is_daylight is False
    ]

    assert night_observations
    assert all(
        observation.ghi_wm2 == 0.0
        and observation.dni_wm2 == 0.0
        and observation.dhi_wm2 == 0.0
        for observation in night_observations
    )


def test_daylight_observations_exist() -> None:
    """A full-day time series should contain daylight observations."""
    weather = generate_weather(
        _weather_config(
            start_at=datetime(2025, 6, 1, tzinfo=UTC),
        ),
        plant_config=PlantGeneratorConfig(
            plant_count=1,
            random_seed=11,
        ),
        equipment_config=_equipment_config(),
    )

    daylight = [observation for observation in weather if observation.is_daylight]

    assert daylight
    assert all(observation.ghi_wm2 > 0.0 for observation in daylight)


def test_module_temperature_responds_to_irradiance() -> None:
    """Daylight module temperatures should generally exceed ambient values."""
    weather = generate_weather(
        _weather_config(
            start_at=datetime(2025, 6, 1, tzinfo=UTC),
        ),
        plant_config=PlantGeneratorConfig(
            plant_count=1,
            random_seed=11,
        ),
        equipment_config=_equipment_config(),
    )

    strong_daylight = [
        observation for observation in weather if observation.ghi_wm2 >= 300.0
    ]

    assert strong_daylight
    assert all(
        observation.module_temperature_c > observation.ambient_temperature_c
        for observation in strong_daylight
    )


def test_zero_quality_probabilities_generate_only_valid_data() -> None:
    """Zero quality-error probabilities should produce VALID records."""
    weather = generate_weather(
        _weather_config(
            estimated_probability=0.0,
            missing_probability=0.0,
        ),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
    )

    assert all(observation.quality is WeatherQuality.VALID for observation in weather)


def test_estimated_probability_one_generates_estimated_data() -> None:
    """An estimated probability of one should mark every record estimated."""
    weather = generate_weather(
        _weather_config(
            estimated_probability=1.0,
            missing_probability=0.0,
        ),
        plant_config=PlantGeneratorConfig(
            plant_count=1,
            random_seed=11,
        ),
        equipment_config=_equipment_config(),
    )

    assert all(
        observation.quality is WeatherQuality.ESTIMATED for observation in weather
    )


def test_missing_probability_one_generates_zeroed_missing_data() -> None:
    """A missing probability of one should create zeroed missing records."""
    weather = generate_weather(
        _weather_config(
            estimated_probability=0.0,
            missing_probability=1.0,
        ),
        plant_config=PlantGeneratorConfig(
            plant_count=1,
            random_seed=11,
        ),
        equipment_config=_equipment_config(),
    )

    assert weather
    assert all(observation.quality is WeatherQuality.MISSING for observation in weather)
    assert all(
        observation.ghi_wm2 == 0.0
        and observation.dni_wm2 == 0.0
        and observation.dhi_wm2 == 0.0
        and observation.ambient_temperature_c == 0.0
        and observation.module_temperature_c == 0.0
        and observation.wind_speed_ms == 0.0
        and observation.relative_humidity_pct == 0.0
        for observation in weather
    )


def test_each_observation_plant_id_is_valid() -> None:
    """Generated observations should reference generated plant IDs."""
    plant_config = _plant_config()
    valid_plant_ids = {
        f"PLANT-{index:03d}" for index in range(1, plant_config.plant_count + 1)
    }
    weather = generate_weather(
        _weather_config(),
        plant_config=plant_config,
        equipment_config=_equipment_config(),
    )

    assert all(observation.plant_id in valid_plant_ids for observation in weather)


def test_generate_weather_records_matches_model_serialization() -> None:
    """Generated records should match WeatherObservation.to_record output."""
    weather_config = _weather_config()
    plant_config = _plant_config()
    equipment_config = _equipment_config()

    observations = generate_weather(
        weather_config,
        plant_config=plant_config,
        equipment_config=equipment_config,
    )
    records = generate_weather_records(
        weather_config,
        plant_config=plant_config,
        equipment_config=equipment_config,
    )

    assert records == tuple(observation.to_record() for observation in observations)


def test_generate_weather_records_returns_primitive_values() -> None:
    """Serialized weather records should expose primitive values."""
    records = generate_weather_records(
        _weather_config(),
        plant_config=PlantGeneratorConfig(
            plant_count=1,
            random_seed=11,
        ),
        equipment_config=_equipment_config(),
    )
    record = records[0]

    assert isinstance(records, tuple)
    assert isinstance(record, dict)
    assert isinstance(record["timestamp"], str)
    assert isinstance(record["quality"], str)
    assert isinstance(record["is_daylight"], bool)
    assert isinstance(record["total_horizontal_irradiance"], float)


def test_generator_config_uses_expected_defaults() -> None:
    """WeatherGeneratorConfig should expose documented defaults."""
    config = WeatherGeneratorConfig()

    assert config.start_at == datetime(2025, 1, 1, tzinfo=UTC)
    assert config.duration_days == 7
    assert config.interval_minutes == 15
    assert config.random_seed == 42
    assert config.estimated_probability == 0.01
    assert config.missing_probability == 0.001
    assert config.minimum_night_temperature_c == 10.0
    assert config.maximum_day_temperature_c == 42.0
    assert config.maximum_clear_sky_ghi_wm2 == 1_050.0


def test_generator_config_is_immutable() -> None:
    """WeatherGeneratorConfig should be frozen."""
    config = WeatherGeneratorConfig()

    with pytest.raises(FrozenInstanceError):
        config.duration_days = 2  # type: ignore[misc]


@pytest.mark.parametrize(
    "start_at",
    [
        "2025-01-01T00:00:00+00:00",
        20250101,
        None,
    ],
)
def test_generator_config_rejects_non_datetime_start(
    start_at: object,
) -> None:
    """start_at must be a datetime value."""
    with pytest.raises(
        TypeError,
        match="start_at must be a timezone-aware datetime",
    ):
        WeatherGeneratorConfig(start_at=start_at)  # type: ignore[arg-type]


def test_generator_config_rejects_timezone_naive_start() -> None:
    """start_at must include timezone information."""
    with pytest.raises(ValueError, match="start_at must be timezone-aware"):
        WeatherGeneratorConfig(
            start_at=datetime(2025, 1, 1),
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "duration_days",
        "interval_minutes",
    ],
)
@pytest.mark.parametrize(
    "invalid_value",
    [
        True,
        1.5,
        "1",
        None,
    ],
)
def test_generator_config_rejects_invalid_integer_types(
    field_name: str,
    invalid_value: object,
) -> None:
    """Positive integer settings should reject invalid types."""
    with pytest.raises(TypeError, match=f"{field_name} must be an integer"):
        WeatherGeneratorConfig(**{field_name: invalid_value})


@pytest.mark.parametrize(
    "field_name",
    [
        "duration_days",
        "interval_minutes",
    ],
)
@pytest.mark.parametrize("invalid_value", [0, -1, -10])
def test_generator_config_rejects_non_positive_integers(
    field_name: str,
    invalid_value: int,
) -> None:
    """Duration and interval values must be greater than zero."""
    with pytest.raises(
        ValueError,
        match=f"{field_name} must be greater than zero",
    ):
        WeatherGeneratorConfig(**{field_name: invalid_value})


@pytest.mark.parametrize("interval_minutes", [7, 11, 17, 31])
def test_generator_config_rejects_non_divisor_intervals(
    interval_minutes: int,
) -> None:
    """Intervals must divide evenly into a complete day."""
    with pytest.raises(ValueError, match="divide evenly into 1440"):
        WeatherGeneratorConfig(
            interval_minutes=interval_minutes,
        )


@pytest.mark.parametrize(
    "random_seed",
    [
        True,
        1.5,
        "42",
        None,
    ],
)
def test_generator_config_rejects_invalid_seed_type(
    random_seed: object,
) -> None:
    """random_seed must be an integer excluding booleans."""
    with pytest.raises(TypeError, match="random_seed must be an integer"):
        WeatherGeneratorConfig(random_seed=random_seed)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field_name",
    [
        "estimated_probability",
        "missing_probability",
    ],
)
@pytest.mark.parametrize(
    "invalid_value",
    [
        -0.01,
        1.01,
    ],
)
def test_generator_config_rejects_invalid_probabilities(
    field_name: str,
    invalid_value: float,
) -> None:
    """Quality probabilities must remain between zero and one."""
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        WeatherGeneratorConfig(**{field_name: invalid_value})


@pytest.mark.parametrize(
    "field_name",
    [
        "estimated_probability",
        "missing_probability",
    ],
)
@pytest.mark.parametrize(
    "invalid_value",
    [
        True,
        "0.1",
        None,
    ],
)
def test_generator_config_rejects_non_numeric_probabilities(
    field_name: str,
    invalid_value: object,
) -> None:
    """Quality probabilities must be numeric."""
    with pytest.raises(TypeError, match=f"{field_name} must be numeric"):
        WeatherGeneratorConfig(**{field_name: invalid_value})


@pytest.mark.parametrize(
    "field_name",
    [
        "estimated_probability",
        "missing_probability",
    ],
)
@pytest.mark.parametrize(
    "invalid_value",
    [
        math.nan,
        math.inf,
        -math.inf,
    ],
)
def test_generator_config_rejects_non_finite_probabilities(
    field_name: str,
    invalid_value: float,
) -> None:
    """Quality probabilities must be finite."""
    with pytest.raises(ValueError, match=f"{field_name} must be finite"):
        WeatherGeneratorConfig(**{field_name: invalid_value})


def test_generator_config_rejects_probability_sum_above_one() -> None:
    """Estimated and missing probabilities must not exceed one together."""
    with pytest.raises(ValueError, match="must not exceed 1.0"):
        WeatherGeneratorConfig(
            estimated_probability=0.6,
            missing_probability=0.5,
        )


def test_generator_config_rejects_reversed_temperature_bounds() -> None:
    """Maximum daytime temperature must exceed minimum nighttime value."""
    with pytest.raises(
        ValueError,
        match="maximum_day_temperature_c must be greater",
    ):
        WeatherGeneratorConfig(
            minimum_night_temperature_c=30.0,
            maximum_day_temperature_c=30.0,
        )


@pytest.mark.parametrize(
    "maximum_clear_sky_ghi_wm2",
    [
        0.0,
        -1.0,
        1_500.1,
    ],
)
def test_generator_config_rejects_invalid_clear_sky_ghi(
    maximum_clear_sky_ghi_wm2: float,
) -> None:
    """Clear-sky GHI must stay within WeatherObservation limits."""
    with pytest.raises(
        ValueError,
        match="maximum_clear_sky_ghi_wm2 must be greater than zero",
    ):
        WeatherGeneratorConfig(
            maximum_clear_sky_ghi_wm2=maximum_clear_sky_ghi_wm2,
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "minimum_night_temperature_c",
        "maximum_day_temperature_c",
        "maximum_clear_sky_ghi_wm2",
    ],
)
@pytest.mark.parametrize(
    "invalid_value",
    [
        True,
        "10",
        None,
    ],
)
def test_generator_config_rejects_non_numeric_weather_limits(
    field_name: str,
    invalid_value: object,
) -> None:
    """Weather-limit settings must be numeric."""
    with pytest.raises(TypeError, match=f"{field_name} must be numeric"):
        WeatherGeneratorConfig(**{field_name: invalid_value})
