"""Data-lineage foundation for EOIP Phase 3 ETL pipelines.

This module provides immutable lineage records describing how datasets move
through the EOIP ETL pipeline.

It captures source datasets, target datasets, processing stages, run
identifiers, timestamps, row counts, metadata, and parent-child relationships.

The module is intentionally independent of Prefect and database persistence.
Later orchestration and repository layers can persist these records without
changing the lineage contract defined here.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Final

import pandas as pd

DEFAULT_LINEAGE_VERSION: Final[str] = "1.0"


class LineageStage(StrEnum):
    """Stable EOIP ETL lineage-stage identifiers."""

    INGESTION = "ingestion"
    VALIDATION = "validation"
    CLEANING = "cleaning"
    TRANSFORMATION = "transformation"
    INCREMENTAL = "incremental"
    LOADING = "loading"
    QUALITY = "quality"


class LineageRelationship(StrEnum):
    """Relationship between source and target lineage assets."""

    DERIVED_FROM = "derived_from"
    VALIDATED_FROM = "validated_from"
    CLEANED_FROM = "cleaned_from"
    TRANSFORMED_FROM = "transformed_from"
    FILTERED_FROM = "filtered_from"
    LOADED_FROM = "loaded_from"


@dataclass(frozen=True, slots=True)
class LineageAsset:
    """One immutable dataset asset participating in ETL lineage."""

    dataset_name: str
    location: str | None = None
    format: str | None = None
    row_count: int | None = None
    checksum: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normalize and validate asset metadata."""
        object.__setattr__(
            self,
            "dataset_name",
            _normalize_required_string(
                "dataset_name",
                self.dataset_name,
            ),
        )

        for field_name in (
            "location",
            "format",
            "checksum",
        ):
            value = getattr(
                self,
                field_name,
            )

            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    _normalize_optional_string(
                        field_name,
                        value,
                    ),
                )

        if self.row_count is not None:
            _validate_non_negative_int(
                "row_count",
                self.row_count,
            )

        object.__setattr__(
            self,
            "metadata",
            _normalize_metadata(self.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a serialization-ready asset mapping."""
        return {
            "dataset_name": self.dataset_name,
            "location": self.location,
            "format": self.format,
            "row_count": self.row_count,
            "checksum": self.checksum,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class LineageRecord:
    """Immutable lineage relationship for one ETL processing step."""

    run_id: str
    stage: LineageStage
    relationship: LineageRelationship
    source: LineageAsset
    target: LineageAsset
    recorded_at: datetime
    operation: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    version: str = DEFAULT_LINEAGE_VERSION

    def __post_init__(self) -> None:
        """Normalize and validate lineage record."""
        object.__setattr__(
            self,
            "run_id",
            _normalize_required_string(
                "run_id",
                self.run_id,
            ),
        )

        if not isinstance(
            self.stage,
            LineageStage,
        ):
            raise TypeError("stage must be a LineageStage.")

        if not isinstance(
            self.relationship,
            LineageRelationship,
        ):
            raise TypeError("relationship must be a LineageRelationship.")

        if not isinstance(
            self.source,
            LineageAsset,
        ):
            raise TypeError("source must be a LineageAsset.")

        if not isinstance(
            self.target,
            LineageAsset,
        ):
            raise TypeError("target must be a LineageAsset.")

        object.__setattr__(
            self,
            "recorded_at",
            _normalize_datetime(
                "recorded_at",
                self.recorded_at,
            ),
        )

        if self.operation is not None:
            object.__setattr__(
                self,
                "operation",
                _normalize_optional_string(
                    "operation",
                    self.operation,
                ),
            )

        object.__setattr__(
            self,
            "metadata",
            _normalize_metadata(self.metadata),
        )

        object.__setattr__(
            self,
            "version",
            _normalize_required_string(
                "version",
                self.version,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a serialization-ready lineage mapping."""
        return {
            "run_id": self.run_id,
            "stage": self.stage.value,
            "relationship": self.relationship.value,
            "source": self.source.to_dict(),
            "target": self.target.to_dict(),
            "recorded_at": self.recorded_at.isoformat(),
            "operation": self.operation,
            "metadata": dict(self.metadata),
            "version": self.version,
        }


@dataclass(frozen=True, slots=True)
class DatasetLineageSummary:
    """Aggregated lineage summary for one logical dataset."""

    dataset_name: str
    record_count: int
    source_datasets: tuple[str, ...]
    target_datasets: tuple[str, ...]
    stages: tuple[LineageStage, ...]

    def __post_init__(self) -> None:
        """Validate lineage summary."""
        object.__setattr__(
            self,
            "dataset_name",
            _normalize_required_string(
                "dataset_name",
                self.dataset_name,
            ),
        )

        _validate_non_negative_int(
            "record_count",
            self.record_count,
        )

        object.__setattr__(
            self,
            "source_datasets",
            _normalize_string_tuple(
                "source_datasets",
                self.source_datasets,
            ),
        )

        object.__setattr__(
            self,
            "target_datasets",
            _normalize_string_tuple(
                "target_datasets",
                self.target_datasets,
            ),
        )

        if not isinstance(
            self.stages,
            tuple,
        ):
            raise TypeError("stages must be a tuple.")

        for stage in self.stages:
            if not isinstance(
                stage,
                LineageStage,
            ):
                raise TypeError("stages must contain LineageStage values.")

    def to_dict(self) -> dict[str, Any]:
        """Return a serialization-ready summary."""
        return {
            "dataset_name": self.dataset_name,
            "record_count": self.record_count,
            "source_datasets": list(self.source_datasets),
            "target_datasets": list(self.target_datasets),
            "stages": [stage.value for stage in self.stages],
        }


class LineageTracker:
    """Deterministic in-memory lineage tracker for one ETL run."""

    def __init__(
        self,
        run_id: str,
    ) -> None:
        """Create a lineage tracker."""
        self._run_id = _normalize_required_string(
            "run_id",
            run_id,
        )
        self._records: list[LineageRecord] = []

    @property
    def run_id(self) -> str:
        """Return the ETL run identifier."""
        return self._run_id

    @property
    def records(self) -> tuple[LineageRecord, ...]:
        """Return immutable lineage records."""
        return tuple(self._records)

    def record(
        self,
        *,
        stage: LineageStage,
        relationship: LineageRelationship,
        source: LineageAsset,
        target: LineageAsset,
        recorded_at: datetime | None = None,
        operation: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> LineageRecord:
        """Record one lineage relationship."""
        record = LineageRecord(
            run_id=self._run_id,
            stage=stage,
            relationship=relationship,
            source=source,
            target=target,
            recorded_at=(recorded_at if recorded_at is not None else datetime.now(UTC)),
            operation=operation,
            metadata=(metadata if metadata is not None else {}),
        )

        self._records.append(record)

        return record

    def derived(
        self,
        *,
        stage: LineageStage,
        source: LineageAsset,
        target: LineageAsset,
        recorded_at: datetime | None = None,
        operation: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> LineageRecord:
        """Record a generic derived-from relationship."""
        return self.record(
            stage=stage,
            relationship=LineageRelationship.DERIVED_FROM,
            source=source,
            target=target,
            recorded_at=recorded_at,
            operation=operation,
            metadata=metadata,
        )

    def validated(
        self,
        *,
        source: LineageAsset,
        target: LineageAsset,
        recorded_at: datetime | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> LineageRecord:
        """Record validation lineage."""
        return self.record(
            stage=LineageStage.VALIDATION,
            relationship=LineageRelationship.VALIDATED_FROM,
            source=source,
            target=target,
            recorded_at=recorded_at,
            operation="validate",
            metadata=metadata,
        )

    def cleaned(
        self,
        *,
        source: LineageAsset,
        target: LineageAsset,
        recorded_at: datetime | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> LineageRecord:
        """Record cleaning lineage."""
        return self.record(
            stage=LineageStage.CLEANING,
            relationship=LineageRelationship.CLEANED_FROM,
            source=source,
            target=target,
            recorded_at=recorded_at,
            operation="clean",
            metadata=metadata,
        )

    def transformed(
        self,
        *,
        source: LineageAsset,
        target: LineageAsset,
        recorded_at: datetime | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> LineageRecord:
        """Record transformation lineage."""
        return self.record(
            stage=LineageStage.TRANSFORMATION,
            relationship=LineageRelationship.TRANSFORMED_FROM,
            source=source,
            target=target,
            recorded_at=recorded_at,
            operation="transform",
            metadata=metadata,
        )

    def incremental(
        self,
        *,
        source: LineageAsset,
        target: LineageAsset,
        recorded_at: datetime | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> LineageRecord:
        """Record incremental-filter lineage."""
        return self.record(
            stage=LineageStage.INCREMENTAL,
            relationship=LineageRelationship.FILTERED_FROM,
            source=source,
            target=target,
            recorded_at=recorded_at,
            operation="incremental_filter",
            metadata=metadata,
        )

    def loaded(
        self,
        *,
        source: LineageAsset,
        target: LineageAsset,
        recorded_at: datetime | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> LineageRecord:
        """Record loading lineage."""
        return self.record(
            stage=LineageStage.LOADING,
            relationship=LineageRelationship.LOADED_FROM,
            source=source,
            target=target,
            recorded_at=recorded_at,
            operation="load",
            metadata=metadata,
        )

    def records_for_dataset(
        self,
        dataset_name: str,
    ) -> tuple[LineageRecord, ...]:
        """Return all lineage records involving one dataset."""
        normalized_name = _normalize_required_string(
            "dataset_name",
            dataset_name,
        )

        return tuple(
            record
            for record in self._records
            if (
                record.source.dataset_name == normalized_name
                or record.target.dataset_name == normalized_name
            )
        )

    def summarize_dataset(
        self,
        dataset_name: str,
    ) -> DatasetLineageSummary:
        """Return a deterministic summary for one dataset."""
        normalized_name = _normalize_required_string(
            "dataset_name",
            dataset_name,
        )

        records = self.records_for_dataset(normalized_name)

        source_datasets = tuple(
            sorted({record.source.dataset_name for record in records})
        )

        target_datasets = tuple(
            sorted({record.target.dataset_name for record in records})
        )

        stages = tuple(
            sorted(
                {record.stage for record in records},
                key=lambda value: value.value,
            )
        )

        return DatasetLineageSummary(
            dataset_name=normalized_name,
            record_count=len(records),
            source_datasets=source_datasets,
            target_datasets=target_datasets,
            stages=stages,
        )

    def to_frame(self) -> pd.DataFrame:
        """Return lineage records as a deterministic DataFrame."""
        columns = [
            "run_id",
            "stage",
            "relationship",
            "source_dataset",
            "source_location",
            "source_format",
            "source_row_count",
            "source_checksum",
            "target_dataset",
            "target_location",
            "target_format",
            "target_row_count",
            "target_checksum",
            "recorded_at",
            "operation",
            "metadata",
            "version",
        ]

        if not self._records:
            return pd.DataFrame(columns=columns)

        rows: list[dict[str, Any]] = []

        for record in self._records:
            rows.append(
                {
                    "run_id": record.run_id,
                    "stage": record.stage.value,
                    "relationship": record.relationship.value,
                    "source_dataset": (record.source.dataset_name),
                    "source_location": (record.source.location),
                    "source_format": (record.source.format),
                    "source_row_count": (record.source.row_count),
                    "source_checksum": (record.source.checksum),
                    "target_dataset": (record.target.dataset_name),
                    "target_location": (record.target.location),
                    "target_format": (record.target.format),
                    "target_row_count": (record.target.row_count),
                    "target_checksum": (record.target.checksum),
                    "recorded_at": (record.recorded_at.isoformat()),
                    "operation": record.operation,
                    "metadata": dict(record.metadata),
                    "version": record.version,
                }
            )

        return pd.DataFrame(
            rows,
            columns=columns,
        )


def build_lineage_asset(
    dataset_name: str,
    *,
    frame: pd.DataFrame | None = None,
    location: str | None = None,
    format: str | None = None,
    checksum: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> LineageAsset:
    """Build a lineage asset from dataset metadata."""
    if frame is not None and not isinstance(
        frame,
        pd.DataFrame,
    ):
        raise TypeError("frame must be a pandas DataFrame or None.")

    return LineageAsset(
        dataset_name=dataset_name,
        location=location,
        format=format,
        row_count=(len(frame) if frame is not None else None),
        checksum=checksum,
        metadata=(metadata if metadata is not None else {}),
    )


def summarize_lineage(
    records: Iterable[LineageRecord],
    dataset_name: str,
) -> DatasetLineageSummary:
    """Summarize lineage records for one dataset."""
    normalized_name = _normalize_required_string(
        "dataset_name",
        dataset_name,
    )

    normalized_records = tuple(records)

    for record in normalized_records:
        if not isinstance(
            record,
            LineageRecord,
        ):
            raise TypeError("records must contain LineageRecord objects.")

    relevant = tuple(
        record
        for record in normalized_records
        if (
            record.source.dataset_name == normalized_name
            or record.target.dataset_name == normalized_name
        )
    )

    source_datasets = tuple(sorted({record.source.dataset_name for record in relevant}))

    target_datasets = tuple(sorted({record.target.dataset_name for record in relevant}))

    stages = tuple(
        sorted(
            {record.stage for record in relevant},
            key=lambda value: value.value,
        )
    )

    return DatasetLineageSummary(
        dataset_name=normalized_name,
        record_count=len(relevant),
        source_datasets=source_datasets,
        target_datasets=target_datasets,
        stages=stages,
    )


def _normalize_required_string(
    name: str,
    value: str,
) -> str:
    """Normalize a required non-empty string."""
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(f"{name} must be a string.")

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{name} cannot be empty.")

    return normalized


def _normalize_optional_string(
    name: str,
    value: str,
) -> str:
    """Normalize a present optional string."""
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(f"{name} must be a string.")

    return value.strip()


def _normalize_datetime(
    name: str,
    value: datetime,
) -> datetime:
    """Normalize datetime to UTC."""
    if not isinstance(
        value,
        datetime,
    ):
        raise TypeError(f"{name} must be a datetime.")

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def _normalize_metadata(
    value: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Normalize metadata to an immutable mapping."""
    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError("metadata must be a mapping.")

    normalized: dict[
        str,
        Any,
    ] = {}

    for key, item in value.items():
        if not isinstance(
            key,
            str,
        ):
            raise TypeError("metadata keys must be strings.")

        normalized_key = key.strip()

        if not normalized_key:
            raise ValueError("metadata keys cannot be empty.")

        normalized[normalized_key] = item

    return MappingProxyType(dict(sorted(normalized.items())))


def _normalize_string_tuple(
    name: str,
    values: tuple[str, ...],
) -> tuple[str, ...]:
    """Normalize a tuple of unique strings."""
    if not isinstance(
        values,
        tuple,
    ):
        raise TypeError(f"{name} must be a tuple.")

    normalized = tuple(
        _normalize_required_string(
            name,
            value,
        )
        for value in values
    )

    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{name} cannot contain duplicate values.")

    return normalized


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
    "DEFAULT_LINEAGE_VERSION",
    "DatasetLineageSummary",
    "LineageAsset",
    "LineageRecord",
    "LineageRelationship",
    "LineageStage",
    "LineageTracker",
    "build_lineage_asset",
    "summarize_lineage",
]
