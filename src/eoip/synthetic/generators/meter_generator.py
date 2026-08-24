"""
Revenue-meter master-data generator for EOIP synthetic data generation.

This module creates exactly one deterministic primary settlement meter for each
synthetic plant. Each meter is linked to the existing Equipment record whose
equipment type is REVENUE_METER. Interval and cumulative readings remain part
of plant SCADA and are not generated here.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Final

from eoip.synthetic.generators.equipment_generator import (
    EquipmentGeneratorConfig,
    generate_equipment,
)
from eoip.synthetic.generators.plant_generator import (
    PlantGeneratorConfig,
    generate_plants,
)
from eoip.synthetic.models.equipment import Equipment, EquipmentType
from eoip.synthetic.models.meter import (
    MeterAccuracyClass,
    MeterStatus,
    RevenueMeter,
)

_DEFAULT_RANDOM_SEED: Final[int] = 42
_DEFAULT_MINIMUM_CALIBRATION_OFFSET_DAYS: Final[int] = 30
_DEFAULT_MAXIMUM_CALIBRATION_OFFSET_DAYS: Final[int] = 365

_METER_CATALOGUE: Final[tuple[tuple[str, str, MeterAccuracyClass], ...]] = (
    ("Schneider Electric", "ION-9000", MeterAccuracyClass.CLASS_02S),
    ("Siemens", "SENTRON-PAC4200", MeterAccuracyClass.CLASS_05S),
    ("ABB", "M4M-30", MeterAccuracyClass.CLASS_05S),
    ("Landis+Gyr", "E650", MeterAccuracyClass.CLASS_02S),
    ("Secure", "Premier-300", MeterAccuracyClass.CLASS_1),
)

_MULTIPLIERS: Final[tuple[float, ...]] = (
    1.0,
    10.0,
    100.0,
    1_000.0,
)


@dataclass(frozen=True, slots=True)
class MeterGeneratorConfig:
    """Configuration for deterministic revenue-meter generation."""

    random_seed: int = _DEFAULT_RANDOM_SEED
    minimum_calibration_offset_days: int = _DEFAULT_MINIMUM_CALIBRATION_OFFSET_DAYS
    maximum_calibration_offset_days: int = _DEFAULT_MAXIMUM_CALIBRATION_OFFSET_DAYS
    calibration_due_probability: float = 0.05
    out_of_service_probability: float = 0.01

    def __post_init__(self) -> None:
        """Validate generator configuration."""
        if isinstance(self.random_seed, bool) or not isinstance(
            self.random_seed,
            int,
        ):
            raise TypeError("random_seed must be an integer.")

        self._validate_positive_integer(
            field_name="minimum_calibration_offset_days",
            value=self.minimum_calibration_offset_days,
        )
        self._validate_positive_integer(
            field_name="maximum_calibration_offset_days",
            value=self.maximum_calibration_offset_days,
        )

        if self.maximum_calibration_offset_days < self.minimum_calibration_offset_days:
            raise ValueError(
                "maximum_calibration_offset_days must be greater than or "
                "equal to minimum_calibration_offset_days."
            )

        self._validate_probability(
            field_name="calibration_due_probability",
            value=self.calibration_due_probability,
        )
        self._validate_probability(
            field_name="out_of_service_probability",
            value=self.out_of_service_probability,
        )

        if self.calibration_due_probability + self.out_of_service_probability > 1.0:
            raise ValueError(
                "calibration_due_probability plus "
                "out_of_service_probability must not exceed 1.0."
            )

    @staticmethod
    def _validate_positive_integer(
        *,
        field_name: str,
        value: int,
    ) -> None:
        """Validate a strictly positive integer."""
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{field_name} must be an integer.")

        if value <= 0:
            raise ValueError(f"{field_name} must be greater than zero.")

    @staticmethod
    def _validate_probability(
        *,
        field_name: str,
        value: float,
    ) -> None:
        """Validate a finite probability between zero and one."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{field_name} must be numeric.")

        if not math.isfinite(value):
            raise ValueError(f"{field_name} must be finite.")

        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{field_name} must be between 0.0 and 1.0.")


