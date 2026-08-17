"""
Unit tests for the EOIP revenue-meter master-data generator.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date
from typing import Any

import pytest

from eoip.synthetic.generators.equipment_generator import (
    EquipmentGeneratorConfig,
    generate_equipment,
)
from eoip.synthetic.generators.meter_generator import (
    MeterGeneratorConfig,
    generate_revenue_meter_records,
    generate_revenue_meters,
)
from eoip.synthetic.generators.plant_generator import (
    PlantGeneratorConfig,
    generate_plants,
)
from eoip.synthetic.models.equipment import EquipmentType
from eoip.synthetic.models.meter import (
    MeterAccuracyClass,
    MeterStatus,
    RevenueMeter,
)


def _plant_config(*, plant_count: int = 2) -> PlantGeneratorConfig:
    """Return a compact deterministic plant configuration."""
    return PlantGeneratorConfig(
        plant_count=plant_count,
        random_seed=11,
    )


def _equipment_config(
    *,
    revenue_meters_per_plant: int = 1,
) -> EquipmentGeneratorConfig:
    """Return equipment configuration aligned with meter tests."""
    return EquipmentGeneratorConfig(
        random_seed=22,
        string_inverters_per_plant=1,
        transformers_per_plant=1,
        feeders_per_plant=1,
        weather_stations_per_plant=1,
        revenue_meters_per_plant=revenue_meters_per_plant,
        protection_relays_per_plant=1,
    )


def _meter_config(**overrides: Any) -> MeterGeneratorConfig:
    """Return a deterministic meter-generator configuration."""
    data: dict[str, Any] = {
        "random_seed": 33,
        "minimum_calibration_offset_days": 30,
        "maximum_calibration_offset_days": 60,
        "calibration_due_probability": 0.0,
        "out_of_service_probability": 0.0,
    }
    data.update(overrides)
    return MeterGeneratorConfig(**data)


def test_generate_revenue_meters_returns_tuple_of_models() -> None:
    """Verify the generator returns immutable RevenueMeter objects."""
    meters = generate_revenue_meters(
        _meter_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
    )

    assert isinstance(meters, tuple)
    assert meters
    assert all(isinstance(meter, RevenueMeter) for meter in meters)


def test_generate_exactly_one_meter_per_plant() -> None:
    """Verify every plant receives exactly one primary settlement meter."""
    plant_config = _plant_config(plant_count=4)
    meters = generate_revenue_meters(
        _meter_config(),
        plant_config=plant_config,
        equipment_config=_equipment_config(),
    )

    assert len(meters) == 4
    assert len({meter.plant_id for meter in meters}) == 4
    assert all(meter.is_primary for meter in meters)


def test_generated_meter_plant_ids_match_generated_plants() -> None:
    """Verify meter plant references resolve to generated plants."""
    plant_config = _plant_config(plant_count=3)
    plants = generate_plants(plant_config)
    meters = generate_revenue_meters(
        _meter_config(),
        plant_config=plant_config,
        equipment_config=_equipment_config(),
    )

    assert {meter.plant_id for meter in meters} == {plant.plant_id for plant in plants}


def test_generated_meter_equipment_ids_link_to_revenue_meter_assets() -> None:
    """Verify each meter links to its plant's REVENUE_METER equipment."""
    plant_config = _plant_config(plant_count=3)
    equipment_config = _equipment_config()
    equipment = generate_equipment(
        equipment_config,
        plant_config=plant_config,
    )
    meters = generate_revenue_meters(
        _meter_config(),
        plant_config=plant_config,
        equipment_config=equipment_config,
    )

    revenue_assets = {
        item.equipment_id: item
        for item in equipment
        if item.equipment_type is EquipmentType.REVENUE_METER
    }

    assert len(revenue_assets) == len(meters)

    for meter in meters:
        linked_asset = revenue_assets[meter.equipment_id]
        assert linked_asset.plant_id == meter.plant_id


