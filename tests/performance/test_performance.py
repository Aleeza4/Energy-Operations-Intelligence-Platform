"""Performance validation tests for the EOIP platform."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from statistics import mean
from time import perf_counter

from fastapi.testclient import TestClient

from eoip.api.app import app
from eoip.synthetic.config import (
    GenerationConfig,
    GenerationProfile,
    PortfolioConfig,
    TimeRangeConfig,
)
from eoip.synthetic.generator import generate_dataset

E2E_SEED = 20260821

SYNTHETIC_GENERATION_LIMIT_SECONDS = float(
    os.getenv(
        "EOIP_PERF_SYNTHETIC_LIMIT_SECONDS",
        "15.0",
    )
)

API_P95_LIMIT_SECONDS = float(
    os.getenv(
        "EOIP_PERF_API_P95_SECONDS",
        "0.5",
    )
)

OPENAPI_P95_LIMIT_SECONDS = float(
    os.getenv(
        "EOIP_PERF_OPENAPI_P95_SECONDS",
        "1.0",
    )
)

API_REPEATED_REQUEST_COUNT = int(
    os.getenv(
        "EOIP_PERF_API_REQUEST_COUNT",
        "50",
    )
)

OPENAPI_REQUEST_COUNT = int(
    os.getenv(
        "EOIP_PERF_OPENAPI_REQUEST_COUNT",
        "10",
    )
)


def _generation_profile() -> GenerationProfile:
    """Return an available deterministic generation profile."""
    return next(iter(GenerationProfile))


def _generation_config() -> GenerationConfig:
    """Create a small but representative performance dataset."""
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


def _percentile_95(
    durations: list[float],
) -> float:
    """Return the nearest-rank 95th percentile."""
    if not durations:
        raise ValueError("durations cannot be empty")

    ordered = sorted(durations)

    index = max(
        0,
        int(len(ordered) * 0.95) - 1,
    )

    return ordered[index]


def _measure_request(
    client: TestClient,
    path: str,
) -> tuple[float, int]:
    """Measure one HTTP GET request."""
    started = perf_counter()

    response = client.get(path)

    duration = perf_counter() - started

    return (
        duration,
        response.status_code,
    )


def test_synthetic_dataset_generation_performance() -> None:
    """Representative synthetic generation should remain within the baseline."""
    config = _generation_config()

    started = perf_counter()

    dataset = generate_dataset(config)

    elapsed = perf_counter() - started

    assert dataset.plants
    assert dataset.equipment
    assert dataset.revenue_meters
    assert dataset.plant_scada

    assert elapsed < SYNTHETIC_GENERATION_LIMIT_SECONDS, (
        "Synthetic dataset generation exceeded "
        f"{SYNTHETIC_GENERATION_LIMIT_SECONDS:.2f}s "
        f"baseline: {elapsed:.3f}s"
    )


def test_health_endpoint_repeated_request_performance() -> None:
    """Health endpoint should remain responsive under repeated requests."""
    durations: list[float] = []

    with TestClient(app) as client:
        warmup = client.get("/api/v1/health")

        assert warmup.status_code == 200

        for _ in range(API_REPEATED_REQUEST_COUNT):
            duration, status_code = _measure_request(
                client,
                "/api/v1/health",
            )

            assert status_code == 200

            durations.append(duration)

    p95 = _percentile_95(durations)

    assert p95 < API_P95_LIMIT_SECONDS, (
        "Health endpoint p95 latency exceeded "
        f"{API_P95_LIMIT_SECONDS:.3f}s: "
        f"{p95:.3f}s"
    )


def test_health_endpoint_average_latency() -> None:
    """Average health-check latency should remain comfortably below baseline."""
    durations: list[float] = []

    with TestClient(app) as client:
        warmup = client.get("/api/v1/health")

        assert warmup.status_code == 200

        for _ in range(API_REPEATED_REQUEST_COUNT):
            duration, status_code = _measure_request(
                client,
                "/api/v1/health",
            )

            assert status_code == 200

            durations.append(duration)

    average_latency = mean(durations)

    assert average_latency < API_P95_LIMIT_SECONDS, (
        "Health endpoint average latency exceeded "
        f"{API_P95_LIMIT_SECONDS:.3f}s: "
        f"{average_latency:.3f}s"
    )


def test_openapi_schema_performance() -> None:
    """OpenAPI schema generation should remain responsive."""
    durations: list[float] = []

    with TestClient(app) as client:
        warmup = client.get("/openapi.json")

        assert warmup.status_code == 200

        for _ in range(OPENAPI_REQUEST_COUNT):
            duration, status_code = _measure_request(
                client,
                "/openapi.json",
            )

            assert status_code == 200

            durations.append(duration)

    p95 = _percentile_95(durations)

    assert p95 < OPENAPI_P95_LIMIT_SECONDS, (
        "OpenAPI p95 latency exceeded "
        f"{OPENAPI_P95_LIMIT_SECONDS:.3f}s: "
        f"{p95:.3f}s"
    )


def test_protected_endpoint_repeated_request_stability() -> None:
    """Repeated unauthorized requests should remain stable and responsive."""
    durations: list[float] = []

    with TestClient(app) as client:
        warmup = client.get("/api/v1/plants")

        assert warmup.status_code in {
            401,
            403,
        }

        for _ in range(API_REPEATED_REQUEST_COUNT):
            duration, status_code = _measure_request(
                client,
                "/api/v1/plants",
            )

            assert status_code in {
                401,
                403,
            }

            durations.append(duration)

    p95 = _percentile_95(durations)

    assert p95 < API_P95_LIMIT_SECONDS, (
        "Protected endpoint p95 latency exceeded "
        f"{API_P95_LIMIT_SECONDS:.3f}s: "
        f"{p95:.3f}s"
    )
