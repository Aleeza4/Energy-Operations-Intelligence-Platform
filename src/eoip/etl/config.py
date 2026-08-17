"""Phase 3 ETL configuration for the Energy Operations Intelligence Platform.

This module defines the immutable configuration contract used by EOIP's
Prefect-based ETL workflows. It contains no Prefect decorators or runtime side
effects; orchestration modules consume these settings explicitly.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final

DEFAULT_BATCH_SIZE: Final[int] = 50_000
DEFAULT_FLOW_RETRIES: Final[int] = 1
DEFAULT_TASK_RETRIES: Final[int] = 2
DEFAULT_RETRY_DELAY_SECONDS: Final[float] = 5.0
DEFAULT_TIMEOUT_SECONDS: Final[float] = 3_600.0
DEFAULT_MAX_BAD_RECORDS: Final[int] = 100


class ETLEnvironment(StrEnum):
    """Supported ETL execution environments."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class SourceFormat(StrEnum):
    """Source formats supported by the Phase 3 ingestion layer."""

    PARQUET = "parquet"
    CSV = "csv"
    JSON = "json"


class LoadMode(StrEnum):
    """Supported ETL load modes."""

    FULL = "full"
    INCREMENTAL = "incremental"


class FailurePolicy(StrEnum):
    """How the ETL pipeline handles invalid source records."""

    FAIL_FAST = "fail_fast"
    QUARANTINE = "quarantine"


@dataclass(frozen=True, slots=True)
class RetryConfig:
    """Retry and timeout configuration for Prefect flows and tasks."""

    flow_retries: int = DEFAULT_FLOW_RETRIES
    task_retries: int = DEFAULT_TASK_RETRIES
    retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        """Validate retry and timeout values."""
        _validate_non_negative_int("flow_retries", self.flow_retries)
        _validate_non_negative_int("task_retries", self.task_retries)

        _validate_positive_finite_number(
            "retry_delay_seconds",
            self.retry_delay_seconds,
        )
        _validate_positive_finite_number(
            "timeout_seconds",
            self.timeout_seconds,
        )


@dataclass(frozen=True, slots=True)
class IngestionConfig:
    """Configuration controlling Phase 3 source-data ingestion."""

    source_root: Path = Path("data/synthetic/runs")
    source_format: SourceFormat = SourceFormat.PARQUET
    batch_size: int = DEFAULT_BATCH_SIZE
    recursive: bool = True

    def __post_init__(self) -> None:
        """Normalize and validate ingestion settings."""
        source_root = Path(self.source_root)

        if not str(source_root).strip():
            raise ValueError("source_root cannot be empty.")

        object.__setattr__(self, "source_root", source_root)

        if not isinstance(self.source_format, SourceFormat):
            raise TypeError("source_format must be a SourceFormat.")

        _validate_positive_int("batch_size", self.batch_size)

        if not isinstance(self.recursive, bool):
            raise TypeError("recursive must be a boolean.")


@dataclass(frozen=True, slots=True)
class StagingConfig:
    """Filesystem locations used during ETL processing."""

    staging_root: Path = Path("data/etl/staging")
    quarantine_root: Path = Path("data/etl/quarantine")
    checkpoint_root: Path = Path("data/etl/checkpoints")

    def __post_init__(self) -> None:
        """Normalize and validate ETL filesystem paths."""
        for field_name in (
            "staging_root",
            "quarantine_root",
            "checkpoint_root",
        ):
            path = Path(getattr(self, field_name))

            if not str(path).strip():
                raise ValueError(f"{field_name} cannot be empty.")

            object.__setattr__(self, field_name, path)

        normalized_paths = {
            self.staging_root.as_posix(),
            self.quarantine_root.as_posix(),
            self.checkpoint_root.as_posix(),
        }

        if len(normalized_paths) != 3:
            raise ValueError(
                "staging_root, quarantine_root, and checkpoint_root "
                "must be distinct."
            )


