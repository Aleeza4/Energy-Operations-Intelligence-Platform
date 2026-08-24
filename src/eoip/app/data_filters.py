"""Pure DataFrame filtering helpers for EOIP dashboards."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from eoip.app.components.filters import FilterSelection

PLANT_COLUMNS: tuple[str, ...] = ("Plant", "plant", "plant_name")
EQUIPMENT_COLUMNS: tuple[str, ...] = (
    "Equipment ID",
    "Equipment",
    "equipment_id",
)
DATE_COLUMNS: tuple[str, ...] = ("Date", "Time", "Timestamp", "timestamp")


def first_matching_column(
    dataframe: pd.DataFrame,
    candidates: Sequence[str],
) -> str | None:
    """Return the first candidate column present in a DataFrame."""
    return next((column for column in candidates if column in dataframe.columns), None)


def apply_dataframe_filters(
    dataframe: pd.DataFrame,
    filters: FilterSelection,
    *,
    plant_columns: Sequence[str] = PLANT_COLUMNS,
    equipment_columns: Sequence[str] = EQUIPMENT_COLUMNS,
    date_columns: Sequence[str] = DATE_COLUMNS,
) -> pd.DataFrame:
    """Apply relevant EOIP filters when matching fields are available."""
    if dataframe.empty:
        return dataframe.copy()

    mask = pd.Series(True, index=dataframe.index, dtype=bool)

    plant_column = first_matching_column(dataframe, plant_columns)
    if plant_column is not None and filters.plant != "All Plants":
        mask &= dataframe[plant_column].astype("string").eq(filters.plant)

    equipment_column = first_matching_column(dataframe, equipment_columns)
    if equipment_column is not None and filters.equipment_id is not None:
        mask &= dataframe[equipment_column].astype("string").eq(filters.equipment_id)

    date_column = first_matching_column(dataframe, date_columns)
    if date_column is not None:
        dates = pd.to_datetime(dataframe[date_column], errors="coerce")
        start = pd.Timestamp(filters.start_date)
        end = pd.Timestamp(filters.end_date) + pd.Timedelta(days=1)
        mask &= dates.ge(start) & dates.lt(end)

    return dataframe.loc[mask].copy()


def has_rows(dataframe: pd.DataFrame | None) -> bool:
    """Return whether a DataFrame exists and contains at least one row."""
    return dataframe is not None and not dataframe.empty
