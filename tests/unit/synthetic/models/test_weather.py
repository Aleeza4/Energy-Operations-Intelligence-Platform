"""
Unit tests for the EOIP weather observation domain model.

These tests verify valid weather observations, identifier normalization,
timezone requirements, measurement boundaries, serialization, derived
properties, data-quality states, immutability, and invalid-value handling.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest

from eoip.synthetic.models.weather import (
    WeatherObservation,
    WeatherQuality,
)


def _make_weather_observation(**overrides: Any) -> WeatherObservation:
    """Create a valid weather observation with optional field overrides."""
    observation_data: dict[str, Any] = {
        "plant_id": "PLANT-001",
        "weather_station_id": "WS-001",
        "timestamp": datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
        "ghi_wm2": 850.0,
        "dni_wm2": 700.0,
        "dhi_wm2": 150.0,
        "ambient_temperature_c": 32.0,
        "module_temperature_c": 48.0,
        "wind_speed_ms": 4.5,
        "relative_humidity_pct": 55.0,
        "quality": WeatherQuality.VALID,
    }
    observation_data.update(overrides)
    return WeatherObservation(**observation_data)


def test_weather_observation_preserves_valid_fields() -> None:
    """A valid weather observation should retain all supplied values."""
    observation = _make_weather_observation()

    assert observation.plant_id == "PLANT-001"
    assert observation.weather_station_id == "WS-001"
    assert observation.timestamp == datetime(
        2026,
        1,
        15,
        12,
        0,
        tzinfo=UTC,
    )
    assert observation.ghi_wm2 == 850.0
    assert observation.dni_wm2 == 700.0
    assert observation.dhi_wm2 == 150.0
    assert observation.ambient_temperature_c == 32.0
    assert observation.module_temperature_c == 48.0
    assert observation.wind_speed_ms == 4.5
    assert observation.relative_humidity_pct == 55.0
    assert observation.quality is WeatherQuality.VALID


def test_weather_observation_normalizes_identifiers() -> None:
    """Plant and weather-station identifiers should be normalized."""
    observation = _make_weather_observation(
        plant_id=" plant-001 ",
        weather_station_id=" ws-001 ",
    )

    assert observation.plant_id == "PLANT-001"
    assert observation.weather_station_id == "WS-001"


def test_weather_observation_uses_valid_quality_by_default() -> None:
    """Weather quality should default to VALID."""
    observation = WeatherObservation(
        plant_id="PLANT-001",
        weather_station_id="WS-001",
        timestamp=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
        ghi_wm2=850.0,
        dni_wm2=700.0,
        dhi_wm2=150.0,
        ambient_temperature_c=32.0,
        module_temperature_c=48.0,
        wind_speed_ms=4.5,
        relative_humidity_pct=55.0,
    )

    assert observation.quality is WeatherQuality.VALID


def test_total_horizontal_irradiance_returns_expected_value() -> None:
    """Total horizontal irradiance should equal GHI plus DHI."""
    observation = _make_weather_observation(
        ghi_wm2=850.12345,
        dhi_wm2=149.98765,
    )

    assert observation.total_horizontal_irradiance == 1000.1111


@pytest.mark.parametrize(
    ("ghi_wm2", "expected"),
    [
        (0.0, False),
        (0, False),
        (0.0001, True),
        (250.0, True),
        (1500.0, True),
    ],
)
def test_is_daylight_depends_on_positive_ghi(
    ghi_wm2: float,
    expected: bool,
) -> None:
    """Daylight should be true only when GHI is greater than zero."""
    observation = _make_weather_observation(ghi_wm2=ghi_wm2)

    assert observation.is_daylight is expected


def test_to_record_returns_complete_serialized_record() -> None:
    """Serialization should return a complete analytics-ready dictionary."""
    observation = _make_weather_observation()

    assert observation.to_record() == {
        "plant_id": "PLANT-001",
        "weather_station_id": "WS-001",
        "timestamp": "2026-01-15T12:00:00+00:00",
        "ghi_wm2": 850.0,
        "dni_wm2": 700.0,
        "dhi_wm2": 150.0,
        "ambient_temperature_c": 32.0,
        "module_temperature_c": 48.0,
        "wind_speed_ms": 4.5,
        "relative_humidity_pct": 55.0,
        "quality": "valid",
        "total_horizontal_irradiance": 1000.0,
        "is_daylight": True,
    }


def test_weather_observation_is_immutable() -> None:
    """Weather observations should reject field modification."""
    observation = _make_weather_observation()

    with pytest.raises(FrozenInstanceError):
        observation.ghi_wm2 = 900.0  # type: ignore[misc]


@pytest.mark.parametrize(
    "plant_id",
    [
        "",
        "   ",
        "PLANT-1",
        "PLANT-01",
        "PLANT-0001",
        "SITE-001",
        "PLANT-ABC",
        "PLANT_001",
    ],
)
def test_weather_observation_rejects_invalid_plant_id(
    plant_id: str,
) -> None:
    """Plant IDs must follow the PLANT-001 format."""
    with pytest.raises(
        ValueError,
        match="Invalid plant_id",
    ):
        _make_weather_observation(plant_id=plant_id)


@pytest.mark.parametrize(
    "weather_station_id",
    [
        "",
        "   ",
        "WS-1",
        "WS-01",
        "WS-0001",
        "WEATHER-001",
        "WS-ABC",
        "WS_001",
    ],
)
def test_weather_observation_rejects_invalid_weather_station_id(
    weather_station_id: str,
) -> None:
    """Weather-station IDs must follow the WS-001 format."""
    with pytest.raises(
        ValueError,
        match="Invalid weather_station_id",
    ):
        _make_weather_observation(
            weather_station_id=weather_station_id,
        )


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-01-15T12:00:00+00:00",
        20260115,
        None,
        object(),
    ],
)
def test_weather_observation_rejects_non_datetime_timestamp(
    timestamp: object,
) -> None:
    """Timestamps must be datetime instances."""
    with pytest.raises(
        TypeError,
        match="Use a datetime value",
    ):
        _make_weather_observation(timestamp=timestamp)


def test_weather_observation_rejects_timezone_naive_timestamp() -> None:
    """Timezone-naive timestamps must be rejected."""
    naive_timestamp = datetime(2026, 1, 15, 12, 0)

    with pytest.raises(
        ValueError,
        match="is timezone-naive",
    ):
        _make_weather_observation(timestamp=naive_timestamp)


def test_weather_observation_accepts_utc_timestamp() -> None:
    """A UTC-aware timestamp should be accepted."""
    timestamp = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)

    observation = _make_weather_observation(timestamp=timestamp)

    assert observation.timestamp == timestamp
    assert observation.timestamp.utcoffset() == timedelta(0)


def test_weather_observation_accepts_non_utc_aware_timestamp() -> None:
    """Any timezone-aware timestamp should be accepted."""
    local_timezone = timezone(timedelta(hours=5))
    timestamp = datetime(2026, 1, 15, 12, 0, tzinfo=local_timezone)

    observation = _make_weather_observation(timestamp=timestamp)

    assert observation.timestamp == timestamp
    assert observation.timestamp.utcoffset() == timedelta(hours=5)


@pytest.mark.parametrize("quality", list(WeatherQuality))
def test_weather_observation_accepts_all_quality_values(
    quality: WeatherQuality,
) -> None:
    """Every documented WeatherQuality member should be accepted."""
    observation = _make_weather_observation(quality=quality)

    assert observation.quality is quality


@pytest.mark.parametrize(
    "quality",
    [
        "valid",
        "estimated",
        "missing",
        1,
        None,
    ],
)
def test_weather_observation_rejects_invalid_quality(
    quality: object,
) -> None:
    """Raw strings and unsupported values must not replace WeatherQuality."""
    with pytest.raises(
        TypeError,
        match="Use a WeatherQuality value",
    ):
        _make_weather_observation(quality=quality)


@pytest.mark.parametrize(
    ("field_name", "minimum", "maximum"),
    [
        ("ghi_wm2", 0.0, 1500.0),
        ("dni_wm2", 0.0, 1500.0),
        ("dhi_wm2", 0.0, 1500.0),
        ("ambient_temperature_c", -40.0, 70.0),
        ("module_temperature_c", -40.0, 120.0),
        ("wind_speed_ms", 0.0, 70.0),
        ("relative_humidity_pct", 0.0, 100.0),
    ],
)
def test_weather_observation_accepts_measurement_boundaries(
    field_name: str,
    minimum: float,
    maximum: float,
) -> None:
    """Every documented minimum and maximum should be accepted."""
    minimum_observation = _make_weather_observation(
        **{field_name: minimum}
    )
    maximum_observation = _make_weather_observation(
        **{field_name: maximum}
    )

    assert getattr(minimum_observation, field_name) == minimum
    assert getattr(maximum_observation, field_name) == maximum


@pytest.mark.parametrize(
    ("field_name", "invalid_value", "expected_message"),
    [
        ("ghi_wm2", -0.1, "Invalid ghi_wm2 value"),
        ("ghi_wm2", 1500.1, "Invalid ghi_wm2 value"),
        ("dni_wm2", -0.1, "Invalid dni_wm2 value"),
        ("dni_wm2", 1500.1, "Invalid dni_wm2 value"),
        ("dhi_wm2", -0.1, "Invalid dhi_wm2 value"),
        ("dhi_wm2", 1500.1, "Invalid dhi_wm2 value"),
        (
            "ambient_temperature_c",
            -40.1,
            "Invalid ambient_temperature_c value",
        ),
        (
            "ambient_temperature_c",
            70.1,
            "Invalid ambient_temperature_c value",
        ),
        (
            "module_temperature_c",
            -40.1,
            "Invalid module_temperature_c value",
        ),
        (
            "module_temperature_c",
            120.1,
            "Invalid module_temperature_c value",
        ),
        ("wind_speed_ms", -0.1, "Invalid wind_speed_ms value"),
        ("wind_speed_ms", 70.1, "Invalid wind_speed_ms value"),
        (
            "relative_humidity_pct",
            -0.1,
            "Invalid relative_humidity_pct value",
        ),
        (
            "relative_humidity_pct",
            100.1,
            "Invalid relative_humidity_pct value",
        ),
    ],
)
def test_weather_observation_rejects_out_of_range_measurements(
    field_name: str,
    invalid_value: float,
    expected_message: str,
) -> None:
    """Measurements outside their documented ranges must be rejected."""
    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        _make_weather_observation(
            **{field_name: invalid_value}
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "ghi_wm2",
        "dni_wm2",
        "dhi_wm2",
        "ambient_temperature_c",
        "module_temperature_c",
        "wind_speed_ms",
        "relative_humidity_pct",
    ],
)
@pytest.mark.parametrize(
    "invalid_value",
    [
        True,
        False,
        "10",
        None,
        [],
        {},
    ],
)
def test_weather_observation_rejects_non_numeric_measurements(
    field_name: str,
    invalid_value: object,
) -> None:
    """Measurements must be numeric and must reject boolean values."""
    with pytest.raises(
        TypeError,
        match=f"Invalid {field_name} value",
    ):
        _make_weather_observation(
            **{field_name: invalid_value}
        )