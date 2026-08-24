"""Incremental-processing utilities for EOIP Phase 3 ETL pipelines.

This module provides deterministic watermark handling, checkpoint metadata,
incremental row filtering, and full-vs-incremental load decisions.

It deliberately does not perform source ingestion, business validation,
database persistence, or Prefect orchestration.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Final

import pandas as pd

from eoip.etl.config import ETLConfig, LoadMode

DEFAULT_WATERMARK_COLUMN: Final[str] = "timestamp"
DEFAULT_PRIMARY_KEY: Final[tuple[str, ...]] = ()
DEFAULT_CHECKPOINT_VERSION: Final[str] = "1.0"


class IncrementalDecision(StrEnum):
    """Outcome of an incremental-processing decision."""

    FULL_LOAD = "full_load"
    INCREMENTAL_LOAD = "incremental_load"
    NO_NEW_ROWS = "no_new_rows"


@dataclass(frozen=True, slots=True)
class IncrementalConfig:
    """Configuration controlling dataset-level incremental processing."""

    watermark_column: str = DEFAULT_WATERMARK_COLUMN
    primary_key: tuple[str, ...] = DEFAULT_PRIMARY_KEY
    inclusive_watermark: bool = False
    drop_duplicate_keys: bool = True
    sort_output: bool = True
    reset_index: bool = True

    def __post_init__(self) -> None:
        """Normalize and validate incremental configuration."""
        if not isinstance(self.watermark_column, str):
            raise TypeError("watermark_column must be a string.")

        normalized_watermark = self.watermark_column.strip()

        if not normalized_watermark:
            raise ValueError("watermark_column cannot be empty.")

        object.__setattr__(
            self,
            "watermark_column",
            normalized_watermark,
        )

        normalized_key = _normalize_string_tuple(
            "primary_key",
            self.primary_key,
        )

        object.__setattr__(
            self,
            "primary_key",
            normalized_key,
        )

        for field_name in (
            "inclusive_watermark",
            "drop_duplicate_keys",
            "sort_output",
            "reset_index",
        ):
            if not isinstance(
                getattr(self, field_name),
                bool,
            ):
                raise TypeError(f"{field_name} must be a boolean.")


@dataclass(frozen=True, slots=True)
class DatasetCheckpoint:
    """Persistent checkpoint metadata for one ETL dataset."""

    dataset_name: str
    watermark_column: str
    watermark_value: pd.Timestamp | None = None
    processed_rows: int = 0
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: str = DEFAULT_CHECKPOINT_VERSION
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normalize and validate checkpoint metadata."""
        dataset_name = _normalize_non_empty_string(
            "dataset_name",
            self.dataset_name,
        )
        watermark_column = _normalize_non_empty_string(
            "watermark_column",
            self.watermark_column,
        )
        version = _normalize_non_empty_string(
            "version",
            self.version,
        )

        object.__setattr__(
            self,
            "dataset_name",
            dataset_name,
        )
        object.__setattr__(
            self,
            "watermark_column",
            watermark_column,
        )
        object.__setattr__(
            self,
            "version",
            version,
        )

        if self.watermark_value is not None:
            normalized_watermark = _normalize_timestamp(self.watermark_value)

            object.__setattr__(
                self,
                "watermark_value",
                normalized_watermark,
            )

        _validate_non_negative_int(
            "processed_rows",
            self.processed_rows,
        )

        if not isinstance(
            self.updated_at,
            datetime,
        ):
            raise TypeError("updated_at must be a datetime.")

        updated_at = self.updated_at

        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
        else:
            updated_at = updated_at.astimezone(UTC)

        object.__setattr__(
            self,
            "updated_at",
            updated_at,
        )

        if not isinstance(
            self.metadata,
            Mapping,
        ):
            raise TypeError("metadata must be a mapping.")

        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(
                dict(
                    sorted(
                        self.metadata.items(),
                        key=lambda item: str(item[0]),
                    )
                )
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return serialization-ready checkpoint metadata."""
        return {
            "dataset_name": self.dataset_name,
            "watermark_column": self.watermark_column,
            "watermark_value": (
                self.watermark_value.isoformat()
                if self.watermark_value is not None
                else None
            ),
            "processed_rows": self.processed_rows,
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
    ) -> DatasetCheckpoint:
        """Build a checkpoint from a serialized mapping."""
        if not isinstance(
            value,
            Mapping,
        ):
            raise TypeError("value must be a mapping.")

        watermark_raw = value.get("watermark_value")

        updated_at_raw = value.get("updated_at")

        if updated_at_raw is None:
            updated_at = datetime.now(UTC)
        else:
            updated_at_timestamp = pd.Timestamp(updated_at_raw)

            if updated_at_timestamp.tzinfo is None:
                updated_at_timestamp = updated_at_timestamp.tz_localize("UTC")
            else:
                updated_at_timestamp = updated_at_timestamp.tz_convert("UTC")

            updated_at = updated_at_timestamp.to_pydatetime()

        return cls(
            dataset_name=value["dataset_name"],
            watermark_column=value["watermark_column"],
            watermark_value=(
                _normalize_timestamp(watermark_raw)
                if watermark_raw is not None
                else None
            ),
            processed_rows=int(
                value.get(
                    "processed_rows",
                    0,
                )
            ),
            updated_at=updated_at,
            version=str(
                value.get(
                    "version",
                    DEFAULT_CHECKPOINT_VERSION,
                )
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )


@dataclass(frozen=True, slots=True)
class IncrementalResult:
    """Result of applying full or incremental row selection."""

    dataset_name: str
    frame: pd.DataFrame
    decision: IncrementalDecision
    input_rows: int
    output_rows: int
    previous_watermark: pd.Timestamp | None
    new_watermark: pd.Timestamp | None
    checkpoint: DatasetCheckpoint

    def __post_init__(self) -> None:
        """Validate incremental-processing result metadata."""
        if not isinstance(
            self.dataset_name,
            str,
        ):
            raise TypeError("dataset_name must be a string.")

        if not self.dataset_name.strip():
            raise ValueError("dataset_name cannot be empty.")

        if not isinstance(
            self.frame,
            pd.DataFrame,
        ):
            raise TypeError("frame must be a pandas DataFrame.")

        if not isinstance(
            self.decision,
            IncrementalDecision,
        ):
            raise TypeError("decision must be an IncrementalDecision.")

        _validate_non_negative_int(
            "input_rows",
            self.input_rows,
        )
        _validate_non_negative_int(
            "output_rows",
            self.output_rows,
        )

        if not isinstance(
            self.checkpoint,
            DatasetCheckpoint,
        ):
            raise TypeError("checkpoint must be a DatasetCheckpoint.")

    @property
    def has_rows(self) -> bool:
        """Return whether this result contains rows to process."""
        return self.output_rows > 0


class IncrementalProcessor:
    """Deterministic full/incremental row selector."""

    def __init__(
        self,
        etl_config: ETLConfig,
        config: IncrementalConfig | None = None,
    ) -> None:
        """Create an incremental processor."""
        if not isinstance(
            etl_config,
            ETLConfig,
        ):
            raise TypeError("etl_config must be an ETLConfig.")

        self._etl_config = etl_config
        self._config = config if config is not None else IncrementalConfig()

        if not isinstance(
            self._config,
            IncrementalConfig,
        ):
            raise TypeError("config must be an IncrementalConfig.")

    @property
    def etl_config(self) -> ETLConfig:
        """Return the immutable ETL configuration."""
        return self._etl_config

    @property
    def config(self) -> IncrementalConfig:
        """Return the immutable incremental configuration."""
        return self._config

    def process(
        self,
        dataset_name: str,
        frame: pd.DataFrame,
        checkpoint: DatasetCheckpoint | None = None,
    ) -> IncrementalResult:
        """Apply full or incremental selection to one DataFrame."""
        normalized_name = _normalize_non_empty_string(
            "dataset_name",
            dataset_name,
        )

        if not isinstance(
            frame,
            pd.DataFrame,
        ):
            raise TypeError("frame must be a pandas DataFrame.")

        if checkpoint is not None:
            if not isinstance(
                checkpoint,
                DatasetCheckpoint,
            ):
                raise TypeError("checkpoint must be a DatasetCheckpoint or None.")

            if checkpoint.dataset_name != normalized_name:
                raise ValueError(
                    "checkpoint dataset_name does not match "
                    f"requested dataset: {normalized_name}"
                )

            if checkpoint.watermark_column != self._config.watermark_column:
                raise ValueError(
                    "checkpoint watermark_column does not match "
                    "incremental configuration."
                )

        working = frame.copy(deep=True)

        input_rows = len(working)

        watermark_column = self._config.watermark_column

        if watermark_column not in working.columns:
            raise KeyError(
                "Watermark column is missing from dataset: " f"{watermark_column}"
            )

        working[watermark_column] = pd.to_datetime(
            working[watermark_column],
            errors="coerce",
            utc=True,
        )

        invalid_watermarks = working[watermark_column].isna()

        if invalid_watermarks.any():
            raise ValueError("Watermark column contains null or unparseable values.")

        previous_watermark = (
            checkpoint.watermark_value if checkpoint is not None else None
        )

        load_mode = self._etl_config.load_mode

        if load_mode is LoadMode.FULL:
            selected = working
            decision = IncrementalDecision.FULL_LOAD
        elif load_mode is LoadMode.INCREMENTAL:
            if previous_watermark is None:
                selected = working
            else:
                selected = self._filter_incremental_rows(
                    working,
                    previous_watermark,
                )

            decision = (
                IncrementalDecision.INCREMENTAL_LOAD
                if not selected.empty
                else IncrementalDecision.NO_NEW_ROWS
            )
        else:
            raise ValueError(f"Unsupported load mode: {load_mode}")

        selected = self._deduplicate(selected)

        selected = self._sort(selected)

        if self._config.reset_index:
            selected = selected.reset_index(drop=True)

        new_watermark = _maximum_watermark(
            selected,
            watermark_column,
            fallback=previous_watermark,
        )

        processed_rows = (
            checkpoint.processed_rows if checkpoint is not None else 0
        ) + len(selected)

        new_checkpoint = DatasetCheckpoint(
            dataset_name=normalized_name,
            watermark_column=watermark_column,
            watermark_value=new_watermark,
            processed_rows=processed_rows,
        )

        return IncrementalResult(
            dataset_name=normalized_name,
            frame=selected,
            decision=decision,
            input_rows=input_rows,
            output_rows=len(selected),
            previous_watermark=previous_watermark,
            new_watermark=new_watermark,
            checkpoint=new_checkpoint,
        )

    def _filter_incremental_rows(
        self,
        frame: pd.DataFrame,
        previous_watermark: pd.Timestamp,
    ) -> pd.DataFrame:
        """Filter rows against the previous watermark."""
        column = self._config.watermark_column

        if self._config.inclusive_watermark:
            mask = frame[column] >= previous_watermark
        else:
            mask = frame[column] > previous_watermark

        return frame.loc[mask].copy(deep=True)

    def _deduplicate(
        self,
        frame: pd.DataFrame,
    ) -> pd.DataFrame:
        """Remove duplicates using configured business keys."""
        if not self._config.drop_duplicate_keys or not self._config.primary_key:
            return frame

        missing = [
            column for column in self._config.primary_key if column not in frame.columns
        ]

        if missing:
            raise KeyError(
                "Primary-key columns are missing from dataset: " f"{missing}"
            )

        return frame.drop_duplicates(
            subset=list(self._config.primary_key),
            keep="last",
        )

    def _sort(
        self,
        frame: pd.DataFrame,
    ) -> pd.DataFrame:
        """Sort output deterministically."""
        if not self._config.sort_output:
            return frame

        sort_columns = [self._config.watermark_column]

        for column in self._config.primary_key:
            if column not in sort_columns:
                sort_columns.append(column)

        missing = [column for column in sort_columns if column not in frame.columns]

        if missing:
            raise KeyError(
                "Cannot sort incremental output; missing columns: " f"{missing}"
            )

        return frame.sort_values(
            by=sort_columns,
            kind="stable",
        )


def process_incremental(
    etl_config: ETLConfig,
    dataset_name: str,
    frame: pd.DataFrame,
    checkpoint: DatasetCheckpoint | None = None,
    *,
    config: IncrementalConfig | None = None,
) -> IncrementalResult:
    """Process one dataset using full/incremental ETL semantics."""
    return IncrementalProcessor(
        etl_config,
        config,
    ).process(
        dataset_name,
        frame,
        checkpoint,
    )


def process_incremental_datasets(
    etl_config: ETLConfig,
    datasets: Mapping[
        str,
        pd.DataFrame,
    ],
    checkpoints: (
        Mapping[
            str,
            DatasetCheckpoint,
        ]
        | None
    ) = None,
    configs: (
        Mapping[
            str,
            IncrementalConfig,
        ]
        | None
    ) = None,
) -> dict[
    str,
    IncrementalResult,
]:
    """Process multiple datasets in deterministic name order."""
    if not isinstance(
        etl_config,
        ETLConfig,
    ):
        raise TypeError("etl_config must be an ETLConfig.")

    if not isinstance(
        datasets,
        Mapping,
    ):
        raise TypeError("datasets must be a mapping.")

    if checkpoints is not None and not isinstance(
        checkpoints,
        Mapping,
    ):
        raise TypeError("checkpoints must be a mapping or None.")

    if configs is not None and not isinstance(
        configs,
        Mapping,
    ):
        raise TypeError("configs must be a mapping or None.")

    results: dict[
        str,
        IncrementalResult,
    ] = {}

    for dataset_name in sorted(datasets):
        config = configs.get(dataset_name) if configs is not None else None

        checkpoint = checkpoints.get(dataset_name) if checkpoints is not None else None

        results[dataset_name] = process_incremental(
            etl_config,
            dataset_name,
            datasets[dataset_name],
            checkpoint,
            config=config,
        )

    return results


def _maximum_watermark(
    frame: pd.DataFrame,
    watermark_column: str,
    *,
    fallback: pd.Timestamp | None,
) -> pd.Timestamp | None:
    """Return the maximum UTC watermark for a processed frame."""
    if frame.empty:
        return fallback

    maximum = frame[watermark_column].max()

    if pd.isna(maximum):
        return fallback

    return _normalize_timestamp(maximum)


def _normalize_timestamp(
    value: Any,
) -> pd.Timestamp:
    """Normalize one timestamp-like value to UTC."""
    timestamp = pd.Timestamp(value)

    if pd.isna(timestamp):
        raise ValueError("timestamp cannot be NaT.")

    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")

    return timestamp


def _normalize_non_empty_string(
    name: str,
    value: str,
) -> str:
    """Normalize one required string."""
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(f"{name} must be a string.")

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{name} cannot be empty.")

    return normalized


def _normalize_string_tuple(
    field_name: str,
    values: tuple[str, ...],
) -> tuple[str, ...]:
    """Normalize a tuple of unique non-empty strings."""
    if not isinstance(
        values,
        tuple,
    ):
        raise TypeError(f"{field_name} must be a tuple.")

    normalized: list[str] = []

    for value in values:
        normalized.append(
            _normalize_non_empty_string(
                field_name,
                value,
            )
        )

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
    "DEFAULT_CHECKPOINT_VERSION",
    "DEFAULT_PRIMARY_KEY",
    "DEFAULT_WATERMARK_COLUMN",
    "DatasetCheckpoint",
    "IncrementalConfig",
    "IncrementalDecision",
    "IncrementalProcessor",
    "IncrementalResult",
    "process_incremental",
    "process_incremental_datasets",
]
