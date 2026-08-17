"""Deterministic transformation pipeline for EOIP Phase 3 ETL.

This module applies reusable, dataset-level business transformations after
cleaning and validation. Transformations are explicit, ordered, immutable in
configuration, and non-destructive to source DataFrames.

The transformation layer does not perform ingestion, validation, database
loading, or Prefect orchestration.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final

import pandas as pd

TransformationCallable = Callable[[pd.DataFrame], pd.DataFrame]

DEFAULT_COPY_DEEP: Final[bool] = True


@dataclass(frozen=True, slots=True)
class ColumnExpression:
    """Definition for creating or replacing one derived column."""

    target_column: str
    function: Callable[[pd.DataFrame], pd.Series]

    def __post_init__(self) -> None:
        """Validate expression configuration."""
        if not isinstance(self.target_column, str):
            raise TypeError("target_column must be a string.")

        normalized_target = self.target_column.strip()

        if not normalized_target:
            raise ValueError("target_column cannot be empty.")

        if not callable(self.function):
            raise TypeError("function must be callable.")

        object.__setattr__(
            self,
            "target_column",
            normalized_target,
        )


@dataclass(frozen=True, slots=True)
class TransformationConfig:
    """Configuration for one deterministic dataset transformation."""

    select_columns: tuple[str, ...] = ()
    drop_columns: tuple[str, ...] = ()
    rename_columns: Mapping[str, str] = field(default_factory=dict)
    derived_columns: tuple[ColumnExpression, ...] = ()
    sort_by: tuple[str, ...] = ()
    drop_duplicate_keys: tuple[str, ...] = ()
    reset_index: bool = True

    def __post_init__(self) -> None:
        """Normalize and validate transformation configuration."""
        for field_name in (
            "select_columns",
            "drop_columns",
            "sort_by",
            "drop_duplicate_keys",
        ):
            normalized = _normalize_string_tuple(
                field_name,
                getattr(
                    self,
                    field_name,
                ),
            )

            object.__setattr__(
                self,
                field_name,
                normalized,
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

        if not isinstance(
            self.derived_columns,
            tuple,
        ):
            raise TypeError("derived_columns must be a tuple.")

        for expression in self.derived_columns:
            if not isinstance(
                expression,
                ColumnExpression,
            ):
                raise TypeError(
                    "derived_columns must contain " "ColumnExpression objects."
                )

        if not isinstance(
            self.reset_index,
            bool,
        ):
            raise TypeError("reset_index must be a boolean.")

        selected = set(self.select_columns)

        dropped = set(self.drop_columns)

        overlap = selected & dropped

        if overlap:
            raise ValueError(
                "Columns cannot be configured for both selection "
                f"and dropping: {sorted(overlap)}"
            )


@dataclass(frozen=True, slots=True)
class TransformationResult:
    """Result of one deterministic DataFrame transformation."""

    frame: pd.DataFrame
    rows_before: int
    rows_after: int
    columns_before: tuple[str, ...]
    columns_after: tuple[str, ...]
    changes: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate transformation result metadata."""
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
                getattr(
                    self,
                    field_name,
                ),
                tuple,
            ):
                raise TypeError(f"{field_name} must be a tuple.")


