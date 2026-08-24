"""End-to-end validation tests for the EOIP platform flow."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from fastapi.testclient import TestClient

from eoip.api.app import app
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
from eoip.synthetic.generator import (
    SyntheticDataset,
    generate_dataset,
)

E2E_SEED = 20260821


def _records_to_frame(
    records: Any,
) -> pd.DataFrame:
    """Convert EOIP records into a DataFrame for cross-layer validation."""
    if isinstance(records, pd.DataFrame):
        return records.copy(deep=True)

    if records is None:
        return pd.DataFrame()

    if isinstance(records, Mapping):
        return pd.DataFrame([dict(records)])

    if isinstance(
        records,
        Iterable,
    ) and not isinstance(
        records,
        (str, bytes),
    ):
        rows: list[dict[str, Any]] = []

        for record in records:
            if isinstance(
                record,
                Mapping,
            ):
                rows.append(dict(record))
                continue

            to_record = getattr(
                record,
                "to_record",
                None,
            )

            if callable(to_record):
                rows.append(dict(to_record()))
                continue

            if is_dataclass(record):
                rows.append(asdict(record))
                continue

            record_dict = getattr(
                record,
                "__dict__",
                None,
            )

            if isinstance(
                record_dict,
                dict,
            ):
                rows.append(dict(record_dict))
                continue

            raise TypeError("Unsupported EOIP record type: " f"{type(record).__name__}")

        return pd.DataFrame(rows)

    raise TypeError("Unsupported EOIP dataset type: " f"{type(records).__name__}")


def _first_existing_column(
    frame: pd.DataFrame,
    candidates: tuple[str, ...],
) -> str | None:
    """Return the first matching column from candidate names."""
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate

    return None


def _generation_profile() -> GenerationProfile:
    """Return a deterministic available generation profile."""
    return next(iter(GenerationProfile))


def _generation_config() -> GenerationConfig:
    """Return a small deterministic synthetic-generation configuration."""
    return GenerationConfig(
        profile_name=_generation_profile(),
        seed=E2E_SEED,
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
            plant_count=1,
            aggregate_ac_capacity_min_mw=20.0,
            aggregate_ac_capacity_max_mw=25.0,
            plant_ac_capacity_min_mw=20.0,
            plant_ac_capacity_max_mw=25.0,
            inverter_count_min=2,
            inverter_count_max=3,
        ),
    )


def _generate_small_dataset() -> SyntheticDataset:
    """Generate the deterministic Phase 12 E2E dataset."""
    return generate_dataset(_generation_config())


def _pipeline_config(
    *,
    dataset_name: str,
    frame: pd.DataFrame,
    watermark_column: str,
    primary_key: tuple[str, ...] = (),
) -> DatasetPipelineConfig:
    """Create an ETL configuration using a real dataset watermark."""
    if watermark_column not in frame.columns:
        raise ValueError(
            f"{dataset_name} does not contain "
            f"watermark column {watermark_column!r}."
        )

    return DatasetPipelineConfig(
        contract=DatasetContract(
            dataset_name=dataset_name,
            required_columns=tuple(frame.columns),
            allow_empty=False,
        ),
        incremental=IncrementalConfig(
            watermark_column=watermark_column,
            primary_key=primary_key,
        ),
    )


def test_synthetic_dataset_generates_required_platform_tables() -> None:
    """Synthetic generation should produce required EOIP datasets."""
    dataset = _generate_small_dataset()

    dataset_names = (
        "plants",
        "equipment",
        "revenue_meters",
        "weather",
        "inverter_scada",
        "plant_scada",
        "ground_truth_events",
        "alarms",
        "incidents",
        "work_orders",
        "tariffs",
        "budgets",
    )

    for dataset_name in dataset_names:
        assert hasattr(
            dataset,
            dataset_name,
        )

    plants = _records_to_frame(dataset.plants)

    equipment = _records_to_frame(dataset.equipment)

    plant_scada = _records_to_frame(dataset.plant_scada)

    assert not plants.empty
    assert not equipment.empty
    assert not plant_scada.empty


def test_synthetic_referential_integrity_across_platform_tables() -> None:
    """Generated dependent records should reference valid plants."""
    dataset = _generate_small_dataset()

    plants = _records_to_frame(dataset.plants)

    plant_id_column = _first_existing_column(
        plants,
        (
            "plant_id",
            "id",
        ),
    )

    assert plant_id_column is not None

    plant_ids = set(plants[plant_id_column].dropna().astype(str).tolist())

    assert plant_ids

    dependent_datasets = {
        "equipment": dataset.equipment,
        "revenue_meters": dataset.revenue_meters,
        "weather": dataset.weather,
        "inverter_scada": dataset.inverter_scada,
        "plant_scada": dataset.plant_scada,
        "ground_truth_events": dataset.ground_truth_events,
        "alarms": dataset.alarms,
        "incidents": dataset.incidents,
        "work_orders": dataset.work_orders,
        "tariffs": dataset.tariffs,
        "budgets": dataset.budgets,
    }

    checked_tables = 0

    for records in dependent_datasets.values():
        frame = _records_to_frame(records)

        if frame.empty:
            continue

        dependent_plant_column = _first_existing_column(
            frame,
            (
                "plant_id",
                "site_id",
            ),
        )

        if dependent_plant_column is None:
            continue

        referenced_ids = set(
            frame[dependent_plant_column].dropna().astype(str).tolist()
        )

        assert referenced_ids.issubset(plant_ids)

        checked_tables += 1

    assert checked_tables >= 3


def test_synthetic_generation_is_reproducible() -> None:
    """The same configuration and seed should reproduce key datasets."""
    first = _generate_small_dataset()
    second = _generate_small_dataset()

    datasets_to_compare = (
        "plants",
        "equipment",
        "revenue_meters",
        "weather",
        "plant_scada",
    )

    for dataset_name in datasets_to_compare:
        first_frame = _records_to_frame(
            getattr(
                first,
                dataset_name,
            )
        ).reset_index(drop=True)

        second_frame = _records_to_frame(
            getattr(
                second,
                dataset_name,
            )
        ).reset_index(drop=True)

        pd.testing.assert_frame_equal(
            first_frame,
            second_frame,
            check_dtype=True,
            check_like=False,
        )


def test_generated_plants_can_cross_the_etl_boundary() -> None:
    """Synthetic plant master data should cross the ETL boundary."""
    dataset = _generate_small_dataset()

    plants = _records_to_frame(dataset.plants)

    assert not plants.empty
    assert "plant_id" in plants.columns
    assert "commissioning_date" in plants.columns

    dataset_configs = {
        "plants": _pipeline_config(
            dataset_name="plants",
            frame=plants,
            watermark_column="commissioning_date",
            primary_key=("plant_id",),
        )
    }

    result = run_pipeline(
        config=ETLConfig(),
        dataset_configs=dataset_configs,
        datasets={
            "plants": plants,
        },
        run_id="phase12-e2e-plants",
    )

    assert result is not None


def test_multiple_generated_tables_can_cross_the_etl_boundary() -> None:
    """Multiple EOIP datasets should cross one ETL execution."""
    dataset = _generate_small_dataset()

    plants = _records_to_frame(dataset.plants)

    equipment = _records_to_frame(dataset.equipment)

    plant_scada = _records_to_frame(dataset.plant_scada)

    assert not plants.empty
    assert not equipment.empty
    assert not plant_scada.empty

    frames = {
        "plants": plants,
        "equipment": equipment,
        "plant_scada": plant_scada,
    }

    dataset_configs = {
        "plants": _pipeline_config(
            dataset_name="plants",
            frame=plants,
            watermark_column="commissioning_date",
            primary_key=("plant_id",),
        ),
        "equipment": _pipeline_config(
            dataset_name="equipment",
            frame=equipment,
            watermark_column="commissioning_date",
            primary_key=("equipment_id",),
        ),
        "plant_scada": _pipeline_config(
            dataset_name="plant_scada",
            frame=plant_scada,
            watermark_column="timestamp",
            primary_key=(
                "plant_id",
                "meter_id",
                "timestamp",
            ),
        ),
    }

    result = run_pipeline(
        config=ETLConfig(),
        dataset_configs=dataset_configs,
        datasets=frames,
        run_id="phase12-e2e-multi-table",
    )

    assert result is not None


def test_api_boundary_starts_after_platform_layers_import() -> None:
    """The FastAPI boundary should remain available with platform layers loaded."""
    client = TestClient(app)

    health_response = client.get("/api/v1/health")

    assert health_response.status_code == 200

    payload = health_response.json()

    assert payload["status"] == "healthy"


def test_openapi_contract_is_available_end_to_end() -> None:
    """EOIP should expose its documented HTTP contract successfully."""
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200

    schema = response.json()

    assert "paths" in schema
    assert "/api/v1/health" in schema["paths"]

    expected_route_fragments = (
        "/api/v1/plants",
        "/api/v1/equipment",
        "/api/v1/scada",
        "/api/v1/analytics",
        "/api/v1/forecasts",
        "/api/v1/anomalies",
        "/api/v1/recommendations",
    )

    paths = tuple(schema["paths"])

    for expected_path in expected_route_fragments:
        assert any(path.startswith(expected_path) for path in paths)
