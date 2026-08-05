"""
Unit tests for the EOIP synthetic equipment generator.

These tests verify deterministic equipment generation, configuration
validation, unique identifiers, plant relationships, parent-child references,
equipment-type counts, serialization, and generated Equipment model integrity.
"""

from __future__ import annotations

import re
from dataclasses import FrozenInstanceError

import pytest

from eoip.synthetic.generators.equipment_generator import (
    EquipmentGeneratorConfig,
    generate_equipment,
    generate_equipment_records,
)
from eoip.synthetic.generators.plant_generator import (
    PlantGeneratorConfig,
    generate_plants,
)
from eoip.synthetic.models.equipment import (
    Equipment,
    EquipmentStatus,
    EquipmentType,
)

_EQUIPMENT_ID_PATTERN = re.compile(r"^EQP-\d{5}$")


def _small_plant_config() -> PlantGeneratorConfig:
    """Return a compact plant configuration for focused generator tests."""
    return PlantGeneratorConfig(
        plant_count=3,
        random_seed=11,
    )


def _small_equipment_config() -> EquipmentGeneratorConfig:
    """Return a compact equipment configuration for focused tests."""
    return EquipmentGeneratorConfig(
        random_seed=22,
        string_inverters_per_plant=4,
        transformers_per_plant=2,
        feeders_per_plant=2,
        weather_stations_per_plant=1,
        revenue_meters_per_plant=1,
        protection_relays_per_plant=2,
    )


def test_generate_equipment_returns_tuple_of_equipment() -> None:
    """The generator should return immutable Equipment domain objects."""
    equipment = generate_equipment(
        _small_equipment_config(),
        plant_config=_small_plant_config(),
    )

    assert isinstance(equipment, tuple)
    assert equipment
    assert all(isinstance(item, Equipment) for item in equipment)


def test_default_generation_returns_expected_count() -> None:
    """Default generation should create 22 assets for each of 20 plants."""
    equipment = generate_equipment()

    assert len(equipment) == 440


def test_custom_generation_returns_expected_count() -> None:
    """Custom per-plant counts should determine total equipment count."""
    plant_config = _small_plant_config()
    equipment_config = _small_equipment_config()

    equipment = generate_equipment(
        equipment_config,
        plant_config=plant_config,
    )

    expected_per_plant = (
        equipment_config.string_inverters_per_plant
        + equipment_config.transformers_per_plant
        + equipment_config.feeders_per_plant
        + equipment_config.weather_stations_per_plant
        + equipment_config.revenue_meters_per_plant
        + equipment_config.protection_relays_per_plant
    )

    assert len(equipment) == plant_config.plant_count * expected_per_plant


def test_equipment_ids_are_unique_and_sequential() -> None:
    """Equipment IDs should be unique and sequential."""
    equipment = generate_equipment(
        _small_equipment_config(),
        plant_config=_small_plant_config(),
    )

    equipment_ids = tuple(item.equipment_id for item in equipment)

    assert len(equipment_ids) == len(set(equipment_ids))
    assert equipment_ids == tuple(
        f"EQP-{index:05d}" for index in range(1, len(equipment) + 1)
    )


def test_equipment_ids_follow_canonical_format() -> None:
    """Every generated equipment ID should follow EQP-00001 format."""
    equipment = generate_equipment(
        _small_equipment_config(),
        plant_config=_small_plant_config(),
    )

    assert all(_EQUIPMENT_ID_PATTERN.fullmatch(item.equipment_id) for item in equipment)


def test_serial_numbers_are_unique() -> None:
    """Every generated serial number should be unique."""
    equipment = generate_equipment(
        _small_equipment_config(),
        plant_config=_small_plant_config(),
    )

    serial_numbers = [item.serial_number for item in equipment]

    assert len(serial_numbers) == len(set(serial_numbers))


def test_generated_equipment_is_deterministic_for_same_seed() -> None:
    """The same configurations should generate identical equipment."""
    equipment_config = _small_equipment_config()
    plant_config = _small_plant_config()

    first_result = generate_equipment(
        equipment_config,
        plant_config=plant_config,
    )
    second_result = generate_equipment(
        equipment_config,
        plant_config=plant_config,
    )

    assert first_result == second_result