class DataTransformer:
    """Deterministic transformation engine for cleaned ETL data."""

    def __init__(
        self,
        config: TransformationConfig | None = None,
    ) -> None:
        """Create a data transformer."""
        self._config = config if config is not None else TransformationConfig()

        if not isinstance(
            self._config,
            TransformationConfig,
        ):
            raise TypeError("config must be a TransformationConfig.")

    @property
    def config(self) -> TransformationConfig:
        """Return immutable transformation configuration."""
        return self._config

    def transform(
        self,
        frame: pd.DataFrame,
    ) -> TransformationResult:
        """Transform one DataFrame without mutating its source."""
        if not isinstance(
            frame,
            pd.DataFrame,
        ):
            raise TypeError("frame must be a pandas DataFrame.")

        working = frame.copy(deep=DEFAULT_COPY_DEEP)

        rows_before = len(working)

        columns_before = tuple(str(column) for column in working.columns)

        changes: list[str] = []

        working = self._select_columns(
            working,
            changes,
        )

        working = self._drop_columns(
            working,
            changes,
        )

        working = self._rename_columns(
            working,
            changes,
        )

        working = self._apply_derived_columns(
            working,
            changes,
        )

        working = self._drop_duplicates(
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

        return TransformationResult(
            frame=working,
            rows_before=rows_before,
            rows_after=len(working),
            columns_before=columns_before,
            columns_after=columns_after,
            changes=tuple(changes),
        )

    def _select_columns(
        self,
        frame: pd.DataFrame,
        changes: list[str],
    ) -> pd.DataFrame:
        """Select configured columns in deterministic order."""
        if not self._config.select_columns:
            return frame

        missing = [
            column
            for column in self._config.select_columns
            if column not in frame.columns
        ]

        if missing:
            raise KeyError("Cannot select missing columns: " f"{missing}")

        selected = frame.loc[
            :,
            list(self._config.select_columns),
        ].copy(deep=True)

        changes.append("selected_columns")

        return selected

    def _drop_columns(
        self,
        frame: pd.DataFrame,
        changes: list[str],
    ) -> pd.DataFrame:
        """Drop configured columns."""
        if not self._config.drop_columns:
            return frame

        existing = [
            column for column in self._config.drop_columns if column in frame.columns
        ]

        if not existing:
            return frame

        result = frame.drop(columns=existing)

        changes.append("dropped_columns")

        return result

    def _rename_columns(
        self,
        frame: pd.DataFrame,
        changes: list[str],
    ) -> pd.DataFrame:
        """Rename configured columns."""
        if not self._config.rename_columns:
            return frame

        applicable = {
            source: target
            for source, target in self._config.rename_columns.items()
            if source in frame.columns
        }

        if not applicable:
            return frame

        result = frame.rename(columns=applicable)

        if len(result.columns) != len(set(result.columns)):
            raise ValueError("Column renaming produced duplicate column names.")

        changes.append("renamed_columns")

        return result

    def _apply_derived_columns(
        self,
        frame: pd.DataFrame,
        changes: list[str],
    ) -> pd.DataFrame:
        """Create or replace configured derived columns."""
        if not self._config.derived_columns:
            return frame

        for expression in self._config.derived_columns:
            result = expression.function(frame.copy(deep=False))

            if not isinstance(
                result,
                pd.Series,
            ):
                raise TypeError(
                    "Derived column function must return " "a pandas Series."
                )

            if len(result) != len(frame):
                raise ValueError(
                    "Derived column result length must match "
                    "the DataFrame row count."
                )

            if not result.index.equals(frame.index):
                result = result.reindex(frame.index)

            frame[expression.target_column] = result

        changes.append("derived_columns")

        return frame

    def _drop_duplicates(
        self,
        frame: pd.DataFrame,
        changes: list[str],
    ) -> pd.DataFrame:
        """Drop duplicate rows using configured business keys."""
        if not self._config.drop_duplicate_keys:
            return frame

        missing = [
            column
            for column in self._config.drop_duplicate_keys
            if column not in frame.columns
        ]

        if missing:
            raise KeyError("Cannot deduplicate using missing columns: " f"{missing}")

        before = len(frame)

        result = frame.drop_duplicates(
            subset=list(self._config.drop_duplicate_keys),
            keep="first",
        )

        if len(result) != before:
            changes.append("dropped_duplicates")

        return result

    def _sort_rows(
        self,
        frame: pd.DataFrame,
        changes: list[str],
    ) -> pd.DataFrame:
        """Sort rows using configured columns."""
        if not self._config.sort_by:
            return frame

        missing = [
            column for column in self._config.sort_by if column not in frame.columns
        ]

        if missing:
            raise KeyError("Cannot sort by missing columns: " f"{missing}")

        result = frame.sort_values(
            by=list(self._config.sort_by),
            kind="stable",
        )

        changes.append("sorted_rows")

        return result


@dataclass(frozen=True, slots=True)
class TransformationStep:
    """Named custom transformation step."""

    name: str
    function: TransformationCallable

    def __post_init__(self) -> None:
        """Validate custom transformation step."""
        if not isinstance(
            self.name,
            str,
        ):
            raise TypeError("name must be a string.")

        normalized_name = self.name.strip()

        if not normalized_name:
            raise ValueError("name cannot be empty.")

        if not callable(self.function):
            raise TypeError("function must be callable.")

        object.__setattr__(
            self,
            "name",
            normalized_name,
        )


class TransformationPipeline:
    """Ordered pipeline for reusable custom transformations."""

    def __init__(
        self,
        steps: Sequence[TransformationStep] | None = None,
    ) -> None:
        """Create a transformation pipeline."""
        normalized_steps = tuple(steps) if steps is not None else ()

        for step in normalized_steps:
            if not isinstance(
                step,
                TransformationStep,
            ):
                raise TypeError("steps must contain TransformationStep objects.")

        names = [step.name for step in normalized_steps]

        if len(names) != len(set(names)):
            raise ValueError("Transformation step names must be unique.")

        self._steps = normalized_steps

    @property
    def steps(
        self,
    ) -> tuple[
        TransformationStep,
        ...,
    ]:
        """Return ordered transformation steps."""
        return self._steps

    def run(
        self,
        frame: pd.DataFrame,
    ) -> pd.DataFrame:
        """Run custom transformations sequentially."""
        if not isinstance(
            frame,
            pd.DataFrame,
        ):
            raise TypeError("frame must be a pandas DataFrame.")

        working = frame.copy(deep=True)

        for step in self._steps:
            result = step.function(working.copy(deep=True))

            if not isinstance(
                result,
                pd.DataFrame,
            ):
                raise TypeError(
                    f"Transformation step '{step.name}' "
                    "must return a pandas DataFrame."
                )

            working = result.copy(deep=True)

        return working


def transform_dataframe(
    frame: pd.DataFrame,
    config: TransformationConfig | None = None,
) -> TransformationResult:
    """Transform one DataFrame using configured deterministic rules."""
    return DataTransformer(config).transform(frame)


def transform_datasets(
    datasets: Mapping[
        str,
        pd.DataFrame,
    ],
    configs: (
        Mapping[
            str,
            TransformationConfig,
        ]
        | None
    ) = None,
) -> dict[
    str,
    TransformationResult,
]:
    """Transform multiple datasets in deterministic name order."""
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
        TransformationResult,
    ] = {}

    for dataset_name in sorted(datasets):
        if not isinstance(
            dataset_name,
            str,
        ):
            raise TypeError("dataset names must be strings.")

        config = configs.get(dataset_name) if configs is not None else None

        results[dataset_name] = transform_dataframe(
            datasets[dataset_name],
            config,
        )

    return results


def apply_pipeline(
    frame: pd.DataFrame,
    steps: Iterable[TransformationStep],
) -> pd.DataFrame:
    """Apply an ordered sequence of custom transformations."""
    return TransformationPipeline(tuple(steps)).run(frame)


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
    "DEFAULT_COPY_DEEP",
    "ColumnExpression",
    "DataTransformer",
    "TransformationConfig",
    "TransformationPipeline",
    "TransformationResult",
    "TransformationStep",
    "apply_pipeline",
    "transform_dataframe",
    "transform_datasets",
]
