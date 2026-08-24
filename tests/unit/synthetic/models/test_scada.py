"""
Unit tests for the EOIP SCADA telemetry domain model.

These tests verify valid telemetry creation, identifier normalization,
timestamp requirements, measurement validation, operational consistency,
derived properties, serialization, and dataclass immutability.
"""

from __future__ import annotations

import math
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest

from eoip.synthetic.models.scada import (
    SCADAObservation,
    SCADAOperatingState,
    SCADAQuality,
)


def _make_scada_observation(**overrides: Any) -> SCADAObservation:
    """Create a valid SCADA observation with optional field overrides."""
    observation_data: dict[str, Any] = {
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "timestamp": datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
        "active_power_kw": 100.0,
        "interval_energy_kwh": 25.0,
        "dc_voltage_v": 1000.0,
        "dc_current_a": 110.0,
        "ac_voltage_v": 400.0,
        "ac_current_a": 145.0,
        "frequency_hz": 50.0,
        "power_factor": 0.98,
        "equipment_available": True,
        "grid_available": True,
        "operating_state": SCADAOperatingState.NORMAL,
        "quality": SCADAQuality.VALID,
    }
    observation_data.update(overrides)
    return SCADAObservation(**observation_data)


def test_scada_observation_preserves_valid_fields() -> None:
    """A valid SCADA observation should retain all supplied values."""
    observation = _make_scada_observation()

    assert observation.plant_id == "PLANT-001"
    assert observation.equipment_id == "EQP-00001"
    assert observation.timestamp == datetime(
        2026,
        1,
        15,
        12,
        0,
        tzinfo=UTC,
    )
    assert observation.active_power_kw == 100.0
    assert observation.interval_energy_kwh == 25.0
    assert observation.dc_voltage_v == 1000.0
    assert observation.dc_current_a == 110.0
    assert observation.ac_voltage_v == 400.0
    assert observation.ac_current_a == 145.0
    assert observation.frequency_hz == 50.0
    assert observation.power_factor == 0.98
    assert observation.equipment_available is True
    assert observation.grid_available is True
    assert observation.operating_state is SCADAOperatingState.NORMAL
    assert observation.quality is SCADAQuality.VALID


def test_scada_observation_normalizes_identifiers() -> None:
    """Plant and equipment identifiers should be trimmed and uppercased."""
    observation = _make_scada_observation(
        plant_id=" plant-001 ",
        equipment_id=" eqp-00001 ",
    )

    assert observation.plant_id == "PLANT-001"
    assert observation.equipment_id == "EQP-00001"


def test_scada_quality_defaults_to_valid() -> None:
    """SCADA quality should default to VALID."""
    observation = SCADAObservation(
        plant_id="PLANT-001",
        equipment_id="EQP-00001",
        timestamp=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
        active_power_kw=100.0,
        interval_energy_kwh=25.0,
        dc_voltage_v=1000.0,
        dc_current_a=110.0,
        ac_voltage_v=400.0,
        ac_current_a=145.0,
        frequency_hz=50.0,
        power_factor=0.98,
        equipment_available=True,
        grid_available=True,
        operating_state=SCADAOperatingState.NORMAL,
    )

    assert observation.quality is SCADAQuality.VALID


def test_calculated_interval_energy_matches_fifteen_minute_interval() -> None:
    """Calculated interval energy should equal active power multiplied by 0.25."""
    observation = _make_scada_observation(active_power_kw=123.456)

    assert observation.calculated_interval_energy_kwh == 30.864


def test_energy_deviation_returns_reported_minus_calculated_energy() -> None:
    """Energy deviation should compare reported and calculated interval energy."""
    observation = _make_scada_observation(
        active_power_kw=100.0,
        interval_energy_kwh=24.5,
    )

    assert observation.energy_deviation_kwh == -0.5


