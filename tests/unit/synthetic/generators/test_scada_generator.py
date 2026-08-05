"""
Unit tests for the EOIP synthetic SCADA generator.
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
from eoip.synthetic.generators.plant_generator import PlantGeneratorConfig
from eoip.synthetic.generators.scada_generator import (
    SCADAGeneratorConfig,
    generate_scada,
    generate_scada_records,
)
from eoip.synthetic.generators.weather_generator import (
    WeatherGeneratorConfig,
)
from eoip.synthetic.models.scada import (
    SCADAObservation,
    SCADAOperatingState,
    SCADAQuality,
)


def _plant_config() -> PlantGeneratorConfig:
    return PlantGeneratorConfig(plant_count=1, random_seed=11)


def _equipment_config(
    string_inverters_per_plant: int = 2,
) -> EquipmentGeneratorConfig:
    return EquipmentGeneratorConfig(
        random_seed=22,
        string_inverters_per_plant=string_inverters_per_plant,
        transformers_per_plant=1,
        feeders_per_plant=1,
        weather_stations_per_plant=1,
        revenue_meters_per_plant=1,
        protection_relays_per_plant=1,
    )


def _scada_config(**overrides: Any) -> SCADAGeneratorConfig:
    data: dict[str, Any] = {
        "start_at": datetime(2025, 1, 1, tzinfo=UTC),
        "duration_days": 1,
        "interval_minutes": 15,
        "random_seed": 33,
        "derating_probability": 0.0,
        "forced_outage_probability": 0.0,
        "maintenance_probability": 0.0,
        "estimated_probability": 0.0,
        "missing_probability": 0.0,
    }
    data.update(overrides)
    return SCADAGeneratorConfig(**data)


def _weather_config(**overrides: Any) -> WeatherGeneratorConfig:
    data: dict[str, Any] = {
        "start_at": datetime(2025, 1, 1, tzinfo=UTC),
        "duration_days": 1,
        "interval_minutes": 15,
        "random_seed": 44,
        "estimated_probability": 0.0,
        "missing_probability": 0.0,
    }
    data.update(overrides)
    return WeatherGeneratorConfig(**data)


def test_generate_scada_returns_observations() -> None:
    observations = generate_scada(
        _scada_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        weather_config=_weather_config(),
    )
    assert isinstance(observations, tuple)
    assert len(observations) == 192
    assert all(isinstance(item, SCADAObservation) for item in observations)


def test_generate_scada_is_deterministic() -> None:
    kwargs = {
        "plant_config": _plant_config(),
        "equipment_config": _equipment_config(),
        "weather_config": _weather_config(),
    }
    assert generate_scada(_scada_config(), **kwargs) == generate_scada(
        _scada_config(),
        **kwargs,
    )


def test_different_seeds_change_results() -> None:
    kwargs = {
        "plant_config": _plant_config(),
        "equipment_config": _equipment_config(),
        "weather_config": _weather_config(),
    }
    assert generate_scada(
        _scada_config(random_seed=1),
        **kwargs,
    ) != generate_scada(
        _scada_config(random_seed=2),
        **kwargs,
    )


def test_each_equipment_has_complete_timeline() -> None:
    observations = generate_scada(
        _scada_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(3),
        weather_config=_weather_config(),
    )
    counts: dict[str, int] = {}
    for item in observations:
        counts[item.equipment_id] = counts.get(item.equipment_id, 0) + 1
    assert len(counts) == 3
    assert set(counts.values()) == {96}


def test_timestamps_use_fifteen_minute_intervals() -> None:
    observations = generate_scada(
        _scada_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(1),
        weather_config=_weather_config(),
    )
    timestamps = [item.timestamp for item in observations]
    assert observations[0].timestamp == datetime(2025, 1, 1, tzinfo=UTC)
    assert observations[-1].timestamp == datetime(
        2025,
        1,
        1,
        23,
        45,
        tzinfo=UTC,
    )
    assert all(
        later - earlier == timedelta(minutes=15)
        for earlier, later in zip(timestamps, timestamps[1:], strict=False)
    )


def test_night_records_do_not_generate() -> None:
    start = datetime(2025, 6, 1, tzinfo=UTC)
    observations = generate_scada(
        _scada_config(start_at=start),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(1),
        weather_config=_weather_config(start_at=start),
    )
    night = [
        item
        for item in observations
        if item.operating_state is SCADAOperatingState.NIGHT
    ]
    assert night
    assert all(item.active_power_kw == 0.0 for item in night)
    assert all(item.interval_energy_kwh == 0.0 for item in night)


def test_daylight_records_export_power() -> None:
    start = datetime(2025, 6, 1, tzinfo=UTC)
    observations = generate_scada(
        _scada_config(start_at=start),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(1),
        weather_config=_weather_config(start_at=start),
    )
    assert any(item.is_exporting for item in observations)
    assert any(item.active_power_kw > 0.0 for item in observations)


@pytest.mark.parametrize(
    ("config_overrides", "expected_state"),
    [
        ({"derating_probability": 1.0}, SCADAOperatingState.DERATED),
        (
            {"forced_outage_probability": 1.0},
            SCADAOperatingState.FAULT,
        ),
        (
            {"maintenance_probability": 1.0},
            SCADAOperatingState.MAINTENANCE,
        ),
    ],
)
def test_forced_operating_states(
    config_overrides: dict[str, float],
    expected_state: SCADAOperatingState,
) -> None:
    start = datetime(2025, 6, 1, tzinfo=UTC)
    observations = generate_scada(
        _scada_config(start_at=start, **config_overrides),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(1),
        weather_config=_weather_config(start_at=start),
    )
    daylight = [
        item
        for item in observations
        if item.operating_state is not SCADAOperatingState.NIGHT
    ]
    assert daylight
    assert all(item.operating_state is expected_state for item in daylight)


def test_missing_probability_one_zeroes_records() -> None:
    observations = generate_scada(
        _scada_config(missing_probability=1.0),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(1),
        weather_config=_weather_config(),
    )
    assert all(item.quality is SCADAQuality.MISSING for item in observations)
    assert all(item.active_power_kw == 0.0 for item in observations)
    assert all(item.grid_available is False for item in observations)


def test_estimated_probability_one_marks_estimated() -> None:
    observations = generate_scada(
        _scada_config(estimated_probability=1.0),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(1),
        weather_config=_weather_config(),
    )
    assert all(item.quality is SCADAQuality.ESTIMATED for item in observations)


def test_missing_weather_propagates_to_scada() -> None:
    observations = generate_scada(
        _scada_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(1),
        weather_config=_weather_config(missing_probability=1.0),
    )
    assert all(item.quality is SCADAQuality.MISSING for item in observations)


def test_generated_values_stay_within_model_bounds() -> None:
    observations = generate_scada(
        _scada_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        weather_config=_weather_config(),
    )
    for item in observations:
        assert 0.0 <= item.active_power_kw <= 50_000.0
        assert 0.0 <= item.interval_energy_kwh <= 12_500.0
        assert 0.0 <= item.dc_voltage_v <= 2_000.0
        assert 0.0 <= item.dc_current_a <= 10_000.0
        assert 0.0 <= item.ac_voltage_v <= 50_000.0
        assert 0.0 <= item.ac_current_a <= 10_000.0
        assert 0.0 <= item.frequency_hz <= 70.0
        assert -1.0 <= item.power_factor <= 1.0


def test_interval_energy_matches_active_power() -> None:
    observations = generate_scada(
        _scada_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        weather_config=_weather_config(),
    )
    assert all(
        item.energy_deviation_kwh == pytest.approx(0.0, abs=0.0001)
        for item in observations
    )


def test_generate_scada_records_matches_serialization() -> None:
    config = _scada_config()
    kwargs = {
        "plant_config": _plant_config(),
        "equipment_config": _equipment_config(),
        "weather_config": _weather_config(),
    }
    observations = generate_scada(config, **kwargs)
    records = generate_scada_records(config, **kwargs)
    assert records == tuple(item.to_record() for item in observations)


def test_default_config_values() -> None:
    config = SCADAGeneratorConfig()
    assert config.start_at == datetime(2025, 1, 1, tzinfo=UTC)
    assert config.duration_days == 7
    assert config.interval_minutes == 15
    assert config.random_seed == 42
    assert config.inverter_efficiency == 0.975
    assert config.nominal_ac_voltage_v == 400.0
    assert config.nominal_frequency_hz == 50.0
    assert config.nominal_power_factor == 0.99


def test_config_is_immutable() -> None:
    config = SCADAGeneratorConfig()
    with pytest.raises(FrozenInstanceError):
        config.duration_days = 2  # type: ignore[misc]


@pytest.mark.parametrize("value", ["bad", 1, None])
def test_invalid_start_type(value: object) -> None:
    with pytest.raises(TypeError):
        SCADAGeneratorConfig(start_at=value)  # type: ignore[arg-type]


def test_timezone_naive_start_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        SCADAGeneratorConfig(start_at=datetime(2025, 1, 1))


@pytest.mark.parametrize("field_name", ["duration_days", "interval_minutes"])
@pytest.mark.parametrize("value", [True, 1.5, "1", None])
def test_invalid_integer_types(field_name: str, value: object) -> None:
    with pytest.raises(TypeError):
        SCADAGeneratorConfig(**{field_name: value})


@pytest.mark.parametrize("field_name", ["duration_days", "interval_minutes"])
@pytest.mark.parametrize("value", [0, -1])
def test_non_positive_integers(field_name: str, value: int) -> None:
    with pytest.raises(ValueError):
        SCADAGeneratorConfig(**{field_name: value})


@pytest.mark.parametrize("value", [5, 10, 30, 60])
def test_only_fifteen_minute_interval_allowed(value: int) -> None:
    with pytest.raises(ValueError, match="must be 15"):
        SCADAGeneratorConfig(interval_minutes=value)


@pytest.mark.parametrize(
    "field_name",
    [
        "derating_probability",
        "forced_outage_probability",
        "maintenance_probability",
        "estimated_probability",
        "missing_probability",
    ],
)
@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_probability_bounds(field_name: str, value: float) -> None:
    with pytest.raises(ValueError):
        SCADAGeneratorConfig(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "derating_probability",
        "forced_outage_probability",
        "maintenance_probability",
        "estimated_probability",
        "missing_probability",
    ],
)
@pytest.mark.parametrize("value", [True, "0.1", None])
def test_probability_types(field_name: str, value: object) -> None:
    with pytest.raises(TypeError):
        SCADAGeneratorConfig(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "derating_probability",
        "forced_outage_probability",
        "maintenance_probability",
        "estimated_probability",
        "missing_probability",
    ],
)
@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_probability_finiteness(field_name: str, value: float) -> None:
    with pytest.raises(ValueError):
        SCADAGeneratorConfig(**{field_name: value})


def test_state_probability_sum_above_one_rejected() -> None:
    with pytest.raises(ValueError, match="must not exceed 1.0"):
        SCADAGeneratorConfig(
            derating_probability=0.5,
            forced_outage_probability=0.3,
            maintenance_probability=0.3,
        )


def test_quality_probability_sum_above_one_rejected() -> None:
    with pytest.raises(ValueError, match="must not exceed 1.0"):
        SCADAGeneratorConfig(
            estimated_probability=0.6,
            missing_probability=0.5,
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("inverter_efficiency", 0.0),
        ("inverter_efficiency", 1.1),
        ("nominal_ac_voltage_v", 0.0),
        ("nominal_frequency_hz", 0.0),
        ("nominal_power_factor", 1.1),
    ],
)
def test_invalid_electrical_bounds(
    field_name: str,
    value: float,
) -> None:
    with pytest.raises(ValueError):
        SCADAGeneratorConfig(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "inverter_efficiency",
        "nominal_ac_voltage_v",
        "nominal_frequency_hz",
        "nominal_power_factor",
    ],
)
@pytest.mark.parametrize("value", [True, "1", None])
def test_invalid_electrical_types(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(TypeError):
        SCADAGeneratorConfig(**{field_name: value})


def test_weather_start_must_match() -> None:
    with pytest.raises(ValueError, match="start_at must match"):
        generate_scada(
            _scada_config(),
            plant_config=_plant_config(),
            equipment_config=_equipment_config(),
            weather_config=_weather_config(start_at=datetime(2025, 1, 2, tzinfo=UTC)),
        )


def test_weather_duration_must_match() -> None:
    with pytest.raises(ValueError, match="duration_days must match"):
        generate_scada(
            _scada_config(duration_days=1),
            plant_config=_plant_config(),
            equipment_config=_equipment_config(),
            weather_config=_weather_config(duration_days=2),
        )
