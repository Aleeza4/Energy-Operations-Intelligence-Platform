"""Cleaning and standardization utilities for EOIP Phase 3 ETL pipelines.

This module performs deterministic, non-destructive DataFrame cleaning before
business transformations. It standardizes column names, string values,
timestamps, numeric values, missing-value representations, and row ordering.

The cleaning layer does not perform dataset-specific business logic, database
loading, or Prefect orchestration.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Final

import pandas as pd

DEFAULT_NULL_TOKENS: Final[tuple[str, ...]] = (
    "",
    "na",
    "n/a",
    "nan",
    "none",
    "null",
)


@dataclass(frozen=True, slots=True)
class CleaningConfig:
    """Configuration controlling deterministic ETL cleaning."""

    strip_column_names: bool = True
    lowercase_column_names: bool = True
    normalize_column_separators: bool = True
    strip_string_values: bool = True
    normalize_empty_strings: bool = True
    null_tokens: tuple[str, ...] = DEFAULT_NULL_TOKENS
    timestamp_columns: tuple[str, ...] = ()
    numeric_columns: tuple[str, ...] = ()
    uppercase_columns: tuple[str, ...] = ()
    lowercase_columns: tuple[str, ...] = ()
    rename_columns: Mapping[str, str] = field(default_factory=dict)
    sort_by: tuple[str, ...] = ()
    reset_index: bool = True

    def __post_init__(self) -> None:
        """Normalize and validate cleaning configuration."""
        for field_name in (
            "strip_column_names",
            "lowercase_column_names",
            "normalize_column_separators",
            "strip_string_values",
            "normalize_empty_strings",
            "reset_index",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be a boolean.")

        normalized_null_tokens = _normalize_null_tokens(self.null_tokens)

        object.__setattr__(
            self,
            "null_tokens",
            normalized_null_tokens,
        )

        for field_name in (
            "timestamp_columns",
            "numeric_columns",
            "uppercase_columns",
            "lowercase_columns",
            "sort_by",
        ):
            normalized = _normalize_string_tuple(
                field_name,
                getattr(self, field_name),
            )

            object.__setattr__(
                self,
                field_name,
                normalized,
            )

        overlap = set(self.uppercase_columns) & set(self.lowercase_columns)

        if overlap:
            raise ValueError(
                "Columns cannot be configured for both uppercase "
                f"and lowercase normalization: {sorted(overlap)}"
            )

        if not isinstance(
            self.rename_columns,
            Mapping,
        ):
            raise TypeError("rename_columns must be a mapping.")

        normalized_renames: dict[str, str] = {}

        for source, target in self.rename_columns.items():
            if not isinstance(source, str):
                raise TypeError("rename_columns keys must be strings.")

            if not isinstance(target, str):
                raise TypeError("rename_columns values must be strings.")

            normalized_source = source.strip()
            normalized_target = target.strip()

            if not normalized_source:
                raise ValueError("rename_columns keys cannot be empty.")

            if not normalized_target:
                raise ValueError("rename_columns values cannot be empty.")

            normalized_renames[normalized_source] = normalized_target

        object.__setattr__(
            self,
            "rename_columns",
            MappingProxyType(dict(sorted(normalized_renames.items()))),
        )


@dataclass(frozen=True, slots=True)
class CleaningResult:
    """Result of deterministic DataFrame cleaning."""

    frame: pd.DataFrame
    rows_before: int
    rows_after: int
    columns_before: tuple[str, ...]
    columns_after: tuple[str, ...]
    changes: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate cleaning result metadata."""
        if not isinstance(
            self.frame,
            pd.DataFrame,
        ):
            raise TypeError("frame must be a pandas DataFrame.")

        _validate_non_negative_int(
            "rows_before",
            self.rows_before,
        )

        _validate_non_negative_int(
            "rows_after",
            self.rows_after,
        )

        for field_name in (
            "columns_before",
            "columns_after",
            "changes",
        ):
            if not isinstance(
                getattr(self, field_name),
                tuple,
            ):
                raise TypeError(f"{field_name} must be a tuple.")


