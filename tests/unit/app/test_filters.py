"""Tests for shared EOIP filter validation and DataFrame filtering."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from eoip.app.components.filters import FilterSelection, normalize_filter_selection
from eoip.app.data_filters import apply_dataframe_filters, has_rows


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
