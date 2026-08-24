"""
Unit tests for the EOIP WeatherObservation SQLAlchemy ORM model.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index

from eoip.database.models.weather import WeatherObservationORM
from eoip.synthetic.models.weather import (
    WeatherObservation,
    WeatherQuality,
)


def _timestamp() -> datetime:
    """Return the standard timezone-aware weather timestamp."""
    return datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def _domain_observation(**overrides: object) -> WeatherObservation:
    """Return a valid WeatherObservation with optional overrides."""
    data: dict[str, object] = {
        "plant_id": "PLANT-001",
        "weather_station_id": "WS-001",
        "timestamp": _timestamp(),
        "ghi_wm2": 800.0,
        "dni_wm2": 650.0,
        "dhi_wm2": 150.0,
        "ambient_temperature_c": 32.0,
        "module_temperature_c": 48.0,
        "wind_speed_ms": 4.5,
        "relative_humidity_pct": 45.0,
        "quality": WeatherQuality.VALID,
    }
    data.update(overrides)
    return WeatherObservation(**data)


def _orm_observation(**overrides: object) -> WeatherObservationORM:
    """Return a valid WeatherObservationORM with optional overrides."""
    data: dict[str, object] = {
        "plant_id": "PLANT-001",
        "weather_station_id": "WS-001",
        "timestamp": _timestamp(),
        "ghi_wm2": 800.0,
        "dni_wm2": 650.0,
        "dhi_wm2": 150.0,
        "ambient_temperature_c": 32.0,
        "module_temperature_c": 48.0,
        "wind_speed_ms": 4.5,
        "relative_humidity_pct": 45.0,
        "quality": WeatherQuality.VALID.value,
    }
    data.update(overrides)
    return WeatherObservationORM(**data)


def test_table_name() -> None:
    """Verify the mapped database table name."""
    assert WeatherObservationORM.__tablename__ == "weather_observations"


def test_composite_primary_key() -> None:
    """Verify station and timestamp form the composite primary key."""
    primary_keys = tuple(
        column.name for column in WeatherObservationORM.__table__.primary_key.columns
    )

    assert primary_keys == ("weather_station_id", "timestamp")


def test_expected_columns_exist() -> None:
    """Verify the complete persistence contract."""
    assert set(WeatherObservationORM.__table__.columns.keys()) == {
        "plant_id",
        "weather_station_id",
        "timestamp",
        "ghi_wm2",
        "dni_wm2",
        "dhi_wm2",
        "ambient_temperature_c",
        "module_temperature_c",
        "wind_speed_ms",
        "relative_humidity_pct",
        "quality",
        "inserted_at",
        "updated_at",
    }


def test_all_columns_are_not_nullable() -> None:
    """Verify every mapped weather column is required."""
    for column in WeatherObservationORM.__table__.columns:
        assert column.nullable is False


def test_plant_foreign_key_exists() -> None:
    """Verify the plant foreign key target."""
    targets = {
        foreign_key.target_fullname
        for foreign_key in WeatherObservationORM.__table__.foreign_keys
    }

    assert targets == {"plants.plant_id"}


def test_plant_foreign_key_actions() -> None:
    """Verify plant foreign-key update and delete behavior."""
    foreign_key = next(iter(WeatherObservationORM.__table__.foreign_keys))

    assert foreign_key.parent.name == "plant_id"
    assert foreign_key.onupdate == "CASCADE"
    assert foreign_key.ondelete == "RESTRICT"


def test_foreign_key_constraint_is_declared() -> None:
    """Verify SQLAlchemy registers one foreign-key constraint."""
    constraints = [
        constraint
        for constraint in WeatherObservationORM.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]

    assert len(constraints) == 1


def test_expected_check_constraints_exist() -> None:
    """Verify weather measurement and quality constraints."""
    constraint_names = {
        constraint.name
        for constraint in WeatherObservationORM.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert constraint_names == {
        "ck_weather_observations_ghi_range",
        "ck_weather_observations_dni_range",
        "ck_weather_observations_dhi_range",
        "ck_weather_observations_ambient_temperature_range",
        "ck_weather_observations_module_temperature_range",
        "ck_weather_observations_wind_speed_range",
        "ck_weather_observations_relative_humidity_range",
        "ck_weather_observations_valid_quality",
    }


def test_expected_indexes_exist() -> None:
    """Verify time-series weather indexes are declared."""
    index_names = {
        index.name
        for index in WeatherObservationORM.__table__.indexes
        if isinstance(index, Index)
    }

    assert index_names == {
        "ix_weather_observations_plant_id",
        "ix_weather_observations_timestamp",
        "ix_weather_observations_plant_timestamp",
        "ix_weather_observations_station_timestamp",
        "ix_weather_observations_quality_timestamp",
    }


@pytest.mark.parametrize(
    ("index_name", "expected_columns"),
    [
        (
            "ix_weather_observations_plant_timestamp",
            ("plant_id", "timestamp"),
        ),
        (
            "ix_weather_observations_station_timestamp",
            ("weather_station_id", "timestamp"),
        ),
        (
            "ix_weather_observations_quality_timestamp",
            ("quality", "timestamp"),
        ),
    ],
)
def test_composite_index_column_order(
    index_name: str,
    expected_columns: tuple[str, ...],
) -> None:
    """Verify composite index column order."""
    index = next(
        item
        for item in WeatherObservationORM.__table__.indexes
        if item.name == index_name
    )

    assert tuple(column.name for column in index.columns) == expected_columns


def test_from_domain_maps_all_fields() -> None:
    """Verify conversion from the authoritative domain model."""
    observation = _domain_observation(
        plant_id="PLANT-002",
        weather_station_id="WS-002",
        ghi_wm2=600.0,
        dni_wm2=500.0,
        dhi_wm2=100.0,
        ambient_temperature_c=28.5,
        module_temperature_c=42.0,
        wind_speed_ms=6.2,
        relative_humidity_pct=55.0,
        quality=WeatherQuality.ESTIMATED,
    )

    orm = WeatherObservationORM.from_domain(observation)

    assert orm.plant_id == "PLANT-002"
    assert orm.weather_station_id == "WS-002"
    assert orm.timestamp == observation.timestamp
    assert orm.ghi_wm2 == 600.0
    assert orm.dni_wm2 == 500.0
    assert orm.dhi_wm2 == 100.0
    assert orm.ambient_temperature_c == 28.5
    assert orm.module_temperature_c == 42.0
    assert orm.wind_speed_ms == 6.2
    assert orm.relative_humidity_pct == 55.0
    assert orm.quality == WeatherQuality.ESTIMATED.value


def test_from_domain_rejects_invalid_type() -> None:
    """Verify conversion rejects non-weather values."""
    with pytest.raises(TypeError, match="WeatherObservation instance"):
        WeatherObservationORM.from_domain(object())  # type: ignore[arg-type]


def test_to_domain_returns_authoritative_model() -> None:
    """Verify conversion back to the WeatherObservation domain model."""
    orm = _orm_observation(
        quality=WeatherQuality.ESTIMATED.value,
    )

    observation = orm.to_domain()

    assert isinstance(observation, WeatherObservation)
    assert observation.plant_id == orm.plant_id
    assert observation.weather_station_id == orm.weather_station_id
    assert observation.timestamp == orm.timestamp
    assert observation.ghi_wm2 == orm.ghi_wm2
    assert observation.dni_wm2 == orm.dni_wm2
    assert observation.dhi_wm2 == orm.dhi_wm2
    assert observation.ambient_temperature_c == orm.ambient_temperature_c
    assert observation.module_temperature_c == orm.module_temperature_c
    assert observation.wind_speed_ms == orm.wind_speed_ms
    assert observation.relative_humidity_pct == orm.relative_humidity_pct
    assert observation.quality is WeatherQuality.ESTIMATED


def test_domain_round_trip_preserves_values() -> None:
    """Verify domain-to-ORM-to-domain conversion is lossless."""
    original = _domain_observation(
        quality=WeatherQuality.ESTIMATED,
    )

    restored = WeatherObservationORM.from_domain(original).to_domain()

    assert restored == original


@pytest.mark.parametrize(
    ("ghi_wm2", "dhi_wm2", "expected"),
    [
        (800.0, 150.0, 950.0),
        (0.0, 0.0, 0.0),
        (123.45678, 22.11119, 145.568),
    ],
)
def test_total_horizontal_irradiance(
    ghi_wm2: float,
    dhi_wm2: float,
    expected: float,
) -> None:
    """Verify combined horizontal irradiance calculation."""
    orm = _orm_observation(
        ghi_wm2=ghi_wm2,
        dhi_wm2=dhi_wm2,
    )

    assert orm.total_horizontal_irradiance == expected


@pytest.mark.parametrize(
    ("ghi_wm2", "expected"),
    [
        (800.0, True),
        (0.1, True),
        (0.0, False),
    ],
)
def test_is_daylight(ghi_wm2: float, expected: bool) -> None:
    """Verify daylight classification."""
    orm = _orm_observation(ghi_wm2=ghi_wm2)

    assert orm.is_daylight is expected


def test_update_from_domain_updates_mutable_fields() -> None:
    """Verify weather measurements can be refreshed for the same key."""
    orm = _orm_observation()
    updated = _domain_observation(
        plant_id="PLANT-002",
        ghi_wm2=500.0,
        dni_wm2=420.0,
        dhi_wm2=80.0,
        ambient_temperature_c=27.0,
        module_temperature_c=39.0,
        wind_speed_ms=8.0,
        relative_humidity_pct=60.0,
        quality=WeatherQuality.ESTIMATED,
    )

    orm.update_from_domain(updated)

    assert orm.plant_id == "PLANT-002"
    assert orm.ghi_wm2 == 500.0
    assert orm.dni_wm2 == 420.0
    assert orm.dhi_wm2 == 80.0
    assert orm.ambient_temperature_c == 27.0
    assert orm.module_temperature_c == 39.0
    assert orm.wind_speed_ms == 8.0
    assert orm.relative_humidity_pct == 60.0
    assert orm.quality == WeatherQuality.ESTIMATED.value


def test_update_from_domain_rejects_invalid_type() -> None:
    """Verify update rejects non-weather values."""
    orm = _orm_observation()

    with pytest.raises(TypeError, match="WeatherObservation instance"):
        orm.update_from_domain(object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "overrides",
    [
        {"weather_station_id": "WS-002"},
        {"timestamp": _timestamp() + timedelta(minutes=15)},
    ],
)
def test_update_from_domain_rejects_different_primary_key(
    overrides: dict[str, object],
) -> None:
    """Verify persisted composite identity cannot be changed."""
    orm = _orm_observation()
    different = _domain_observation(**overrides)

    with pytest.raises(
        ValueError,
        match="different weather_station_id or timestamp",
    ):
        orm.update_from_domain(different)


def test_to_record_serializes_all_values() -> None:
    """Verify weather records are serialization-ready."""
    inserted_at = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
    updated_at = inserted_at + timedelta(hours=1)
    orm = _orm_observation()
    orm.inserted_at = inserted_at
    orm.updated_at = updated_at

    record = orm.to_record()

    assert record == {
        "plant_id": "PLANT-001",
        "weather_station_id": "WS-001",
        "timestamp": _timestamp().isoformat(),
        "ghi_wm2": 800.0,
        "dni_wm2": 650.0,
        "dhi_wm2": 150.0,
        "ambient_temperature_c": 32.0,
        "module_temperature_c": 48.0,
        "wind_speed_ms": 4.5,
        "relative_humidity_pct": 45.0,
        "quality": WeatherQuality.VALID.value,
        "total_horizontal_irradiance": 950.0,
        "is_daylight": True,
        "inserted_at": inserted_at.isoformat(),
        "updated_at": updated_at.isoformat(),
    }


def test_to_record_handles_unset_audit_timestamps() -> None:
    """Verify unsaved ORM objects serialize missing audit timestamps."""
    record = _orm_observation().to_record()

    assert record["inserted_at"] is None
    assert record["updated_at"] is None


def test_repr_contains_key_identity_fields() -> None:
    """Verify developer representation is concise and useful."""
    value = repr(_orm_observation())

    assert "WeatherObservationORM" in value
    assert "WS-001" in value
    assert "valid" in value


def test_quality_default_matches_domain_default() -> None:
    """Verify ORM quality defaults to valid."""
    column = WeatherObservationORM.__table__.columns["quality"]

    assert column.default is not None
    assert column.default.arg == WeatherQuality.VALID.value
    assert column.server_default is not None


def test_timestamp_columns_are_timezone_aware() -> None:
    """Verify observation and audit timestamps preserve timezone data."""
    for column_name in ("timestamp", "inserted_at", "updated_at"):
        assert (
            WeatherObservationORM.__table__.columns[column_name].type.timezone is True
        )


def test_plant_relationship_configuration() -> None:
    """Verify weather observations link to PlantORM."""
    relationship_property = WeatherObservationORM.__mapper__.relationships["plant"]

    assert relationship_property.mapper.class_.__name__ == "PlantORM"
    assert relationship_property.uselist is False


def test_measurement_columns_use_float_type() -> None:
    """Verify weather measurements use floating-point storage."""
    for column_name in (
        "ghi_wm2",
        "dni_wm2",
        "dhi_wm2",
        "ambient_temperature_c",
        "module_temperature_c",
        "wind_speed_ms",
        "relative_humidity_pct",
    ):
        assert (
            WeatherObservationORM.__table__.columns[column_name].type.python_type
            is float
        )


def test_weather_station_id_length_is_six() -> None:
    """Verify station identifiers match the domain format."""
    column = WeatherObservationORM.__table__.columns["weather_station_id"]

    assert column.type.length == 6


def test_timeseries_key_contains_timestamp() -> None:
    """Verify timestamp participates in the primary key."""
    primary_keys = {
        column.name for column in WeatherObservationORM.__table__.primary_key.columns
    }

    assert primary_keys == {"weather_station_id", "timestamp"}


def test_direct_timestamp_index_exists() -> None:
    """Verify direct timestamp filtering is indexed."""
    timestamp_index = next(
        index
        for index in WeatherObservationORM.__table__.indexes
        if index.name == "ix_weather_observations_timestamp"
    )

    assert tuple(column.name for column in timestamp_index.columns) == ("timestamp",)
