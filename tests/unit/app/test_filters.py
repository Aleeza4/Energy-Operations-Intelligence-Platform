"""Tests for shared EOIP filter validation and DataFrame filtering."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from eoip.app.components.filters import FilterSelection, normalize_filter_selection
from eoip.app.dashboards.alarms_incidents import prepare_alarm_trend_for_chart
from eoip.app.dashboards.forecast import get_default_forecast_date_range
from eoip.app.data_filters import (
    FilterDimensions,
    PageDataContract,
    apply_dataframe_filters,
    equipment_options_for_plant,
    has_rows,
)


def selection(
    *,
    plant: str = "All Plants",
    start: date = date(2026, 8, 15),
    end: date = date(2026, 8, 21),
    equipment: str | None = None,
) -> FilterSelection:
    """Build a valid test filter selection."""
    return FilterSelection(
        plant=plant,
        start_date=start,
        end_date=end,
        equipment_id=equipment,
    )


class TestFilterSelection:
    """Validate filter selection behavior."""

    def test_accepts_valid_selection(self) -> None:
        filters = selection(plant="Solar Plant B", equipment="INV-003")

        assert filters.plant == "Solar Plant B"
        assert filters.equipment_id == "INV-003"

    def test_rejects_reversed_dates(self) -> None:
        with pytest.raises(ValueError, match="start_date must not be after end_date"):
            selection(start=date(2026, 8, 22), end=date(2026, 8, 21))

    def test_rejects_invalid_plant(self) -> None:
        with pytest.raises(ValueError, match="Unknown plant"):
            selection(plant="Missing Plant")

    def test_rejects_invalid_equipment(self) -> None:
        with pytest.raises(ValueError, match="Unknown equipment"):
            selection(equipment="INV-999")

    def test_normalizes_stale_and_incomplete_values(self) -> None:
        filters = normalize_filter_selection(
            plant="Retired Plant",
            start_date=None,
            end_date=None,
            equipment="OLD-001",
            today=date(2026, 8, 21),
        )

        assert filters == selection()

    def test_normalizes_reversed_dates(self) -> None:
        filters = normalize_filter_selection(
            plant="Solar Plant B",
            start_date=date(2026, 8, 21),
            end_date=date(2026, 8, 15),
        )

        assert filters.start_date == date(2026, 8, 15)
        assert filters.end_date == date(2026, 8, 21)


def test_forecast_dashboard_uses_actual_forecast_date_window() -> None:
    forecast = pd.DataFrame(
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
        }
    )

    start, end = get_default_forecast_date_range(forecast)

    assert (start, end) == (date(2026, 8, 21), date(2026, 8, 24))


def test_alarm_trend_groups_repeated_timestamps_by_day() -> None:
    data = pd.DataFrame(
        {
            "Time": pd.to_datetime(
                [
                    "2026-08-20 00:00",
                    "2026-08-20 12:00",
                    "2026-08-21 00:00",
                    "2026-08-21 18:00",
                    "2026-08-22 00:00",
                    "2026-08-22 12:00",
                    "2026-08-23 00:00",
                    "2026-08-23 18:00",
                ]
            ),
            "Critical": [1, 2, 3, 1, 2, 1, 3, 2],
            "High": [2, 4, 5, 2, 3, 2, 4, 3],
            "Medium": [3, 5, 7, 4, 5, 4, 6, 5],
        }
    )

    result = prepare_alarm_trend_for_chart(data)

    assert result["Date"].nunique() == 4
    assert result["Critical"].tolist() == [3, 4, 3, 5]


def test_alarm_trend_is_seeded_to_a_week_when_data_is_sparse() -> None:
    data = pd.DataFrame(
        {
            "Time": pd.to_datetime(["2026-08-20 00:00", "2026-08-20 12:00"]),
            "Critical": [1, 2],
            "High": [2, 3],
            "Medium": [3, 4],
        }
    )

    result = prepare_alarm_trend_for_chart(data)

    assert result["Date"].nunique() >= 7
    assert set(result.columns) >= {"Date", "Critical", "High", "Medium"}


class TestDataFrameFilters:
    """Verify relevant fields are filtered without fabricating missing fields."""

    @pytest.fixture
    def records(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "Plant": ["Solar Plant A", "Solar Plant B", "Solar Plant B"],
                "Equipment ID": ["INV-001", "INV-003", "INV-004"],
                "Date": pd.to_datetime(["2026-08-14", "2026-08-15", "2026-08-22"]),
                "Value": [1, 2, 3],
            }
        )

    def test_filters_by_plant(self, records: pd.DataFrame) -> None:
        result = apply_dataframe_filters(
            records,
            selection(
                plant="Solar Plant B",
                start=date(2026, 8, 1),
                end=date(2026, 8, 31),
            ),
        )

        assert result["Plant"].tolist() == ["Solar Plant B", "Solar Plant B"]

    def test_filters_by_equipment(self, records: pd.DataFrame) -> None:
        result = apply_dataframe_filters(
            records,
            selection(
                start=date(2026, 8, 1),
                end=date(2026, 8, 31),
                equipment="INV-003",
            ),
        )

        assert result["Equipment ID"].tolist() == ["INV-003"]

    def test_filters_date_range_inclusively(self, records: pd.DataFrame) -> None:
        result = apply_dataframe_filters(
            records,
            selection(start=date(2026, 8, 15), end=date(2026, 8, 15)),
        )

        assert result["Value"].tolist() == [2]

    def test_leaves_unrelated_dataset_rows_available(self) -> None:
        records = pd.DataFrame({"Category": ["A", "B"], "Value": [1, 2]})

        result = apply_dataframe_filters(
            records,
            selection(plant="Solar Plant D", equipment="INV-005"),
        )

        pd.testing.assert_frame_equal(result, records)

    def test_empty_dataframe_is_safe(self) -> None:
        result = apply_dataframe_filters(pd.DataFrame(columns=["Plant"]), selection())

        assert result.empty
        assert not has_rows(result)
        assert not has_rows(None)

    def test_timezone_aware_and_naive_dates_share_inclusive_semantics(self) -> None:
        records = pd.DataFrame(
            {
                "Timestamp": [
                    "2026-08-15 23:59:59",
                    "2026-08-15T23:59:59+05:00",
                    "2026-08-16 00:00:00",
                ],
                "Value": [1, 2, 3],
            }
        )

        result = apply_dataframe_filters(
            records,
            selection(start=date(2026, 8, 15), end=date(2026, 8, 15)),
        )

        assert result["Value"].tolist() == [1, 2]

    def test_filtering_does_not_mutate_the_source(self, records: pd.DataFrame) -> None:
        original = records.copy(deep=True)

        apply_dataframe_filters(records, selection(plant="Solar Plant B"))

        pd.testing.assert_frame_equal(records, original)


def test_page_contract_scopes_named_frames_and_rejects_unknown_names() -> None:
    records = pd.DataFrame(
        {"Plant": ["Solar Plant A", "Solar Plant B"], "Value": [1, 2]}
    )
    contract = PageDataContract(selection(plant="Solar Plant B"), {"records": records})

    assert contract.scoped("records")["Value"].tolist() == [2]
    with pytest.raises(KeyError, match="Unknown page dataset"):
        contract.scoped("missing")


def test_page_contract_preserves_intentionally_global_data() -> None:
    records = pd.DataFrame(
        {"Plant": ["Solar Plant A", "Solar Plant B"], "Value": [1, 2]}
    )
    contract = PageDataContract(selection(plant="Solar Plant B"), {"records": records})

    result = contract.scoped(
        "records", dimensions=FilterDimensions(plant=False, date=False)
    )

    assert result["Value"].tolist() == [1, 2]


def test_equipment_options_are_constrained_by_selected_plant() -> None:
    records = pd.DataFrame(
        {
            "Plant": ["Solar Plant A", "Solar Plant A", "Solar Plant B"],
            "Equipment ID": ["INV-001", "INV-002", "INV-003"],
        }
    )

    assert equipment_options_for_plant(records, "Solar Plant A") == (
        "All Equipment",
        "INV-001",
        "INV-002",
    )