def test_generation_is_deterministic_for_same_configuration() -> None:
    """Verify identical inputs generate identical meter master data."""
    kwargs = {
        "plant_config": _plant_config(),
        "equipment_config": _equipment_config(),
    }

    first = generate_revenue_meters(_meter_config(), **kwargs)
    second = generate_revenue_meters(_meter_config(), **kwargs)

    assert first == second


def test_different_seeds_change_generated_attributes() -> None:
    """Verify changing the meter seed changes generated master data."""
    kwargs = {
        "plant_config": _plant_config(plant_count=5),
        "equipment_config": _equipment_config(),
    }

    first = generate_revenue_meters(
        _meter_config(random_seed=1),
        **kwargs,
    )
    second = generate_revenue_meters(
        _meter_config(random_seed=2),
        **kwargs,
    )

    assert first != second


def test_meter_ids_are_stable_and_sequential() -> None:
    """Verify canonical meter identifiers follow plant ordering."""
    meters = generate_revenue_meters(
        _meter_config(),
        plant_config=_plant_config(plant_count=3),
        equipment_config=_equipment_config(),
    )

    assert tuple(meter.meter_id for meter in meters) == (
        "MTR-00001",
        "MTR-00002",
        "MTR-00003",
    )


def test_serial_numbers_are_stable_and_unique() -> None:
    """Verify deterministic serial-like values are unique."""
    meters = generate_revenue_meters(
        _meter_config(),
        plant_config=_plant_config(plant_count=3),
        equipment_config=_equipment_config(),
    )

    assert tuple(meter.serial_number for meter in meters) == (
        "RM-00000001",
        "RM-00000002",
        "RM-00000003",
    )
    assert len({meter.serial_number for meter in meters}) == len(meters)


def test_meter_names_include_plant_names() -> None:
    """Verify settlement-meter names remain human-readable."""
    plant_config = _plant_config(plant_count=2)
    plants = generate_plants(plant_config)
    meters = generate_revenue_meters(
        _meter_config(),
        plant_config=plant_config,
        equipment_config=_equipment_config(),
    )

    names_by_plant = {plant.plant_id: plant.plant_name for plant in plants}

    for meter in meters:
        assert names_by_plant[meter.plant_id] in meter.meter_name
        assert "Primary Settlement Meter" in meter.meter_name


def test_catalogue_combinations_are_valid() -> None:
    """Verify generated manufacturer/model/accuracy combinations."""
    meters = generate_revenue_meters(
        _meter_config(),
        plant_config=_plant_config(plant_count=20),
        equipment_config=_equipment_config(),
    )

    valid_combinations = {
        (
            "Schneider Electric",
            "ION-9000",
            MeterAccuracyClass.CLASS_02S,
        ),
        (
            "Siemens",
            "SENTRON-PAC4200",
            MeterAccuracyClass.CLASS_05S,
        ),
        ("ABB", "M4M-30", MeterAccuracyClass.CLASS_05S),
        ("Landis+Gyr", "E650", MeterAccuracyClass.CLASS_02S),
        ("Secure", "PREMIER-300", MeterAccuracyClass.CLASS_1),
    }

    assert all(
        (
            meter.manufacturer,
            meter.model_number,
            meter.accuracy_class,
        )
        in valid_combinations
        for meter in meters
    )


def test_multipliers_are_positive_and_supported() -> None:
    """Verify generated multipliers come from the supported set."""
    meters = generate_revenue_meters(
        _meter_config(),
        plant_config=_plant_config(plant_count=20),
        equipment_config=_equipment_config(),
    )

    supported = {1.0, 10.0, 100.0, 1_000.0}

    assert all(meter.multiplier in supported for meter in meters)
    assert all(meter.multiplier > 0 for meter in meters)


