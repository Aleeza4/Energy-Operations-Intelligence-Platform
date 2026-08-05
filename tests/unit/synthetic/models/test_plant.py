"""
Unit tests for the EOIP synthetic Plant domain model.

These tests verify valid construction, normalization, serialization, derived
values, immutability, and clear rejection of invalid plant master data.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date, timedelta
from typing import Any

import pytest

from eoip.core.constants import UTC_TIMEZONE_NAME
from eoip.synthetic.models.plant import Plant, PlantStatus


def _make_plant(**overrides: Any) -> Plant:
    """Return a representative valid plant with optional field overrides."""
    values: dict[str, Any] = {
        "plant_id": "PLANT-001",
        "plant_name": "EOIP Solar Plant 01",
        "region": "Central Region",
        "latitude": 31.5204,
        "longitude": 74.3587,
        "dc_capacity_mw": 50.0,
        "ac_capacity_mw": 40.0,
        "commissioning_date": date(2020, 1, 15),
    }
    values.update(overrides)
    return Plant(**values)


def test_plant_creation_stores_expected_fields() -> None:
    """A valid plant should retain all supplied master-data values."""
    plant = _make_plant()

    assert plant.plant_id == "PLANT-001"
    assert plant.plant_name == "EOIP Solar Plant 01"
    assert plant.region == "Central Region"
    assert plant.latitude == 31.5204
    assert plant.longitude == 74.3587
    assert plant.dc_capacity_mw == 50.0
    assert plant.ac_capacity_mw == 40.0
    assert plant.commissioning_date == date(2020, 1, 15)


def test_plant_normalizes_text_fields() -> None:
    """Plant text fields should be trimmed and its identifier uppercased."""
    plant = _make_plant(
        plant_id="  plant-001  ",
        plant_name="  EOIP Solar Plant 01  ",
        region="  Central Region  ",
        timezone_name="  Asia/Karachi  ",
    )

    assert plant.plant_id == "PLANT-001"
    assert plant.plant_name == "EOIP Solar Plant 01"
    assert plant.region == "Central Region"
    assert plant.timezone_name == "Asia/Karachi"


def test_plant_uses_operational_status_and_utc_defaults() -> None:
    """A plant should default to operational status and the UTC timezone."""
    plant = _make_plant()

    assert plant.status is PlantStatus.OPERATIONAL
    assert plant.timezone_name == UTC_TIMEZONE_NAME


@pytest.mark.parametrize(
    ("dc_capacity_mw", "ac_capacity_mw", "expected_ratio"),
    [
        (50.0, 40.0, 1.25),
        (10.0, 3.0, 3.3333),
    ],
)
def test_dc_ac_ratio_is_rounded_to_four_decimal_places(
    dc_capacity_mw: float,
    ac_capacity_mw: float,
    expected_ratio: float,
) -> None:
    """The DC-to-AC ratio should be rounded to the documented precision."""
    plant = _make_plant(
        dc_capacity_mw=dc_capacity_mw,
        ac_capacity_mw=ac_capacity_mw,
    )

    assert plant.dc_ac_ratio == expected_ratio


def test_to_record_returns_complete_serialization_ready_dictionary() -> None:
    """Serialization should convert date and enum fields and include the ratio."""
    plant = _make_plant()

    assert plant.to_record() == {
        "plant_id": "PLANT-001",
        "plant_name": "EOIP Solar Plant 01",
        "region": "Central Region",
        "latitude": 31.5204,
        "longitude": 74.3587,
        "dc_capacity_mw": 50.0,
        "ac_capacity_mw": 40.0,
        "commissioning_date": "2020-01-15",
        "status": "operational",
        "timezone_name": UTC_TIMEZONE_NAME,
        "dc_ac_ratio": 1.25,
    }


def test_plant_is_immutable() -> None:
    """A constructed plant should reject field assignment."""
    plant = _make_plant()

    with pytest.raises(FrozenInstanceError):
        plant.plant_name = "Changed Plant Name"


@pytest.mark.parametrize(
    "plant_id",
    [
        "",
        "PLANT-1",
        "PLANT-01",
        "PLANT-0001",
        "SITE-001",
        "PLANT-00A",
        " PLANT-01 ",
    ],
)
def test_plant_rejects_invalid_identifier(plant_id: str) -> None:
    """Identifiers outside the PLANT-NNN format should be rejected."""
    with pytest.raises(ValueError, match="Invalid plant_id"):
        _make_plant(plant_id=plant_id)


@pytest.mark.parametrize("plant_name", ["", "   "])
def test_plant_rejects_empty_name(plant_name: str) -> None:
    """Empty and whitespace-only plant names should be rejected."""
    with pytest.raises(ValueError, match="plant_name cannot be empty"):
        _make_plant(plant_name=plant_name)


@pytest.mark.parametrize("region", ["", "   "])
def test_plant_rejects_empty_region(region: str) -> None:
    """Empty and whitespace-only operational regions should be rejected."""
    with pytest.raises(ValueError, match="region cannot be empty"):
        _make_plant(region=region)


@pytest.mark.parametrize("latitude", [-90.0001, 90.0001])
def test_plant_rejects_latitude_outside_valid_range(latitude: float) -> None:
    """Latitudes outside the inclusive geographic range should be rejected."""
    with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
        _make_plant(latitude=latitude)


@pytest.mark.parametrize("latitude", [-90.0, 90.0])
def test_plant_accepts_latitude_boundaries(latitude: float) -> None:
    """Latitude values at both geographic boundaries should be accepted."""
    assert _make_plant(latitude=latitude).latitude == latitude


@pytest.mark.parametrize("longitude", [-180.0001, 180.0001])
def test_plant_rejects_longitude_outside_valid_range(longitude: float) -> None:
    """Longitudes outside the inclusive geographic range should be rejected."""
    with pytest.raises(
        ValueError,
        match="Longitude must be between -180 and 180",
    ):
        _make_plant(longitude=longitude)


@pytest.mark.parametrize("longitude", [-180.0, 180.0])
def test_plant_accepts_longitude_boundaries(longitude: float) -> None:
    """Longitude values at both geographic boundaries should be accepted."""
    assert _make_plant(longitude=longitude).longitude == longitude


@pytest.mark.parametrize("dc_capacity_mw", [0.0, -1.0])
def test_plant_rejects_non_positive_dc_capacity(dc_capacity_mw: float) -> None:
    """Zero and negative DC capacities should be rejected."""
    with pytest.raises(ValueError, match="DC capacity must be greater than zero"):
        _make_plant(dc_capacity_mw=dc_capacity_mw)


@pytest.mark.parametrize("ac_capacity_mw", [0.0, -1.0])
def test_plant_rejects_non_positive_ac_capacity(ac_capacity_mw: float) -> None:
    """Zero and negative AC capacities should be rejected."""
    with pytest.raises(ValueError, match="AC capacity must be greater than zero"):
        _make_plant(ac_capacity_mw=ac_capacity_mw)


def test_plant_rejects_ac_capacity_greater_than_dc_capacity() -> None:
    """AC capacity exceeding installed DC capacity should be rejected."""
    with pytest.raises(ValueError, match="AC capacity .* exceeds DC capacity"):
        _make_plant(dc_capacity_mw=40.0, ac_capacity_mw=50.0)


def test_plant_accepts_equal_ac_and_dc_capacity() -> None:
    """Equal positive AC and DC capacities should be accepted."""
    plant = _make_plant(dc_capacity_mw=40.0, ac_capacity_mw=40.0)

    assert plant.dc_ac_ratio == 1.0


def test_plant_rejects_future_commissioning_date() -> None:
    """A commissioning date later than today should be rejected."""
    future_date = date.today() + timedelta(days=1)

    with pytest.raises(ValueError, match="Commissioning date .* is in the future"):
        _make_plant(commissioning_date=future_date)


@pytest.mark.parametrize("status", list(PlantStatus))
def test_plant_accepts_supported_status(status: PlantStatus) -> None:
    """Every declared PlantStatus member should be accepted unchanged."""
    assert _make_plant(status=status).status is status


@pytest.mark.parametrize("status", ["operational", "unsupported", 1, None])
def test_plant_rejects_values_that_are_not_plant_status(status: object) -> None:
    """Raw strings and unrelated types should not bypass status validation."""
    with pytest.raises(TypeError, match="Use a PlantStatus value"):
        _make_plant(status=status)


@pytest.mark.parametrize("timezone_name", ["", "   "])
def test_plant_rejects_empty_timezone(timezone_name: str) -> None:
    """Empty and whitespace-only timezone names should be rejected."""
    with pytest.raises(ValueError, match="timezone_name cannot be empty"):
        _make_plant(timezone_name=timezone_name)