def generate_revenue_meters(
    config: MeterGeneratorConfig | None = None,
    *,
    plant_config: PlantGeneratorConfig | None = None,
    equipment_config: EquipmentGeneratorConfig | None = None,
) -> tuple[RevenueMeter, ...]:
    """
    Generate exactly one primary settlement meter for every plant.

    The linked equipment record must already be generated as an
    EquipmentType.REVENUE_METER asset. Multiple or missing revenue-meter
    equipment records for a plant are rejected because the Phase 2 contract
    requires exactly one primary settlement meter per plant.
    """
    resolved_config = config or MeterGeneratorConfig()
    resolved_equipment_config = equipment_config or EquipmentGeneratorConfig()

    if resolved_equipment_config.revenue_meters_per_plant != 1:
        raise ValueError("equipment_config.revenue_meters_per_plant must be exactly 1.")

    plants = generate_plants(plant_config)
    equipment = generate_equipment(
        resolved_equipment_config,
        plant_config=plant_config,
    )
    revenue_equipment_by_plant = _revenue_equipment_by_plant(
        equipment=equipment,
        plant_ids={plant.plant_id for plant in plants},
    )

    generated: list[RevenueMeter] = []

    for meter_index, plant in enumerate(plants, start=1):
        linked_equipment = revenue_equipment_by_plant[plant.plant_id]
        rng = random.Random(
            _meter_seed(
                base_seed=resolved_config.random_seed,
                meter_index=meter_index,
            )
        )
        manufacturer, model_number, accuracy_class = rng.choice(_METER_CATALOGUE)
        calibration_date = _calibration_date(
            commissioning_date=plant.commissioning_date,
            config=resolved_config,
            rng=rng,
        )
        status = _sample_status(config=resolved_config, rng=rng)

        generated.append(
            RevenueMeter(
                meter_id=_meter_id(meter_index),
                plant_id=plant.plant_id,
                equipment_id=linked_equipment.equipment_id,
                meter_name=f"{plant.plant_name} Primary Settlement Meter",
                manufacturer=manufacturer,
                model_number=model_number,
                serial_number=_serial_number(meter_index),
                accuracy_class=accuracy_class,
                multiplier=rng.choice(_MULTIPLIERS),
                calibration_date=calibration_date,
                status=status,
                is_primary=True,
                notes="Primary point-of-interconnection revenue meter.",
            )
        )

    return tuple(generated)


def generate_revenue_meter_records(
    config: MeterGeneratorConfig | None = None,
    *,
    plant_config: PlantGeneratorConfig | None = None,
    equipment_config: EquipmentGeneratorConfig | None = None,
) -> tuple[dict[str, object], ...]:
    """Generate serialization-ready revenue-meter master-data records."""
    return tuple(
        meter.to_record()
        for meter in generate_revenue_meters(
            config,
            plant_config=plant_config,
            equipment_config=equipment_config,
        )
    )


def _revenue_equipment_by_plant(
    *,
    equipment: tuple[Equipment, ...],
    plant_ids: set[str],
) -> dict[str, Equipment]:
    """Return exactly one revenue-meter Equipment record for each plant."""
    grouped: dict[str, list[Equipment]] = {plant_id: [] for plant_id in plant_ids}

    for item in equipment:
        if item.equipment_type is EquipmentType.REVENUE_METER:
            if item.plant_id not in grouped:
                raise ValueError(
                    f"Revenue meter equipment {item.equipment_id} references "
                    f"unknown plant_id '{item.plant_id}'."
                )
            grouped[item.plant_id].append(item)

    invalid_counts = {
        plant_id: len(items) for plant_id, items in grouped.items() if len(items) != 1
    }
    if invalid_counts:
        details = ", ".join(
            f"{plant_id}={count}" for plant_id, count in sorted(invalid_counts.items())
        )
        raise ValueError(
            "Exactly one revenue-meter equipment record is required per "
            f"plant; found {details}."
        )

    return {plant_id: items[0] for plant_id, items in grouped.items()}


def _calibration_date(
    *,
    commissioning_date: date,
    config: MeterGeneratorConfig,
    rng: random.Random,
) -> date:
    """Return a deterministic calibration date after commissioning."""
    offset_days = rng.randint(
        config.minimum_calibration_offset_days,
        config.maximum_calibration_offset_days,
    )
    return commissioning_date + timedelta(days=offset_days)


def _sample_status(
    *,
    config: MeterGeneratorConfig,
    rng: random.Random,
) -> MeterStatus:
    """Sample a bounded operational status."""
    sample = rng.random()

    if sample < config.out_of_service_probability:
        return MeterStatus.OUT_OF_SERVICE

    if sample < (
        config.out_of_service_probability + config.calibration_due_probability
    ):
        return MeterStatus.CALIBRATION_DUE

    return MeterStatus.ACTIVE


def _meter_id(index: int) -> str:
    """Return a canonical deterministic meter identifier."""
    return f"MTR-{index:05d}"


def _serial_number(index: int) -> str:
    """Return a deterministic serial-like meter identifier."""
    return f"RM-{index:08d}"


def _meter_seed(*, base_seed: int, meter_index: int) -> int:
    """Return a stable independent random seed for one meter."""
    return base_seed * 100_000 + meter_index


__all__ = [
    "MeterGeneratorConfig",
    "generate_revenue_meter_records",
    "generate_revenue_meters",
]