def test_different_equipment_seeds_change_generated_attributes() -> None:
    """Different equipment seeds should change randomized manufacturers."""
    plant_config = _small_plant_config()

    first_result = generate_equipment(
        EquipmentGeneratorConfig(
            random_seed=1,
            string_inverters_per_plant=4,
            transformers_per_plant=2,
            feeders_per_plant=2,
            weather_stations_per_plant=1,
            revenue_meters_per_plant=1,
            protection_relays_per_plant=2,
        ),
        plant_config=plant_config,
    )
    second_result = generate_equipment(
        EquipmentGeneratorConfig(
            random_seed=2,
            string_inverters_per_plant=4,
            transformers_per_plant=2,
            feeders_per_plant=2,
            weather_stations_per_plant=1,
            revenue_meters_per_plant=1,
            protection_relays_per_plant=2,
        ),
        plant_config=plant_config,
    )

    first_manufacturers = tuple(item.manufacturer for item in first_result)
    second_manufacturers = tuple(item.manufacturer for item in second_result)

    assert first_manufacturers != second_manufacturers
    assert tuple(item.equipment_id for item in first_result) == tuple(
        item.equipment_id for item in second_result
    )


def test_every_equipment_plant_id_exists() -> None:
    """Every generated equipment record should reference a generated plant."""
    plant_config = _small_plant_config()
    plants = generate_plants(plant_config)
    equipment = generate_equipment(
        _small_equipment_config(),
        plant_config=plant_config,
    )

    valid_plant_ids = {plant.plant_id for plant in plants}

    assert all(item.plant_id in valid_plant_ids for item in equipment)


def test_commissioning_dates_match_parent_plants() -> None:
    """Equipment commissioning dates should match their plant dates."""
    plant_config = _small_plant_config()
    plants = generate_plants(plant_config)
    equipment = generate_equipment(
        _small_equipment_config(),
        plant_config=plant_config,
    )

    plant_dates = {plant.plant_id: plant.commissioning_date for plant in plants}

    assert all(
        item.commissioning_date == plant_dates[item.plant_id] for item in equipment
    )


def test_every_equipment_status_is_operational() -> None:
    """Newly generated equipment should be operational."""
    equipment = generate_equipment(
        _small_equipment_config(),
        plant_config=_small_plant_config(),
    )

    assert all(item.status is EquipmentStatus.OPERATIONAL for item in equipment)


def test_generated_text_fields_are_non_empty() -> None:
    """Generated descriptive fields should contain visible text."""
    equipment = generate_equipment(
        _small_equipment_config(),
        plant_config=_small_plant_config(),
    )

    assert all(item.equipment_name for item in equipment)
    assert all(item.manufacturer for item in equipment)
    assert all(item.model_number for item in equipment)
    assert all(item.serial_number for item in equipment)


def test_generated_equipment_names_are_unique() -> None:
    """Equipment names should be unique across the generated portfolio."""
    equipment = generate_equipment(
        _small_equipment_config(),
        plant_config=_small_plant_config(),
    )

    names = [item.equipment_name for item in equipment]

    assert len(names) == len(set(names))


def test_parent_ids_reference_existing_equipment() -> None:
    """Every parent equipment ID should reference a generated asset."""
    equipment = generate_equipment(
        _small_equipment_config(),
        plant_config=_small_plant_config(),
    )

    equipment_ids = {item.equipment_id for item in equipment}

    assert all(
        item.parent_equipment_id is None or item.parent_equipment_id in equipment_ids
        for item in equipment
    )


def test_parent_and_child_belong_to_same_plant() -> None:
    """Equipment parent-child relationships must remain within one plant."""
    equipment = generate_equipment(
        _small_equipment_config(),
        plant_config=_small_plant_config(),
    )

    by_id = {item.equipment_id: item for item in equipment}

    for item in equipment:
        if item.parent_equipment_id is None:
            continue

        parent = by_id[item.parent_equipment_id]

        assert parent.plant_id == item.plant_id


def test_transformers_do_not_have_parents() -> None:
    """Generated transformers should be plant-level assets."""
    equipment = generate_equipment(
        _small_equipment_config(),
        plant_config=_small_plant_config(),
    )

    transformers = [
        item for item in equipment if item.equipment_type is EquipmentType.TRANSFORMER
    ]

    assert transformers
    assert all(item.parent_equipment_id is None for item in transformers)


def test_feeders_reference_transformers() -> None:
    """Generated feeders should reference transformer parents."""
    equipment = generate_equipment(
        _small_equipment_config(),
        plant_config=_small_plant_config(),
    )

    by_id = {item.equipment_id: item for item in equipment}
    feeders = [
        item for item in equipment if item.equipment_type is EquipmentType.FEEDER
    ]

    assert feeders
    assert all(item.parent_equipment_id is not None for item in feeders)
    assert all(
        by_id[item.parent_equipment_id].equipment_type is EquipmentType.TRANSFORMER
        for item in feeders
        if item.parent_equipment_id is not None
    )


