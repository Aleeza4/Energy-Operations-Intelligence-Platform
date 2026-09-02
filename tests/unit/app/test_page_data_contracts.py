"""Behavior tests for Phase A dashboard data scope contracts."""

from __future__ import annotations

from datetime import date

import pandas as pd

from eoip.app import data_access
from eoip.app.components.downloads import dataframe_to_csv_bytes
from eoip.app.components.filters import FilterSelection
from eoip.app.dashboards.operations import _operations_status_data
from eoip.app.data_filters import FilterDimensions, PageDataContract


def _scope(
    *,
    plant: str = "All Plants",
    start: date = date(2026, 8, 1),
    end: date = date(2026, 8, 31),
    equipment: str | None = None,
) -> FilterSelection:
    return FilterSelection(
        plant=plant,
        start_date=start,
        end_date=end,
        equipment_id=equipment,
    )


def test_plant_scope_changes_operational_kpis_and_table_rows() -> None:
    raw = _operations_status_data()
    portfolio = PageDataContract(_scope(), {"operations": raw}).scoped(
        "operations", dimensions=FilterDimensions(date=False)
    )
    plant_d = PageDataContract(
        _scope(plant="Solar Plant D"), {"operations": raw}
    ).scoped("operations", dimensions=FilterDimensions(date=False))

    assert len(portfolio) == 4
    assert len(plant_d) == 1
    assert portfolio["Active Alarms"].sum() == 24
    assert plant_d["Active Alarms"].sum() == 14


def test_date_scope_changes_forecast_kpi_source() -> None:
    raw = data_access.get_forecasts()
    one_day = PageDataContract(
        _scope(start=date(2026, 8, 21), end=date(2026, 8, 21)),
        {"forecast": raw},
    ).scoped("forecast", dimensions=FilterDimensions(plant=False, equipment=False))
    two_days = PageDataContract(
        _scope(start=date(2026, 8, 21), end=date(2026, 8, 22)),
        {"forecast": raw},
    ).scoped("forecast", dimensions=FilterDimensions(plant=False, equipment=False))

    assert one_day["Forecast Energy (MWh)"].sum() == 548.0
    assert two_days["Forecast Energy (MWh)"].sum() == 1110.0


def test_filtered_export_contains_only_selected_scope_records() -> None:
    incidents = PageDataContract(
        _scope(plant="Solar Plant D"), {"incidents": data_access.get_incidents()}
    ).scoped("incidents", dimensions=FilterDimensions(date=False))

    csv_text = dataframe_to_csv_bytes(incidents).decode("utf-8")

    assert "Solar Plant D" in csv_text
    assert "Solar Plant A" not in csv_text
    assert "Solar Plant B" not in csv_text


def test_valid_scope_with_no_records_stays_empty_without_fallback() -> None:
    records = pd.DataFrame(
        {
            "Plant": ["Solar Plant A"],
            "Equipment ID": ["INV-001"],
            "Value": [1],
        }
    )
    result = PageDataContract(
        _scope(plant="Solar Plant A", equipment="INV-004"),
        {"records": records},
    ).scoped("records", dimensions=FilterDimensions(date=False))

    assert result.empty


def test_forecast_contract_has_date_scope_without_false_plant_scope() -> None:
    raw = data_access.get_forecasts()
    scope = _scope(
        plant="Solar Plant D",
        start=date(2026, 8, 21),
        end=date(2026, 9, 3),
    )
    result = PageDataContract(scope, {"forecast": raw}).scoped(
        "forecast", dimensions=FilterDimensions(plant=False, equipment=False)
    )

    assert len(result) == len(raw)
