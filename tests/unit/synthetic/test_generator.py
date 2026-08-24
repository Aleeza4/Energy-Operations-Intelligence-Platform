"""Unit tests for the EOIP Phase 2 in-memory master dataset generator."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest

from eoip.core.exceptions import DataGenerationError
from eoip.synthetic.config import (
    GenerationConfig,
    GenerationProfile,
    PortfolioConfig,
    TimeRangeConfig,
)
from eoip.synthetic.generator import (
    GenerationSummary,
    SyntheticDataset,
    SyntheticDatasetGenerator,
    generate_dataset,
)
from eoip.synthetic.random import create_random_context


def _unit_config() -> GenerationConfig:
    """Return a small deterministic unit-profile configuration."""
    return GenerationConfig(
        profile_name=GenerationProfile.UNIT,
        seed=20250201,
        time=TimeRangeConfig(
            datetime(2025, 1, 1, tzinfo=UTC),
            datetime(2025, 1, 3, tzinfo=UTC),
        ),
        portfolio=PortfolioConfig(
            plant_count=1,
            aggregate_ac_capacity_min_mw=20,
            aggregate_ac_capacity_max_mw=100,
            inverter_count_min=1,
            inverter_count_max=50,
        ),
    )


def test_generate_dataset_returns_synthetic_dataset() -> None:
    """The generator returns a SyntheticDataset with all datasets."""
    config = _unit_config()
    dataset = generate_dataset(config)

    assert isinstance(dataset, SyntheticDataset)
    assert isinstance(dataset.plants, tuple)
    assert isinstance(dataset.equipment, tuple)
    assert isinstance(dataset.revenue_meters, tuple)
    assert isinstance(dataset.weather, tuple)
    assert isinstance(dataset.inverter_scada, tuple)
    assert isinstance(dataset.plant_scada, tuple)
    assert isinstance(dataset.ground_truth_events, pd.DataFrame)
    assert isinstance(dataset.alarms, pd.DataFrame)
    assert isinstance(dataset.incidents, pd.DataFrame)
    assert isinstance(dataset.work_orders, pd.DataFrame)
    assert isinstance(dataset.tariffs, pd.DataFrame)
    assert isinstance(dataset.budgets, pd.DataFrame)


def test_generate_dataset_is_deterministic() -> None:
    """Same configuration and seed produce identical datasets."""
    config = _unit_config()
    first = generate_dataset(config)
    second = generate_dataset(config)

    assert first.plants == second.plants
    assert first.equipment == second.equipment
    assert first.revenue_meters == second.revenue_meters
    assert first.weather == second.weather
    assert first.inverter_scada == second.inverter_scada
    assert first.plant_scada == second.plant_scada
    assert first.ground_truth_events.equals(second.ground_truth_events)
    assert first.alarms.equals(second.alarms)
    assert first.incidents.equals(second.incidents)
    assert first.work_orders.equals(second.work_orders)
    assert first.tariffs.equals(second.tariffs)
    assert first.budgets.equals(second.budgets)


def test_generate_dataset_row_counts() -> None:
    """Row counts match the unit profile expectations."""
    config = _unit_config()
    dataset = generate_dataset(config)

    assert len(dataset.plants) == 1
    assert len(dataset.revenue_meters) == 1
    assert len(dataset.weather) > 0
    assert len(dataset.inverter_scada) > 0
    assert len(dataset.plant_scada) > 0
    assert len(dataset.tariffs) >= 1
    assert len(dataset.budgets) >= 1


def test_generation_sequence_plants_before_equipment() -> None:
    """Plants are generated before equipment and meters."""
    config = _unit_config()
    generator = SyntheticDatasetGenerator(config)
    plants = generator._generate_plants()
    equipment = generator._generate_equipment(plants)
    meters = generator._generate_revenue_meters(plants, equipment)

    assert len(plants) == 1
    assert len(equipment) > 0
    assert len(meters) == 1
    assert all(
        item.plant_id in {plant.plant_id for plant in plants} for item in equipment
    )
    assert all(
        meter.plant_id in {plant.plant_id for plant in plants} for meter in meters
    )


def test_plant_equipment_meter_references() -> None:
    """All equipment and meters reference valid plants."""
    config = _unit_config()
    dataset = generate_dataset(config)

    plant_ids = {plant.plant_id for plant in dataset.plants}
    assert all(item.plant_id in plant_ids for item in dataset.equipment)
    assert all(meter.plant_id in plant_ids for meter in dataset.revenue_meters)
    assert all(item.plant_id in plant_ids for item in dataset.weather)
    assert all(item.plant_id in plant_ids for item in dataset.inverter_scada)
    assert all(item.plant_id in plant_ids for item in dataset.plant_scada)


def test_summary_generation() -> None:
    """The generator produces a valid GenerationSummary."""
    config = _unit_config()
    generator = SyntheticDatasetGenerator(config)
    dataset = generator.generate()
    summary = generator.summarize(dataset)

    assert isinstance(summary, GenerationSummary)
    assert summary.plant_count == 1
    assert summary.revenue_meter_count == 1
    assert summary.generation_run_id == generator.generation_run_id
    record = summary.to_record()
    assert record["plant_count"] == 1
    assert record["generation_run_id"] == generator.generation_run_id


def test_immutable_result_objects() -> None:
    """SyntheticDataset and GenerationSummary are frozen dataclasses."""
    config = _unit_config()
    dataset = generate_dataset(config)

    with pytest.raises(AttributeError):
        dataset.plants = ()  # type: ignore[misc]

    summary = GenerationSummary(
        plant_count=1,
        equipment_count=1,
        revenue_meter_count=1,
        weather_count=1,
        inverter_scada_count=1,
        plant_scada_count=1,
        ground_truth_event_count=1,
        alarm_count=1,
        incident_count=1,
        work_order_count=1,
        tariff_count=1,
        budget_count=1,
        generation_run_id="RUN-TEST",
    )
    with pytest.raises(AttributeError):
        summary.plant_count = 2  # type: ignore[misc]


def test_invalid_configuration_raises() -> None:
    """Invalid configuration fails before generation."""
    with pytest.raises(TypeError):
        SyntheticDatasetGenerator("not-a-config")  # type: ignore[arg-type]


def test_broken_references_raise_data_generation_error() -> None:
    """Broken referential integrity raises DataGenerationError."""
    # Use a two-plant configuration so a reference can be broken.
    config = GenerationConfig(
        profile_name=GenerationProfile.SMOKE,
        seed=20250201,
        time=TimeRangeConfig(
            datetime(2025, 1, 1, tzinfo=UTC),
            datetime(2025, 1, 3, tzinfo=UTC),
        ),
        portfolio=PortfolioConfig(
            plant_count=2,
            aggregate_ac_capacity_min_mw=40,
            aggregate_ac_capacity_max_mw=200,
            inverter_count_min=2,
            inverter_count_max=100,
        ),
    )
    generator = SyntheticDatasetGenerator(config)

    plants = generator._generate_plants()
    equipment = generator._generate_equipment(plants)
    revenue_meters = generator._generate_revenue_meters(plants, equipment)

    # Break a plant reference by removing one plant.
    broken_plants = plants[:-1]
    assert len(broken_plants) == 1
    assert len(plants) == 2

    with pytest.raises(DataGenerationError):
        generator._validate_master_references(
            broken_plants,
            equipment,
            revenue_meters,
        )


def test_generate_dataset_uses_random_context() -> None:
    """The generator accepts an explicit RandomContext."""
    config = _unit_config()
    random_context = create_random_context(config.seed)
    generator = SyntheticDatasetGenerator(config, random_context)
    dataset = generator.generate()

    assert generator.random_context is random_context
    assert len(dataset.plants) == 1


def test_generate_dataset_different_seed_changes_values() -> None:
    """A different seed changes stochastic values while preserving structure."""
    config_a = _unit_config()
    config_b = GenerationConfig(
        profile_name=GenerationProfile.UNIT,
        seed=999,
        time=config_a.time,
        portfolio=config_a.portfolio,
    )

    dataset_a = generate_dataset(config_a)
    dataset_b = generate_dataset(config_b)

    assert len(dataset_a.plants) == len(dataset_b.plants)
    assert dataset_a.weather != dataset_b.weather