def test_inverters_reference_feeders() -> None:
    """Generated string inverters should reference feeder parents."""
    equipment = generate_equipment(
        _small_equipment_config(),
        plant_config=_small_plant_config(),
    )

    by_id = {item.equipment_id: item for item in equipment}
    inverters = [
        item
        for item in equipment
        if item.equipment_type is EquipmentType.STRING_INVERTER
    ]

    assert inverters
    assert all(item.parent_equipment_id is not None for item in inverters)
    assert all(
        by_id[item.parent_equipment_id].equipment_type is EquipmentType.FEEDER
        for item in inverters
        if item.parent_equipment_id is not None
    )


def test_protection_relays_reference_transformers() -> None:
    """Protection relays should reference transformer parents."""
    equipment = generate_equipment(
        _small_equipment_config(),
        plant_config=_small_plant_config(),
    )

    by_id = {item.equipment_id: item for item in equipment}
    relays = [
        item
        for item in equipment
        if item.equipment_type is EquipmentType.PROTECTION_RELAY
    ]

    assert relays
    assert all(item.parent_equipment_id is not None for item in relays)
    assert all(
        by_id[item.parent_equipment_id].equipment_type is EquipmentType.TRANSFORMER
        for item in relays
        if item.parent_equipment_id is not None
    )


def test_weather_stations_and_revenue_meters_have_no_parent() -> None:
    """Plant-level monitoring assets should not have equipment parents."""
    equipment = generate_equipment(
        _small_equipment_config(),
        plant_config=_small_plant_config(),
    )

    plant_level_types = {
        EquipmentType.WEATHER_STATION,
        EquipmentType.REVENUE_METER,
    }

    plant_level_assets = [
        item for item in equipment if item.equipment_type in plant_level_types
    ]

    assert plant_level_assets
    assert all(item.parent_equipment_id is None for item in plant_level_assets)


def test_equipment_type_counts_match_configuration() -> None:
    """Each plant should receive the configured equipment-type counts."""
    plant_config = _small_plant_config()
    equipment_config = _small_equipment_config()
    equipment = generate_equipment(
        equipment_config,
        plant_config=plant_config,
    )

    expected_counts = {
        EquipmentType.STRING_INVERTER: (
            plant_config.plant_count * equipment_config.string_inverters_per_plant
        ),
        EquipmentType.TRANSFORMER: (
            plant_config.plant_count * equipment_config.transformers_per_plant
        ),
        EquipmentType.FEEDER: (
            plant_config.plant_count * equipment_config.feeders_per_plant
        ),
        EquipmentType.WEATHER_STATION: (
            plant_config.plant_count * equipment_config.weather_stations_per_plant
        ),
        EquipmentType.REVENUE_METER: (
            plant_config.plant_count * equipment_config.revenue_meters_per_plant
        ),
        EquipmentType.PROTECTION_RELAY: (
            plant_config.plant_count * equipment_config.protection_relays_per_plant
        ),
    }

    for equipment_type, expected_count in expected_counts.items():
        actual_count = sum(item.equipment_type is equipment_type for item in equipment)
        assert actual_count == expected_count


def test_inverter_capacity_sums_to_plant_ac_capacity() -> None:
    """Generated inverter ratings should approximate plant AC capacity."""
    plant_config = _small_plant_config()
    plants = generate_plants(plant_config)
    equipment = generate_equipment(
        _small_equipment_config(),
        plant_config=plant_config,
    )

    for plant in plants:
        inverter_capacity_kw = sum(
            item.rated_power_kw or 0.0
            for item in equipment
            if item.plant_id == plant.plant_id
            and item.equipment_type is EquipmentType.STRING_INVERTER
        )

        assert inverter_capacity_kw == pytest.approx(
            plant.ac_capacity_mw * 1_000,
            abs=0.05,
        )


def test_transformer_capacity_sums_to_plant_ac_capacity() -> None:
    """Generated transformer ratings should approximate plant AC capacity."""
    plant_config = _small_plant_config()
    plants = generate_plants(plant_config)
    equipment = generate_equipment(
        _small_equipment_config(),
        plant_config=plant_config,
    )

    for plant in plants:
        transformer_capacity_kw = sum(
            item.rated_power_kw or 0.0
            for item in equipment
            if item.plant_id == plant.plant_id
            and item.equipment_type is EquipmentType.TRANSFORMER
        )

        assert transformer_capacity_kw == pytest.approx(
            plant.ac_capacity_mw * 1_000,
            abs=0.05,
        )


