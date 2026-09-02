"""Tests for the centralized read-only EOIP application data boundary."""

from __future__ import annotations

import importlib
from pathlib import Path

import pandas as pd
import pytest

from eoip.app import data_access
from eoip.app.dashboards import data_quality

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DASHBOARD_DIR = PROJECT_ROOT / "src" / "eoip" / "app" / "dashboards"

EXPECTED_SCHEMAS = {
    "plant_performance": (
        "Plant",
        "Actual Energy (MWh)",
        "Expected Energy (MWh)",
        "Performance Ratio (%)",
        "Capacity Factor (%)",
        "Availability (%)",
    ),
    "assets": (
        "Equipment ID",
        "Plant",
        "Equipment Type",
        "Health Score",
        "Failure Probability",
        "Risk Level",
        "Priority Rank",
    ),
    "incidents": (
        "Incident ID",
        "Plant",
        "Equipment",
        "Severity",
        "Status",
        "MTTA (min)",
        "Downtime (min)",
    ),
    "forecasts": (
        "Date",
        "Forecast Energy (MWh)",
        "Lower Bound (MWh)",
        "Upper Bound (MWh)",
    ),
    "anomalies": (
        "Anomaly ID",
        "Plant",
        "Equipment",
        "Severity",
        "Method",
        "Anomaly Score",
        "Status",
    ),
    "maintenance": (
        "Priority Rank",
        "Equipment ID",
        "Plant",
        "Health Score",
        "Failure Probability",
        "Risk Level",
        "Priority Score",
    ),
    "recommendations": (
        "Recommendation ID",
        "Source System",
        "Source Record ID",
        "Provenance",
        "Priority Rank",
        "Priority Classification",
        "Equipment ID",
        "Plant",
        "Recommendation Type",
        "Recommended Action",
        "Rationale",
        "Risk Score",
        "Risk Score Classification",
        "Recoverable Energy (kWh)",
        "Recoverable Energy Classification",
        "Governance Status",
        "Status Classification",
        "Owner",
        "Owner Classification",
        "Evidence Type",
        "Evidence Source",
        "Evidence ID",
        "Evidence Relationship",
        "Evidence Classification",
        "Assumption Version",
        "Analysis Horizon",
        "Currency",
        "Financial Impact",
        "Financial Impact Classification",
        "ROI",
        "ROI Classification",
        "Revenue at Risk",
        "Revenue at Risk Classification",
        "Realized Benefit",
        "Realized Benefit Classification",
        "Financial Status",
    ),
}


@pytest.mark.parametrize("dataset", tuple(EXPECTED_SCHEMAS))
def test_primary_dataset_schema_and_determinism(dataset: str) -> None:
    loader = data_access.APPLICATION_DATA_LOADERS[dataset]
    first = loader()
    second = loader()

    assert tuple(first.columns) == EXPECTED_SCHEMAS[dataset]
    pd.testing.assert_frame_equal(first, second, check_dtype=True)


@pytest.mark.parametrize("dataset", tuple(EXPECTED_SCHEMAS))
def test_returned_frames_are_independent_read_only_snapshots(dataset: str) -> None:
    loader = data_access.APPLICATION_DATA_LOADERS[dataset]
    first = loader()
    expected = loader()

    first.drop(index=first.index[0], inplace=True)

    pd.testing.assert_frame_equal(loader(), expected, check_dtype=True)


def test_identifiers_attribution_and_timestamp_support_are_preserved() -> None:
    assets = data_access.get_assets()
    incidents = data_access.get_incidents()
    anomalies = data_access.get_anomalies()
    forecasts = data_access.get_forecasts()

    assert assets.loc[assets["Equipment ID"].eq("INV-005"), "Plant"].item() == (
        "Solar Plant D"
    )
    assert (
        incidents.loc[incidents["Incident ID"].eq("INC-1042"), "Equipment"].item()
        == "INV-005"
    )
    assert (
        anomalies.loc[anomalies["Anomaly ID"].eq("ANM-2031"), "Plant"].item()
        == "Solar Plant D"
    )
    assert pd.api.types.is_datetime64_any_dtype(forecasts["Date"].dtype)


def test_global_forecast_semantics_and_secret_exclusion_are_explicit() -> None:
    datasets = data_access.get_application_datasets()
    assert "Plant" not in datasets["forecasts"].columns
    forbidden = {"password", "secret", "token", "api_key", "connection_string"}
    exposed = {
        str(column).casefold()
        for dataframe in datasets.values()
        for column in dataframe.columns
    }
    assert forbidden.isdisjoint(exposed)


def test_demo_recommendations_are_governed_without_financial_fabrication() -> None:
    recommendations = data_access.get_recommendations()
    assert recommendations["Recommendation ID"].is_unique
    assert recommendations["Recommendation ID"].str.startswith("REC-").all()
    assert recommendations["Governance Status"].eq("PROPOSED").all()
    assert recommendations["Owner"].eq("Unassigned").all()
    assert recommendations["Owner Classification"].eq("UNAVAILABLE").all()
    assert recommendations["Status Classification"].eq("CONFIGURED").all()
    assert set(recommendations["Evidence Relationship"]) <= {
        "RELATED_TO",
        "UNAVAILABLE",
    }
    assert recommendations["Currency"].eq("UNAVAILABLE").all()
    assert recommendations["Financial Impact"].isna().all()
    assert recommendations["ROI"].isna().all()
    assert recommendations["Revenue at Risk"].isna().all()
    assert recommendations["Realized Benefit"].isna().all()


def test_data_access_can_be_patched_at_one_stable_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replacement = pd.DataFrame({"Plant": ["Test Plant"]})
    monkeypatch.setattr(
        data_access, "get_plant_performance", lambda: replacement.copy()
    )

    governed = data_quality._governed_datasets()

    pd.testing.assert_frame_equal(governed["Plants"], replacement)


def test_dashboards_have_no_cross_dashboard_imports_or_shared_source_factories() -> (
    None
):
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(DASHBOARD_DIR.glob("*.py"))
    )
    assert "from eoip.app.dashboards." not in source
    assert "import eoip.app.dashboards." not in source
    for obsolete_loader in (
        "def _portfolio_performance_data",
        "def _plant_comparison_data",
        "def _asset_health_data",
        "def _incident_data",
        "def _forecast_data",
        "def _active_anomalies_data",
        "def _maintenance_priority_data",
    ):
        assert obsolete_loader not in source


def test_all_page_modules_still_import() -> None:
    pages = (
        "executive",
        "operations",
        "plant_performance",
        "assets",
        "alarms_incidents",
        "forecast",
        "anomaly",
        "maintenance",
        "recommendations",
        "data_quality",
        "administration",
    )
    for page in pages:
        importlib.import_module(f"eoip.app.dashboards.{page}")