def test_calibration_dates_follow_plant_commissioning() -> None:
    """Verify calibration dates respect configured offsets."""
    plant_config = _plant_config(plant_count=5)
    plants = generate_plants(plant_config)
    meters = generate_revenue_meters(
        _meter_config(
            minimum_calibration_offset_days=30,
            maximum_calibration_offset_days=60,
        ),
        plant_config=plant_config,
        equipment_config=_equipment_config(),
    )
    plants_by_id = {plant.plant_id: plant for plant in plants}

    for meter in meters:
        offset = (
            meter.calibration_date - plants_by_id[meter.plant_id].commissioning_date
        ).days
        assert 30 <= offset <= 60


def test_zero_status_probabilities_generate_active_meters() -> None:
    """Verify zero exception probabilities produce active meters."""
    meters = generate_revenue_meters(
        _meter_config(
            calibration_due_probability=0.0,
            out_of_service_probability=0.0,
        ),
        plant_config=_plant_config(plant_count=10),
        equipment_config=_equipment_config(),
    )

    assert all(meter.status is MeterStatus.ACTIVE for meter in meters)


def test_out_of_service_probability_one_generates_out_of_service() -> None:
    """Verify forced out-of-service generation."""
    meters = generate_revenue_meters(
        _meter_config(
            calibration_due_probability=0.0,
            out_of_service_probability=1.0,
        ),
        plant_config=_plant_config(plant_count=4),
        equipment_config=_equipment_config(),
    )

    assert all(meter.status is MeterStatus.OUT_OF_SERVICE for meter in meters)


def test_calibration_due_probability_one_generates_due_status() -> None:
    """Verify forced calibration-due generation."""
    meters = generate_revenue_meters(
        _meter_config(
            calibration_due_probability=1.0,
            out_of_service_probability=0.0,
        ),
        plant_config=_plant_config(plant_count=4),
        equipment_config=_equipment_config(),
    )

    assert all(meter.status is MeterStatus.CALIBRATION_DUE for meter in meters)


def test_generated_notes_describe_primary_meter() -> None:
    """Verify generated notes document the meter role."""
    meters = generate_revenue_meters(
        _meter_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
    )

    assert all(
        meter.notes == "Primary point-of-interconnection revenue meter."
        for meter in meters
    )


def test_generate_records_matches_model_serialization() -> None:
    """Verify record generation delegates to RevenueMeter.to_record."""
    config = _meter_config()
    plant_config = _plant_config()
    equipment_config = _equipment_config()

    meters = generate_revenue_meters(
        config,
        plant_config=plant_config,
        equipment_config=equipment_config,
    )
    records = generate_revenue_meter_records(
        config,
        plant_config=plant_config,
        equipment_config=equipment_config,
    )

    assert records == tuple(meter.to_record() for meter in meters)


def test_generate_records_returns_primitive_values() -> None:
    """Verify generated records are serialization-ready."""
    records = generate_revenue_meter_records(
        _meter_config(),
        plant_config=_plant_config(plant_count=1),
        equipment_config=_equipment_config(),
    )
    record = records[0]

    assert isinstance(records, tuple)
    assert isinstance(record, dict)
    assert isinstance(record["accuracy_class"], str)
    assert isinstance(record["status"], str)
    assert isinstance(record["calibration_date"], str)
    assert isinstance(record["is_primary"], bool)
    assert isinstance(record["is_operational"], bool)
    assert isinstance(record["requires_attention"], bool)


def test_rejects_more_than_one_revenue_meter_per_plant() -> None:
    """Verify the Phase 2 one-primary-meter rule is enforced."""
    with pytest.raises(
        ValueError,
        match="revenue_meters_per_plant must be exactly 1",
    ):
        generate_revenue_meters(
            _meter_config(),
            plant_config=_plant_config(),
            equipment_config=_equipment_config(revenue_meters_per_plant=2),
        )


def test_generator_config_uses_expected_defaults() -> None:
    """Verify documented default generator values."""
    config = MeterGeneratorConfig()

    assert config.random_seed == 42
    assert config.minimum_calibration_offset_days == 30
    assert config.maximum_calibration_offset_days == 365
    assert config.calibration_due_probability == 0.05
    assert config.out_of_service_probability == 0.01