@pytest.mark.parametrize(
    (
        "active_power_kw",
        "interval_energy_kwh",
        "equipment_available",
        "grid_available",
        "operating_state",
        "expected",
    ),
    [
        (
            100.0,
            25.0,
            True,
            True,
            SCADAOperatingState.NORMAL,
            True,
        ),
        (
            0.0,
            0.0,
            True,
            True,
            SCADAOperatingState.STOPPED,
            False,
        ),
        (
            0.0,
            0.0,
            False,
            True,
            SCADAOperatingState.STOPPED,
            False,
        ),
        (
            0.0,
            0.0,
            True,
            False,
            SCADAOperatingState.STOPPED,
            False,
        ),
        (
            0.0,
            0.0,
            False,
            False,
            SCADAOperatingState.STOPPED,
            False,
        ),
    ],
)
def test_is_exporting_uses_power_and_availability(
    active_power_kw: float,
    interval_energy_kwh: float,
    equipment_available: bool,
    grid_available: bool,
    operating_state: SCADAOperatingState,
    expected: bool,
) -> None:
    """Exporting should require positive power and both availability flags."""
    observation = _make_scada_observation(
        active_power_kw=active_power_kw,
        interval_energy_kwh=interval_energy_kwh,
        equipment_available=equipment_available,
        grid_available=grid_available,
        operating_state=operating_state,
    )

    assert observation.is_exporting is expected


def test_to_record_returns_complete_serialized_record() -> None:
    """Serialization should return a complete analytics-ready dictionary."""
    observation = _make_scada_observation()

    assert observation.to_record() == {
        "plant_id": "PLANT-001",
        "equipment_id": "EQP-00001",
        "timestamp": "2026-01-15T12:00:00+00:00",
        "active_power_kw": 100.0,
        "interval_energy_kwh": 25.0,
        "dc_voltage_v": 1000.0,
        "dc_current_a": 110.0,
        "ac_voltage_v": 400.0,
        "ac_current_a": 145.0,
        "frequency_hz": 50.0,
        "power_factor": 0.98,
        "equipment_available": True,
        "grid_available": True,
        "operating_state": "normal",
        "quality": "valid",
        "is_exporting": True,
        "calculated_interval_energy_kwh": 25.0,
        "energy_deviation_kwh": 0.0,
    }


def test_scada_observation_is_immutable() -> None:
    """SCADA observations should reject field modification."""
    observation = _make_scada_observation()

    with pytest.raises(FrozenInstanceError):
        observation.active_power_kw = 200.0  # type: ignore[misc]


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
def test_scada_observation_rejects_invalid_plant_id(
    plant_id: str,
) -> None:
    """Plant IDs must follow the PLANT-001 format."""
    with pytest.raises(ValueError, match="Invalid plant_id"):
        _make_scada_observation(plant_id=plant_id)


@pytest.mark.parametrize(
    "equipment_id",
    [
        "",
        "   ",
        "EQP-1",
        "EQP-0001",
        "EQP-000001",
        "EQUIPMENT-00001",
        "EQP-ABCDE",
        "EQP_00001",
    ],
)
def test_scada_observation_rejects_invalid_equipment_id(
    equipment_id: str,
) -> None:
    """Equipment IDs must follow the EQP-00001 format."""
    with pytest.raises(ValueError, match="Invalid equipment_id"):
        _make_scada_observation(equipment_id=equipment_id)


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-01-15T12:00:00+00:00",
        20260115,
        None,
        object(),
    ],
)
def test_scada_observation_rejects_non_datetime_timestamp(
    timestamp: object,
) -> None:
    """SCADA timestamps must be datetime values."""
    with pytest.raises(TypeError, match="Use a datetime value"):
        _make_scada_observation(timestamp=timestamp)


def test_scada_observation_rejects_timezone_naive_timestamp() -> None:
    """Timezone-naive SCADA timestamps must be rejected."""
    timestamp = datetime(2026, 1, 15, 12, 0)

    with pytest.raises(ValueError, match="is timezone-naive"):
        _make_scada_observation(timestamp=timestamp)


def test_scada_observation_accepts_non_utc_aware_timestamp() -> None:
    """Any timezone-aware timestamp should be accepted."""
    local_timezone = timezone(timedelta(hours=5))
    timestamp = datetime(2026, 1, 15, 12, 0, tzinfo=local_timezone)

    observation = _make_scada_observation(timestamp=timestamp)

    assert observation.timestamp == timestamp
    assert observation.timestamp.utcoffset() == timedelta(hours=5)


@pytest.mark.parametrize(
    "timestamp",
    [
        datetime(2026, 1, 15, 12, 1, tzinfo=UTC),
        datetime(2026, 1, 15, 12, 14, tzinfo=UTC),
        datetime(2026, 1, 15, 12, 16, tzinfo=UTC),
        datetime(2026, 1, 15, 12, 0, 1, tzinfo=UTC),
        datetime(2026, 1, 15, 12, 0, 0, 1, tzinfo=UTC),
    ],
)
def test_scada_observation_rejects_misaligned_timestamp(
    timestamp: datetime,
) -> None:
    """SCADA timestamps must align to exact 15-minute intervals."""
    with pytest.raises(ValueError, match="not aligned"):
        _make_scada_observation(timestamp=timestamp)


