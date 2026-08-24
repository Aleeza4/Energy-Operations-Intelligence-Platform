"""Data-volume validation tests for the EOIP synthetic platform."""

from __future__ import annotations

import os
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from time import perf_counter
from typing import Any

import pandas as pd

from eoip.etl.config import ETLConfig
from eoip.etl.incremental import IncrementalConfig
from eoip.etl.pipeline import (
    DatasetPipelineConfig,
    run_pipeline,
)
from eoip.etl.validation import DatasetContract
from eoip.synthetic.config import (
    GenerationConfig,
    GenerationProfile,
    PortfolioConfig,
    TimeRangeConfig,
)
from eoip.synthetic.generator import generate_dataset

SEED = 20260822

PLANT_COUNT = int(
    os.getenv(
        "EOIP_VOLUME_PLANT_COUNT",
        "5",
    )
)

INVERTER_COUNT_MIN = int(
    os.getenv(
        "EOIP_VOLUME_INVERTER_MIN",
        "5",
    )
)

INVERTER_COUNT_MAX = int(
    os.getenv(
        "EOIP_VOLUME_INVERTER_MAX",
        "8",
    )
)

GENERATION_LIMIT_SECONDS = float(
    os.getenv(
        "EOIP_VOLUME_GENERATION_LIMIT_SECONDS",
        "45.0",
    )
)

ETL_LIMIT_SECONDS = float(
    os.getenv(
        "EOIP_VOLUME_ETL_LIMIT_SECONDS",
        "30.0",
    )
)


def _config() -> GenerationConfig:
    """Return a controlled multi-plant data-volume configuration."""
    return GenerationConfig(
        profile_name=GenerationProfile.DEFAULT,
        seed=SEED,
        time=TimeRangeConfig(
            start=datetime(
                2026,
                8,
                1,
                0,
                0,
                tzinfo=UTC,
            ),
            end=datetime(
                2026,
                8,
                2,
                0,
                0,
                tzinfo=UTC,
            ),
            interval_minutes=15,
        ),
        portfolio=PortfolioConfig(
            plant_count=PLANT_COUNT,
            aggregate_ac_capacity_min_mw=100.0,
            aggregate_ac_capacity_max_mw=400.0,
            plant_ac_capacity_min_mw=20.0,
            plant_ac_capacity_max_mw=80.0,
            inverter_count_min=INVERTER_COUNT_MIN,
            inverter_count_max=INVERTER_COUNT_MAX,
        ),
    )


def _record_to_dict(
    record: Any,
) -> dict[str, Any]:
    """Convert one synthetic record to a plain dictionary."""
    if hasattr(record, "to_record"):
        values = record.to_record()
    elif is_dataclass(record):
        values = asdict(record)
    elif hasattr(record, "__dict__"):
        values = vars(record)
    else:
        raise TypeError(
            "Synthetic record cannot be converted " f"to a dictionary: {type(record)!r}"
        )

    normalized: dict[str, Any] = {}

    for key, value in values.items():
        if isinstance(value, Enum):
            normalized[key] = value.value
        else:
            normalized[key] = value

    return normalized


def _records_to_frame(
    records: Any,
) -> pd.DataFrame:
    """Convert synthetic records to a pandas DataFrame."""
    if isinstance(records, pd.DataFrame):
        return records.copy(deep=True)

    return pd.DataFrame(_record_to_dict(record) for record in records)


def test_multi_plant_generation_volume() -> None:
    """Synthetic generation should support a representative portfolio."""
    started = perf_counter()

    dataset = generate_dataset(_config())

    elapsed = perf_counter() - started

    assert len(dataset.plants) == PLANT_COUNT

    assert len(dataset.equipment) >= (PLANT_COUNT * INVERTER_COUNT_MIN)

    assert len(dataset.plant_scada) > 0

    assert elapsed < GENERATION_LIMIT_SECONDS, (
        "High-volume synthetic generation exceeded "
        f"{GENERATION_LIMIT_SECONDS:.2f}s: "
        f"{elapsed:.3f}s"
    )


def test_time_series_volume_scales_with_portfolio() -> None:
    """Plant SCADA volume should scale across plants and time intervals."""
    dataset = generate_dataset(_config())

    expected_intervals_per_plant = 96

    expected_minimum_rows = PLANT_COUNT * expected_intervals_per_plant

    assert len(dataset.plant_scada) >= expected_minimum_rows


def test_high_volume_referential_integrity() -> None:
    """Larger generated datasets must retain plant relationships."""
    dataset = generate_dataset(_config())

    plant_ids = {plant.plant_id for plant in dataset.plants}

    equipment_plant_ids = {equipment.plant_id for equipment in dataset.equipment}

    scada_plant_ids = {observation.plant_id for observation in dataset.plant_scada}

    assert equipment_plant_ids
    assert scada_plant_ids

    assert equipment_plant_ids <= plant_ids
    assert scada_plant_ids <= plant_ids
    assert scada_plant_ids == plant_ids


def test_high_volume_identifiers_remain_unique() -> None:
    """Generated primary identifiers should remain unique at higher volume."""
    dataset = generate_dataset(_config())

    plant_ids = [plant.plant_id for plant in dataset.plants]

    equipment_ids = [equipment.equipment_id for equipment in dataset.equipment]

    assert len(plant_ids) == len(set(plant_ids))

    assert len(equipment_ids) == len(set(equipment_ids))


def test_large_scada_frame_has_expected_shape() -> None:
    """Plant SCADA should convert cleanly to a tabular workload."""
    dataset = generate_dataset(_config())

    frame = _records_to_frame(dataset.plant_scada)

    assert not frame.empty

    assert len(frame) == len(dataset.plant_scada)

    required_columns = {
        "plant_id",
        "meter_id",
        "timestamp",
        "export_power_kw",
        "import_power_kw",
        "interval_export_energy_kwh",
        "grid_available",
        "plant_available",
    }

    assert required_columns <= set(frame.columns)

    assert frame["plant_id"].nunique() == PLANT_COUNT
    assert frame["timestamp"].notna().all()


def test_high_volume_scada_crosses_etl_boundary() -> None:
    """A larger SCADA workload should pass through the ETL pipeline."""
    dataset = generate_dataset(_config())

    frame = _records_to_frame(dataset.plant_scada)

    assert not frame.empty
    assert "timestamp" in frame.columns

    contract = DatasetContract(
        dataset_name="plant_scada",
        required_columns=tuple(frame.columns),
        allow_empty=False,
    )

    dataset_configs = {
        "plant_scada": DatasetPipelineConfig(
            contract=contract,
            incremental=IncrementalConfig(
                watermark_column="timestamp",
            ),
        )
    }

    started = perf_counter()

    result = run_pipeline(
        config=ETLConfig(),
        dataset_configs=dataset_configs,
        datasets={
            "plant_scada": frame,
        },
        run_id="phase12-volume-scada",
    )

    elapsed = perf_counter() - started

    assert result is not None

    assert elapsed < ETL_LIMIT_SECONDS, (
        "High-volume SCADA ETL exceeded "
        f"{ETL_LIMIT_SECONDS:.2f}s: "
        f"{elapsed:.3f}s"
    )