@dataclass(frozen=True, slots=True)
class QualityConfig:
    """Data-quality policy applied during ETL ingestion."""

    failure_policy: FailurePolicy = FailurePolicy.QUARANTINE
    max_bad_records: int = DEFAULT_MAX_BAD_RECORDS
    reject_duplicate_rows: bool = True
    require_manifest: bool = True
    verify_source_checksums: bool = True

    def __post_init__(self) -> None:
        """Validate data-quality configuration."""
        if not isinstance(self.failure_policy, FailurePolicy):
            raise TypeError("failure_policy must be a FailurePolicy.")

        _validate_non_negative_int(
            "max_bad_records",
            self.max_bad_records,
        )

        for field_name in (
            "reject_duplicate_rows",
            "require_manifest",
            "verify_source_checksums",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be a boolean.")


@dataclass(frozen=True, slots=True)
class ETLConfig:
    """Complete immutable configuration for the Phase 3 ETL platform."""

    environment: ETLEnvironment = ETLEnvironment.DEVELOPMENT
    load_mode: LoadMode = LoadMode.FULL

    ingestion: IngestionConfig = field(default_factory=IngestionConfig)
    staging: StagingConfig = field(default_factory=StagingConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)

    pipeline_name: str = "eoip-phase3-etl"

    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and normalize the complete ETL configuration."""
        if not isinstance(self.environment, ETLEnvironment):
            raise TypeError("environment must be an ETLEnvironment.")

        if not isinstance(self.load_mode, LoadMode):
            raise TypeError("load_mode must be a LoadMode.")

        if not isinstance(self.ingestion, IngestionConfig):
            raise TypeError("ingestion must be an IngestionConfig.")

        if not isinstance(self.staging, StagingConfig):
            raise TypeError("staging must be a StagingConfig.")

        if not isinstance(self.quality, QualityConfig):
            raise TypeError("quality must be a QualityConfig.")

        if not isinstance(self.retry, RetryConfig):
            raise TypeError("retry must be a RetryConfig.")

        if not isinstance(self.pipeline_name, str):
            raise TypeError("pipeline_name must be a string.")

        pipeline_name = self.pipeline_name.strip()

        if not pipeline_name:
            raise ValueError("pipeline_name cannot be empty.")

        object.__setattr__(self, "pipeline_name", pipeline_name)

        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping.")

        normalized_metadata: dict[str, str] = {}

        for key, value in self.metadata.items():
            if not isinstance(key, str):
                raise TypeError("metadata keys must be strings.")

            if not isinstance(value, str):
                raise TypeError("metadata values must be strings.")

            normalized_key = key.strip()
            normalized_value = value.strip()

            if not normalized_key:
                raise ValueError("metadata keys must be non-empty strings.")

            if not normalized_value:
                raise ValueError(f"metadata[{key!r}] must be a non-empty string.")

            normalized_metadata[normalized_key] = normalized_value

        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(
                dict(
                    sorted(
                        normalized_metadata.items(),
                    )
                )
            ),
        )

        if (
            self.quality.failure_policy is FailurePolicy.FAIL_FAST
            and self.quality.max_bad_records != 0
        ):
            raise ValueError(
                "max_bad_records must be 0 when failure_policy " "is 'fail_fast'."
            )

    def to_dict(self) -> dict[str, Any]:
        """Return a portable serialization-ready configuration mapping."""
        return {
            "environment": self.environment.value,
            "load_mode": self.load_mode.value,
            "ingestion": {
                "source_root": self.ingestion.source_root.as_posix(),
                "source_format": self.ingestion.source_format.value,
                "batch_size": self.ingestion.batch_size,
                "recursive": self.ingestion.recursive,
            },
            "staging": {
                "staging_root": self.staging.staging_root.as_posix(),
                "quarantine_root": self.staging.quarantine_root.as_posix(),
                "checkpoint_root": self.staging.checkpoint_root.as_posix(),
            },
            "quality": {
                "failure_policy": self.quality.failure_policy.value,
                "max_bad_records": self.quality.max_bad_records,
                "reject_duplicate_rows": (self.quality.reject_duplicate_rows),
                "require_manifest": self.quality.require_manifest,
                "verify_source_checksums": (self.quality.verify_source_checksums),
            },
            "retry": {
                "flow_retries": self.retry.flow_retries,
                "task_retries": self.retry.task_retries,
                "retry_delay_seconds": self.retry.retry_delay_seconds,
                "timeout_seconds": self.retry.timeout_seconds,
            },
            "pipeline_name": self.pipeline_name,
            "metadata": dict(self.metadata),
        }


def development_config() -> ETLConfig:
    """Return the default local-development ETL configuration."""
    return ETLConfig()


def test_config() -> ETLConfig:
    """Return a deterministic configuration for Phase 3 unit tests."""
    return ETLConfig(
        environment=ETLEnvironment.TEST,
        ingestion=IngestionConfig(
            source_root=Path("data/test/synthetic"),
            batch_size=100,
        ),
        staging=StagingConfig(
            staging_root=Path("data/test/etl/staging"),
            quarantine_root=Path("data/test/etl/quarantine"),
            checkpoint_root=Path("data/test/etl/checkpoints"),
        ),
        retry=RetryConfig(
            flow_retries=0,
            task_retries=0,
            retry_delay_seconds=0.1,
            timeout_seconds=60.0,
        ),
        pipeline_name="eoip-phase3-etl-test",
    )


def production_config() -> ETLConfig:
    """Return conservative production-oriented ETL defaults."""
    return ETLConfig(
        environment=ETLEnvironment.PRODUCTION,
        ingestion=IngestionConfig(
            batch_size=100_000,
        ),
        retry=RetryConfig(
            flow_retries=2,
            task_retries=3,
            retry_delay_seconds=10.0,
            timeout_seconds=7_200.0,
        ),
    )


def _validate_positive_int(
    name: str,
    value: int,
) -> None:
    """Validate a strictly positive integer."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer.")

    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")


def _validate_non_negative_int(
    name: str,
    value: int,
) -> None:
    """Validate a non-negative integer."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer.")

    if value < 0:
        raise ValueError(f"{name} must be greater than or equal to zero.")


def _validate_positive_finite_number(
    name: str,
    value: float,
) -> None:
    """Validate a finite numeric value greater than zero."""
    if isinstance(value, bool) or not isinstance(
        value,
        (int, float),
    ):
        raise TypeError(f"{name} must be numeric.")

    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")

    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")


__all__ = [
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_FLOW_RETRIES",
    "DEFAULT_MAX_BAD_RECORDS",
    "DEFAULT_RETRY_DELAY_SECONDS",
    "DEFAULT_TASK_RETRIES",
    "DEFAULT_TIMEOUT_SECONDS",
    "ETLConfig",
    "ETLEnvironment",
    "FailurePolicy",
    "IngestionConfig",
    "LoadMode",
    "QualityConfig",
    "RetryConfig",
    "SourceFormat",
    "StagingConfig",
    "development_config",
    "production_config",
    "test_config",
]