@pytest.mark.parametrize(
    "timestamp",
    [
        datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
        datetime(2026, 1, 15, 12, 15, tzinfo=UTC),
        datetime(2026, 1, 15, 12, 30, tzinfo=UTC),
        datetime(2026, 1, 15, 12, 45, tzinfo=UTC),
    ],
)
def test_scada_observation_accepts_aligned_timestamp(
    timestamp: datetime,
) -> None:
    """Minutes 00, 15, 30, and 45 should be accepted."""
    observation = _make_scada_observation(timestamp=timestamp)

    assert observation.timestamp == timestamp


@pytest.mark.parametrize(
    ("field_name", "minimum", "maximum"),
    [
        ("active_power_kw", 0.0, 50_000.0),
        ("interval_energy_kwh", 0.0, 12_500.0),
        ("dc_voltage_v", 0.0, 2_000.0),
        ("dc_current_a", 0.0, 10_000.0),
        ("ac_voltage_v", 0.0, 50_000.0),
        ("ac_current_a", 0.0, 10_000.0),
        ("frequency_hz", 0.0, 70.0),
        ("power_factor", -1.0, 1.0),
    ],
)
def test_scada_observation_accepts_measurement_boundaries(
    field_name: str,
    minimum: float,
    maximum: float,
) -> None:
    """Every documented measurement boundary should be accepted."""
    minimum_kwargs: dict[str, Any] = {field_name: minimum}
    maximum_kwargs: dict[str, Any] = {field_name: maximum}

    minimum_observation = _make_scada_observation(**minimum_kwargs)
    maximum_observation = _make_scada_observation(**maximum_kwargs)

    assert getattr(minimum_observation, field_name) == minimum
    assert getattr(maximum_observation, field_name) == maximum


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("active_power_kw", -0.1),
        ("active_power_kw", 50_000.1),
        ("interval_energy_kwh", -0.1),
        ("interval_energy_kwh", 12_500.1),
        ("dc_voltage_v", -0.1),
        ("dc_voltage_v", 2_000.1),
        ("dc_current_a", -0.1),
        ("dc_current_a", 10_000.1),
        ("ac_voltage_v", -0.1),
        ("ac_voltage_v", 50_000.1),
        ("ac_current_a", -0.1),
        ("ac_current_a", 10_000.1),
        ("frequency_hz", -0.1),
        ("frequency_hz", 70.1),
        ("power_factor", -1.1),
        ("power_factor", 1.1),
    ],
)
def test_scada_observation_rejects_out_of_range_measurements(
    field_name: str,
    invalid_value: float,
) -> None:
    """Measurements outside their documented ranges must be rejected."""
    with pytest.raises(ValueError, match=f"Invalid {field_name} value"):
        _make_scada_observation(**{field_name: invalid_value})


@pytest.mark.parametrize(
    "field_name",
    [
        "active_power_kw",
        "interval_energy_kwh",
        "dc_voltage_v",
        "dc_current_a",
        "ac_voltage_v",
        "ac_current_a",
        "frequency_hz",
        "power_factor",
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
def test_scada_observation_rejects_non_numeric_measurements(
    field_name: str,
    invalid_value: object,
) -> None:
    """Measurements must be numeric and must reject boolean values."""
    with pytest.raises(TypeError, match=f"Invalid {field_name} value"):
        _make_scada_observation(**{field_name: invalid_value})


@pytest.mark.parametrize(
    "invalid_value",
    [
        math.nan,
        math.inf,
        -math.inf,
    ],
)
@pytest.mark.parametrize(
    "field_name",
    [
        "active_power_kw",
        "interval_energy_kwh",
        "dc_voltage_v",
        "dc_current_a",
        "ac_voltage_v",
        "ac_current_a",
        "frequency_hz",
        "power_factor",
    ],
)
def test_scada_observation_rejects_non_finite_measurements(
    field_name: str,
    invalid_value: float,
) -> None:
    """NaN and infinite SCADA measurements must be rejected."""
    with pytest.raises(ValueError, match="must be finite"):
        _make_scada_observation(**{field_name: invalid_value})


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("equipment_available", 1),
        ("equipment_available", "true"),
        ("equipment_available", None),
        ("grid_available", 0),
        ("grid_available", "false"),
        ("grid_available", None),
    ],
)
def test_scada_observation_rejects_non_boolean_availability(
    field_name: str,
    invalid_value: object,
) -> None:
    """Availability fields must be actual boolean values."""
    with pytest.raises(TypeError, match=f"Invalid {field_name} value"):
        _make_scada_observation(**{field_name: invalid_value})


