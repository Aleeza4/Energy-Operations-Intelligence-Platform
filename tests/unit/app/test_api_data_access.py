"""Regression tests for the Streamlit-to-FastAPI production data boundary."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from eoip.app import data_access


def _response(payload: object) -> httpx.Response:
    return httpx.Response(200, json=payload, request=httpx.Request("GET", "http://api"))


def test_plant_performance_uses_authenticated_api_and_active_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A displayed KPI source must be an API response, scoped server-side."""
    observed: list[tuple[str, dict[str, object], dict[str, str]]] = []

    def fake_get(url: str, *, params, headers, timeout):
        observed.append((url, dict(params), dict(headers)))
        if url.endswith("/plants"):
            return _response({"items": [{"plant_id": "PLANT001"}]})
        return _response(
            {"scada_hourly": [{"plant_id": "PLANT001", "total_energy_kwh": 2500}]}
        )

    monkeypatch.setattr(
        data_access,
        "settings",
        SimpleNamespace(
            api_access_token="test-token",
            api_base_url="http://api/api/v1",
            api_request_timeout_seconds=1,
        ),
    )
    monkeypatch.setattr(data_access.httpx, "get", fake_get)
    monkeypatch.setattr(
        data_access,
        "_active_filter_params",
        lambda: {"plant_id": "PLANT001", "start_time": "2026-01-01T00:00:00Z"},
    )

    frame = data_access.get_plant_performance()

    assert frame.loc[0, "Plant"] == "PLANT001"
    assert frame.loc[0, "Actual Energy (MWh)"] == 2.5
    assert all(params["plant_id"] == "PLANT001" for _, params, _ in observed)
    assert all(
        headers["Authorization"] == "Bearer test-token" for _, _, headers in observed
    )


def test_backend_failure_never_returns_demo_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unavailable API is an explicit application error, not a demo fallback."""
    monkeypatch.setattr(data_access, "settings", SimpleNamespace(api_access_token=""))

    with pytest.raises(data_access.BackendUnavailableError):
        data_access.get_assets()


def test_production_provider_contains_no_legacy_static_operational_records() -> None:
    """Prevent a future dashboard regression to the audited fake production data."""
    source = Path(data_access.__file__).read_text(encoding="utf-8")
    forbidden = (
        "_PLANT_PERFORMANCE_RECORDS",
        "_ASSET_RECORDS",
        "_INCIDENT_RECORDS",
        "_ANOMALY_RECORDS",
        "_MAINTENANCE_RECORDS",
        "_RECOMMENDATION_RECORDS",
        "Solar Plant A",
        "INV-005",
    )
    assert not any(value in source for value in forbidden)
