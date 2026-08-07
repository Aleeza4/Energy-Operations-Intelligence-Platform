"""
Unit tests for the EOIP SCADAObservation SQLAlchemy ORM model.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index

from eoip.database.models.scada import SCADAObservationORM
from eoip.synthetic.models.scada import (
    SCADAObservation,
    SCADAOperatingState,
    SCADAQuality,
)


def _timestamp() -> datetime:
    """Return the standard aligned SCADA timestamp."""
    return datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def _domain_observation(**overrides: object) -> SCADAObservation:
    """Return a valid SCADA domain observation with optional overrides."""
    data: dict[str, object] = {
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "timestamp": _timestamp(),
        "active_power_kw": 800.0,
        "interval_energy_kwh": 200.0,
        "dc_voltage_v": 1_000.0,
        "dc_current_a": 820.0,
        "ac_voltage_v": 400.0,
        "ac_current_a": 1_160.0,
        "frequency_hz": 50.0,
        "power_factor": 0.99,
        "equipment_available": True,
        "grid_available": True,
        "operating_state": SCADAOperatingState.NORMAL,
        "quality": SCADAQuality.VALID,
    }
    data.update(overrides)
    return SCADAObservation(**data)


def _orm_observation(**overrides: object) -> SCADAObservationORM:
    """Return a valid SCADA ORM observation with optional overrides."""
    data: dict[str, object] = {
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "timestamp": _timestamp(),
        "active_power_kw": 800.0,
        "interval_energy_kwh": 200.0,
        "dc_voltage_v": 1_000.0,
        "dc_current_a": 820.0,
        "ac_voltage_v": 400.0,
        "ac_current_a": 1_160.0,
        "frequency_hz": 50.0,
        "power_factor": 0.99,
        "equipment_available": True,
        "grid_available": True,
        "operating_state": SCADAOperatingState.NORMAL.value,
        "quality": SCADAQuality.VALID.value,
    }
    data.update(overrides)
    return SCADAObservationORM(**data)


def test_table_name() -> None:
    """Verify the mapped database table name."""
    assert SCADAObservationORM.__tablename__ == "scada_observations"


def test_composite_primary_key() -> None:
    """Verify equipment_id and timestamp form the primary key."""
    primary_keys = tuple(
        column.name for column in SCADAObservationORM.__table__.primary_key.columns
    )

    assert primary_keys == ("equipment_id", "timestamp")


def test_expected_columns_exist() -> None:
    """Verify the complete persistence contract."""
    assert set(SCADAObservationORM.__table__.columns.keys()) == {
        "plant_id",
        "equipment_id",
        "timestamp",
        "active_power_kw",
        "interval_energy_kwh",
        "dc_voltage_v",
        "dc_current_a",
        "ac_voltage_v",
        "ac_current_a",
        "frequency_hz",
        "power_factor",
        "equipment_available",
        "grid_available",
        "operating_state",
        "quality",
        "inserted_at",
        "updated_at",
    }


def test_all_columns_are_not_nullable() -> None:
    """Verify every SCADA persistence column is required."""
    for column in SCADAObservationORM.__table__.columns:
        assert column.nullable is False


def test_expected_foreign_keys_exist() -> None:
    """Verify plant and equipment foreign keys."""
    targets = {
        foreign_key.target_fullname
        for foreign_key in SCADAObservationORM.__table__.foreign_keys
    }

    assert targets == {
        "plants.plant_id",
        "equipment.equipment_id",
    }


def test_foreign_key_actions() -> None:
    """Verify foreign-key update and delete behavior."""
    foreign_keys = {
        foreign_key.parent.name: foreign_key
        for foreign_key in SCADAObservationORM.__table__.foreign_keys
    }

    assert foreign_keys["plant_id"].onupdate == "CASCADE"
    assert foreign_keys["plant_id"].ondelete == "RESTRICT"
    assert foreign_keys["equipment_id"].onupdate == "CASCADE"
    assert foreign_keys["equipment_id"].ondelete == "CASCADE"


def test_foreign_key_constraints_are_declared() -> None:
    """Verify both foreign-key constraints are registered."""
    constraints = [
        constraint
        for constraint in SCADAObservationORM.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]

    assert len(constraints) == 2


def test_expected_check_constraints_exist() -> None:
    """Verify telemetry, state, and timestamp constraints."""
    constraint_names = {
        constraint.name
        for constraint in SCADAObservationORM.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert constraint_names == {
        "ck_scada_observations_active_power_range",
        "ck_scada_observations_interval_energy_range",
        "ck_scada_observations_dc_voltage_range",
        "ck_scada_observations_dc_current_range",
        "ck_scada_observations_ac_voltage_range",
        "ck_scada_observations_ac_current_range",
        "ck_scada_observations_frequency_range",
        "ck_scada_observations_power_factor_range",
        "ck_scada_observations_valid_operating_state",
        "ck_scada_observations_valid_quality",
        "ck_scada_observations_unavailable_equipment_has_no_generation",
        "ck_scada_observations_unavailable_grid_has_no_generation",
        "ck_scada_observations_non_generating_state_has_no_generation",
        "ck_scada_observations_normal_state_requires_availability",
        "ck_scada_observations_timestamp_zero_seconds",
        "ck_scada_observations_timestamp_interval_aligned",
    }


def test_expected_indexes_exist() -> None:
    """Verify time-series query indexes are declared."""
    index_names = {
        index.name
        for index in SCADAObservationORM.__table__.indexes
        if isinstance(index, Index)
    }

    assert index_names == {
        "ix_scada_observations_plant_id",
        "ix_scada_observations_timestamp",
        "ix_scada_observations_plant_timestamp",
        "ix_scada_observations_equipment_timestamp",
        "ix_scada_observations_state_timestamp",
        "ix_scada_observations_quality_timestamp",
    }


@pytest.mark.parametrize(
    ("index_name", "expected_columns"),
    [
        (
            "ix_scada_observations_plant_timestamp",
            ("plant_id", "timestamp"),
        ),
        (
            "ix_scada_observations_equipment_timestamp",
            ("equipment_id", "timestamp"),
        ),
        (
            "ix_scada_observations_state_timestamp",
            ("operating_state", "timestamp"),
        ),
        (
            "ix_scada_observations_quality_timestamp",
            ("quality", "timestamp"),
        ),
    ],
)
def test_composite_index_column_order(
    index_name: str,
    expected_columns: tuple[str, ...],
) -> None:
    """Verify composite index column ordering."""
    index = next(
        item
        for item in SCADAObservationORM.__table__.indexes
        if item.name == index_name
    )

    assert tuple(column.name for column in index.columns) == expected_columns


def test_from_domain_maps_all_fields() -> None:
    """Verify conversion from the authoritative domain model."""
    observation = _domain_observation(
        operating_state=SCADAOperatingState.DERATED,
        quality=SCADAQuality.ESTIMATED,
        active_power_kw=650.0,
        interval_energy_kwh=162.5,
    )

    orm = SCADAObservationORM.from_domain(observation)

    assert orm.plant_id == observation.plant_id
    assert orm.equipment_id == observation.equipment_id
    assert orm.timestamp == observation.timestamp
    assert orm.active_power_kw == 650.0
    assert orm.interval_energy_kwh == 162.5
    assert orm.dc_voltage_v == observation.dc_voltage_v
    assert orm.dc_current_a == observation.dc_current_a
    assert orm.ac_voltage_v == observation.ac_voltage_v
    assert orm.ac_current_a == observation.ac_current_a
    assert orm.frequency_hz == observation.frequency_hz
    assert orm.power_factor == observation.power_factor
    assert orm.equipment_available is True
    assert orm.grid_available is True
    assert orm.operating_state == SCADAOperatingState.DERATED.value
    assert orm.quality == SCADAQuality.ESTIMATED.value


def test_from_domain_rejects_invalid_type() -> None:
    """Verify conversion rejects non-SCADA values."""
    with pytest.raises(TypeError, match="SCADAObservation instance"):
        SCADAObservationORM.from_domain(object())  # type: ignore[arg-type]


def test_to_domain_returns_authoritative_model() -> None:
    """Verify conversion back to the SCADA domain model."""
    orm = _orm_observation(
        operating_state=SCADAOperatingState.DERATED.value,
        quality=SCADAQuality.ESTIMATED.value,
    )

    observation = orm.to_domain()

    assert isinstance(observation, SCADAObservation)
    assert observation.plant_id == orm.plant_id
    assert observation.equipment_id == orm.equipment_id
    assert observation.timestamp == orm.timestamp
    assert observation.active_power_kw == orm.active_power_kw
    assert observation.interval_energy_kwh == orm.interval_energy_kwh
    assert observation.dc_voltage_v == orm.dc_voltage_v
    assert observation.dc_current_a == orm.dc_current_a
    assert observation.ac_voltage_v == orm.ac_voltage_v
    assert observation.ac_current_a == orm.ac_current_a
    assert observation.frequency_hz == orm.frequency_hz
    assert observation.power_factor == orm.power_factor
    assert observation.equipment_available is True
    assert observation.grid_available is True
    assert observation.operating_state is SCADAOperatingState.DERATED
    assert observation.quality is SCADAQuality.ESTIMATED


def test_domain_round_trip_preserves_values() -> None:
    """Verify domain-to-ORM-to-domain conversion is lossless."""
    original = _domain_observation(
        operating_state=SCADAOperatingState.DERATED,
        quality=SCADAQuality.ESTIMATED,
    )

    restored = SCADAObservationORM.from_domain(original).to_domain()

    assert restored == original


@pytest.mark.parametrize(
    ("active_power_kw", "equipment_available", "grid_available", "expected"),
    [
        (800.0, True, True, True),
        (0.0, True, True, False),
        (800.0, False, True, False),
        (800.0, True, False, False),
    ],
)
def test_is_exporting(
    active_power_kw: float,
    equipment_available: bool,
    grid_available: bool,
    expected: bool,
) -> None:
    """Verify export classification."""
    orm = _orm_observation(
        active_power_kw=active_power_kw,
        equipment_available=equipment_available,
        grid_available=grid_available,
    )

    assert orm.is_exporting is expected


@pytest.mark.parametrize(
    ("active_power_kw", "expected"),
    [
        (0.0, 0.0),
        (100.0, 25.0),
        (800.0, 200.0),
        (123.4567, 30.8642),
    ],
)
def test_calculated_interval_energy_kwh(
    active_power_kw: float,
    expected: float,
) -> None:
    """Verify 15-minute energy derived from active power."""
    orm = _orm_observation(active_power_kw=active_power_kw)

    assert orm.calculated_interval_energy_kwh == expected


@pytest.mark.parametrize(
    ("active_power_kw", "reported_energy", "expected"),
    [
        (800.0, 200.0, 0.0),
        (800.0, 198.5, -1.5),
        (800.0, 202.25, 2.25),
    ],
)
def test_energy_deviation_kwh(
    active_power_kw: float,
    reported_energy: float,
    expected: float,
) -> None:
    """Verify reported-minus-calculated energy deviation."""
    orm = _orm_observation(
        active_power_kw=active_power_kw,
        interval_energy_kwh=reported_energy,
    )

    assert orm.energy_deviation_kwh == expected


def test_update_from_domain_updates_mutable_fields() -> None:
    """Verify telemetry fields can be refreshed for the same key."""
    orm = _orm_observation()
    updated = _domain_observation(
        plant_id="PLANT-002",
        active_power_kw=500.0,
        interval_energy_kwh=125.0,
        dc_voltage_v=950.0,
        dc_current_a=600.0,
        ac_voltage_v=415.0,
        ac_current_a=700.0,
        frequency_hz=49.9,
        power_factor=0.97,
        equipment_available=True,
        grid_available=True,
        operating_state=SCADAOperatingState.DERATED,
        quality=SCADAQuality.ESTIMATED,
    )

    orm.update_from_domain(updated)

    assert orm.plant_id == "PLANT-002"
    assert orm.active_power_kw == 500.0
    assert orm.interval_energy_kwh == 125.0
    assert orm.dc_voltage_v == 950.0
    assert orm.dc_current_a == 600.0
    assert orm.ac_voltage_v == 415.0
    assert orm.ac_current_a == 700.0
    assert orm.frequency_hz == 49.9
    assert orm.power_factor == 0.97
    assert orm.equipment_available is True
    assert orm.grid_available is True
    assert orm.operating_state == SCADAOperatingState.DERATED.value
    assert orm.quality == SCADAQuality.ESTIMATED.value


def test_update_from_domain_rejects_invalid_type() -> None:
    """Verify update rejects non-SCADA values."""
    orm = _orm_observation()

    with pytest.raises(TypeError, match="SCADAObservation instance"):
        orm.update_from_domain(object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "overrides",
    [
        {"equipment_id": "EQP-00002"},
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
        match="different equipment_id or timestamp",
    ):
        orm.update_from_domain(different)


def test_to_record_serializes_all_values() -> None:
    """Verify SCADA records are serialization-ready."""
    inserted_at = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
    updated_at = inserted_at + timedelta(hours=1)
    orm = _orm_observation()
    orm.inserted_at = inserted_at
    orm.updated_at = updated_at

    record = orm.to_record()

    assert record == {
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "timestamp": _timestamp().isoformat(),
        "active_power_kw": 800.0,
        "interval_energy_kwh": 200.0,
        "dc_voltage_v": 1_000.0,
        "dc_current_a": 820.0,
        "ac_voltage_v": 400.0,
        "ac_current_a": 1_160.0,
        "frequency_hz": 50.0,
        "power_factor": 0.99,
        "equipment_available": True,
        "grid_available": True,
        "operating_state": SCADAOperatingState.NORMAL.value,
        "quality": SCADAQuality.VALID.value,
        "is_exporting": True,
        "calculated_interval_energy_kwh": 200.0,
        "energy_deviation_kwh": 0.0,
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

    assert "SCADAObservationORM" in value
    assert "EQP-00001" in value
    assert "normal" in value
    assert "valid" in value


def test_quality_default_matches_domain_default() -> None:
    """Verify ORM quality defaults to valid."""
    column = SCADAObservationORM.__table__.columns["quality"]

    assert column.default is not None
    assert column.default.arg == SCADAQuality.VALID.value
    assert column.server_default is not None


def test_timestamp_columns_are_timezone_aware() -> None:
    """Verify telemetry and audit timestamps preserve timezone data."""
    for column_name in ("timestamp", "inserted_at", "updated_at"):
        assert SCADAObservationORM.__table__.columns[column_name].type.timezone is True


def test_plant_relationship_configuration() -> None:
    """Verify SCADA observations link to PlantORM."""
    relationship_property = SCADAObservationORM.__mapper__.relationships["plant"]

    assert relationship_property.mapper.class_.__name__ == "PlantORM"
    assert relationship_property.uselist is False


def test_equipment_relationship_configuration() -> None:
    """Verify SCADA observations link to EquipmentORM."""
    relationship_property = SCADAObservationORM.__mapper__.relationships["equipment"]

    assert relationship_property.mapper.class_.__name__ == "EquipmentORM"
    assert relationship_property.uselist is False


def test_numeric_measurement_columns_use_float_type() -> None:
    """Verify telemetry measurements use floating-point storage."""
    for column_name in (
        "active_power_kw",
        "interval_energy_kwh",
        "dc_voltage_v",
        "dc_current_a",
        "ac_voltage_v",
        "ac_current_a",
        "frequency_hz",
        "power_factor",
    ):
        assert (
            SCADAObservationORM.__table__.columns[column_name].type.python_type is float
        )


def test_boolean_columns_use_bool_type() -> None:
    """Verify availability fields use Boolean storage."""
    for column_name in ("equipment_available", "grid_available"):
        assert (
            SCADAObservationORM.__table__.columns[column_name].type.python_type is bool
        )


def test_timeseries_key_order_supports_hypertable_design() -> None:
    """Verify timestamp participates in the primary key for TimescaleDB."""
    primary_keys = {
        column.name for column in SCADAObservationORM.__table__.primary_key.columns
    }

    assert "timestamp" in primary_keys
    assert "equipment_id" in primary_keys


def test_table_has_timestamp_index() -> None:
    """Verify direct timestamp filtering is indexed."""
    timestamp_index = next(
        index
        for index in SCADAObservationORM.__table__.indexes
        if index.name == "ix_scada_observations_timestamp"
    )

    assert tuple(column.name for column in timestamp_index.columns) == ("timestamp",)
