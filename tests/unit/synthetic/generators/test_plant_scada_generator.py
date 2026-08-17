"""
Unit tests for the EOIP plant-level SCADA aggregation generator.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from eoip.synthetic.generators.equipment_generator import (
    EquipmentGeneratorConfig,
)
from eoip.synthetic.generators.meter_generator import MeterGeneratorConfig
from eoip.synthetic.generators.plant_generator import PlantGeneratorConfig
from eoip.synthetic.generators.plant_scada_generator import (
    PlantSCADAGeneratorConfig,
    generate_plant_scada,
    generate_plant_scada_records,
)
from eoip.synthetic.models.plant_scada import (
    PlantSCADAObservation,
    PlantSCADAQuality,
)
from eoip.synthetic.models.scada import (
    SCADAObservation,
    SCADAOperatingState,
    SCADAQuality,
)


def _timestamp() -> datetime:
    """Return the standard aligned timestamp."""
    return datetime(2025, 1, 1, 12, 0, tzinfo=UTC)


def _plant_config(*, plant_count: int = 1) -> PlantGeneratorConfig:
    """Return a compact deterministic plant configuration."""
    return PlantGeneratorConfig(
        plant_count=plant_count,
        random_seed=11,
    )


def _equipment_config() -> EquipmentGeneratorConfig:
    """Return compact equipment configuration."""
    return EquipmentGeneratorConfig(
        random_seed=22,
        string_inverters_per_plant=2,
        transformers_per_plant=1,
        feeders_per_plant=1,
        weather_stations_per_plant=1,
        revenue_meters_per_plant=1,
        protection_relays_per_plant=1,
    )


def _meter_config() -> MeterGeneratorConfig:
    """Return deterministic meter configuration."""
    return MeterGeneratorConfig(
        random_seed=33,
        calibration_due_probability=0.0,
        out_of_service_probability=0.0,
    )


def _generator_config(**overrides: Any) -> PlantSCADAGeneratorConfig:
    """Return deterministic plant-SCADA aggregation configuration."""
    data: dict[str, Any] = {
        "transformer_loss_pct": 2.0,
        "collection_loss_pct": 1.0,
        "auxiliary_import_pct_of_plant_capacity": 0.1,
        "minimum_auxiliary_import_kw": 5.0,
        "initial_export_register_kwh": 100.0,
        "initial_import_register_kwh": 10.0,
    }
    data.update(overrides)
    return PlantSCADAGeneratorConfig(**data)


def _inverter_observation(
    *,
    equipment_id: str,
    timestamp: datetime | None = None,
    active_power_kw: float = 100.0,
    equipment_available: bool = True,
    grid_available: bool = True,
    quality: SCADAQuality = SCADAQuality.VALID,
    plant_id: str = "PLANT-001",
) -> SCADAObservation:
    """Return one valid inverter-SCADA observation."""
    resolved_timestamp = timestamp or _timestamp()
    generating = active_power_kw > 0.0

    return SCADAObservation(
        plant_id=plant_id,
        equipment_id=equipment_id,
        timestamp=resolved_timestamp,
        active_power_kw=active_power_kw,
        interval_energy_kwh=active_power_kw * 0.25,
        dc_voltage_v=1_000.0 if generating else 0.0,
        dc_current_a=active_power_kw if generating else 0.0,
        ac_voltage_v=400.0 if generating else 0.0,
        ac_current_a=active_power_kw if generating else 0.0,
        frequency_hz=50.0 if grid_available else 0.0,
        power_factor=0.99 if generating else 0.0,
        equipment_available=equipment_available,
        grid_available=grid_available,
        operating_state=(
            SCADAOperatingState.NORMAL if generating else SCADAOperatingState.NIGHT
        ),
        quality=quality,
    )


def _two_inverter_group(
    *,
    timestamp: datetime | None = None,
    first_power_kw: float = 100.0,
    second_power_kw: float = 200.0,
    first_quality: SCADAQuality = SCADAQuality.VALID,
    second_quality: SCADAQuality = SCADAQuality.VALID,
    grid_available: bool = True,
) -> tuple[SCADAObservation, ...]:
    """Return two observations for one plant and timestamp."""
    return (
        _inverter_observation(
            equipment_id="EQP-00001",
            timestamp=timestamp,
            active_power_kw=first_power_kw,
            quality=first_quality,
            grid_available=grid_available,
        ),
        _inverter_observation(
            equipment_id="EQP-00002",
            timestamp=timestamp,
            active_power_kw=second_power_kw,
            quality=second_quality,
            grid_available=grid_available,
        ),
    )


def test_returns_tuple_of_plant_scada_models() -> None:
    """Verify aggregation returns immutable domain models."""
    observations = generate_plant_scada(
        _generator_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        meter_config=_meter_config(),
        inverter_observations=_two_inverter_group(),
    )

    assert isinstance(observations, tuple)
    assert len(observations) == 1
    assert isinstance(observations[0], PlantSCADAObservation)


def test_aggregates_one_record_per_plant_and_timestamp() -> None:
    """Verify one aggregate is created for each plant/timestamp grain."""
    first_time = _timestamp()
    second_time = first_time + timedelta(minutes=15)
    inverter_observations = (
        *_two_inverter_group(timestamp=first_time),
        *_two_inverter_group(timestamp=second_time),
    )

    observations = generate_plant_scada(
        _generator_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        meter_config=_meter_config(),
        inverter_observations=inverter_observations,
    )

    assert len(observations) == 2
    assert tuple(item.timestamp for item in observations) == (
        first_time,
        second_time,
    )


def test_links_generated_primary_meter() -> None:
    """Verify plant aggregates reference the generated meter."""
    observation = generate_plant_scada(
        _generator_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        meter_config=_meter_config(),
        inverter_observations=_two_inverter_group(),
    )[0]

    assert observation.plant_id == "PLANT-001"
    assert observation.meter_id == "MTR-00001"


def test_sums_gross_inverter_power() -> None:
    """Verify gross power equals the sum of inverter power."""
    observation = generate_plant_scada(
        _generator_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        meter_config=_meter_config(),
        inverter_observations=_two_inverter_group(
            first_power_kw=125.0,
            second_power_kw=275.0,
        ),
    )[0]

    assert observation.gross_inverter_power_kw == 400.0


def test_applies_transformer_and_collection_losses() -> None:
    """Verify configured loss percentages are applied to gross power."""
    observation = generate_plant_scada(
        _generator_config(
            transformer_loss_pct=2.0,
            collection_loss_pct=1.0,
        ),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        meter_config=_meter_config(),
        inverter_observations=_two_inverter_group(
            first_power_kw=100.0,
            second_power_kw=200.0,
        ),
    )[0]

    assert observation.transformer_loss_kw == 6.0
    assert observation.collection_loss_kw == 3.0
    assert observation.export_power_kw == 291.0


def test_calculates_interval_export_energy() -> None:
    """Verify export energy uses the 15-minute interval."""
    observation = generate_plant_scada(
        _generator_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        meter_config=_meter_config(),
        inverter_observations=_two_inverter_group(),
    )[0]

    assert observation.interval_export_energy_kwh == 72.75


def test_maintains_cumulative_export_register() -> None:
    """Verify cumulative export increases in timestamp order."""
    first_time = _timestamp()
    second_time = first_time + timedelta(minutes=15)

    observations = generate_plant_scada(
        _generator_config(initial_export_register_kwh=100.0),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        meter_config=_meter_config(),
        inverter_observations=(
            *_two_inverter_group(timestamp=first_time),
            *_two_inverter_group(timestamp=second_time),
        ),
    )

    assert observations[0].cumulative_export_energy_kwh == 172.75
    assert observations[1].cumulative_export_energy_kwh == 245.5


def test_generates_auxiliary_import_when_not_generating() -> None:
    """Verify a grid-connected non-generating plant imports auxiliaries."""
    observation = generate_plant_scada(
        _generator_config(
            auxiliary_import_pct_of_plant_capacity=0.0,
            minimum_auxiliary_import_kw=12.0,
        ),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        meter_config=_meter_config(),
        inverter_observations=_two_inverter_group(
            first_power_kw=0.0,
            second_power_kw=0.0,
        ),
    )[0]

    assert observation.export_power_kw == 0.0
    assert observation.import_power_kw == 12.0
    assert observation.interval_import_energy_kwh == 3.0
    assert observation.cumulative_import_energy_kwh == 13.0


def test_no_auxiliary_import_when_grid_unavailable() -> None:
    """Verify grid outages prevent auxiliary import."""
    observation = generate_plant_scada(
        _generator_config(minimum_auxiliary_import_kw=12.0),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        meter_config=_meter_config(),
        inverter_observations=_two_inverter_group(
            first_power_kw=0.0,
            second_power_kw=0.0,
            grid_available=False,
        ),
    )[0]

    assert observation.grid_available is False
    assert observation.import_power_kw == 0.0


def test_valid_quality_when_all_inverters_are_valid() -> None:
    """Verify fully valid inverter groups remain valid."""
    observation = generate_plant_scada(
        _generator_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        meter_config=_meter_config(),
        inverter_observations=_two_inverter_group(),
    )[0]

    assert observation.quality is PlantSCADAQuality.VALID


@pytest.mark.parametrize(
    ("first_quality", "second_quality"),
    [
        (SCADAQuality.ESTIMATED, SCADAQuality.VALID),
        (SCADAQuality.MISSING, SCADAQuality.VALID),
    ],
)
def test_mixed_quality_becomes_estimated(
    first_quality: SCADAQuality,
    second_quality: SCADAQuality,
) -> None:
    """Verify mixed quality aggregates conservatively to estimated."""
    observation = generate_plant_scada(
        _generator_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        meter_config=_meter_config(),
        inverter_observations=_two_inverter_group(
            first_quality=first_quality,
            second_quality=second_quality,
        ),
    )[0]

    assert observation.quality is PlantSCADAQuality.ESTIMATED


def test_all_missing_quality_becomes_missing() -> None:
    """Verify all-missing groups produce zero missing observations."""
    inverter_observations = (
        _inverter_observation(
            equipment_id="EQP-00001",
            active_power_kw=0.0,
            equipment_available=False,
            grid_available=False,
            quality=SCADAQuality.MISSING,
        ),
        _inverter_observation(
            equipment_id="EQP-00002",
            active_power_kw=0.0,
            equipment_available=False,
            grid_available=False,
            quality=SCADAQuality.MISSING,
        ),
    )

    observation = generate_plant_scada(
        _generator_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        meter_config=_meter_config(),
        inverter_observations=inverter_observations,
    )[0]

    assert observation.quality is PlantSCADAQuality.MISSING
    assert observation.gross_inverter_power_kw == 0.0
    assert observation.export_power_kw == 0.0
    assert observation.import_power_kw == 0.0


def test_grid_availability_requires_all_inverters_available_to_grid() -> None:
    """Verify one unavailable grid flag makes the plant grid unavailable."""
    observations = (
        _inverter_observation(
            equipment_id="EQP-00001",
            active_power_kw=0.0,
            grid_available=True,
        ),
        _inverter_observation(
            equipment_id="EQP-00002",
            active_power_kw=0.0,
            grid_available=False,
        ),
    )

    aggregate = generate_plant_scada(
        _generator_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        meter_config=_meter_config(),
        inverter_observations=observations,
    )[0]

    assert aggregate.grid_available is False


def test_plant_availability_requires_any_available_inverter() -> None:
    """Verify one available inverter keeps the plant available."""
    observations = (
        _inverter_observation(
            equipment_id="EQP-00001",
            active_power_kw=0.0,
            equipment_available=False,
        ),
        _inverter_observation(
            equipment_id="EQP-00002",
            active_power_kw=0.0,
            equipment_available=True,
        ),
    )

    aggregate = generate_plant_scada(
        _generator_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        meter_config=_meter_config(),
        inverter_observations=observations,
    )[0]

    assert aggregate.plant_available is True


def test_generation_is_deterministic_for_same_inputs() -> None:
    """Verify identical inputs produce identical plant SCADA."""
    kwargs = {
        "plant_config": _plant_config(),
        "equipment_config": _equipment_config(),
        "meter_config": _meter_config(),
        "inverter_observations": _two_inverter_group(),
    }

    first = generate_plant_scada(_generator_config(), **kwargs)
    second = generate_plant_scada(_generator_config(), **kwargs)

    assert first == second


def test_generate_records_matches_model_serialization() -> None:
    """Verify record generation delegates to model serialization."""
    kwargs = {
        "plant_config": _plant_config(),
        "equipment_config": _equipment_config(),
        "meter_config": _meter_config(),
        "inverter_observations": _two_inverter_group(),
    }

    observations = generate_plant_scada(_generator_config(), **kwargs)
    records = generate_plant_scada_records(_generator_config(), **kwargs)

    assert records == tuple(item.to_record() for item in observations)


def test_generate_records_returns_primitive_values() -> None:
    """Verify generated records are serialization-ready."""
    record = generate_plant_scada_records(
        _generator_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        meter_config=_meter_config(),
        inverter_observations=_two_inverter_group(),
    )[0]

    assert isinstance(record, dict)
    assert isinstance(record["timestamp"], str)
    assert isinstance(record["quality"], str)
    assert isinstance(record["is_exporting"], bool)
    assert isinstance(record["is_importing"], bool)


def test_rejects_duplicate_inverter_observation() -> None:
    """Verify duplicate equipment/timestamp observations are rejected."""
    observation = _inverter_observation(
        equipment_id="EQP-00001",
    )

    with pytest.raises(ValueError, match="Duplicate inverter SCADA"):
        generate_plant_scada(
            _generator_config(),
            plant_config=_plant_config(),
            equipment_config=_equipment_config(),
            meter_config=_meter_config(),
            inverter_observations=(observation, observation),
        )


def test_rejects_unknown_plant_reference() -> None:
    """Verify inverter records cannot reference an unknown plant."""
    with pytest.raises(ValueError, match="unknown plant IDs"):
        generate_plant_scada(
            _generator_config(),
            plant_config=_plant_config(),
            equipment_config=_equipment_config(),
            meter_config=_meter_config(),
            inverter_observations=(
                _inverter_observation(
                    equipment_id="EQP-00001",
                    plant_id="PLANT-999",
                ),
            ),
        )


def test_rejects_non_tuple_inverter_observations() -> None:
    """Verify caller-supplied observations must be a tuple."""
    with pytest.raises(TypeError, match="must be a tuple"):
        generate_plant_scada(
            _generator_config(),
            plant_config=_plant_config(),
            equipment_config=_equipment_config(),
            meter_config=_meter_config(),
            inverter_observations=[  # type: ignore[arg-type]
                _inverter_observation(equipment_id="EQP-00001")
            ],
        )


def test_rejects_empty_inverter_observations() -> None:
    """Verify aggregation requires at least one inverter observation."""
    with pytest.raises(ValueError, match="At least one"):
        generate_plant_scada(
            _generator_config(),
            plant_config=_plant_config(),
            equipment_config=_equipment_config(),
            meter_config=_meter_config(),
            inverter_observations=(),
        )


def test_generator_config_uses_expected_defaults() -> None:
    """Verify documented aggregation defaults."""
    config = PlantSCADAGeneratorConfig()

    assert config.transformer_loss_pct == 1.5
    assert config.collection_loss_pct == 1.0
    assert config.auxiliary_import_pct_of_plant_capacity == 0.15
    assert config.minimum_auxiliary_import_kw == 10.0
    assert config.initial_export_register_kwh == 0.0
    assert config.initial_import_register_kwh == 0.0


def test_generator_config_is_immutable() -> None:
    """Verify aggregation configuration is frozen."""
    config = PlantSCADAGeneratorConfig()

    with pytest.raises(FrozenInstanceError):
        config.transformer_loss_pct = 2.0  # type: ignore[misc]


@pytest.mark.parametrize(
    "field_name",
    [
        "transformer_loss_pct",
        "collection_loss_pct",
        "auxiliary_import_pct_of_plant_capacity",
        "minimum_auxiliary_import_kw",
        "initial_export_register_kwh",
        "initial_import_register_kwh",
    ],
)
@pytest.mark.parametrize("value", [True, "1.0", None])
def test_config_rejects_non_numeric_values(
    field_name: str,
    value: object,
) -> None:
    """Verify all numeric configuration fields reject invalid types."""
    with pytest.raises(TypeError, match=f"{field_name} must be numeric"):
        PlantSCADAGeneratorConfig(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "transformer_loss_pct",
        "collection_loss_pct",
        "auxiliary_import_pct_of_plant_capacity",
        "minimum_auxiliary_import_kw",
        "initial_export_register_kwh",
        "initial_import_register_kwh",
    ],
)
@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf")],
)
def test_config_rejects_non_finite_values(
    field_name: str,
    value: float,
) -> None:
    """Verify configuration values must be finite."""
    with pytest.raises(ValueError, match=f"{field_name} must be finite"):
        PlantSCADAGeneratorConfig(**{field_name: value})


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("transformer_loss_pct", -0.1),
        ("transformer_loss_pct", 20.1),
        ("collection_loss_pct", -0.1),
        ("collection_loss_pct", 20.1),
        ("auxiliary_import_pct_of_plant_capacity", -0.1),
        ("auxiliary_import_pct_of_plant_capacity", 10.1),
    ],
)
def test_config_rejects_out_of_range_percentages(
    field_name: str,
    value: float,
) -> None:
    """Verify percentage fields enforce configured bounds."""
    with pytest.raises(ValueError, match=field_name):
        PlantSCADAGeneratorConfig(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "minimum_auxiliary_import_kw",
        "initial_export_register_kwh",
        "initial_import_register_kwh",
    ],
)
def test_config_rejects_negative_non_percentage_values(
    field_name: str,
) -> None:
    """Verify register and auxiliary defaults cannot be negative."""
    with pytest.raises(ValueError, match="greater than or equal to zero"):
        PlantSCADAGeneratorConfig(**{field_name: -0.1})


def test_generated_models_are_immutable() -> None:
    """Verify generated plant-SCADA models are frozen."""
    observation = generate_plant_scada(
        _generator_config(),
        plant_config=_plant_config(),
        equipment_config=_equipment_config(),
        meter_config=_meter_config(),
        inverter_observations=_two_inverter_group(),
    )[0]

    with pytest.raises(FrozenInstanceError):
        observation.export_power_kw = 0.0  # type: ignore[misc]