def test_generator_config_is_immutable() -> None:
    """Verify meter configuration is frozen."""
    config = MeterGeneratorConfig()

    with pytest.raises(FrozenInstanceError):
        config.random_seed = 1  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("random_seed", True),
        ("random_seed", 1.5),
        ("random_seed", "42"),
        ("minimum_calibration_offset_days", True),
        ("minimum_calibration_offset_days", 1.5),
        ("minimum_calibration_offset_days", "30"),
        ("maximum_calibration_offset_days", True),
        ("maximum_calibration_offset_days", 1.5),
        ("maximum_calibration_offset_days", "365"),
    ],
)
def test_config_rejects_invalid_integer_types(
    field_name: str,
    value: object,
) -> None:
    """Verify integer configuration fields reject invalid types."""
    with pytest.raises(TypeError, match=f"{field_name} must be an integer"):
        MeterGeneratorConfig(**{field_name: value})


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("minimum_calibration_offset_days", 0),
        ("minimum_calibration_offset_days", -1),
        ("maximum_calibration_offset_days", 0),
        ("maximum_calibration_offset_days", -1),
    ],
)
def test_config_rejects_non_positive_offsets(
    field_name: str,
    value: int,
) -> None:
    """Verify calibration offsets must be positive."""
    with pytest.raises(
        ValueError,
        match=f"{field_name} must be greater than zero",
    ):
        MeterGeneratorConfig(**{field_name: value})


def test_config_rejects_reversed_calibration_offsets() -> None:
    """Verify maximum offset cannot be below minimum offset."""
    with pytest.raises(
        ValueError,
        match="maximum_calibration_offset_days",
    ):
        MeterGeneratorConfig(
            minimum_calibration_offset_days=60,
            maximum_calibration_offset_days=30,
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "calibration_due_probability",
        "out_of_service_probability",
    ],
)
@pytest.mark.parametrize("value", [True, "0.1", None])
def test_config_rejects_non_numeric_probabilities(
    field_name: str,
    value: object,
) -> None:
    """Verify probability fields must be numeric."""
    with pytest.raises(TypeError, match=f"{field_name} must be numeric"):
        MeterGeneratorConfig(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "calibration_due_probability",
        "out_of_service_probability",
    ],
)
@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_config_rejects_non_finite_probabilities(
    field_name: str,
    value: float,
) -> None:
    """Verify probability fields must be finite."""
    with pytest.raises(ValueError, match=f"{field_name} must be finite"):
        MeterGeneratorConfig(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "calibration_due_probability",
        "out_of_service_probability",
    ],
)
@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_config_rejects_out_of_range_probabilities(
    field_name: str,
    value: float,
) -> None:
    """Verify probability fields remain between zero and one."""
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        MeterGeneratorConfig(**{field_name: value})


def test_config_rejects_status_probability_sum_above_one() -> None:
    """Verify exceptional status probabilities cannot exceed one."""
    with pytest.raises(
        ValueError,
        match="must not exceed 1.0",
    ):
        MeterGeneratorConfig(
            calibration_due_probability=0.6,
            out_of_service_probability=0.5,
        )


def test_generated_meter_model_is_immutable() -> None:
    """Verify generated RevenueMeter objects remain immutable."""
    meter = generate_revenue_meters(
        _meter_config(),
        plant_config=_plant_config(plant_count=1),
        equipment_config=_equipment_config(),
    )[0]

    with pytest.raises(FrozenInstanceError):
        meter.status = MeterStatus.RETIRED  # type: ignore[misc]


def test_calibration_date_is_date_value() -> None:
    """Verify generated calibration values use date objects."""
    meter = generate_revenue_meters(
        _meter_config(),
        plant_config=_plant_config(plant_count=1),
        equipment_config=_equipment_config(),
    )[0]

    assert isinstance(meter.calibration_date, date)