@pytest.mark.parametrize("operating_state", list(SCADAOperatingState))
def test_scada_observation_accepts_every_operating_state(
    operating_state: SCADAOperatingState,
) -> None:
    """Every documented operating state should be accepted when consistent."""
    zero_generation_states = {
        SCADAOperatingState.STOPPED,
        SCADAOperatingState.FAULT,
        SCADAOperatingState.MAINTENANCE,
        SCADAOperatingState.NIGHT,
    }

    overrides: dict[str, Any] = {
        "operating_state": operating_state,
    }

    if operating_state in zero_generation_states:
        overrides.update(
            active_power_kw=0.0,
            interval_energy_kwh=0.0,
        )

    observation = _make_scada_observation(**overrides)

    assert observation.operating_state is operating_state


@pytest.mark.parametrize(
    "operating_state",
    [
        "normal",
        "fault",
        1,
        None,
    ],
)
def test_scada_observation_rejects_invalid_operating_state(
    operating_state: object,
) -> None:
    """Raw strings and unsupported values must not replace the state enum."""
    with pytest.raises(
        TypeError,
        match="Use a SCADAOperatingState value",
    ):
        _make_scada_observation(operating_state=operating_state)


@pytest.mark.parametrize("quality", list(SCADAQuality))
def test_scada_observation_accepts_every_quality(
    quality: SCADAQuality,
) -> None:
    """Every documented SCADA quality value should be accepted."""
    observation = _make_scada_observation(quality=quality)

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
def test_scada_observation_rejects_invalid_quality(
    quality: object,
) -> None:
    """Raw strings and unsupported values must not replace SCADAQuality."""
    with pytest.raises(TypeError, match="Use a SCADAQuality value"):
        _make_scada_observation(quality=quality)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("active_power_kw", 100.0),
        ("interval_energy_kwh", 25.0),
    ],
)
def test_unavailable_equipment_rejects_positive_generation(
    field_name: str,
    invalid_value: float,
) -> None:
    """Unavailable equipment must not report positive power or energy."""
    overrides: dict[str, Any] = {
        "active_power_kw": 0.0,
        "interval_energy_kwh": 0.0,
        "equipment_available": False,
        "operating_state": SCADAOperatingState.STOPPED,
    }
    overrides[field_name] = invalid_value

    with pytest.raises(ValueError, match="equipment_available=False"):
        _make_scada_observation(**overrides)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("active_power_kw", 100.0),
        ("interval_energy_kwh", 25.0),
    ],
)
def test_unavailable_grid_rejects_positive_generation(
    field_name: str,
    invalid_value: float,
) -> None:
    """Grid-unavailable observations must not report positive generation."""
    overrides: dict[str, Any] = {
        "active_power_kw": 0.0,
        "interval_energy_kwh": 0.0,
        "grid_available": False,
        "operating_state": SCADAOperatingState.STOPPED,
    }
    overrides[field_name] = invalid_value

    with pytest.raises(ValueError, match="grid_available=False"):
        _make_scada_observation(**overrides)


@pytest.mark.parametrize(
    "operating_state",
    [
        SCADAOperatingState.STOPPED,
        SCADAOperatingState.FAULT,
        SCADAOperatingState.MAINTENANCE,
        SCADAOperatingState.NIGHT,
    ],
)
def test_non_generating_states_reject_positive_generation(
    operating_state: SCADAOperatingState,
) -> None:
    """Non-generating states must report zero power and interval energy."""
    with pytest.raises(ValueError, match="requires active_power_kw"):
        _make_scada_observation(operating_state=operating_state)


@pytest.mark.parametrize(
    ("equipment_available", "grid_available"),
    [
        (False, True),
        (True, False),
        (False, False),
    ],
)
def test_normal_state_requires_both_availability_flags(
    equipment_available: bool,
    grid_available: bool,
) -> None:
    """NORMAL state should require equipment and grid availability."""
    with pytest.raises(ValueError, match="requires equipment_available=True"):
        _make_scada_observation(
            active_power_kw=0.0,
            interval_energy_kwh=0.0,
            equipment_available=equipment_available,
            grid_available=grid_available,
            operating_state=SCADAOperatingState.NORMAL,
        )
