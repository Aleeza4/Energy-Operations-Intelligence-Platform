"""
Plant-level SCADA aggregation generator for EOIP synthetic data generation.

This module derives plant-level telemetry from inverter SCADA observations.
It aggregates inverter production by plant and timestamp, applies bounded
transformer and collection losses, enforces plant export capacity, calculates
night auxiliary import, and maintains cumulative revenue-meter registers.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from eoip.synthetic.generators.equipment_generator import (
    EquipmentGeneratorConfig,
)
from eoip.synthetic.generators.meter_generator import (
    MeterGeneratorConfig,
    generate_revenue_meters,
)
from eoip.synthetic.generators.plant_generator import (
    PlantGeneratorConfig,
    generate_plants,
)
from eoip.synthetic.generators.scada_generator import (
    SCADAGeneratorConfig,
    generate_scada,
)
from eoip.synthetic.generators.weather_generator import (
    WeatherGeneratorConfig,
)
from eoip.synthetic.models.plant_scada import (
    PlantSCADAObservation,
    PlantSCADAQuality,
)
from eoip.synthetic.models.scada import (
    SCADAObservation,
    SCADAQuality,
)

_DEFAULT_TRANSFORMER_LOSS_PCT: Final[float] = 1.5
_DEFAULT_COLLECTION_LOSS_PCT: Final[float] = 1.0
_DEFAULT_AUXILIARY_IMPORT_PCT: Final[float] = 0.15
_DEFAULT_MINIMUM_AUXILIARY_IMPORT_KW: Final[float] = 10.0
_DEFAULT_INITIAL_EXPORT_REGISTER_KWH: Final[float] = 0.0
_DEFAULT_INITIAL_IMPORT_REGISTER_KWH: Final[float] = 0.0


@dataclass(frozen=True, slots=True)
class PlantSCADAGeneratorConfig:
    """Configuration for deterministic plant-level SCADA aggregation."""

    transformer_loss_pct: float = _DEFAULT_TRANSFORMER_LOSS_PCT
    collection_loss_pct: float = _DEFAULT_COLLECTION_LOSS_PCT
    auxiliary_import_pct_of_plant_capacity: float = _DEFAULT_AUXILIARY_IMPORT_PCT
    minimum_auxiliary_import_kw: float = _DEFAULT_MINIMUM_AUXILIARY_IMPORT_KW
    initial_export_register_kwh: float = _DEFAULT_INITIAL_EXPORT_REGISTER_KWH
    initial_import_register_kwh: float = _DEFAULT_INITIAL_IMPORT_REGISTER_KWH

    def __post_init__(self) -> None:
        """Validate aggregation configuration."""
        self._validate_percentage(
            field_name="transformer_loss_pct",
            value=self.transformer_loss_pct,
            maximum=20.0,
        )
        self._validate_percentage(
            field_name="collection_loss_pct",
            value=self.collection_loss_pct,
            maximum=20.0,
        )
        self._validate_percentage(
            field_name="auxiliary_import_pct_of_plant_capacity",
            value=self.auxiliary_import_pct_of_plant_capacity,
            maximum=10.0,
        )
        self._validate_non_negative_number(
            field_name="minimum_auxiliary_import_kw",
            value=self.minimum_auxiliary_import_kw,
        )
        self._validate_non_negative_number(
            field_name="initial_export_register_kwh",
            value=self.initial_export_register_kwh,
        )
        self._validate_non_negative_number(
            field_name="initial_import_register_kwh",
            value=self.initial_import_register_kwh,
        )

        if self.transformer_loss_pct + self.collection_loss_pct >= 100.0:
            raise ValueError(
                "transformer_loss_pct plus collection_loss_pct must be "
                "less than 100.0."
            )

    @staticmethod
    def _validate_percentage(
        *,
        field_name: str,
        value: float,
        maximum: float,
    ) -> None:
        """Validate a finite percentage within configured bounds."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{field_name} must be numeric.")
        if not math.isfinite(value):
            raise ValueError(f"{field_name} must be finite.")
        if not 0.0 <= value <= maximum:
            raise ValueError(f"{field_name} must be between 0.0 and {maximum}.")

    @staticmethod
    def _validate_non_negative_number(
        *,
        field_name: str,
        value: float,
    ) -> None:
        """Validate a finite non-negative numeric field."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{field_name} must be numeric.")
        if not math.isfinite(value):
            raise ValueError(f"{field_name} must be finite.")
        if value < 0.0:
            raise ValueError(f"{field_name} must be greater than or equal to zero.")


def generate_plant_scada(
    config: PlantSCADAGeneratorConfig | None = None,
    *,
    scada_config: SCADAGeneratorConfig | None = None,
    plant_config: PlantGeneratorConfig | None = None,
    equipment_config: EquipmentGeneratorConfig | None = None,
    weather_config: WeatherGeneratorConfig | None = None,
    meter_config: MeterGeneratorConfig | None = None,
    inverter_observations: tuple[SCADAObservation, ...] | None = None,
) -> tuple[PlantSCADAObservation, ...]:
    """
    Generate deterministic plant-level SCADA from inverter observations.

    Parameters
    ----------
    config:
        Optional plant-SCADA aggregation configuration.
    scada_config:
        Optional inverter-SCADA generator configuration.
    plant_config:
        Optional plant master-data configuration.
    equipment_config:
        Optional equipment master-data configuration.
    weather_config:
        Optional weather generator configuration.
    meter_config:
        Optional revenue-meter master-data configuration.
    inverter_observations:
        Optional pre-generated inverter observations. When omitted, the
        existing inverter SCADA generator is called.

    Returns
    -------
    tuple[PlantSCADAObservation, ...]
        Plant observations sorted by timestamp and plant identifier.
    """
    resolved_config = config or PlantSCADAGeneratorConfig()
    plants = generate_plants(plant_config)
    meters = generate_revenue_meters(
        meter_config,
        plant_config=plant_config,
        equipment_config=equipment_config,
    )
    observations = (
        inverter_observations
        if inverter_observations is not None
        else generate_scada(
            scada_config,
            plant_config=plant_config,
            equipment_config=equipment_config,
            weather_config=weather_config,
        )
    )

    plants_by_id = {plant.plant_id: plant for plant in plants}
    meters_by_plant = {meter.plant_id: meter for meter in meters}

    if set(plants_by_id) != set(meters_by_plant):
        raise ValueError("Every generated plant must have exactly one revenue meter.")

    grouped = _group_inverter_observations(observations)
    _validate_grouped_plant_ids(
        grouped=grouped,
        known_plant_ids=set(plants_by_id),
    )

    cumulative_export = {
        plant_id: float(resolved_config.initial_export_register_kwh)
        for plant_id in plants_by_id
    }
    cumulative_import = {
        plant_id: float(resolved_config.initial_import_register_kwh)
        for plant_id in plants_by_id
    }

    plant_observations: list[PlantSCADAObservation] = []

    for timestamp, plant_id in sorted(grouped):
        inverter_group = grouped[(timestamp, plant_id)]
        plant = plants_by_id[plant_id]
        meter = meters_by_plant[plant_id]

        gross_power_kw = round(
            sum(item.active_power_kw for item in inverter_group),
            6,
        )
        plant_capacity_kw = plant.ac_capacity_mw * 1_000.0

        transformer_loss_kw = round(
            gross_power_kw * (resolved_config.transformer_loss_pct / 100.0),
            6,
        )
        collection_loss_kw = round(
            gross_power_kw * (resolved_config.collection_loss_pct / 100.0),
            6,
        )
        delivered_power_kw = max(
            gross_power_kw - transformer_loss_kw - collection_loss_kw,
            0.0,
        )

        grid_available = all(item.grid_available for item in inverter_group)
        plant_available = any(item.equipment_available for item in inverter_group)
        quality = _aggregate_quality(inverter_group)

        if quality is PlantSCADAQuality.MISSING:
            gross_power_kw = 0.0
            transformer_loss_kw = 0.0
            collection_loss_kw = 0.0
            export_power_kw = 0.0
            import_power_kw = 0.0
            grid_available = False
            plant_available = False
        else:
            export_power_kw = (
                min(delivered_power_kw, plant_capacity_kw)
                if grid_available and plant_available
                else 0.0
            )
            import_power_kw = _auxiliary_import_kw(
                gross_inverter_power_kw=gross_power_kw,
                plant_capacity_kw=plant_capacity_kw,
                grid_available=grid_available,
                plant_available=plant_available,
                config=resolved_config,
            )

        interval_export_energy_kwh = round(export_power_kw * 0.25, 6)
        interval_import_energy_kwh = round(import_power_kw * 0.25, 6)

        cumulative_export[plant_id] = round(
            cumulative_export[plant_id] + interval_export_energy_kwh,
            6,
        )
        cumulative_import[plant_id] = round(
            cumulative_import[plant_id] + interval_import_energy_kwh,
            6,
        )

        plant_observations.append(
            PlantSCADAObservation(
                plant_id=plant_id,
                meter_id=meter.meter_id,
                timestamp=timestamp,
                gross_inverter_power_kw=gross_power_kw,
                transformer_loss_kw=transformer_loss_kw,
                collection_loss_kw=collection_loss_kw,
                export_power_kw=round(export_power_kw, 6),
                import_power_kw=round(import_power_kw, 6),
                interval_export_energy_kwh=interval_export_energy_kwh,
                interval_import_energy_kwh=interval_import_energy_kwh,
                cumulative_export_energy_kwh=(cumulative_export[plant_id]),
                cumulative_import_energy_kwh=(cumulative_import[plant_id]),
                grid_available=grid_available,
                plant_available=plant_available,
                quality=quality,
            )
        )

    return tuple(plant_observations)


def generate_plant_scada_records(
    config: PlantSCADAGeneratorConfig | None = None,
    *,
    scada_config: SCADAGeneratorConfig | None = None,
    plant_config: PlantGeneratorConfig | None = None,
    equipment_config: EquipmentGeneratorConfig | None = None,
    weather_config: WeatherGeneratorConfig | None = None,
    meter_config: MeterGeneratorConfig | None = None,
    inverter_observations: tuple[SCADAObservation, ...] | None = None,
) -> tuple[dict[str, object], ...]:
    """Generate serialization-ready plant-level SCADA records."""
    return tuple(
        observation.to_record()
        for observation in generate_plant_scada(
            config,
            scada_config=scada_config,
            plant_config=plant_config,
            equipment_config=equipment_config,
            weather_config=weather_config,
            meter_config=meter_config,
            inverter_observations=inverter_observations,
        )
    )


def _group_inverter_observations(
    observations: tuple[SCADAObservation, ...],
) -> dict[tuple[datetime, str], tuple[SCADAObservation, ...]]:
    """Group inverter telemetry by timestamp and plant."""
    if not isinstance(observations, tuple):
        raise TypeError("inverter_observations must be a tuple.")

    grouped_lists: dict[
        tuple[datetime, str],
        list[SCADAObservation],
    ] = defaultdict(list)

    seen_keys: set[tuple[str, datetime]] = set()

    for observation in observations:
        if not isinstance(observation, SCADAObservation):
            raise TypeError("Every inverter observation must be a SCADAObservation.")

        observation_key = (
            observation.equipment_id,
            observation.timestamp,
        )
        if observation_key in seen_keys:
            raise ValueError(
                "Duplicate inverter SCADA observation found for "
                f"{observation.equipment_id} at "
                f"{observation.timestamp.isoformat()}."
            )
        seen_keys.add(observation_key)

        grouped_lists[(observation.timestamp, observation.plant_id)].append(observation)

    if not grouped_lists:
        raise ValueError("At least one inverter SCADA observation is required.")

    return {
        key: tuple(
            sorted(
                values,
                key=lambda item: item.equipment_id,
            )
        )
        for key, values in grouped_lists.items()
    }


def _validate_grouped_plant_ids(
    *,
    grouped: dict[
        tuple[datetime, str],
        tuple[SCADAObservation, ...],
    ],
    known_plant_ids: set[str],
) -> None:
    """Validate that all inverter observations reference known plants."""
    referenced_plant_ids = {plant_id for _, plant_id in grouped}
    unknown = referenced_plant_ids - known_plant_ids
    if unknown:
        raise ValueError(
            "Inverter observations reference unknown plant IDs: "
            + ", ".join(sorted(unknown))
        )


def _aggregate_quality(
    observations: tuple[SCADAObservation, ...],
) -> PlantSCADAQuality:
    """Return the most conservative quality across inverter observations."""
    qualities = {item.quality for item in observations}

    if qualities == {SCADAQuality.MISSING}:
        return PlantSCADAQuality.MISSING

    if SCADAQuality.MISSING in qualities or SCADAQuality.ESTIMATED in qualities:
        return PlantSCADAQuality.ESTIMATED

    return PlantSCADAQuality.VALID


def _auxiliary_import_kw(
    *,
    gross_inverter_power_kw: float,
    plant_capacity_kw: float,
    grid_available: bool,
    plant_available: bool,
    config: PlantSCADAGeneratorConfig,
) -> float:
    """Return auxiliary import when the plant is not exporting."""
    if not grid_available:
        return 0.0

    if gross_inverter_power_kw > 0.0 and plant_available:
        return 0.0

    percentage_import = plant_capacity_kw * (
        config.auxiliary_import_pct_of_plant_capacity / 100.0
    )
    return max(
        percentage_import,
        config.minimum_auxiliary_import_kw,
    )


__all__ = [
    "PlantSCADAGeneratorConfig",
    "generate_plant_scada",
    "generate_plant_scada_records",
]
