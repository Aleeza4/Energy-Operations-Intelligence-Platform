"""
Unit tests for the EOIP synthetic plant generator.

These tests verify deterministic generation, configuration validation,
identifier uniqueness, capacity constraints, serialization, and generated
Plant model integrity.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date
from typing import Any

import pytest

from eoip.synthetic.generators.plant_generator import (
    PlantGeneratorConfig,
    generate_plant_records,
    generate_plants,
)
from eoip.synthetic.models.plant import Plant, PlantStatus


def test_generate_plants_returns_default_portfolio() -> None:
    """The default generator should create 20 validated plants."""
    plants = generate_plants()

    assert isinstance(plants, tuple)
    assert len(plants) == 20
    assert all(isinstance(plant, Plant) for plant in plants)


def test_generate_plants_uses_unique_sequential_ids() -> None:
    """Generated plant IDs should be unique and sequential."""
    plants = generate_plants()

    assert tuple(plant.plant_id for plant in plants) == tuple(
        f"PLANT-{index:03d}" for index in range(1, 21)
    )


def test_generate_plants_is_deterministic_for_same_seed() -> None:
    """The same configuration should generate identical plants."""
    config = PlantGeneratorConfig(
        plant_count=8,
        random_seed=123,
    )

    first_result = generate_plants(config)
    second_result = generate_plants(config)

    assert first_result == second_result


def test_generate_plants_changes_with_different_seed() -> None:
    """Different random seeds should change generated plant attributes."""
    first_result = generate_plants(PlantGeneratorConfig(plant_count=5, random_seed=1))
    second_result = generate_plants(PlantGeneratorConfig(plant_count=5, random_seed=2))

    assert first_result != second_result
    assert tuple(plant.plant_id for plant in first_result) == tuple(
        plant.plant_id for plant in second_result
    )


def test_generate_plants_respects_custom_count() -> None:
    """A custom plant count should control portfolio size."""
    plants = generate_plants(
        PlantGeneratorConfig(
            plant_count=3,
            random_seed=42,
        )
    )

    assert len(plants) == 3
    assert plants[-1].plant_id == "PLANT-003"


def test_generated_plants_respect_capacity_bounds() -> None:
    """Generated capacities should remain inside configured limits."""
    config = PlantGeneratorConfig(
        plant_count=50,
        minimum_dc_capacity_mw=30.0,
        maximum_dc_capacity_mw=40.0,
        minimum_dc_ac_ratio=1.15,
        maximum_dc_ac_ratio=1.25,
    )

    plants = generate_plants(config)

    for plant in plants:
        assert 30.0 <= plant.dc_capacity_mw <= 40.0
        assert plant.ac_capacity_mw <= plant.dc_capacity_mw
        assert 1.14 <= plant.dc_ac_ratio <= 1.26


def test_generated_plants_respect_commissioning_year_bounds() -> None:
    """Commissioning years should remain inside configured bounds."""
    config = PlantGeneratorConfig(
        plant_count=30,
        earliest_commissioning_year=2018,
        latest_commissioning_year=2020,
    )

    plants = generate_plants(config)

    assert all(2018 <= plant.commissioning_date.year <= 2020 for plant in plants)


def test_generated_plants_have_operational_status() -> None:
    """Generated plants should start in the operational state."""
    plants = generate_plants()

    assert all(plant.status is PlantStatus.OPERATIONAL for plant in plants)


def test_generated_plants_have_valid_coordinates() -> None:
    """Generated coordinates should remain within geographic limits."""
    plants = generate_plants()

    assert all(-90.0 <= plant.latitude <= 90.0 for plant in plants)
    assert all(-180.0 <= plant.longitude <= 180.0 for plant in plants)


def test_generated_plants_have_non_empty_names_and_regions() -> None:
    """Every generated plant should have descriptive master data."""
    plants = generate_plants()

    assert all(plant.plant_name for plant in plants)
    assert all(plant.region for plant in plants)
    assert len({plant.plant_name for plant in plants}) == len(plants)


def test_generate_plant_records_matches_model_serialization() -> None:
    """Generated records should match Plant.to_record output."""
    config = PlantGeneratorConfig(
        plant_count=4,
        random_seed=99,
    )

    plants = generate_plants(config)
    records = generate_plant_records(config)

    assert records == tuple(plant.to_record() for plant in plants)


def test_generate_plant_records_returns_serializable_values() -> None:
    """Plant records should expose primitive serialization-ready values."""
    record = generate_plant_records(PlantGeneratorConfig(plant_count=1))[0]

    assert isinstance(record, dict)
    assert isinstance(record["commissioning_date"], str)
    assert isinstance(record["status"], str)
    assert isinstance(record["dc_ac_ratio"], float)


def test_generator_config_uses_expected_defaults() -> None:
    """Generator configuration should expose documented defaults."""
    config = PlantGeneratorConfig()

    assert config.plant_count == 20
    assert config.random_seed == 42
    assert config.minimum_dc_capacity_mw == 25.0
    assert config.maximum_dc_capacity_mw == 100.0
    assert config.minimum_dc_ac_ratio == 1.10
    assert config.maximum_dc_ac_ratio == 1.35
    assert config.earliest_commissioning_year == 2015
    assert config.latest_commissioning_year == 2024


def test_generator_config_is_immutable() -> None:
    """PlantGeneratorConfig should be frozen."""
    config = PlantGeneratorConfig()

    with pytest.raises(FrozenInstanceError):
        config.plant_count = 10  # type: ignore[misc]


@pytest.mark.parametrize(
    "plant_count",
    [
        True,
        1.5,
        "20",
        None,
    ],
)
def test_generator_config_rejects_invalid_count_type(
    plant_count: object,
) -> None:
    """Plant count must be an integer excluding booleans."""
    with pytest.raises(TypeError, match="plant_count must be an integer"):
        PlantGeneratorConfig(plant_count=plant_count)  # type: ignore[arg-type]


@pytest.mark.parametrize("plant_count", [0, -1, -20])
def test_generator_config_rejects_non_positive_count(
    plant_count: int,
) -> None:
    """Plant count must be greater than zero."""
    with pytest.raises(ValueError, match="Invalid plant_count"):
        PlantGeneratorConfig(plant_count=plant_count)


@pytest.mark.parametrize(
    "random_seed",
    [
        True,
        1.5,
        "42",
        None,
    ],
)
def test_generator_config_rejects_invalid_seed_type(
    random_seed: object,
) -> None:
    """Random seed must be an integer excluding booleans."""
    with pytest.raises(TypeError, match="random_seed must be an integer"):
        PlantGeneratorConfig(random_seed=random_seed)  # type: ignore[arg-type]


def test_generator_config_rejects_non_positive_minimum_capacity() -> None:
    """Minimum DC capacity must be greater than zero."""
    with pytest.raises(
        ValueError,
        match="minimum_dc_capacity_mw must be greater than zero",
    ):
        PlantGeneratorConfig(minimum_dc_capacity_mw=0.0)


def test_generator_config_rejects_reversed_capacity_bounds() -> None:
    """Maximum capacity must not be below minimum capacity."""
    with pytest.raises(
        ValueError,
        match="maximum_dc_capacity_mw must be greater than or equal",
    ):
        PlantGeneratorConfig(
            minimum_dc_capacity_mw=50.0,
            maximum_dc_capacity_mw=40.0,
        )


def test_generator_config_rejects_ratio_below_one() -> None:
    """Minimum DC-to-AC ratio must be at least one."""
    with pytest.raises(
        ValueError,
        match="minimum_dc_ac_ratio must be at least 1.0",
    ):
        PlantGeneratorConfig(minimum_dc_ac_ratio=0.99)


def test_generator_config_rejects_reversed_ratio_bounds() -> None:
    """Maximum DC-to-AC ratio must not be below the minimum."""
    with pytest.raises(
        ValueError,
        match="maximum_dc_ac_ratio must be greater than or equal",
    ):
        PlantGeneratorConfig(
            minimum_dc_ac_ratio=1.30,
            maximum_dc_ac_ratio=1.20,
        )


def test_generator_config_rejects_early_commissioning_year() -> None:
    """The earliest commissioning year must be 2000 or later."""
    with pytest.raises(
        ValueError,
        match="earliest_commissioning_year must be 2000 or later",
    ):
        PlantGeneratorConfig(earliest_commissioning_year=1999)


def test_generator_config_rejects_reversed_year_bounds() -> None:
    """Latest commissioning year must not be below the earliest year."""
    with pytest.raises(
        ValueError,
        match="latest_commissioning_year must be greater than or equal",
    ):
        PlantGeneratorConfig(
            earliest_commissioning_year=2024,
            latest_commissioning_year=2023,
        )


def test_generator_config_rejects_future_latest_year() -> None:
    """The latest commissioning year cannot be in the future."""
    with pytest.raises(
        ValueError,
        match="latest_commissioning_year cannot be in the future",
    ):
        PlantGeneratorConfig(latest_commissioning_year=date.today().year + 1)


def test_single_value_capacity_and_ratio_ranges_are_supported() -> None:
    """Equal lower and upper bounds should produce fixed values."""
    config = PlantGeneratorConfig(
        plant_count=2,
        minimum_dc_capacity_mw=50.0,
        maximum_dc_capacity_mw=50.0,
        minimum_dc_ac_ratio=1.25,
        maximum_dc_ac_ratio=1.25,
    )

    plants = generate_plants(config)

    assert all(plant.dc_capacity_mw == 50.0 for plant in plants)
    assert all(plant.ac_capacity_mw == 40.0 for plant in plants)
    assert all(plant.dc_ac_ratio == 1.25 for plant in plants)


@pytest.mark.parametrize(
    "overrides",
    [
        {"minimum_dc_capacity_mw": "25"},
        {"maximum_dc_capacity_mw": "100"},
        {"minimum_dc_ac_ratio": "1.1"},
        {"maximum_dc_ac_ratio": "1.35"},
    ],
)
def test_invalid_numeric_config_types_raise_clear_errors(
    overrides: dict[str, Any],
) -> None:
    """
    Invalid numeric configuration types should fail during validation.

    The implementation may raise TypeError from the comparison itself because
    these configuration fields currently rely on Python numeric comparisons.
    """
    with pytest.raises(TypeError):
        PlantGeneratorConfig(**overrides)