class DataCleaner:
    """Deterministic cleaning engine for ingested DataFrames."""

    def __init__(
        self,
        config: CleaningConfig | None = None,
    ) -> None:
        """Create a data cleaner."""
        self._config = config if config is not None else CleaningConfig()

        if not isinstance(
            self._config,
            CleaningConfig,
        ):
            raise TypeError("config must be a CleaningConfig.")

    @property
    def config(self) -> CleaningConfig:
        """Return immutable cleaning configuration."""
        return self._config

    def clean(
        self,
        frame: pd.DataFrame,
    ) -> CleaningResult:
        """Clean one DataFrame without mutating the source."""
        if not isinstance(
            frame,
            pd.DataFrame,
        ):
            raise TypeError("frame must be a pandas DataFrame.")

        working = frame.copy(deep=True)

        rows_before = len(working)

        columns_before = tuple(str(column) for column in working.columns)

        changes: list[str] = []

        working = self._standardize_columns(
            working,
            changes,
        )

        working = self._apply_explicit_renames(
            working,
            changes,
        )

        working = self._strip_string_values(
            working,
            changes,
        )

        working = self._normalize_null_tokens(
            working,
            changes,
        )

        working = self._normalize_case_columns(
            working,
            changes,
        )

        working = self._normalize_timestamps(
            working,
            changes,
        )

        working = self._normalize_numeric_columns(
            working,
            changes,
        )

        working = self._sort_rows(
            working,
            changes,
        )

        if self._config.reset_index:
            working = working.reset_index(drop=True)
            changes.append("reset_index")

        columns_after = tuple(str(column) for column in working.columns)

        return CleaningResult(
            frame=working,
            rows_before=rows_before,
            rows_after=len(working),
            columns_before=columns_before,
            columns_after=columns_after,
            changes=tuple(changes),
        )

    def _standardize_columns(
        self,
        frame: pd.DataFrame,
        changes: list[str],
    ) -> pd.DataFrame:
        """Standardize column names."""
        if not (
            self._config.strip_column_names
            or self._config.lowercase_column_names
            or self._config.normalize_column_separators
        ):
            return frame

        normalized: list[str] = []

        for column in frame.columns:
            value = str(column)

            if self._config.strip_column_names:
                value = value.strip()

            if self._config.lowercase_column_names:
                value = value.lower()

            if self._config.normalize_column_separators:
                value = re.sub(
                    r"[\s\-]+",
                    "_",
                    value,
                )
                value = re.sub(
                    r"_+",
                    "_",
                    value,
                )
                value = value.strip("_")

            normalized.append(value)

        if len(normalized) != len(set(normalized)):
            raise ValueError("Column normalization produced duplicate column names.")

        original_columns = tuple(str(column) for column in frame.columns)

        if tuple(normalized) != original_columns:
            frame = frame.copy(deep=True)
            frame.columns = normalized
            changes.append("standardized_columns")

        return frame

    def _apply_explicit_renames(
        self,
        frame: pd.DataFrame,
        changes: list[str],
    ) -> pd.DataFrame:
        """Apply configured explicit column renames."""
        if not self._config.rename_columns:
            return frame

        available_renames = {
            source: target
            for source, target in self._config.rename_columns.items()
            if source in frame.columns
        }

        if not available_renames:
            return frame

        renamed = frame.rename(columns=available_renames)

        if len(renamed.columns) != len(set(renamed.columns)):
            raise ValueError("Explicit column renaming produced duplicate columns.")

        changes.append("renamed_columns")

        return renamed

    def _strip_string_values(
        self,
        frame: pd.DataFrame,
        changes: list[str],
    ) -> pd.DataFrame:
        """Trim leading and trailing whitespace from string values."""
        if not self._config.strip_string_values:
            return frame

        changed = False

        for column in frame.columns:
            series = frame[column]

            if not (
                pd.api.types.is_object_dtype(series.dtype)
                or pd.api.types.is_string_dtype(series.dtype)
            ):
                continue

            original = series.copy(deep=True)

            frame[column] = series.map(_strip_if_string)

            if not frame[column].equals(original):
                changed = True

        if changed:
            changes.append("stripped_string_values")

        return frame

    def _normalize_null_tokens(
        self,
        frame: pd.DataFrame,
        changes: list[str],
    ) -> pd.DataFrame:
        """Normalize configured string null tokens to pandas NA."""
        if not self._config.normalize_empty_strings:
            return frame

        tokens = {token.casefold() for token in self._config.null_tokens}

        changed = False

        for column in frame.columns:
            series = frame[column]

            if not (
                pd.api.types.is_object_dtype(series.dtype)
                or pd.api.types.is_string_dtype(series.dtype)
            ):
                continue

            mask = series.map(
                lambda value: (isinstance(value, str) and value.casefold() in tokens)
            )

            if not bool(mask.any()):
                continue

            frame.loc[
                mask,
                column,
            ] = pd.NA

            changed = True

        if changed:
            changes.append("normalized_null_tokens")

        return frame

    def _normalize_case_columns(
        self,
        frame: pd.DataFrame,
        changes: list[str],
    ) -> pd.DataFrame:
        """Normalize configured string columns to upper/lower case."""
        uppercase_changed = False
        lowercase_changed = False

        for column in self._config.uppercase_columns:
            if column not in frame.columns:
                continue

            original = frame[column].copy(deep=True)

            frame[column] = frame[column].map(
                lambda value: (
                    value.upper()
                    if isinstance(
                        value,
                        str,
                    )
                    else value
                )
            )

            if not frame[column].equals(original):
                uppercase_changed = True

        for column in self._config.lowercase_columns:
            if column not in frame.columns:
                continue

            original = frame[column].copy(deep=True)

            frame[column] = frame[column].map(
                lambda value: (
                    value.lower()
                    if isinstance(
                        value,
                        str,
                    )
                    else value
                )
            )

            if not frame[column].equals(original):
                lowercase_changed = True

        if uppercase_changed:
            changes.append("uppercased_columns")

        if lowercase_changed:
            changes.append("lowercased_columns")

        return frame

    def _normalize_timestamps(
        self,
        frame: pd.DataFrame,
        changes: list[str],
    ) -> pd.DataFrame:
        """Convert configured timestamp columns to UTC datetimes."""
        changed = False

        for column in self._config.timestamp_columns:
            if column not in frame.columns:
                continue

            original = frame[column]

            converted = pd.to_datetime(
                original,
                errors="coerce",
                utc=True,
            )

            if not converted.equals(original):
                frame[column] = converted
                changed = True

        if changed:
            changes.append("normalized_timestamps")

        return frame

    def _normalize_numeric_columns(
        self,
        frame: pd.DataFrame,
        changes: list[str],
    ) -> pd.DataFrame:
        """Convert configured numeric columns using pandas coercion."""
        changed = False

        for column in self._config.numeric_columns:
            if column not in frame.columns:
                continue

            original = frame[column]

            converted = pd.to_numeric(
                original,
                errors="coerce",
            )

            if not converted.equals(original):
                frame[column] = converted
                changed = True

        if changed:
            changes.append("normalized_numeric_columns")

        return frame

    def _sort_rows(
        self,
        frame: pd.DataFrame,
        changes: list[str],
    ) -> pd.DataFrame:
        """Sort rows by configured columns."""
        if not self._config.sort_by:
            return frame

        missing = [
            column for column in self._config.sort_by if column not in frame.columns
        ]

        if missing:
            raise KeyError("Cannot sort by missing columns: " f"{missing}")

        sorted_frame = frame.sort_values(
            by=list(self._config.sort_by),
            kind="stable",
        )

        changes.append("sorted_rows")

        return sorted_frame


