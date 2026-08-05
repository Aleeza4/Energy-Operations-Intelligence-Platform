"""
Unit tests for the EOIP synthetic alarm generator.

These tests verify deterministic alarm derivation from SCADA states, lifecycle
generation, configuration validation, event merging, serialization, and Alarm
domain-model integrity.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import Any

import pytest

from eoip.synthetic.generators.alarm_generator import (
    AlarmGeneratorConfig,
    generate_alarm_records,
    generate_alarms,
)
from eoip.synthetic.generators.equipment_generator import (
    EquipmentGeneratorConfig,
)
from eoip.synthetic.generators.plant_generator import (
    PlantGeneratorConfig,
)
from eoip.synthetic.generators.scada_generator import (
    SCADAGeneratorConfig,
)
from eoip.synthetic.generators.weather_generator import (
    WeatherGeneratorConfig,
)
from eoip.synthetic.models.alarm import (
    Alarm,
    AlarmCategory,
    AlarmSeverity,
    AlarmStatus,
)


def _start() -> datetime:
    """Return the standard generator start timestamp."""
    return datetime(2025, 6, 1, tzinfo=UTC)


def _plant_config() -> PlantGeneratorConfig:
    """Return a one-plant deterministic configuration."""
    return PlantGeneratorConfig(
        plant_count=1,
        random_seed=11,
    )


def _equipment_config(
    *,
    string_inverters_per_plant: int = 1,
) -> EquipmentGeneratorConfig:
    """Return a compact deterministic equipment configuration."""
    return EquipmentGeneratorConfig(
        random_seed=22,
        string_inverters_per_plant=string_inverters_per_plant,
        transformers_per_plant=1,
        feeders_per_plant=1,
        weather_stations_per_plant=1,
        revenue_meters_per_plant=1,
        protection_relays_per_plant=1,
    )


def _weather_config() -> WeatherGeneratorConfig:
    """Return weather aligned with alarm-generator SCADA tests."""
    return WeatherGeneratorConfig(
        start_at=_start(),
        duration_days=1,
        interval_minutes=15,
        random_seed=33,
        estimated_probability=0.0,
        missing_probability=0.0,
    )


def _scada_config(**overrides: Any) -> SCADAGeneratorConfig:
    """Return a compact deterministic SCADA configuration."""
    data: dict[str, Any] = {
        "start_at": _start(),
        "duration_days": 1,
        "interval_minutes": 15,
        "random_seed": 44,
        "derating_probability": 0.0,
        "forced_outage_probability": 0.0,
        "maintenance_probability": 0.0,
        "estimated_probability": 0.0,
        "missing_probability": 0.0,
    }
    data.update(overrides)
    return SCADAGeneratorConfig(**data)


def _alarm_config(**overrides: Any) -> AlarmGeneratorConfig:
    """Return a deterministic alarm-generator configuration."""
    data: dict[str, Any] = {
        "random_seed": 55,
        "acknowledgement_probability": 1.0,
        "clearance_probability": 1.0,
        "minimum_acknowledgement_minutes": 1,
        "maximum_acknowledgement_minutes": 1,
        "minimum_clearance_minutes": 5,
        "maximum_clearance_minutes": 5,
        "generate_derating_alarms": True,
        "generate_maintenance_alarms": True,
        "generate_grid_alarms": True,
        "is_synthetic_ground_truth": True,
    }
    data.update(overrides)
    return AlarmGeneratorConfig(**data)


def _generate(
    *,
    alarm_config: AlarmGeneratorConfig | None = None,
    scada_config: SCADAGeneratorConfig | None = None,
) -> tuple[Alarm, ...]:
    """Generate alarms using compact aligned dependencies."""
    return generate_alarms(
        alarm_config or _alarm_config(),
        scada_config=scada_config or _scada_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        weather_config=_weather_config(),
    )


def test_generate_alarms_returns_tuple() -> None:
    """The public API should return an immutable tuple."""
    alarms = _generate(
        scada_config=_scada_config(forced_outage_probability=1.0),
    )

    assert isinstance(alarms, tuple)
    assert all(isinstance(alarm, Alarm) for alarm in alarms)


def test_no_alarm_states_generate_no_alarms() -> None:
    """Normal and night SCADA states should not create alarms."""
    alarms = _generate()

    assert alarms == ()


def test_fault_state_generates_critical_equipment_alarm() -> None:
    """Fault SCADA states should create critical equipment alarms."""
    alarms = _generate(
        scada_config=_scada_config(forced_outage_probability=1.0),
    )

    assert alarms
    assert all(alarm.alarm_code == "EQUIPMENT_FAULT" for alarm in alarms)
    assert all(alarm.category is AlarmCategory.EQUIPMENT for alarm in alarms)
    assert all(alarm.severity is AlarmSeverity.CRITICAL for alarm in alarms)


def test_derated_state_generates_performance_alarm() -> None:
    """Derated SCADA states should create warning performance alarms."""
    alarms = _generate(
        scada_config=_scada_config(derating_probability=1.0),
    )

    assert alarms
    assert all(alarm.alarm_code == "PERFORMANCE_DERATING" for alarm in alarms)
    assert all(alarm.category is AlarmCategory.PERFORMANCE for alarm in alarms)
    assert all(alarm.severity is AlarmSeverity.WARNING for alarm in alarms)


def test_maintenance_state_generates_informational_alarm() -> None:
    """Maintenance SCADA states should create informational alarms."""
    alarms = _generate(
        scada_config=_scada_config(maintenance_probability=1.0),
    )

    assert alarms
    assert all(alarm.alarm_code == "PLANNED_MAINTENANCE" for alarm in alarms)
    assert all(alarm.severity is AlarmSeverity.INFORMATIONAL for alarm in alarms)


def test_derating_alarms_can_be_disabled() -> None:
    """Disabling derating alarms should suppress derated-state events."""
    alarms = _generate(
        alarm_config=_alarm_config(generate_derating_alarms=False),
        scada_config=_scada_config(derating_probability=1.0),
    )

    assert alarms == ()


def test_maintenance_alarms_can_be_disabled() -> None:
    """Disabling maintenance alarms should suppress maintenance events."""
    alarms = _generate(
        alarm_config=_alarm_config(generate_maintenance_alarms=False),
        scada_config=_scada_config(maintenance_probability=1.0),
    )

    assert alarms == ()


def test_consecutive_states_are_merged_into_single_alarm() -> None:
    """One continuous daylight fault window should produce one alarm."""
    alarms = _generate(
        scada_config=_scada_config(forced_outage_probability=1.0),
    )

    assert len(alarms) == 1


def test_multiple_equipment_assets_receive_unique_alarm_ids() -> None:
    """Alarm IDs should remain unique across equipment streams."""
    alarms = generate_alarms(
        _alarm_config(),
        scada_config=_scada_config(forced_outage_probability=1.0),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(
            string_inverters_per_plant=3,
        ),
        weather_config=_weather_config(),
    )

    alarm_ids = [alarm.alarm_id for alarm in alarms]

    assert len(alarms) == 3
    assert len(alarm_ids) == len(set(alarm_ids))
    assert alarm_ids == [
        "ALM-0000001",
        "ALM-0000002",
        "ALM-0000003",
    ]


def test_generation_is_deterministic() -> None:
    """The same configuration should generate identical alarms."""
    first_result = _generate(
        scada_config=_scada_config(forced_outage_probability=1.0),
    )
    second_result = _generate(
        scada_config=_scada_config(forced_outage_probability=1.0),
    )

    assert first_result == second_result


def test_acknowledgement_probability_zero_keeps_alarm_active() -> None:
    """Without acknowledgement or clearance, alarms should remain active."""
    alarms = _generate(
        alarm_config=_alarm_config(
            acknowledgement_probability=0.0,
            clearance_probability=0.0,
        ),
        scada_config=_scada_config(forced_outage_probability=1.0),
    )

    assert alarms
    assert all(alarm.status is AlarmStatus.ACTIVE for alarm in alarms)
    assert all(alarm.acknowledged_at is None for alarm in alarms)
    assert all(alarm.cleared_at is None for alarm in alarms)


def test_acknowledged_alarm_has_acknowledgement_timestamp() -> None:
    """Acknowledged alarms should include a valid acknowledgement time."""
    alarms = _generate(
        alarm_config=_alarm_config(clearance_probability=0.0),
        scada_config=_scada_config(forced_outage_probability=1.0),
    )

    assert alarms
    assert all(alarm.status is AlarmStatus.ACKNOWLEDGED for alarm in alarms)
    assert all(alarm.acknowledged_at is not None for alarm in alarms)
    assert all(alarm.cleared_at is None for alarm in alarms)


def test_cleared_alarm_has_ordered_lifecycle_timestamps() -> None:
    """Cleared alarms should preserve raise, acknowledgement, and clear order."""
    alarms = _generate(
        scada_config=_scada_config(forced_outage_probability=1.0),
    )

    assert alarms
    assert all(alarm.status is AlarmStatus.CLEARED for alarm in alarms)

    for alarm in alarms:
        assert alarm.acknowledged_at is not None
        assert alarm.cleared_at is not None
        assert alarm.raised_at <= alarm.acknowledged_at
        assert alarm.acknowledged_at <= alarm.cleared_at


def test_ground_truth_flag_uses_configuration() -> None:
    """Generated alarms should preserve the configured ground-truth flag."""
    true_alarms = _generate(
        alarm_config=_alarm_config(is_synthetic_ground_truth=True),
        scada_config=_scada_config(forced_outage_probability=1.0),
    )
    false_alarms = _generate(
        alarm_config=_alarm_config(is_synthetic_ground_truth=False),
        scada_config=_scada_config(forced_outage_probability=1.0),
    )

    assert all(alarm.is_synthetic_ground_truth for alarm in true_alarms)
    assert all(alarm.is_synthetic_ground_truth is False for alarm in false_alarms)


def test_alarm_plant_and_equipment_ids_are_valid() -> None:
    """Generated alarms should contain canonical plant and equipment IDs."""
    alarms = _generate(
        scada_config=_scada_config(forced_outage_probability=1.0),
    )

    assert all(alarm.plant_id == "PLANT-001" for alarm in alarms)
    assert all(alarm.equipment_id.startswith("EQP-") for alarm in alarms)


def test_generate_alarm_records_matches_serialization() -> None:
    """Generated dictionaries should match Alarm.to_record output."""
    alarm_config = _alarm_config()
    scada_config = _scada_config(forced_outage_probability=1.0)

    alarms = generate_alarms(
        alarm_config,
        scada_config=scada_config,
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        weather_config=_weather_config(),
    )
    records = generate_alarm_records(
        alarm_config,
        scada_config=scada_config,
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        weather_config=_weather_config(),
    )

    assert records == tuple(alarm.to_record() for alarm in alarms)


def test_alarm_records_use_primitive_values() -> None:
    """Serialized alarm records should contain primitive analytics values."""
    records = generate_alarm_records(
        _alarm_config(),
        scada_config=_scada_config(forced_outage_probability=1.0),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        weather_config=_weather_config(),
    )

    assert records
    record = records[0]

    assert isinstance(record, dict)
    assert isinstance(record["raised_at"], str)
    assert isinstance(record["category"], str)
    assert isinstance(record["severity"], str)
    assert isinstance(record["status"], str)
    assert isinstance(record["is_open"], bool)


def test_default_config_values() -> None:
    """AlarmGeneratorConfig should expose documented defaults."""
    config = AlarmGeneratorConfig()

    assert config.random_seed == 42
    assert config.acknowledgement_probability == 0.85
    assert config.clearance_probability == 0.80
    assert config.minimum_acknowledgement_minutes == 1
    assert config.maximum_acknowledgement_minutes == 15
    assert config.minimum_clearance_minutes == 5
    assert config.maximum_clearance_minutes == 120
    assert config.generate_derating_alarms is True
    assert config.generate_maintenance_alarms is True
    assert config.generate_grid_alarms is True
    assert config.is_synthetic_ground_truth is True


def test_config_is_immutable() -> None:
    """AlarmGeneratorConfig should be frozen."""
    config = AlarmGeneratorConfig()

    with pytest.raises(FrozenInstanceError):
        config.random_seed = 1  # type: ignore[misc]


@pytest.mark.parametrize(
    "random_seed",
    [True, 1.5, "42", None],
)
def test_invalid_random_seed_type(random_seed: object) -> None:
    """random_seed must be an integer excluding booleans."""
    with pytest.raises(TypeError, match="random_seed must be an integer"):
        AlarmGeneratorConfig(random_seed=random_seed)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field_name",
    [
        "acknowledgement_probability",
        "clearance_probability",
    ],
)
@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_probability_bounds(
    field_name: str,
    value: float,
) -> None:
    """Probabilities must remain between zero and one."""
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        AlarmGeneratorConfig(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "acknowledgement_probability",
        "clearance_probability",
    ],
)
@pytest.mark.parametrize("value", [True, "0.5", None])
def test_probability_types(
    field_name: str,
    value: object,
) -> None:
    """Probabilities must be numeric values."""
    with pytest.raises(TypeError, match=f"{field_name} must be numeric"):
        AlarmGeneratorConfig(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "minimum_acknowledgement_minutes",
        "maximum_acknowledgement_minutes",
        "minimum_clearance_minutes",
        "maximum_clearance_minutes",
    ],
)
@pytest.mark.parametrize("value", [True, 1.5, "1", None])
def test_delay_fields_require_integers(
    field_name: str,
    value: object,
) -> None:
    """Lifecycle delay settings must be integers."""
    with pytest.raises(TypeError, match=f"{field_name} must be an integer"):
        AlarmGeneratorConfig(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "minimum_acknowledgement_minutes",
        "maximum_acknowledgement_minutes",
        "minimum_clearance_minutes",
        "maximum_clearance_minutes",
    ],
)
def test_delay_fields_reject_negative_values(field_name: str) -> None:
    """Lifecycle delay settings must not be negative."""
    with pytest.raises(ValueError, match="greater than or equal to zero"):
        AlarmGeneratorConfig(**{field_name: -1})


def test_reversed_acknowledgement_bounds_are_rejected() -> None:
    """Maximum acknowledgement delay must not be below minimum."""
    with pytest.raises(
        ValueError,
        match="maximum_acknowledgement_minutes",
    ):
        AlarmGeneratorConfig(
            minimum_acknowledgement_minutes=10,
            maximum_acknowledgement_minutes=5,
        )


def test_reversed_clearance_bounds_are_rejected() -> None:
    """Maximum clearance delay must not be below minimum."""
    with pytest.raises(
        ValueError,
        match="maximum_clearance_minutes",
    ):
        AlarmGeneratorConfig(
            minimum_clearance_minutes=10,
            maximum_clearance_minutes=5,
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "generate_derating_alarms",
        "generate_maintenance_alarms",
        "generate_grid_alarms",
        "is_synthetic_ground_truth",
    ],
)
@pytest.mark.parametrize("value", [1, 0, "true", None])
def test_boolean_fields_require_actual_booleans(
    field_name: str,
    value: object,
) -> None:
    """Boolean configuration fields must reject non-bool values."""
    with pytest.raises(TypeError, match=f"{field_name} must be a boolean"):
        AlarmGeneratorConfig(**{field_name: value})