def test_non_generation_assets_have_no_rated_power() -> None:
    """Monitoring and protection assets should not carry power ratings."""
    equipment = generate_equipment(
        _small_equipment_config(),
        plant_config=_small_plant_config(),
    )

    no_rating_types = {
        EquipmentType.FEEDER,
        EquipmentType.WEATHER_STATION,
        EquipmentType.REVENUE_METER,
        EquipmentType.PROTECTION_RELAY,
    }

    assert all(
        item.rated_power_kw is None
        for item in equipment
        if item.equipment_type in no_rating_types
    )


def test_generate_equipment_records_matches_model_serialization() -> None:
    """Generated records should match Equipment.to_record output."""
    equipment_config = _small_equipment_config()
    plant_config = _small_plant_config()

    equipment = generate_equipment(
        equipment_config,
        plant_config=plant_config,
    )
    records = generate_equipment_records(
        equipment_config,
        plant_config=plant_config,
    )

    assert records == tuple(item.to_record() for item in equipment)


def test_generate_equipment_records_returns_primitive_values() -> None:
    """Serialized equipment records should expose primitive values."""
    records = generate_equipment_records(
        _small_equipment_config(),
        plant_config=_small_plant_config(),
    )

    first_record = records[0]

    assert isinstance(records, tuple)
    assert isinstance(first_record, dict)
    assert isinstance(first_record["commissioning_date"], str)
    assert isinstance(first_record["equipment_type"], str)
    assert isinstance(first_record["status"], str)
    assert isinstance(first_record["is_generation_equipment"], bool)
    assert isinstance(first_record["is_available"], bool)


def test_generator_config_uses_expected_defaults() -> None:
    """Configuration should expose documented default counts."""
    config = EquipmentGeneratorConfig()

    assert config.random_seed == 42
    assert config.string_inverters_per_plant == 12
    assert config.transformers_per_plant == 2
    assert config.feeders_per_plant == 4
    assert config.weather_stations_per_plant == 1
    assert config.revenue_meters_per_plant == 1
    assert config.protection_relays_per_plant == 2


def test_package_exports_generator_api() -> None:
    """The generators package should re-export the public generator API."""
    from eoip.synthetic.generators import (
        EquipmentGeneratorConfig as PackageEquipmentGeneratorConfig,
    )
    from eoip.synthetic.generators import (
        generate_equipment as package_generate_equipment,
    )

    equipment = package_generate_equipment(
        PackageEquipmentGeneratorConfig(random_seed=7),
        plant_config=_small_plant_config(),
    )

    assert equipment


def test_generator_config_is_immutable() -> None:
    """EquipmentGeneratorConfig should be frozen."""
    config = EquipmentGeneratorConfig()

    with pytest.raises(FrozenInstanceError):
        config.random_seed = 1  # type: ignore[misc]


@pytest.mark.parametrize(
    "field_name",
    [
        "random_seed",
        "string_inverters_per_plant",
        "transformers_per_plant",
        "feeders_per_plant",
        "weather_stations_per_plant",
        "revenue_meters_per_plant",
        "protection_relays_per_plant",
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
    """Configuration integer fields should reject invalid types."""
    with pytest.raises(TypeError, match=f"{field_name} must be an integer"):
        EquipmentGeneratorConfig(**{field_name: invalid_value})


@pytest.mark.parametrize(
    "field_name",
    [
        "string_inverters_per_plant",
        "transformers_per_plant",
        "feeders_per_plant",
        "weather_stations_per_plant",
        "revenue_meters_per_plant",
        "protection_relays_per_plant",
    ],
)
@pytest.mark.parametrize("invalid_value", [0, -1, -10])
def test_generator_config_rejects_non_positive_counts(
    field_name: str,
    invalid_value: int,
) -> None:
    """Per-plant equipment counts must be greater than zero."""
    with pytest.raises(
        ValueError,
        match=f"{field_name} must be greater than zero",
    ):
        EquipmentGeneratorConfig(**{field_name: invalid_value})


def test_custom_single_asset_counts_are_supported() -> None:
    """The minimum valid count of one should be supported for all types."""
    config = EquipmentGeneratorConfig(
        random_seed=7,
        string_inverters_per_plant=1,
        transformers_per_plant=1,
        feeders_per_plant=1,
        weather_stations_per_plant=1,
        revenue_meters_per_plant=1,
        protection_relays_per_plant=1,
    )
    plant_config = PlantGeneratorConfig(
        plant_count=1,
        random_seed=8,
    )

    equipment = generate_equipment(
        config,
        plant_config=plant_config,
    )

    assert len(equipment) == 6
    assert {item.equipment_type for item in equipment} == {
        EquipmentType.STRING_INVERTER,
        EquipmentType.TRANSFORMER,
        EquipmentType.FEEDER,
        EquipmentType.WEATHER_STATION,
        EquipmentType.REVENUE_METER,
        EquipmentType.PROTECTION_RELAY,
    }
