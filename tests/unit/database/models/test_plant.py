"""
Unit tests for the EOIP Plant SQLAlchemy ORM model.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import CheckConstraint, Index

from eoip.database.models.plant import PlantORM
from eoip.synthetic.models.plant import Plant, PlantStatus


def _domain_plant(**overrides: object) -> Plant:
    """Return a valid Plant domain model with optional overrides."""
    data: dict[str, object] = {
        "plant_id": "PLANT-001",
        "plant_name": "Lahore Solar One",
        "region": "Punjab",
        "latitude": 31.5204,
        "longitude": 74.3587,
        "dc_capacity_mw": 120.0,
        "ac_capacity_mw": 100.0,
        "commissioning_date": date(2024, 1, 15),
        "status": PlantStatus.OPERATIONAL,
        "timezone_name": "UTC",
    }
    data.update(overrides)
    return Plant(**data)


def _orm_plant(**overrides: object) -> PlantORM:
    """Return a valid PlantORM object with optional overrides."""
    data: dict[str, object] = {
        "plant_id": "PLANT-001",
        "plant_name": "Lahore Solar One",
        "region": "Punjab",
        "latitude": 31.5204,
        "longitude": 74.3587,
        "dc_capacity_mw": 120.0,
        "ac_capacity_mw": 100.0,
        "commissioning_date": date(2024, 1, 15),
        "status": PlantStatus.OPERATIONAL.value,
        "timezone_name": "UTC",
    }
    data.update(overrides)
    return PlantORM(**data)


def test_table_name() -> None:
    """Verify the mapped database table name."""
    assert PlantORM.__tablename__ == "plants"


def test_primary_key_column() -> None:
    """Verify plant_id is the only primary-key column."""
    primary_keys = {column.name for column in PlantORM.__table__.primary_key.columns}

    assert primary_keys == {"plant_id"}


def test_expected_columns_exist() -> None:
    """Verify the table exposes the complete persistence contract."""
    assert set(PlantORM.__table__.columns.keys()) == {
        "plant_id",
        "plant_name",
        "region",
        "latitude",
        "longitude",
        "dc_capacity_mw",
        "ac_capacity_mw",
        "commissioning_date",
        "status",
        "timezone_name",
        "created_at",
        "updated_at",
    }


def test_required_columns_are_not_nullable() -> None:
    """Verify all mapped plant fields are required."""
    for column_name in (
        "plant_id",
        "plant_name",
        "region",
        "latitude",
        "longitude",
        "dc_capacity_mw",
        "ac_capacity_mw",
        "commissioning_date",
        "status",
        "timezone_name",
        "created_at",
        "updated_at",
    ):
        assert PlantORM.__table__.columns[column_name].nullable is False


def test_expected_check_constraints_exist() -> None:
    """Verify engineering and controlled-value constraints."""
    constraint_names = {
        constraint.name
        for constraint in PlantORM.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert constraint_names == {
        "ck_plants_latitude_range",
        "ck_plants_longitude_range",
        "ck_plants_dc_capacity_positive",
        "ck_plants_ac_capacity_positive",
        "ck_plants_ac_not_greater_than_dc",
        "ck_plants_valid_status",
    }


def test_expected_indexes_exist() -> None:
    """Verify query-supporting indexes are declared."""
    index_names = {
        index.name for index in PlantORM.__table__.indexes if isinstance(index, Index)
    }

    assert index_names == {
        "ix_plants_region",
        "ix_plants_status",
        "ix_plants_commissioning_date",
    }


def test_from_domain_maps_all_fields() -> None:
    """Verify conversion from the authoritative domain model."""
    plant = _domain_plant(
        status=PlantStatus.PLANNED_OUTAGE,
        timezone_name="Asia/Karachi",
    )

    orm = PlantORM.from_domain(plant)

    assert orm.plant_id == plant.plant_id
    assert orm.plant_name == plant.plant_name
    assert orm.region == plant.region
    assert orm.latitude == plant.latitude
    assert orm.longitude == plant.longitude
    assert orm.dc_capacity_mw == plant.dc_capacity_mw
    assert orm.ac_capacity_mw == plant.ac_capacity_mw
    assert orm.commissioning_date == plant.commissioning_date
    assert orm.status == PlantStatus.PLANNED_OUTAGE.value
    assert orm.timezone_name == "Asia/Karachi"


def test_from_domain_rejects_invalid_type() -> None:
    """Verify conversion rejects non-Plant values."""
    with pytest.raises(TypeError, match="Plant instance"):
        PlantORM.from_domain(object())  # type: ignore[arg-type]


def test_to_domain_returns_authoritative_model() -> None:
    """Verify conversion back to the Plant domain model."""
    orm = _orm_plant(
        status=PlantStatus.DECOMMISSIONED.value,
        timezone_name="Asia/Karachi",
    )

    plant = orm.to_domain()

    assert isinstance(plant, Plant)
    assert plant.plant_id == orm.plant_id
    assert plant.plant_name == orm.plant_name
    assert plant.region == orm.region
    assert plant.latitude == orm.latitude
    assert plant.longitude == orm.longitude
    assert plant.dc_capacity_mw == orm.dc_capacity_mw
    assert plant.ac_capacity_mw == orm.ac_capacity_mw
    assert plant.commissioning_date == orm.commissioning_date
    assert plant.status is PlantStatus.DECOMMISSIONED
    assert plant.timezone_name == "Asia/Karachi"


def test_domain_round_trip_preserves_values() -> None:
    """Verify domain-to-ORM-to-domain conversion is lossless."""
    original = _domain_plant(
        status=PlantStatus.PLANNED_OUTAGE,
        timezone_name="Asia/Karachi",
    )

    restored = PlantORM.from_domain(original).to_domain()

    assert restored == original


def test_dc_ac_ratio() -> None:
    """Verify the derived DC-to-AC ratio."""
    orm = _orm_plant(
        dc_capacity_mw=125.0,
        ac_capacity_mw=100.0,
    )

    assert orm.dc_ac_ratio == 1.25


def test_update_from_domain_updates_mutable_fields() -> None:
    """Verify ORM values can be refreshed from a matching domain object."""
    orm = _orm_plant()
    updated = _domain_plant(
        plant_name="Lahore Solar Updated",
        region="Central Punjab",
        latitude=31.6,
        longitude=74.4,
        dc_capacity_mw=130.0,
        ac_capacity_mw=105.0,
        commissioning_date=date(2023, 6, 1),
        status=PlantStatus.PLANNED_OUTAGE,
        timezone_name="Asia/Karachi",
    )

    orm.update_from_domain(updated)

    assert orm.plant_name == "Lahore Solar Updated"
    assert orm.region == "Central Punjab"
    assert orm.latitude == 31.6
    assert orm.longitude == 74.4
    assert orm.dc_capacity_mw == 130.0
    assert orm.ac_capacity_mw == 105.0
    assert orm.commissioning_date == date(2023, 6, 1)
    assert orm.status == PlantStatus.PLANNED_OUTAGE.value
    assert orm.timezone_name == "Asia/Karachi"


def test_update_from_domain_rejects_invalid_type() -> None:
    """Verify update rejects non-Plant values."""
    orm = _orm_plant()

    with pytest.raises(TypeError, match="Plant instance"):
        orm.update_from_domain(object())  # type: ignore[arg-type]


def test_update_from_domain_rejects_different_identifier() -> None:
    """Verify a persisted identity cannot be changed accidentally."""
    orm = _orm_plant()
    different = _domain_plant(plant_id="PLANT-002")

    with pytest.raises(ValueError, match="different plant_id"):
        orm.update_from_domain(different)


def test_to_record_serializes_values() -> None:
    """Verify database records are serialization-ready."""
    created_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    updated_at = created_at + timedelta(hours=1)
    orm = _orm_plant()
    orm.created_at = created_at
    orm.updated_at = updated_at

    record = orm.to_record()

    assert record == {
        "plant_id": "PLANT-001",
        "plant_name": "Lahore Solar One",
        "region": "Punjab",
        "latitude": 31.5204,
        "longitude": 74.3587,
        "dc_capacity_mw": 120.0,
        "ac_capacity_mw": 100.0,
        "commissioning_date": "2024-01-15",
        "status": PlantStatus.OPERATIONAL.value,
        "timezone_name": "UTC",
        "dc_ac_ratio": 1.2,
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
    }


def test_to_record_handles_unset_audit_timestamps() -> None:
    """Verify unsaved ORM objects serialize missing audit timestamps."""
    record = _orm_plant().to_record()

    assert record["created_at"] is None
    assert record["updated_at"] is None


def test_repr_contains_key_identity_fields() -> None:
    """Verify developer representation is concise and useful."""
    value = repr(_orm_plant())

    assert "PlantORM" in value
    assert "PLANT-001" in value
    assert "Lahore Solar One" in value
    assert PlantStatus.OPERATIONAL.value in value


def test_status_default_matches_domain_default() -> None:
    """Verify ORM status defaults to operational."""
    column = PlantORM.__table__.columns["status"]

    assert column.default is not None
    assert column.default.arg == PlantStatus.OPERATIONAL.value
    assert column.server_default is not None


def test_timezone_default_is_utc() -> None:
    """Verify ORM timezone defaults to UTC."""
    column = PlantORM.__table__.columns["timezone_name"]

    assert column.default is not None
    assert column.default.arg == "UTC"
    assert column.server_default is not None


def test_audit_columns_are_timezone_aware() -> None:
    """Verify audit timestamps use timezone-aware SQL types."""
    created_type = PlantORM.__table__.columns["created_at"].type
    updated_type = PlantORM.__table__.columns["updated_at"].type

    assert created_type.timezone is True
    assert updated_type.timezone is True
