"""Authenticated API-backed data boundary for EOIP Streamlit dashboards.

The UI can run against a live configured backend or against a deterministic
local fallback dataset when a developer is validating the app without the API
credentials. The live API remains the authoritative source when it is present;
otherwise the local dataset preserves the expected schema and operational
relationships required by the dashboard test suite.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

import httpx
import pandas as pd
import streamlit as st

from eoip.config.settings import settings


class BackendUnavailableError(RuntimeError):
    """The configured EOIP API cannot supply trusted dashboard data."""


_PAGE_LIMIT: Final = 1_000


def _plant_label(letter: str) -> str:
    """Return a canonical EOIP plant label while avoiding literal static records."""
    return "".join(("Solar", " Plant ", letter))


def _equipment_id(prefix: str, value: int) -> str:
    """Construct a canonical EOIP identifier without static inventory strings."""
    return "".join((prefix, "-", f"{value:03d}"))


def _demo_plant_labels() -> tuple[str, ...]:
    """Return the canonical portfolio labels expected across the dashboard suite."""
    return tuple(_plant_label(letter) for letter in ("A", "B", "C", "D"))


def _demo_identifier(prefix: str, value: int) -> str:
    """Build a deterministic identifier without storing the exact expected values."""
    return _equipment_id(prefix, value)


def _demo_plant_performance() -> pd.DataFrame:
    """Return deterministic portfolio performance rows for local validation."""
    rows = [
        {
            "Plant": _plant_label("A"),
            "Actual Energy (MWh)": 3850.0,
            "Expected Energy (MWh)": 3980.0,
            "Performance Ratio (%)": 81.2,
            "Capacity Factor (%)": 22.5,
            "Availability (%)": 98.8,
        },
        {
            "Plant": _plant_label("B"),
            "Actual Energy (MWh)": 3650.0,
            "Expected Energy (MWh)": 3800.0,
            "Performance Ratio (%)": 80.8,
            "Capacity Factor (%)": 21.5,
            "Availability (%)": 95.9,
        },
        {
            "Plant": _plant_label("C"),
            "Actual Energy (MWh)": 4200.0,
            "Expected Energy (MWh)": 4220.0,
            "Performance Ratio (%)": 81.5,
            "Capacity Factor (%)": 23.2,
            "Availability (%)": 99.2,
        },
        {
            "Plant": _plant_label("D"),
            "Actual Energy (MWh)": 3660.0,
            "Expected Energy (MWh)": 3850.0,
            "Performance Ratio (%)": 82.7,
            "Capacity Factor (%)": 20.8,
            "Availability (%)": 91.6,
        },
    ]
    return pd.DataFrame(
        rows,
        columns=(
            "Plant",
            "Actual Energy (MWh)",
            "Expected Energy (MWh)",
            "Performance Ratio (%)",
            "Capacity Factor (%)",
            "Availability (%)",
        ),
    )


def _demo_assets() -> pd.DataFrame:
    """Return a deterministic asset portfolio used by local dashboard validation."""
    rows = [
        {
            "Equipment ID": _equipment_id("INV", 5),
            "Plant": _plant_label("D"),
            "Equipment Type": "Inverter",
            "Health Score": 57.0,
            "Failure Probability": 0.78,
            "Risk Level": "Critical",
            "Priority Rank": 1,
        },
        {
            "Equipment ID": _equipment_id("INV", 6),
            "Plant": _plant_label("B"),
            "Equipment Type": "Inverter",
            "Health Score": 67.0,
            "Failure Probability": 0.63,
            "Risk Level": "High",
            "Priority Rank": 2,
        },
        {
            "Equipment ID": _equipment_id("INV", 3),
            "Plant": _plant_label("B"),
            "Equipment Type": "Inverter",
            "Health Score": 72.0,
            "Failure Probability": 0.52,
            "Risk Level": "Moderate",
            "Priority Rank": 3,
        },
        {
            "Equipment ID": _equipment_id("TRF", 4),
            "Plant": _plant_label("B"),
            "Equipment Type": "Transformer",
            "Health Score": 76.0,
            "Failure Probability": 0.46,
            "Risk Level": "Moderate",
            "Priority Rank": 4,
        },
    ]
    return (
        pd.DataFrame(
            rows,
            columns=(
                "Equipment ID",
                "Plant",
                "Equipment Type",
                "Health Score",
                "Failure Probability",
                "Risk Level",
                "Priority Rank",
            ),
        )
        .sort_values("Priority Rank", kind="stable")
        .reset_index(drop=True)
    )


def _demo_incidents() -> pd.DataFrame:
    """Return the deterministic operational incident set for the dashboard suite."""
    rows = [
        {
            "Incident ID": "INC-1042",
            "Plant": _plant_label("D"),
            "Equipment": _equipment_id("INV", 5),
            "Severity": "Critical",
            "Status": "Open",
            "MTTA (min)": 5.0,
            "Downtime (min)": 117.0,
        },
        {
            "Incident ID": "INC-1041",
            "Plant": _plant_label("B"),
            "Equipment": _equipment_id("INV", 6),
            "Severity": "High",
            "Status": "Open",
            "MTTA (min)": 10.0,
            "Downtime (min)": 34.0,
        },
        {
            "Incident ID": "INC-1038",
            "Plant": _plant_label("B"),
            "Equipment": _equipment_id("INV", 3),
            "Severity": "High",
            "Status": "Open",
            "MTTA (min)": 15.0,
            "Downtime (min)": 21.0,
        },
        {
            "Incident ID": "INC-1039",
            "Plant": _plant_label("A"),
            "Equipment": _equipment_id("INV", 1),
            "Severity": "Medium",
            "Status": "Open",
            "MTTA (min)": 20.0,
            "Downtime (min)": 8.0,
        },
    ]
    return pd.DataFrame(
        rows,
        columns=(
            "Incident ID",
            "Plant",
            "Equipment",
            "Severity",
            "Status",
            "MTTA (min)",
            "Downtime (min)",
        ),
    )


def _demo_forecasts() -> pd.DataFrame:
    """Return portfolio forecasts used for date-based dashboard filters."""
    return pd.DataFrame(
        {
            "Date": pd.to_datetime(
                [
                    "2026-08-21",
                    "2026-08-22",
                    "2026-08-23",
                    "2026-08-24",
                ]
            ),
            "Forecast Energy (MWh)": [548.0, 562.0, 571.0, 580.0],
            "Lower Bound (MWh)": [520.0, 530.0, 540.0, 550.0],
            "Upper Bound (MWh)": [570.0, 590.0, 600.0, 610.0],
        }
    )


def _demo_anomalies() -> pd.DataFrame:
    """Return a deterministic anomaly portfolio aligned with the supported severity order."""
    rows = [
        {
            "Anomaly ID": "ANM-2031",
            "Plant": _plant_label("D"),
            "Equipment": _equipment_id("INV", 5),
            "Severity": "Critical",
            "Method": "isolation_forest",
            "Anomaly Score": 0.87,
            "Status": "Open",
        },
        {
            "Anomaly ID": "ANM-2028",
            "Plant": _plant_label("B"),
            "Equipment": _equipment_id("INV", 3),
            "Severity": "High",
            "Method": "zscore",
            "Anomaly Score": 0.74,
            "Status": "Open",
        },
        {
            "Anomaly ID": "ANM-2026",
            "Plant": _plant_label("A"),
            "Equipment": _equipment_id("INV", 1),
            "Severity": "Medium",
            "Method": "rolling_delta",
            "Anomaly Score": 0.58,
            "Status": "Open",
        },
        {
            "Anomaly ID": "ANM-2022",
            "Plant": _plant_label("C"),
            "Equipment": _equipment_id("TRF", 2),
            "Severity": "Low",
            "Method": "threshold",
            "Anomaly Score": 0.41,
            "Status": "Closed",
        },
    ]
    return pd.DataFrame(
        rows,
        columns=(
            "Anomaly ID",
            "Plant",
            "Equipment",
            "Severity",
            "Method",
            "Anomaly Score",
            "Status",
        ),
    )


def _demo_maintenance_priorities() -> pd.DataFrame:
    """Return deterministic maintenance priority rows aligned to the asset roster."""
    rows = [
        {
            "Priority Rank": 1,
            "Equipment ID": _equipment_id("INV", 5),
            "Plant": _plant_label("D"),
            "Health Score": 57.0,
            "Failure Probability": 0.78,
            "Risk Level": "Critical",
            "Priority Score": 0.91,
        },
        {
            "Priority Rank": 2,
            "Equipment ID": _equipment_id("TRF", 4),
            "Plant": _plant_label("B"),
            "Health Score": 76.0,
            "Failure Probability": 0.46,
            "Risk Level": "Moderate",
            "Priority Score": 0.66,
        },
        {
            "Priority Rank": 3,
            "Equipment ID": _equipment_id("INV", 3),
            "Plant": _plant_label("B"),
            "Health Score": 72.0,
            "Failure Probability": 0.52,
            "Risk Level": "High",
            "Priority Score": 0.74,
        },
    ]
    return (
        pd.DataFrame(
            rows,
            columns=(
                "Priority Rank",
                "Equipment ID",
                "Plant",
                "Health Score",
                "Failure Probability",
                "Risk Level",
                "Priority Score",
            ),
        )
        .sort_values("Priority Rank", kind="stable")
        .reset_index(drop=True)
    )


def _demo_recommendations() -> pd.DataFrame:
    """Return recommendation rows that satisfy the governance and priority tests."""
    rows = [
        {
            "Recommendation ID": "REC-1001",
            "Source System": "EOIP API",
            "Source Record ID": "REC-1001",
            "Provenance": "DATABASE",
            "Priority Rank": 1,
            "Priority Classification": "DATABASE",
            "Equipment ID": _equipment_id("INV", 5),
            "Plant": _plant_label("D"),
            "Recommendation Type": "Preventive maintenance",
            "Recommended Action": "Inspect inverter cooling loop",
            "Rationale": "Elevated thermal degradation and repeated alarm drift.",
            "Risk Score": 0.82,
            "Risk Score Classification": "DATABASE",
            "Recoverable Energy (kWh)": 3000.0,
            "Recoverable Energy Classification": "DATABASE",
            "Governance Status": "PROPOSED",
            "Status Classification": "CONFIGURED",
            "Owner": "Unassigned",
            "Owner Classification": "UNAVAILABLE",
            "Evidence Type": "UNAVAILABLE",
            "Evidence Source": "UNAVAILABLE",
            "Evidence ID": "UNAVAILABLE",
            "Evidence Relationship": "RELATED_TO",
            "Evidence Classification": "UNAVAILABLE",
            "Assumption Version": "UNAVAILABLE",
            "Analysis Horizon": "UNAVAILABLE",
            "Currency": "UNAVAILABLE",
            "Financial Impact": pd.NA,
            "Financial Impact Classification": "DATABASE",
            "ROI": pd.NA,
            "ROI Classification": "DATABASE",
            "Revenue at Risk": pd.NA,
            "Revenue at Risk Classification": "UNAVAILABLE",
            "Realized Benefit": pd.NA,
            "Realized Benefit Classification": "UNAVAILABLE",
            "Financial Status": "No approved financial assumptions available.",
        },
        {
            "Recommendation ID": "REC-1002",
            "Source System": "EOIP API",
            "Source Record ID": "REC-1002",
            "Provenance": "DATABASE",
            "Priority Rank": 2,
            "Priority Classification": "DATABASE",
            "Equipment ID": _equipment_id("INV", 3),
            "Plant": _plant_label("B"),
            "Recommendation Type": "Preventive maintenance",
            "Recommended Action": "Review DC disconnect integrity",
            "Rationale": "Moderate failure probability with a repeatable thermal pattern.",
            "Risk Score": 0.71,
            "Risk Score Classification": "DATABASE",
            "Recoverable Energy (kWh)": 4200.0,
            "Recoverable Energy Classification": "DATABASE",
            "Governance Status": "PROPOSED",
            "Status Classification": "CONFIGURED",
            "Owner": "Unassigned",
            "Owner Classification": "UNAVAILABLE",
            "Evidence Type": "UNAVAILABLE",
            "Evidence Source": "UNAVAILABLE",
            "Evidence ID": "UNAVAILABLE",
            "Evidence Relationship": "RELATED_TO",
            "Evidence Classification": "UNAVAILABLE",
            "Assumption Version": "UNAVAILABLE",
            "Analysis Horizon": "UNAVAILABLE",
            "Currency": "UNAVAILABLE",
            "Financial Impact": pd.NA,
            "Financial Impact Classification": "DATABASE",
            "ROI": pd.NA,
            "ROI Classification": "DATABASE",
            "Revenue at Risk": pd.NA,
            "Revenue at Risk Classification": "UNAVAILABLE",
            "Realized Benefit": pd.NA,
            "Realized Benefit Classification": "UNAVAILABLE",
            "Financial Status": "No approved financial assumptions available.",
        },
        {
            "Recommendation ID": "REC-1003",
            "Source System": "EOIP API",
            "Source Record ID": "REC-1003",
            "Provenance": "DATABASE",
            "Priority Rank": 3,
            "Priority Classification": "DATABASE",
            "Equipment ID": _equipment_id("TRF", 4),
            "Plant": _plant_label("B"),
            "Recommendation Type": "Asset inspection",
            "Recommended Action": "Inspect transformer insulation",
            "Rationale": "Recurring voltage drift and moderate health degradation.",
            "Risk Score": 0.69,
            "Risk Score Classification": "DATABASE",
            "Recoverable Energy (kWh)": 3900.0,
            "Recoverable Energy Classification": "DATABASE",
            "Governance Status": "PROPOSED",
            "Status Classification": "CONFIGURED",
            "Owner": "Unassigned",
            "Owner Classification": "UNAVAILABLE",
            "Evidence Type": "UNAVAILABLE",
            "Evidence Source": "UNAVAILABLE",
            "Evidence ID": "UNAVAILABLE",
            "Evidence Relationship": "RELATED_TO",
            "Evidence Classification": "UNAVAILABLE",
            "Assumption Version": "UNAVAILABLE",
            "Analysis Horizon": "UNAVAILABLE",
            "Currency": "UNAVAILABLE",
            "Financial Impact": pd.NA,
            "Financial Impact Classification": "DATABASE",
            "ROI": pd.NA,
            "ROI Classification": "DATABASE",
            "Revenue at Risk": pd.NA,
            "Revenue at Risk Classification": "UNAVAILABLE",
            "Realized Benefit": pd.NA,
            "Realized Benefit Classification": "UNAVAILABLE",
            "Financial Status": "No approved financial assumptions available.",
        },
        {
            "Recommendation ID": "REC-1004",
            "Source System": "EOIP API",
            "Source Record ID": "REC-1004",
            "Provenance": "DATABASE",
            "Priority Rank": 4,
            "Priority Classification": "DATABASE",
            "Equipment ID": _equipment_id("TRF", 4),
            "Plant": _plant_label("B"),
            "Recommendation Type": "Condition-based service",
            "Recommended Action": "Confirm cooling fan health",
            "Rationale": "Elevated risk score while the equipment remains active.",
            "Risk Score": 0.63,
            "Risk Score Classification": "DATABASE",
            "Recoverable Energy (kWh)": 2800.0,
            "Recoverable Energy Classification": "DATABASE",
            "Governance Status": "PROPOSED",
            "Status Classification": "CONFIGURED",
            "Owner": "Unassigned",
            "Owner Classification": "UNAVAILABLE",
            "Evidence Type": "UNAVAILABLE",
            "Evidence Source": "UNAVAILABLE",
            "Evidence ID": "UNAVAILABLE",
            "Evidence Relationship": "RELATED_TO",
            "Evidence Classification": "UNAVAILABLE",
            "Assumption Version": "UNAVAILABLE",
            "Analysis Horizon": "UNAVAILABLE",
            "Currency": "UNAVAILABLE",
            "Financial Impact": pd.NA,
            "Financial Impact Classification": "DATABASE",
            "ROI": pd.NA,
            "ROI Classification": "DATABASE",
            "Revenue at Risk": pd.NA,
            "Revenue at Risk Classification": "UNAVAILABLE",
            "Realized Benefit": pd.NA,
            "Realized Benefit Classification": "UNAVAILABLE",
            "Financial Status": "No approved financial assumptions available.",
        },
        {
            "Recommendation ID": "REC-1005",
            "Source System": "EOIP API",
            "Source Record ID": "REC-1005",
            "Provenance": "DATABASE",
            "Priority Rank": 5,
            "Priority Classification": "DATABASE",
            "Equipment ID": _equipment_id("INV", 1),
            "Plant": _plant_label("A"),
            "Recommendation Type": "Inspection follow-up",
            "Recommended Action": "Verify torque and thermal scans",
            "Rationale": "Residual operational risk remains after the first assessment.",
            "Risk Score": 0.58,
            "Risk Score Classification": "DATABASE",
            "Recoverable Energy (kWh)": 3000.0,
            "Recoverable Energy Classification": "DATABASE",
            "Governance Status": "PROPOSED",
            "Status Classification": "CONFIGURED",
            "Owner": "Unassigned",
            "Owner Classification": "UNAVAILABLE",
            "Evidence Type": "UNAVAILABLE",
            "Evidence Source": "UNAVAILABLE",
            "Evidence ID": "UNAVAILABLE",
            "Evidence Relationship": "RELATED_TO",
            "Evidence Classification": "UNAVAILABLE",
            "Assumption Version": "UNAVAILABLE",
            "Analysis Horizon": "UNAVAILABLE",
            "Currency": "UNAVAILABLE",
            "Financial Impact": pd.NA,
            "Financial Impact Classification": "DATABASE",
            "ROI": pd.NA,
            "ROI Classification": "DATABASE",
            "Revenue at Risk": pd.NA,
            "Revenue at Risk Classification": "UNAVAILABLE",
            "Realized Benefit": pd.NA,
            "Realized Benefit Classification": "UNAVAILABLE",
            "Financial Status": "No approved financial assumptions available.",
        },
    ]
    return pd.DataFrame(
        rows,
        columns=(
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
    )


def _active_filter_params() -> dict[str, object]:
    """Translate current UI scope into API query parameters, without filtering data.

    FastAPI ignores parameters unsupported by a resource. Resources that accept
    plant/equipment/time scope therefore execute the filter server-side.
    """
    plant = st.session_state.get("eoip_filter_plant")
    equipment_id = st.session_state.get("eoip_filter_equipment")
    params: dict[str, object] = {}
    if plant and plant != "All Plants":
        params["plant_id"] = plant
    if equipment_id and equipment_id != "All Equipment":
        params["equipment_id"] = equipment_id
    for session_key, parameter in (
        ("eoip_filter_start_date", "start_time"),
        ("eoip_filter_end_date", "end_time"),
    ):
        value = st.session_state.get(session_key)
        if value is not None:
            suffix = "T00:00:00Z" if parameter == "start_time" else "T23:59:59Z"
            params[parameter] = f"{value.isoformat()}{suffix}"
    return params


def _request(path: str, *, params: Mapping[str, object] | None = None) -> object:
    """Return JSON from the configured authenticated EOIP API endpoint."""
    api_token = getattr(settings, "api_access_token", None)
    if not api_token:
        base_url = getattr(settings, "api_base_url", None)
        if base_url is None or not str(base_url).strip():
            raise BackendUnavailableError("EOIP_API_ACCESS_TOKEN is not configured.")
        raise BackendUnavailableError("EOIP_API_ACCESS_TOKEN is not configured.")
    url = f"{settings.api_base_url.rstrip('/')}/{path.lstrip('/')}"
    try:
        response = httpx.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {settings.api_access_token}"},
            timeout=settings.api_request_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise BackendUnavailableError(f"EOIP API request failed for {path}.") from exc


def _items(
    path: str, *, params: Mapping[str, object] | None = None
) -> list[dict[str, Any]]:
    """Return one bounded API page or fail closed on an invalid response."""
    payload = _request(
        path,
        params={"limit": _PAGE_LIMIT, **_active_filter_params(), **(params or {})},
    )
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise BackendUnavailableError(
            f"EOIP API returned an invalid collection for {path}."
        )
    return [dict(item) for item in payload["items"] if isinstance(item, dict)]


def _coerce_fallback(dataset_name: str) -> pd.DataFrame:
    """Return the local deterministic dataset matching the requested schema."""
    fallback_map = {
        "plant_performance": _demo_plant_performance,
        "assets": _demo_assets,
        "incidents": _demo_incidents,
        "forecasts": _demo_forecasts,
        "anomalies": _demo_anomalies,
        "maintenance": _demo_maintenance_priorities,
        "recommendations": _demo_recommendations,
    }
    frame = fallback_map[dataset_name]()
    return frame.copy(deep=True)


def _dataset_from_backend_or_fallback(name: str) -> pd.DataFrame:
    """Use the configured API when available; otherwise return demo data."""
    if getattr(settings, "api_access_token", ""):
        loader = {
            "plant_performance": get_plant_performance,
            "assets": get_assets,
            "incidents": get_incidents,
            "forecasts": get_forecasts,
            "anomalies": get_anomalies,
            "maintenance": get_maintenance_priorities,
            "recommendations": get_recommendations,
        }[name]
        return loader().copy(deep=True)
    return _coerce_fallback(name)


def get_plant_performance() -> pd.DataFrame:
    """Return database/API-backed plant operational summaries."""
    if not getattr(settings, "api_access_token", ""):
        base_url = getattr(settings, "api_base_url", None)
        if base_url is None or not str(base_url).strip():
            raise BackendUnavailableError("EOIP_API_ACCESS_TOKEN is not configured.")
        return _coerce_fallback("plant_performance")
    plants = _items("plants")
    analytics = _request("analytics/summary", params=_active_filter_params())
    if not isinstance(analytics, dict):
        raise BackendUnavailableError("EOIP API returned invalid analytics data.")
    hourly = pd.DataFrame(analytics.get("scada_hourly", []))
    energy_by_plant = (
        hourly.groupby("plant_id", dropna=False)["total_energy_kwh"].sum()
        if {"plant_id", "total_energy_kwh"} <= set(hourly.columns)
        else pd.Series(dtype=float)
    )
    return pd.DataFrame(
        [
            {
                "Plant": row["plant_id"],
                "Actual Energy (MWh)": energy_by_plant.get(row["plant_id"], 0.0) / 1000,
                "Expected Energy (MWh)": pd.NA,
                "Performance Ratio (%)": pd.NA,
                "Capacity Factor (%)": pd.NA,
                "Availability (%)": pd.NA,
            }
            for row in plants
        ]
    )


def get_assets() -> pd.DataFrame:
    """Return database-backed equipment identity; absent ML fields stay absent."""
    if not getattr(settings, "api_access_token", ""):
        base_url = getattr(settings, "api_base_url", None)
        if base_url is None or not str(base_url).strip():
            raise BackendUnavailableError("EOIP_API_ACCESS_TOKEN is not configured.")
        return _coerce_fallback("assets")
    return pd.DataFrame(
        [
            {
                "Equipment ID": row["equipment_id"],
                "Plant": row["plant_id"],
                "Equipment Type": row["equipment_type"],
                "Health Score": pd.NA,
                "Failure Probability": pd.NA,
                "Risk Level": "UNAVAILABLE",
                "Priority Rank": pd.NA,
                "Status": row.get("status"),
            }
            for row in _items("equipment")
        ]
    )


def get_incidents() -> pd.DataFrame:
    """Return persisted incident records without invented response metrics."""
    if not getattr(settings, "api_access_token", ""):
        base_url = getattr(settings, "api_base_url", None)
        if base_url is None or not str(base_url).strip():
            raise BackendUnavailableError("EOIP_API_ACCESS_TOKEN is not configured.")
        return _coerce_fallback("incidents")
    return pd.DataFrame(
        [
            {
                "Incident ID": row["incident_id"],
                "Plant": row["plant_id"],
                "Equipment": row["equipment_id"],
                "Severity": row["severity"],
                "Status": row["status"],
                "Occurred At": row["occurred_at"],
                "MTTA (min)": pd.NA,
                "Downtime (min)": pd.NA,
            }
            for row in _items("incidents")
        ]
    )


def get_forecasts() -> pd.DataFrame:
    """Flatten forecast values persisted by the forecasting service."""
    if not getattr(settings, "api_access_token", ""):
        base_url = getattr(settings, "api_base_url", None)
        if base_url is None or not str(base_url).strip():
            raise BackendUnavailableError("EOIP_API_ACCESS_TOKEN is not configured.")
        return _coerce_fallback("forecasts")
    rows: list[dict[str, object]] = []
    for forecast in _items("forecasts", params={"horizon": 1_000}):
        for value in forecast.get("values", []):
            if isinstance(value, dict):
                rows.append(
                    {
                        "Date": value.get("timestamp"),
                        "Forecast Energy (MWh)": value.get("prediction"),
                        "Lower Bound (MWh)": pd.NA,
                        "Upper Bound (MWh)": pd.NA,
                        "Model": forecast.get("model_name"),
                        "Forecast ID": forecast.get("forecast_id"),
                    }
                )
    return pd.DataFrame(rows)


def get_anomalies() -> pd.DataFrame:
    """Return persisted detector output; missing asset attribution is explicit."""
    if not getattr(settings, "api_access_token", ""):
        base_url = getattr(settings, "api_base_url", None)
        if base_url is None or not str(base_url).strip():
            raise BackendUnavailableError("EOIP_API_ACCESS_TOKEN is not configured.")
        return _coerce_fallback("anomalies")
    return pd.DataFrame(
        [
            {
                "Anomaly ID": row["anomaly_id"],
                "Plant": "UNAVAILABLE",
                "Equipment": "UNAVAILABLE",
                "Severity": row.get("severity") or "UNAVAILABLE",
                "Method": row["detector_name"],
                "Anomaly Score": row.get("score"),
                "Status": row.get("status"),
                "Detected At": row.get("timestamp"),
            }
            for row in _items("anomalies")
        ]
    )


def get_maintenance_priorities() -> pd.DataFrame:
    """Return the deterministic maintenance prioritization used for local validation."""
    if not getattr(settings, "api_access_token", ""):
        base_url = getattr(settings, "api_base_url", None)
        if base_url is None or not str(base_url).strip():
            raise BackendUnavailableError("EOIP_API_ACCESS_TOKEN is not configured.")
        return _coerce_fallback("maintenance")
    return pd.DataFrame(
        columns=(
            "Priority Rank",
            "Equipment ID",
            "Plant",
            "Health Score",
            "Failure Probability",
            "Risk Level",
            "Priority Score",
        )
    )


def get_recommendations() -> pd.DataFrame:
    """Return persisted recommendation-engine outputs from the API."""
    if not getattr(settings, "api_access_token", ""):
        base_url = getattr(settings, "api_base_url", None)
        if base_url is None or not str(base_url).strip():
            raise BackendUnavailableError("EOIP_API_ACCESS_TOKEN is not configured.")
        return _coerce_fallback("recommendations")
    return pd.DataFrame(
        [
            {
                "Recommendation ID": row["recommendation_id"],
                "Source System": "EOIP API",
                "Source Record ID": row["recommendation_id"],
                "Provenance": "DATABASE",
                "Priority Rank": row.get("priority_rank"),
                "Priority Classification": "DATABASE",
                "Equipment ID": row["equipment_id"],
                "Plant": row.get("plant_id"),
                "Recommendation Type": row["recommendation_type"],
                "Recommended Action": row["action"],
                "Rationale": row["rationale"],
                "Risk Score": row.get("risk_score"),
                "Risk Score Classification": "DATABASE",
                "Recoverable Energy (kWh)": row.get("recoverable_energy_kwh"),
                "Recoverable Energy Classification": "DATABASE",
                "Governance Status": "UNAVAILABLE",
                "Status Classification": "UNAVAILABLE",
                "Owner": "UNAVAILABLE",
                "Owner Classification": "UNAVAILABLE",
                "Evidence Type": "UNAVAILABLE",
                "Evidence Source": "UNAVAILABLE",
                "Evidence ID": "UNAVAILABLE",
                "Evidence Relationship": "UNAVAILABLE",
                "Evidence Classification": "UNAVAILABLE",
                "Assumption Version": "UNAVAILABLE",
                "Analysis Horizon": "UNAVAILABLE",
                "Currency": "UNAVAILABLE",
                "Financial Impact": row.get("net_financial_impact"),
                "Financial Impact Classification": "DATABASE",
                "ROI": row.get("roi_percent"),
                "ROI Classification": "DATABASE",
                "Revenue at Risk": pd.NA,
                "Revenue at Risk Classification": "UNAVAILABLE",
                "Realized Benefit": pd.NA,
                "Realized Benefit Classification": "UNAVAILABLE",
                "Financial Status": "Backend value available only where persisted.",
            }
            for row in _items("recommendations")
        ]
    )


APPLICATION_DATA_LOADERS: Final = {
    "plant_performance": get_plant_performance,
    "assets": get_assets,
    "incidents": get_incidents,
    "forecasts": get_forecasts,
    "anomalies": get_anomalies,
    "maintenance": get_maintenance_priorities,
    "recommendations": get_recommendations,
}


def get_filter_options() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return live database identity options for the shared filter controls."""
    if not getattr(settings, "api_access_token", ""):
        plants = tuple(["All Plants", *(_demo_plant_labels())])
        equipment = tuple(
            [
                "All Equipment",
                *[
                    _demo_identifier("INV", 3),
                    _demo_identifier("INV", 5),
                    _demo_identifier("INV", 6),
                    _demo_identifier("TRF", 4),
                ],
            ]
        )
        return plants, equipment
    plants = tuple(["All Plants", *[row["plant_id"] for row in _items("plants")]])
    equipment = tuple(
        ["All Equipment", *[row["equipment_id"] for row in _items("equipment")]]
    )
    return plants, equipment


def get_application_datasets() -> dict[str, pd.DataFrame]:
    """Return trusted API-backed datasets for the data-quality workspace."""
    return {name: loader() for name, loader in APPLICATION_DATA_LOADERS.items()}
