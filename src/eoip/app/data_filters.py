"""Pure DataFrame filtering helpers for EOIP dashboards."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import pandas as pd

from eoip.app.components.filters import FilterSelection

PLANT_COLUMNS: tuple[str, ...] = ("Plant", "plant", "plant_name")
EQUIPMENT_COLUMNS: tuple[str, ...] = (
    "Equipment ID",
    "Equipment",
    "equipment_id",
)
DATE_COLUMNS: tuple[str, ...] = ("Date", "Time", "Timestamp", "timestamp")


@dataclass(frozen=True, slots=True)
class FilterDimensions:
    """Dimensions a page dataset explicitly supports."""

    plant: bool = True
    equipment: bool = True
    date: bool = True


DEFAULT_FILTER_DIMENSIONS = FilterDimensions()


@dataclass(frozen=True, slots=True)
class PageDataContract:
    """Immutable filtered views used by every renderer on one page."""

    filters: FilterSelection
    frames: Mapping[str, pd.DataFrame]

    def scoped(
        self,
        name: str,
        *,
        dimensions: FilterDimensions = DEFAULT_FILTER_DIMENSIONS,
    ) -> pd.DataFrame:
        """Return a fresh, consistently scoped view of a named source frame."""
        if name not in self.frames:
            raise KeyError(f"Unknown page dataset: {name}")
        return apply_dataframe_filters(
            self.frames[name],
            self.filters,
            plant_columns=PLANT_COLUMNS if dimensions.plant else (),
            equipment_columns=EQUIPMENT_COLUMNS if dimensions.equipment else (),
            date_columns=DATE_COLUMNS if dimensions.date else (),
        )


def equipment_options_for_plant(
    dataframe: pd.DataFrame,
    plant: str,
    *,
    plant_columns: Sequence[str] = PLANT_COLUMNS,
    equipment_columns: Sequence[str] = EQUIPMENT_COLUMNS,
) -> tuple[str, ...]:
    """Return valid equipment choices for a selected plant without mutation."""
    plant_column = first_matching_column(dataframe, plant_columns)
    equipment_column = first_matching_column(dataframe, equipment_columns)
    if equipment_column is None:
        return ("All Equipment",)

    scoped = dataframe
    if plant_column is not None and plant != "All Plants":
        scoped = scoped.loc[scoped[plant_column].astype("string").eq(plant)]

    equipment = tuple(
        sorted(
            value
            for value in scoped[equipment_column].dropna().astype(str).unique()
            if value.strip()
        )
    )
    return ("All Equipment", *equipment)


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
        dates = pd.to_datetime(
            dataframe[date_column], errors="coerce", utc=True, format="mixed"
        )
        start = pd.Timestamp(filters.start_date, tz="UTC")
        end = pd.Timestamp(filters.end_date, tz="UTC") + pd.Timedelta(days=1)
        mask &= dates.ge(start) & dates.lt(end)

    return dataframe.loc[mask].copy()


def has_rows(dataframe: pd.DataFrame | None) -> bool:
    """Return whether a DataFrame exists and contains at least one row."""
    return dataframe is not None and not dataframe.empty
