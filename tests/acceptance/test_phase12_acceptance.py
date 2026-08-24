"""Phase 12 acceptance tests for EOIP platform quality validation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
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
from eoip.synthetic.generator import generate_dataset

ACCEPTANCE_SEED = 20260822


def _generation_config() -> GenerationConfig:
    """Return a deterministic acceptance-test dataset configuration."""
    return GenerationConfig(
        profile_name=GenerationProfile.DEFAULT,
        seed=ACCEPTANCE_SEED,
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
            plant_count=2,
            aggregate_ac_capacity_min_mw=40.0,
            aggregate_ac_capacity_max_mw=120.0,
            plant_ac_capacity_min_mw=20.0,
            plant_ac_capacity_max_mw=60.0,
            inverter_count_min=2,
            inverter_count_max=4,
        ),
    )


def test_acceptance_synthetic_platform_dataset_is_complete() -> None:
    """Acceptance: required platform datasets can be generated together."""
    dataset = generate_dataset(_generation_config())

    required_datasets = (
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

    for dataset_name in required_datasets:
        assert hasattr(
            dataset,
            dataset_name,
        )

    assert dataset.plants
    assert dataset.equipment
    assert dataset.revenue_meters
    assert dataset.plant_scada


def test_acceptance_identifiers_remain_consistent_across_core_tables() -> None:
    """Acceptance: generated child records reference valid plant identifiers."""
    dataset = generate_dataset(_generation_config())

    plant_ids = {plant.plant_id for plant in dataset.plants}

    equipment_plant_ids = {equipment.plant_id for equipment in dataset.equipment}

    meter_plant_ids = {meter.plant_id for meter in dataset.revenue_meters}

    scada_plant_ids = {row.plant_id for row in dataset.plant_scada}

    assert plant_ids
    assert equipment_plant_ids <= plant_ids
    assert meter_plant_ids <= plant_ids
    assert scada_plant_ids <= plant_ids


def test_acceptance_generation_is_reproducible() -> None:
    """Acceptance: fixed-seed generation produces deterministic outputs."""
    first = generate_dataset(_generation_config())

    second = generate_dataset(_generation_config())

    assert first.plants == second.plants
    assert first.equipment == second.equipment
    assert first.revenue_meters == second.revenue_meters
    assert first.plant_scada == second.plant_scada


def test_acceptance_scada_can_cross_etl_boundary() -> None:
    """Acceptance: generated SCADA data can pass the ETL pipeline."""
    dataset = generate_dataset(_generation_config())

    records = [row.to_record() for row in dataset.plant_scada]

    assert records

    import pandas as pd

    frame = pd.DataFrame(records)

    contract = DatasetContract(
        dataset_name="plant_scada",
        required_columns=tuple(frame.columns),
        timestamp_columns=("timestamp",),
        allow_empty=False,
    )

    dataset_configs = {
        "plant_scada": DatasetPipelineConfig(
            contract=contract,
            incremental=IncrementalConfig(
                watermark_column="timestamp",
                primary_key=(
                    "plant_id",
                    "meter_id",
                    "timestamp",
                ),
            ),
        )
    }

    result = run_pipeline(
        config=ETLConfig(),
        dataset_configs=dataset_configs,
        datasets={
            "plant_scada": frame,
        },
        run_id="phase12-acceptance-scada",
    )

    assert result is not None


def test_acceptance_api_health_endpoint_is_available() -> None:
    """Acceptance: the platform exposes a public health endpoint."""
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "healthy"


def test_acceptance_api_requires_authentication_for_protected_resources() -> None:
    """Acceptance: protected application resources require authentication."""
    with TestClient(app) as client:
        response = client.get("/api/v1/plants")

    assert response.status_code in {
        401,
        403,
    }


def test_acceptance_openapi_documentation_is_available() -> None:
    """Acceptance: OpenAPI documentation is exposed by the API application."""
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200

    schema = response.json()

    assert "openapi" in schema
    assert "paths" in schema
    assert "/api/v1/health" in schema["paths"]


@pytest.mark.parametrize(
    "path_prefix",
    (
        "/api/v1/plants",
        "/api/v1/equipment",
        "/api/v1/scada",
        "/api/v1/analytics",
        "/api/v1/forecasts",
        "/api/v1/anomalies",
        "/api/v1/recommendations",
    ),
)
def test_acceptance_expected_api_domains_are_documented(
    path_prefix: str,
) -> None:
    """Acceptance: required EOIP API domains appear in the OpenAPI contract."""
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = tuple(response.json()["paths"])

    assert any(path.startswith(path_prefix) for path in paths)
