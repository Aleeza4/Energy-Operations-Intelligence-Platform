"""EOIP Phase 3 ETL pipeline orchestration.

This module coordinates the core Phase 3 ETL stages for already-ingested
pandas DataFrames:

validation -> cleaning -> transformation -> incremental processing

It also records structured audit events and data-lineage relationships for
each dataset. Source discovery/reading remains in ``eoip.etl.ingestion`` and
Prefect orchestration remains a separate concern.

The pipeline is deterministic: datasets are processed in sorted name order,
stage configuration is explicit, and source DataFrames are never mutated.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Final

import pandas as pd

from eoip.etl.audit import AuditEvent, AuditLogger, AuditStage
from eoip.etl.cleaning import (
    CleaningConfig,
    CleaningResult,
    clean_dataframe,
)
from eoip.etl.config import ETLConfig
from eoip.etl.incremental import (
    DatasetCheckpoint,
    IncrementalConfig,
    IncrementalResult,
    process_incremental,
)
from eoip.etl.lineage import (
    LineageAsset,
    LineageRecord,
    LineageTracker,
    build_lineage_asset,
)
from eoip.etl.transformation import (
    TransformationConfig,
    TransformationResult,
    transform_dataframe,
)
from eoip.etl.validation import (
    DatasetContract,
    DatasetValidationResult,
    validate_dataset,
)

DEFAULT_PIPELINE_RUN_PREFIX: Final[str] = "ETL"
DEFAULT_SOURCE_LAYER: Final[str] = "ingested"
DEFAULT_VALIDATED_LAYER: Final[str] = "validated"
DEFAULT_CLEAN_LAYER: Final[str] = "clean"
DEFAULT_TRANSFORMED_LAYER: Final[str] = "transformed"
DEFAULT_INCREMENTAL_LAYER: Final[str] = "incremental"


@dataclass(frozen=True, slots=True)
class DatasetPipelineConfig:
    """Configuration bundle for one logical ETL dataset."""

    contract: DatasetContract
    cleaning: CleaningConfig = field(default_factory=CleaningConfig)
    transformation: TransformationConfig = field(default_factory=TransformationConfig)
    incremental: IncrementalConfig = field(default_factory=IncrementalConfig)

    def __post_init__(self) -> None:
        """Validate dataset pipeline configuration."""
        if not isinstance(
            self.contract,
            DatasetContract,
        ):
            raise TypeError("contract must be a DatasetContract.")

        if not isinstance(
            self.cleaning,
            CleaningConfig,
        ):
            raise TypeError("cleaning must be a CleaningConfig.")

        if not isinstance(
            self.transformation,
            TransformationConfig,
        ):
            raise TypeError("transformation must be a TransformationConfig.")

        if not isinstance(
            self.incremental,
            IncrementalConfig,
        ):
            raise TypeError("incremental must be an IncrementalConfig.")


@dataclass(frozen=True, slots=True)
class DatasetPipelineResult:
    """Complete Phase 3 ETL result for one dataset."""

    dataset_name: str
    source_frame: pd.DataFrame
    validation: DatasetValidationResult
    cleaning: CleaningResult
    transformation: TransformationResult
    incremental: IncrementalResult
    audit_events: tuple[AuditEvent, ...]
    lineage_records: tuple[LineageRecord, ...]

    def __post_init__(self) -> None:
        """Validate dataset result metadata."""
        normalized_name = _normalize_required_string(
            "dataset_name",
            self.dataset_name,
        )

        object.__setattr__(
            self,
            "dataset_name",
            normalized_name,
        )

        if not isinstance(
            self.source_frame,
            pd.DataFrame,
        ):
            raise TypeError("source_frame must be a pandas DataFrame.")

        if not isinstance(
            self.validation,
            DatasetValidationResult,
        ):
            raise TypeError("validation must be a DatasetValidationResult.")

        if not isinstance(
            self.cleaning,
            CleaningResult,
        ):
            raise TypeError("cleaning must be a CleaningResult.")

        if not isinstance(
            self.transformation,
            TransformationResult,
        ):
            raise TypeError("transformation must be a TransformationResult.")

        if not isinstance(
            self.incremental,
            IncrementalResult,
        ):
            raise TypeError("incremental must be an IncrementalResult.")

        _validate_tuple_items(
            "audit_events",
            self.audit_events,
            AuditEvent,
        )
        _validate_tuple_items(
            "lineage_records",
            self.lineage_records,
            LineageRecord,
        )

    @property
    def output_frame(self) -> pd.DataFrame:
        """Return the final DataFrame selected for downstream loading."""
        return self.incremental.frame

    @property
    def checkpoint(self) -> DatasetCheckpoint:
        """Return the new dataset checkpoint."""
        return self.incremental.checkpoint

    @property
    def passed_validation(self) -> bool:
        """Return whether source validation passed."""
        return self.validation.passed


@dataclass(frozen=True, slots=True)
class PipelineRunResult:
    """Aggregate result for one multi-dataset ETL run."""

    run_id: str
    datasets: Mapping[str, DatasetPipelineResult]
    audit_events: tuple[AuditEvent, ...]
    lineage_records: tuple[LineageRecord, ...]
    started_at: datetime
    completed_at: datetime

    def __post_init__(self) -> None:
        """Normalize and validate run-level result."""
        object.__setattr__(
            self,
            "run_id",
            _normalize_required_string(
                "run_id",
                self.run_id,
            ),
        )

        if not isinstance(
            self.datasets,
            Mapping,
        ):
            raise TypeError("datasets must be a mapping.")

        normalized_datasets: dict[
            str,
            DatasetPipelineResult,
        ] = {}

        for dataset_name, result in self.datasets.items():
            normalized_name = _normalize_required_string(
                "dataset_name",
                dataset_name,
            )

            if not isinstance(
                result,
                DatasetPipelineResult,
            ):
                raise TypeError("datasets must contain DatasetPipelineResult values.")

            if result.dataset_name != normalized_name:
                raise ValueError("Dataset result name does not match its mapping key.")

            normalized_datasets[normalized_name] = result

        object.__setattr__(
            self,
            "datasets",
            MappingProxyType(dict(sorted(normalized_datasets.items()))),
        )

        _validate_tuple_items(
            "audit_events",
            self.audit_events,
            AuditEvent,
        )
        _validate_tuple_items(
            "lineage_records",
            self.lineage_records,
            LineageRecord,
        )

        started_at = _normalize_datetime(
            "started_at",
            self.started_at,
        )
        completed_at = _normalize_datetime(
            "completed_at",
            self.completed_at,
        )

        if completed_at < started_at:
            raise ValueError("completed_at cannot be earlier than started_at.")

        object.__setattr__(
            self,
            "started_at",
            started_at,
        )
        object.__setattr__(
            self,
            "completed_at",
            completed_at,
        )

    @property
    def passed(self) -> bool:
        """Return whether every dataset passed source validation."""
        return all(result.passed_validation for result in self.datasets.values())

    @property
    def output_frames(self) -> dict[str, pd.DataFrame]:
        """Return final output frames by dataset name."""
        return {
            dataset_name: result.output_frame
            for dataset_name, result in self.datasets.items()
        }

    @property
    def checkpoints(self) -> dict[str, DatasetCheckpoint]:
        """Return generated checkpoints by dataset name."""
        return {
            dataset_name: result.checkpoint
            for dataset_name, result in self.datasets.items()
        }


class ETLPipeline:
    """Deterministic Phase 3 ETL pipeline coordinator."""

    def __init__(
        self,
        config: ETLConfig,
        dataset_configs: Mapping[
            str,
            DatasetPipelineConfig,
        ],
    ) -> None:
        """Create the ETL pipeline."""
        if not isinstance(
            config,
            ETLConfig,
        ):
            raise TypeError("config must be an ETLConfig.")

        if not isinstance(
            dataset_configs,
            Mapping,
        ):
            raise TypeError("dataset_configs must be a mapping.")

        normalized_configs: dict[
            str,
            DatasetPipelineConfig,
        ] = {}

        for dataset_name, dataset_config in dataset_configs.items():
            normalized_name = _normalize_required_string(
                "dataset_name",
                dataset_name,
            )

            if not isinstance(
                dataset_config,
                DatasetPipelineConfig,
            ):
                raise TypeError(
                    "dataset_configs values must be " "DatasetPipelineConfig objects."
                )

            if dataset_config.contract.dataset_name != normalized_name:
                raise ValueError(
                    "Dataset config key must match " "contract.dataset_name."
                )

            normalized_configs[normalized_name] = dataset_config

        self._config = config
        self._dataset_configs = MappingProxyType(
            dict(sorted(normalized_configs.items()))
        )

    @property
    def config(self) -> ETLConfig:
        """Return immutable ETL configuration."""
        return self._config

    @property
    def dataset_configs(
        self,
    ) -> Mapping[str, DatasetPipelineConfig]:
        """Return immutable per-dataset pipeline configuration."""
        return self._dataset_configs

    def run(
        self,
        datasets: Mapping[
            str,
            pd.DataFrame,
        ],
        *,
        run_id: str | None = None,
        checkpoints: (
            Mapping[
                str,
                DatasetCheckpoint,
            ]
            | None
        ) = None,
    ) -> PipelineRunResult:
        """Run the ETL pipeline for multiple already-ingested datasets."""
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

        resolved_run_id = (
            _normalize_required_string(
                "run_id",
                run_id,
            )
            if run_id is not None
            else _generate_run_id()
        )

        unknown_datasets = set(datasets) - set(self._dataset_configs)

        if unknown_datasets:
            raise KeyError(
                "No pipeline configuration registered for datasets: "
                f"{sorted(unknown_datasets)}"
            )

        started_at = datetime.now(UTC)

        audit = AuditLogger(
            resolved_run_id,
            pipeline_name=self._config.pipeline_name,
        )
        lineage = LineageTracker(resolved_run_id)

        audit.started(
            stage=AuditStage.PIPELINE,
            started_at=started_at,
            message="Phase 3 ETL pipeline started.",
            metadata={
                "dataset_count": len(datasets),
            },
        )

        results: dict[
            str,
            DatasetPipelineResult,
        ] = {}

        try:
            for dataset_name in sorted(datasets):
                frame = datasets[dataset_name]

                if not isinstance(
                    frame,
                    pd.DataFrame,
                ):
                    raise TypeError(
                        f"Dataset '{dataset_name}' must be a pandas DataFrame."
                    )

                checkpoint = (
                    checkpoints.get(dataset_name) if checkpoints is not None else None
                )

                results[dataset_name] = self._run_dataset(
                    dataset_name,
                    frame,
                    self._dataset_configs[dataset_name],
                    checkpoint,
                    audit,
                    lineage,
                )

        except Exception as error:
            audit.failed(
                stage=AuditStage.PIPELINE,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                error=error,
                message="Phase 3 ETL pipeline failed.",
            )
            raise

        completed_at = datetime.now(UTC)

        audit.succeeded(
            stage=AuditStage.PIPELINE,
            started_at=started_at,
            completed_at=completed_at,
            input_rows=sum(len(datasets[dataset_name]) for dataset_name in datasets),
            output_rows=sum(len(result.output_frame) for result in results.values()),
            message="Phase 3 ETL pipeline completed.",
            metadata={
                "dataset_count": len(results),
            },
        )

        return PipelineRunResult(
            run_id=resolved_run_id,
            datasets=results,
            audit_events=audit.events,
            lineage_records=lineage.records,
            started_at=started_at,
            completed_at=completed_at,
        )

    def _run_dataset(
        self,
        dataset_name: str,
        source_frame: pd.DataFrame,
        dataset_config: DatasetPipelineConfig,
        checkpoint: DatasetCheckpoint | None,
        audit: AuditLogger,
        lineage: LineageTracker,
    ) -> DatasetPipelineResult:
        """Run all configured ETL stages for one dataset."""
        audit_start = len(audit.events)
        lineage_start = len(lineage.records)

        source = source_frame.copy(deep=True)

        source_asset = build_lineage_asset(
            dataset_name,
            frame=source,
            metadata={
                "layer": DEFAULT_SOURCE_LAYER,
            },
        )

        validation = self._validate(
            dataset_name,
            source,
            dataset_config.contract,
            audit,
        )

        validated_asset = LineageAsset(
            dataset_name=dataset_name,
            row_count=len(source),
            metadata={
                "layer": DEFAULT_VALIDATED_LAYER,
                "passed": validation.passed,
                "error_count": validation.error_count,
            },
        )

        lineage.validated(
            source=source_asset,
            target=validated_asset,
            metadata={
                "passed": validation.passed,
            },
        )

        cleaning = self._clean(
            dataset_name,
            source,
            dataset_config.cleaning,
            audit,
        )

        clean_asset = build_lineage_asset(
            dataset_name,
            frame=cleaning.frame,
            metadata={
                "layer": DEFAULT_CLEAN_LAYER,
            },
        )

        lineage.cleaned(
            source=validated_asset,
            target=clean_asset,
            metadata={
                "rows_before": cleaning.rows_before,
                "rows_after": cleaning.rows_after,
            },
        )

        transformation = self._transform(
            dataset_name,
            cleaning.frame,
            dataset_config.transformation,
            audit,
        )

        transformed_asset = build_lineage_asset(
            dataset_name,
            frame=transformation.frame,
            metadata={
                "layer": DEFAULT_TRANSFORMED_LAYER,
            },
        )

        lineage.transformed(
            source=clean_asset,
            target=transformed_asset,
            metadata={
                "rows_before": transformation.rows_before,
                "rows_after": transformation.rows_after,
            },
        )

        incremental = self._incremental(
            dataset_name,
            transformation.frame,
            dataset_config.incremental,
            checkpoint,
            audit,
        )

        incremental_asset = build_lineage_asset(
            dataset_name,
            frame=incremental.frame,
            metadata={
                "layer": DEFAULT_INCREMENTAL_LAYER,
                "decision": incremental.decision.value,
            },
        )

        lineage.incremental(
            source=transformed_asset,
            target=incremental_asset,
            metadata={
                "decision": incremental.decision.value,
                "previous_watermark": (
                    incremental.previous_watermark.isoformat()
                    if incremental.previous_watermark is not None
                    else None
                ),
                "new_watermark": (
                    incremental.new_watermark.isoformat()
                    if incremental.new_watermark is not None
                    else None
                ),
            },
        )

        dataset_audit_events = audit.events[audit_start:]
        dataset_lineage_records = lineage.records[lineage_start:]

        return DatasetPipelineResult(
            dataset_name=dataset_name,
            source_frame=source,
            validation=validation,
            cleaning=cleaning,
            transformation=transformation,
            incremental=incremental,
            audit_events=dataset_audit_events,
            lineage_records=dataset_lineage_records,
        )

    def _validate(
        self,
        dataset_name: str,
        frame: pd.DataFrame,
        contract: DatasetContract,
        audit: AuditLogger,
    ) -> DatasetValidationResult:
        """Validate one dataset and record its audit event."""
        started_at = datetime.now(UTC)

        try:
            result = validate_dataset(
                self._config,
                contract,
                frame,
            )
        except Exception as error:
            audit.failed(
                stage=AuditStage.VALIDATION,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                dataset_name=dataset_name,
                input_rows=len(frame),
                error=error,
            )
            raise

        audit.succeeded(
            stage=AuditStage.VALIDATION,
            started_at=started_at,
            completed_at=datetime.now(UTC),
            dataset_name=dataset_name,
            input_rows=len(frame),
            output_rows=len(frame),
            rejected_rows=(
                0
                if result.passed
                else sum(issue.failure_count for issue in result.issues)
            ),
            metadata={
                "passed": result.passed,
                "error_count": result.error_count,
                "warning_count": result.warning_count,
            },
        )

        return result

    def _clean(
        self,
        dataset_name: str,
        frame: pd.DataFrame,
        config: CleaningConfig,
        audit: AuditLogger,
    ) -> CleaningResult:
        """Clean one dataset and record its audit event."""
        started_at = datetime.now(UTC)

        try:
            result = clean_dataframe(
                frame,
                config,
            )
        except Exception as error:
            audit.failed(
                stage=AuditStage.CLEANING,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                dataset_name=dataset_name,
                input_rows=len(frame),
                error=error,
            )
            raise

        audit.succeeded(
            stage=AuditStage.CLEANING,
            started_at=started_at,
            completed_at=datetime.now(UTC),
            dataset_name=dataset_name,
            input_rows=result.rows_before,
            output_rows=result.rows_after,
            rejected_rows=max(
                0,
                result.rows_before - result.rows_after,
            ),
        )

        return result

    def _transform(
        self,
        dataset_name: str,
        frame: pd.DataFrame,
        config: TransformationConfig,
        audit: AuditLogger,
    ) -> TransformationResult:
        """Transform one dataset and record its audit event."""
        started_at = datetime.now(UTC)

        try:
            result = transform_dataframe(
                frame,
                config,
            )
        except Exception as error:
            audit.failed(
                stage=AuditStage.TRANSFORMATION,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                dataset_name=dataset_name,
                input_rows=len(frame),
                error=error,
            )
            raise

        audit.succeeded(
            stage=AuditStage.TRANSFORMATION,
            started_at=started_at,
            completed_at=datetime.now(UTC),
            dataset_name=dataset_name,
            input_rows=result.rows_before,
            output_rows=result.rows_after,
            rejected_rows=max(
                0,
                result.rows_before - result.rows_after,
            ),
        )

        return result

    def _incremental(
        self,
        dataset_name: str,
        frame: pd.DataFrame,
        config: IncrementalConfig,
        checkpoint: DatasetCheckpoint | None,
        audit: AuditLogger,
    ) -> IncrementalResult:
        """Apply incremental processing and record its audit event."""
        started_at = datetime.now(UTC)

        try:
            result = process_incremental(
                self._config,
                dataset_name,
                frame,
                checkpoint,
                config=config,
            )
        except Exception as error:
            audit.failed(
                stage=AuditStage.INCREMENTAL,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                dataset_name=dataset_name,
                input_rows=len(frame),
                error=error,
            )
            raise

        audit.succeeded(
            stage=AuditStage.INCREMENTAL,
            started_at=started_at,
            completed_at=datetime.now(UTC),
            dataset_name=dataset_name,
            input_rows=result.input_rows,
            output_rows=result.output_rows,
            rejected_rows=max(
                0,
                result.input_rows - result.output_rows,
            ),
            metadata={
                "decision": result.decision.value,
            },
        )

        return result


def run_pipeline(
    config: ETLConfig,
    dataset_configs: Mapping[
        str,
        DatasetPipelineConfig,
    ],
    datasets: Mapping[
        str,
        pd.DataFrame,
    ],
    *,
    run_id: str | None = None,
    checkpoints: (
        Mapping[
            str,
            DatasetCheckpoint,
        ]
        | None
    ) = None,
) -> PipelineRunResult:
    """Run the Phase 3 ETL pipeline using explicit configuration."""
    return ETLPipeline(
        config,
        dataset_configs,
    ).run(
        datasets,
        run_id=run_id,
        checkpoints=checkpoints,
    )


def _generate_run_id() -> str:
    """Generate a UTC ETL run identifier."""
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")

    return f"{DEFAULT_PIPELINE_RUN_PREFIX}-" f"{timestamp}"


def _normalize_required_string(
    name: str,
    value: str,
) -> str:
    """Normalize one required non-empty string."""
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(f"{name} must be a string.")

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{name} cannot be empty.")

    return normalized


def _normalize_datetime(
    name: str,
    value: datetime,
) -> datetime:
    """Normalize a datetime to UTC."""
    if not isinstance(
        value,
        datetime,
    ):
        raise TypeError(f"{name} must be a datetime.")

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def _validate_tuple_items(
    name: str,
    values: tuple[Any, ...],
    expected_type: type[Any],
) -> None:
    """Validate an immutable tuple containing one expected type."""
    if not isinstance(
        values,
        tuple,
    ):
        raise TypeError(f"{name} must be a tuple.")

    for value in values:
        if not isinstance(
            value,
            expected_type,
        ):
            raise TypeError(f"{name} contains invalid values.")


__all__ = [
    "DEFAULT_CLEAN_LAYER",
    "DEFAULT_INCREMENTAL_LAYER",
    "DEFAULT_PIPELINE_RUN_PREFIX",
    "DEFAULT_SOURCE_LAYER",
    "DEFAULT_TRANSFORMED_LAYER",
    "DEFAULT_VALIDATED_LAYER",
    "DatasetPipelineConfig",
    "DatasetPipelineResult",
    "ETLPipeline",
    "PipelineRunResult",
    "run_pipeline",
]