def clean_dataframe(
    frame: pd.DataFrame,
    config: CleaningConfig | None = None,
) -> CleaningResult:
    """Clean one DataFrame using configured standardization rules."""
    return DataCleaner(config).clean(frame)


def clean_datasets(
    datasets: Mapping[
        str,
        pd.DataFrame,
    ],
    configs: (
        Mapping[
            str,
            CleaningConfig,
        ]
        | None
    ) = None,
) -> dict[
    str,
    CleaningResult,
]:
    """Clean multiple datasets in deterministic name order."""
    if not isinstance(
        datasets,
        Mapping,
    ):
        raise TypeError("datasets must be a mapping.")

    if configs is not None and not isinstance(
        configs,
        Mapping,
    ):
        raise TypeError("configs must be a mapping or None.")

    results: dict[
        str,
        CleaningResult,
    ] = {}

    for dataset_name in sorted(datasets):
        if not isinstance(
            dataset_name,
            str,
        ):
            raise TypeError("dataset names must be strings.")

        frame = datasets[dataset_name]

        config = configs.get(dataset_name) if configs is not None else None

        results[dataset_name] = clean_dataframe(
            frame,
            config,
        )

    return results


def _strip_if_string(
    value: Any,
) -> Any:
    """Strip a value only when it is a string."""
    if isinstance(
        value,
        str,
    ):
        return value.strip()

    return value


def _normalize_null_tokens(
    values: Iterable[str],
) -> tuple[str, ...]:
    """Normalize string tokens representing null values.

    Empty strings are intentionally allowed because the default cleaning
    policy treats empty strings as missing values.
    """
    if isinstance(
        values,
        str,
    ):
        raise TypeError("null_tokens must be an iterable of strings, not a string.")

    try:
        items = tuple(values)
    except TypeError as exc:
        raise TypeError("null_tokens must be iterable.") from exc

    normalized: list[str] = []

    for value in items:
        if not isinstance(
            value,
            str,
        ):
            raise TypeError("null_tokens must contain strings.")

        normalized.append(value.strip().casefold())

    if len(normalized) != len(set(normalized)):
        raise ValueError("null_tokens cannot contain duplicate values.")

    return tuple(normalized)


def _normalize_string_tuple(
    field_name: str,
    values: Iterable[str],
) -> tuple[str, ...]:
    """Normalize a sequence of unique non-empty strings."""
    if isinstance(
        values,
        str,
    ):
        raise TypeError(f"{field_name} must be an iterable of strings, not a string.")

    try:
        items = tuple(values)
    except TypeError as exc:
        raise TypeError(f"{field_name} must be iterable.") from exc

    normalized: list[str] = []

    for value in items:
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(f"{field_name} must contain strings.")

        item = value.strip()

        if not item:
            raise ValueError(f"{field_name} cannot contain empty strings.")

        normalized.append(item)

    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} cannot contain duplicate values.")

    return tuple(normalized)


def _validate_non_negative_int(
    name: str,
    value: int,
) -> None:
    """Validate a non-negative integer."""
    if isinstance(
        value,
        bool,
    ) or not isinstance(
        value,
        int,
    ):
        raise TypeError(f"{name} must be an integer.")

    if value < 0:
        raise ValueError(f"{name} must be greater than or equal to zero.")


__all__ = [
    "DEFAULT_NULL_TOKENS",
    "CleaningConfig",
    "CleaningResult",
    "DataCleaner",
    "clean_dataframe",
    "clean_datasets",
]
