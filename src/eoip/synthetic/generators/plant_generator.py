"""
Plant master-data generator for EOIP synthetic data generation.

This module generates a deterministic portfolio of validated Plant domain
objects. It is the authoritative source for synthetic plant master data and
must be used instead of constructing plant dictionaries independently.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date
from typing import Final

from eoip.synthetic.models.plant import Plant, PlantStatus

_DEFAULT_RANDOM_SEED: Final[int] = 42
_DEFAULT_PLANT_COUNT: Final[int] = 20

_REGIONS: Final[tuple[str, ...]] = (
    "Punjab Central",
    "Punjab South",
    "Sindh North",
    "Sindh South",
    "Balochistan East",
    "Khyber Pakhtunkhwa",
)

_MANUFACTURING_BASE_NAMES: Final[tuple[str, ...]] = (
    "Aurora",
    "Solstice",
    "Helios",
    "Radiant",
    "Suncrest",
    "Horizon",
    "Lumina",
    "Solaris",
    "Zenith",
    "Daystar",
)

_REGION_COORDINATES: Final[dict[str, tuple[float, float]]] = {
    "Punjab Central": (31.5204, 74.3587),
    "Punjab South": (29.3956, 71.6836),
    "Sindh North": (27.7052, 68.8574),
    "Sindh South": (24.8607, 67.0011),
    "Balochistan East": (28.4907, 65.0958),
    "Khyber Pakhtunkhwa": (34.0151, 71.5249),
}


@dataclass(frozen=True, slots=True)
class PlantGeneratorConfig:
    """Configuration for deterministic synthetic plant generation."""

    plant_count: int = _DEFAULT_PLANT_COUNT
    random_seed: int = _DEFAULT_RANDOM_SEED
    minimum_dc_capacity_mw: float = 25.0
    maximum_dc_capacity_mw: float = 100.0
    minimum_dc_ac_ratio: float = 1.10
    maximum_dc_ac_ratio: float = 1.35
    earliest_commissioning_year: int = 2015
    latest_commissioning_year: int = 2024

    def __post_init__(self) -> None:
        """Validate plant-generator configuration."""
        if isinstance(self.plant_count, bool) or not isinstance(
            self.plant_count,
            int,
        ):
            raise TypeError("plant_count must be an integer greater than zero.")

        if self.plant_count <= 0:
            raise ValueError(
                f"Invalid plant_count '{self.plant_count}'. "
                "Use an integer greater than zero."
            )

        if isinstance(self.random_seed, bool) or not isinstance(
            self.random_seed,
            int,
        ):
            raise TypeError("random_seed must be an integer.")

        if self.minimum_dc_capacity_mw <= 0:
            raise ValueError("minimum_dc_capacity_mw must be greater than zero.")

        if self.maximum_dc_capacity_mw < self.minimum_dc_capacity_mw:
            raise ValueError(
                "maximum_dc_capacity_mw must be greater than or equal to "
                "minimum_dc_capacity_mw."
            )

        if self.minimum_dc_ac_ratio < 1.0:
            raise ValueError("minimum_dc_ac_ratio must be at least 1.0.")

        if self.maximum_dc_ac_ratio < self.minimum_dc_ac_ratio:
            raise ValueError(
                "maximum_dc_ac_ratio must be greater than or equal to "
                "minimum_dc_ac_ratio."
            )

        if self.earliest_commissioning_year < 2000:
            raise ValueError("earliest_commissioning_year must be 2000 or later.")

        if self.latest_commissioning_year < self.earliest_commissioning_year:
            raise ValueError(
                "latest_commissioning_year must be greater than or equal to "
                "earliest_commissioning_year."
            )

        if self.latest_commissioning_year > date.today().year:
            raise ValueError("latest_commissioning_year cannot be in the future.")


def generate_plants(
    config: PlantGeneratorConfig | None = None,
) -> tuple[Plant, ...]:
    """
    Generate a deterministic portfolio of validated solar plants.

    Parameters
    ----------
    config:
        Optional generator configuration. Defaults to 20 plants and seed 42.

    Returns
    -------
    tuple[Plant, ...]
        Immutable collection of generated Plant domain objects.
    """
    resolved_config = config or PlantGeneratorConfig()
    rng = random.Random(resolved_config.random_seed)

    plants: list[Plant] = []

    for index in range(1, resolved_config.plant_count + 1):
        region = _REGIONS[(index - 1) % len(_REGIONS)]
        base_latitude, base_longitude = _REGION_COORDINATES[region]

        dc_capacity_mw = round(
            rng.uniform(
                resolved_config.minimum_dc_capacity_mw,
                resolved_config.maximum_dc_capacity_mw,
            ),
            2,
        )
        dc_ac_ratio = rng.uniform(
            resolved_config.minimum_dc_ac_ratio,
            resolved_config.maximum_dc_ac_ratio,
        )
        ac_capacity_mw = round(dc_capacity_mw / dc_ac_ratio, 2)

        commissioning_year = rng.randint(
            resolved_config.earliest_commissioning_year,
            resolved_config.latest_commissioning_year,
        )
        commissioning_month = rng.randint(1, 12)
        commissioning_day = rng.randint(1, 28)

        latitude = round(base_latitude + rng.uniform(-0.75, 0.75), 6)
        longitude = round(base_longitude + rng.uniform(-0.75, 0.75), 6)

        plant_name = _build_plant_name(index=index, region=region)

        plants.append(
            Plant(
                plant_id=f"PLANT-{index:03d}",
                plant_name=plant_name,
                region=region,
                latitude=latitude,
                longitude=longitude,
                dc_capacity_mw=dc_capacity_mw,
                ac_capacity_mw=ac_capacity_mw,
                commissioning_date=date(
                    commissioning_year,
                    commissioning_month,
                    commissioning_day,
                ),
                status=PlantStatus.OPERATIONAL,
            )
        )

    return tuple(plants)


def generate_plant_records(
    config: PlantGeneratorConfig | None = None,
) -> tuple[dict[str, object], ...]:
    """
    Generate serialization-ready plant master-data records.

    Parameters
    ----------
    config:
        Optional generator configuration.

    Returns
    -------
    tuple[dict[str, object], ...]
        Immutable collection of serialized plant records.
    """
    return tuple(plant.to_record() for plant in generate_plants(config))


def _build_plant_name(*, index: int, region: str) -> str:
    """Build a deterministic descriptive plant name."""
    base_name = _MANUFACTURING_BASE_NAMES[(index - 1) % len(_MANUFACTURING_BASE_NAMES)]
    region_label = region.replace(" ", "-")
    return f"{base_name} {region_label} Solar Plant {index:02d}"
