"""
Equipment master-data generator for EOIP synthetic data generation.

This module generates deterministic, validated Equipment domain objects for
each synthetic solar plant. It creates inverter, transformer, feeder, weather
station, revenue meter, and protection relay assets while preserving stable
plant and parent-equipment relationships.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Final

from eoip.synthetic.generators.plant_generator import (
    PlantGeneratorConfig,
    generate_plants,
)
from eoip.synthetic.models.equipment import (
    Equipment,
    EquipmentStatus,
    EquipmentType,
)

_DEFAULT_RANDOM_SEED: Final[int] = 42


@dataclass(frozen=True, slots=True)
class EquipmentGeneratorConfig:
    """Configuration for deterministic equipment generation."""

    random_seed: int = _DEFAULT_RANDOM_SEED
    string_inverters_per_plant: int = 12
    transformers_per_plant: int = 2
    feeders_per_plant: int = 4
    weather_stations_per_plant: int = 1
    revenue_meters_per_plant: int = 1
    protection_relays_per_plant: int = 2

    def __post_init__(self) -> None:
        """Validate generator configuration."""
        if isinstance(self.random_seed, bool) or not isinstance(
            self.random_seed,
            int,
        ):
            raise TypeError("random_seed must be an integer.")

        count_fields = (
            "string_inverters_per_plant",
            "transformers_per_plant",
            "feeders_per_plant",
            "weather_stations_per_plant",
            "revenue_meters_per_plant",
            "protection_relays_per_plant",
        )

        for field_name in count_fields:
            value = getattr(self, field_name)

            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer.")

            if value <= 0:
                raise ValueError(f"{field_name} must be greater than zero.")


def generate_equipment(
    config: EquipmentGeneratorConfig | None = None,
    *,
    plant_config: PlantGeneratorConfig | None = None,
) -> tuple[Equipment, ...]:
    """Generate deterministic equipment for every synthetic plant."""
    resolved_config = config or EquipmentGeneratorConfig()
    rng = random.Random(resolved_config.random_seed)
    plants = generate_plants(plant_config)

    generated: list[Equipment] = []
    counter = 1

    for plant in plants:
        transformer_ids: list[str] = []

        for index in range(1, resolved_config.transformers_per_plant + 1):
            equipment_id = _equipment_id(counter)
            transformer_ids.append(equipment_id)

            generated.append(
                Equipment(
                    equipment_id=equipment_id,
                    plant_id=plant.plant_id,
                    equipment_name=(f"{plant.plant_name} Transformer {index:02d}"),
                    equipment_type=EquipmentType.TRANSFORMER,
                    manufacturer=rng.choice(("ABB", "Siemens", "Schneider")),
                    model_number="TX-33KV",
                    serial_number=_serial_number("TX", counter),
                    commissioning_date=plant.commissioning_date,
                    rated_power_kw=round(
                        plant.ac_capacity_mw
                        * 1_000
                        / resolved_config.transformers_per_plant,
                        2,
                    ),
                    status=EquipmentStatus.OPERATIONAL,
                )
            )
            counter += 1

        feeder_ids: list[str] = []

        for index in range(1, resolved_config.feeders_per_plant + 1):
            equipment_id = _equipment_id(counter)
            feeder_ids.append(equipment_id)
            parent_id = transformer_ids[(index - 1) % len(transformer_ids)]

            generated.append(
                Equipment(
                    equipment_id=equipment_id,
                    plant_id=plant.plant_id,
                    equipment_name=f"{plant.plant_name} Feeder {index:02d}",
                    equipment_type=EquipmentType.FEEDER,
                    manufacturer=rng.choice(("ABB", "Siemens", "Schneider")),
                    model_number="FEEDER-33KV",
                    serial_number=_serial_number("FDR", counter),
                    commissioning_date=plant.commissioning_date,
                    rated_power_kw=None,
                    parent_equipment_id=parent_id,
                    status=EquipmentStatus.OPERATIONAL,
                )
            )
            counter += 1

        inverter_capacity_kw = round(
            plant.ac_capacity_mw * 1_000 / resolved_config.string_inverters_per_plant,
            2,
        )

        for index in range(
            1,
            resolved_config.string_inverters_per_plant + 1,
        ):
            equipment_id = _equipment_id(counter)
            parent_id = feeder_ids[(index - 1) % len(feeder_ids)]

            generated.append(
                Equipment(
                    equipment_id=equipment_id,
                    plant_id=plant.plant_id,
                    equipment_name=(f"{plant.plant_name} String Inverter {index:03d}"),
                    equipment_type=EquipmentType.STRING_INVERTER,
                    manufacturer=rng.choice(("Huawei", "Sungrow", "SMA")),
                    model_number="UTILITY-STRING-INVERTER",
                    serial_number=_serial_number("SINV", counter),
                    commissioning_date=plant.commissioning_date,
                    rated_power_kw=inverter_capacity_kw,
                    parent_equipment_id=parent_id,
                    status=EquipmentStatus.OPERATIONAL,
                )
            )
            counter += 1

        for index in range(
            1,
            resolved_config.weather_stations_per_plant + 1,
        ):
            equipment_id = _equipment_id(counter)

            generated.append(
                Equipment(
                    equipment_id=equipment_id,
                    plant_id=plant.plant_id,
                    equipment_name=(f"{plant.plant_name} Weather Station {index:02d}"),
                    equipment_type=EquipmentType.WEATHER_STATION,
                    manufacturer=rng.choice(
                        ("Vaisala", "Kipp & Zonen", "Campbell Scientific")
                    ),
                    model_number="MET-STATION",
                    serial_number=_serial_number("WS", counter),
                    commissioning_date=plant.commissioning_date,
                    rated_power_kw=None,
                    status=EquipmentStatus.OPERATIONAL,
                )
            )
            counter += 1

        for index in range(
            1,
            resolved_config.revenue_meters_per_plant + 1,
        ):
            equipment_id = _equipment_id(counter)

            generated.append(
                Equipment(
                    equipment_id=equipment_id,
                    plant_id=plant.plant_id,
                    equipment_name=(f"{plant.plant_name} Revenue Meter {index:02d}"),
                    equipment_type=EquipmentType.REVENUE_METER,
                    manufacturer=rng.choice(("Schneider", "Siemens", "Janitza")),
                    model_number="REVENUE-METER",
                    serial_number=_serial_number("RM", counter),
                    commissioning_date=plant.commissioning_date,
                    rated_power_kw=None,
                    status=EquipmentStatus.OPERATIONAL,
                )
            )
            counter += 1

        for index in range(
            1,
            resolved_config.protection_relays_per_plant + 1,
        ):
            equipment_id = _equipment_id(counter)
            parent_id = transformer_ids[(index - 1) % len(transformer_ids)]

            generated.append(
                Equipment(
                    equipment_id=equipment_id,
                    plant_id=plant.plant_id,
                    equipment_name=(f"{plant.plant_name} Protection Relay {index:02d}"),
                    equipment_type=EquipmentType.PROTECTION_RELAY,
                    manufacturer=rng.choice(("ABB", "Siemens", "Schneider")),
                    model_number="PROTECTION-RELAY",
                    serial_number=_serial_number("PR", counter),
                    commissioning_date=plant.commissioning_date,
                    rated_power_kw=None,
                    parent_equipment_id=parent_id,
                    status=EquipmentStatus.OPERATIONAL,
                )
            )
            counter += 1

    return tuple(generated)


def generate_equipment_records(
    config: EquipmentGeneratorConfig | None = None,
    *,
    plant_config: PlantGeneratorConfig | None = None,
) -> tuple[dict[str, object], ...]:
    """Return serialization-ready equipment records."""
    return tuple(
        equipment.to_record()
        for equipment in generate_equipment(
            config,
            plant_config=plant_config,
        )
    )


def _equipment_id(counter: int) -> str:
    """Return an equipment identifier in the canonical EOIP format."""
    return f"EQP-{counter:05d}"


def _serial_number(prefix: str, counter: int) -> str:
    """Return a deterministic equipment serial number."""
    return f"{prefix}-{counter:08d}"
