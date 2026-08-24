"""Synthetic dataset serialization and staged run publication for EOIP Phase 2.

This module owns the physical output pipeline for Phase 2 synthetic datasets.
It serializes an already-generated :class:`SyntheticDataset` to Parquet files
inside a staging directory and atomically publishes the completed run.

Responsibilities
----------------
- serialize tuple-based domain models using their existing ``to_record()``
  methods;
- write pandas DataFrames directly without copying;
- use Zstandard compression and stable column ordering;
- partition large time-series datasets by year/month (and plant for inverter
  SCADA) when configured;
- create run output inside ``.staging/{run_id}`` first;
- publish a completed staging run atomically into ``runs/{run_id}``;
- return structured :class:`DatasetWriteResult` metadata.

This module never generates domain values, mutates the dataset, validates
business rules, builds manifests, accesses PostgreSQL, or performs ETL.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import pandas as pd

from eoip.core.exceptions import DataGenerationError
from eoip.synthetic.config import (
    CompressionCodec,
    GenerationConfig,
    OutputFormat,
    OverwritePolicy,
)
from eoip.synthetic.generator import SyntheticDataset

_STAGING_DIR_NAME: Final[str] = ".staging"
_RUNS_DIR_NAME: Final[str] = "runs"
_SOURCE_SYSTEM: Final[str] = "eoip_synthetic"
_RUN_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_PART_FILE_NAME: Final[str] = "part-00000.parquet"

_TIMESTAMP_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        "timestamp",
        "raised_at",
        "acknowledged_at",
        "cleared_at",
        "event_start_at_utc",
        "event_end_at_utc",
        "occurred_at",
        "detected_at",
        "assigned_at",
        "investigation_started_at",
        "restored_at",
        "resolved_at",
        "closed_at",
        "created_at",
        "scheduled_at",
        "started_at",
        "completed_at",
        "cancelled_at",
        "start_at_utc",
        "end_at_utc",
    }
)

_TIMESTAMP_COLUMN_BY_DATASET: Final[dict[str, str]] = {
    "weather": "timestamp",
    "inverter_scada": "timestamp",
    "plant_scada": "timestamp",
    "alarms": "raised_at",
    "incidents": "occurred_at",
    "work_orders": "created_at",
    "ground_truth_events": "start_at_utc",
}


@dataclass(frozen=True, slots=True)
class _DatasetSpec:
    """Internal mapping from a SyntheticDataset field to its output location."""

    field_name: str
    dataset_name: str
    family: str
    is_fact: bool = False
    partition: bool = False
    partition_by_plant: bool = False


_DATASET_SPECS: Final[tuple[_DatasetSpec, ...]] = (
    _DatasetSpec("plants", "plants", "master"),
    _DatasetSpec("equipment", "equipment", "master"),
    _DatasetSpec("revenue_meters", "revenue_meters", "master"),
    _DatasetSpec("weather", "weather", "timeseries", is_fact=True, partition=True),
    _DatasetSpec(
        "inverter_scada",
        "inverter_scada",
        "timeseries",
        is_fact=True,
        partition=True,
        partition_by_plant=True,
    ),
    _DatasetSpec(
        "plant_scada",
        "plant_scada",
        "timeseries",
        is_fact=True,
        partition=True,
    ),
    _DatasetSpec("alarms", "alarms", "operations", is_fact=True),
    _DatasetSpec("incidents", "incidents", "operations", is_fact=True),
    _DatasetSpec("work_orders", "work_orders", "operations", is_fact=True),
    _DatasetSpec("tariffs", "tariffs", "commercial"),
    _DatasetSpec("budgets", "budgets", "commercial"),
    _DatasetSpec("ground_truth_events", "ground_truth_events", "truth"),
)


@dataclass(frozen=True, slots=True)
class DatasetArtifact:
    """Metadata for one written artifact file."""

    path: Path
    row_count: int
    byte_size: int


@dataclass(frozen=True, slots=True)
class DatasetWriteResult:
    """Structured result for one written dataset."""

    dataset_name: str
    family: str
    relative_paths: tuple[Path, ...]
    row_count: int
    column_names: tuple[str, ...]
    file_count: int
    total_bytes: int
    min_timestamp: datetime | None
    max_timestamp: datetime | None
    artifacts: tuple[DatasetArtifact, ...] = field(default_factory=tuple)


@dataclass(slots=True)
class StagedRunDirectory:
    """Staging directory for one synthetic run.

    The staging directory is created under ``root/.staging/{run_id}`` and is
    atomically moved to ``root/runs/{run_id}`` by :meth:`publish`.
    """

    root: Path
    run_id: str
    overwrite_policy: OverwritePolicy = OverwritePolicy.ERROR
    _staging_path: Path | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Validate the root, run ID, and overwrite policy."""
        if not isinstance(self.root, Path):
            self.root = Path(self.root)
        self.run_id = _validate_run_id(self.run_id)
        if not isinstance(self.overwrite_policy, OverwritePolicy):
            raise TypeError("overwrite_policy must be an OverwritePolicy.")

    @property
    def staging_path(self) -> Path:
        """Return the resolved staging directory path."""
        if self._staging_path is not None:
            return self._staging_path
        return self.root / _STAGING_DIR_NAME / self.run_id

    @property
    def final_path(self) -> Path:
        """Return the final published run directory path."""
        return self.root / _RUNS_DIR_NAME / self.staging_path.name

    def create(self) -> StagedRunDirectory:
        """Create the staging directory, honoring the overwrite policy."""
        base = self.root / _STAGING_DIR_NAME / self.run_id
        if base.exists():
            if self.overwrite_policy is OverwritePolicy.ERROR:
                raise DataGenerationError(
                    f"Staging directory already exists: '{base}'. "
                    "Use OverwritePolicy.REPLACE or OverwritePolicy.VERSION "
                    "to permit reuse."
                )
            if self.overwrite_policy is OverwritePolicy.REPLACE:
                shutil.rmtree(base)
            if self.overwrite_policy is OverwritePolicy.VERSION:
                base = _next_version_path(base)
        base.mkdir(parents=True, exist_ok=True)
        self._staging_path = base
        return self

    def cleanup(self) -> None:
        """Remove the staging directory if it exists."""
        if self.staging_path.exists():
            shutil.rmtree(self.staging_path)

    def publish(self) -> Path:
        """Atomically move the staging directory to the final location."""
        if not self.staging_path.is_dir():
            raise DataGenerationError(
                f"Staging directory does not exist: '{self.staging_path}'. "
                "Create it with create() before publishing."
            )
        final = self.root / _RUNS_DIR_NAME / self.staging_path.name
        if final.exists():
            if self.overwrite_policy is OverwritePolicy.ERROR:
                raise DataGenerationError(
                    f"Final run directory already exists: '{final}'. "
                    "Use OverwritePolicy.REPLACE or OverwritePolicy.VERSION "
                    "to permit reuse."
                )
            if self.overwrite_policy is OverwritePolicy.REPLACE:
                shutil.rmtree(final)
            if self.overwrite_policy is OverwritePolicy.VERSION:
                final = _next_version_path(final)
        final.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.staging_path.rename(final)
        except OSError as exc:
            raise DataGenerationError(
                f"Failed to publish run '{self.run_id}' from "
                f"'{self.staging_path}' to '{final}': {exc}"
            ) from exc
        return final

    def __enter__(self) -> StagedRunDirectory:
        """Create the staging directory on context entry."""
        self.create()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> bool:
        """Clean up staging on exception; never publish automatically."""
        if exc_type is not None:
            self.cleanup()
        return False


class DatasetWriter:
    """Serialize a :class:`SyntheticDataset` to a staged run directory."""

    def __init__(self, config: GenerationConfig, run_id: str | None = None) -> None:
        """Initialize the writer with a generation configuration."""
        if not isinstance(config, GenerationConfig):
            raise TypeError("config must be a GenerationConfig.")
        self._config = config
        self._run_id = run_id or _derive_run_id(config)
        if config.output.format is OutputFormat.PARQUET:
            _check_parquet_dependency()

    @property
    def config(self) -> GenerationConfig:
        """Return the writer's generation configuration."""
        return self._config

    @property
    def run_id(self) -> str:
        """Return the deterministic run identifier."""
        return self._run_id

    def write(
        self,
        dataset: SyntheticDataset,
        staging: StagedRunDirectory,
    ) -> tuple[DatasetWriteResult, ...]:
        """Write every dataset in a SyntheticDataset to the staging directory."""
        if not isinstance(dataset, SyntheticDataset):
            raise TypeError("dataset must be a SyntheticDataset.")
        if not isinstance(staging, StagedRunDirectory):
            raise TypeError("staging must be a StagedRunDirectory.")
        if not staging.staging_path.is_dir():
            staging.create()

        results: list[DatasetWriteResult] = []
        for spec in _DATASET_SPECS:
            results.append(self._write_one(dataset, spec, staging))
        return tuple(results)

    def _write_one(
        self,
        dataset: SyntheticDataset,
        spec: _DatasetSpec,
        staging: StagedRunDirectory,
    ) -> DatasetWriteResult:
        """Write one dataset and return structured metadata."""
        value = getattr(dataset, spec.field_name)
        frame = _to_frame(value)
        frame = self._prepare_frame(frame, spec)

        family_dir = staging.staging_path / spec.family
        partition_enabled = spec.partition and self._config.output.partition_timeseries
        if partition_enabled:
            target = family_dir / spec.dataset_name
        else:
            target = family_dir / f"{spec.dataset_name}.{self._file_extension()}"

        try:
            files = self._write_frame(
                frame,
                target,
                spec,
                partition_enabled=partition_enabled,
            )
        except OSError as exc:
            raise DataGenerationError(
                f"Failed to write dataset '{spec.dataset_name}' to "
                f"'{target}': {exc}"
            ) from exc

        relative_paths = tuple(path.relative_to(staging.staging_path) for path in files)
        artifacts = tuple(
            DatasetArtifact(
                path=path,
                row_count=_artifact_row_count(path),
                byte_size=path.stat().st_size,
            )
            for path in files
        )
        total_bytes = sum(artifact.byte_size for artifact in artifacts)
        min_ts, max_ts = _timestamp_bounds(frame, spec.dataset_name)

        return DatasetWriteResult(
            dataset_name=spec.dataset_name,
            family=spec.family,
            relative_paths=relative_paths,
            row_count=len(frame),
            column_names=tuple(frame.columns),
            file_count=len(files),
            total_bytes=total_bytes,
            min_timestamp=min_ts,
            max_timestamp=max_ts,
            artifacts=artifacts,
        )

    def _prepare_frame(
        self,
        frame: pd.DataFrame,
        spec: _DatasetSpec,
    ) -> pd.DataFrame:
        """Add audit columns and coerce timestamps without mutating input."""
        result = frame.copy()
        if "generation_run_id" not in result.columns:
            result["generation_run_id"] = self._run_id
        if "schema_version" not in result.columns:
            result["schema_version"] = self._config.schema_version
        if spec.is_fact and "source_system" not in result.columns:
            result["source_system"] = _SOURCE_SYSTEM
        for column in result.columns:
            if column in _TIMESTAMP_COLUMNS:
                result[column] = pd.to_datetime(
                    result[column],
                    utc=True,
                    errors="coerce",
                )
        return result

    def _write_frame(
        self,
        frame: pd.DataFrame,
        target: Path,
        spec: _DatasetSpec,
        *,
        partition_enabled: bool,
    ) -> list[Path]:
        """Write a DataFrame to the configured output format."""
        if self._config.output.format is OutputFormat.PARQUET:
            return self._write_parquet(
                frame,
                target,
                spec,
                partition_enabled=partition_enabled,
            )
        if self._config.output.format is OutputFormat.CSV:
            return self._write_csv(frame, target)
        raise DataGenerationError(
            f"Unsupported output format: {self._config.output.format}"
        )

    def _write_parquet(
        self,
        frame: pd.DataFrame,
        target: Path,
        spec: _DatasetSpec,
        *,
        partition_enabled: bool,
    ) -> list[Path]:
        """Write a DataFrame to Parquet, returning written file paths."""
        compression = self._compression_codec()

        if partition_enabled and not frame.empty:
            timestamp_col = _TIMESTAMP_COLUMN_BY_DATASET.get(spec.dataset_name)
            if timestamp_col is None or timestamp_col not in frame.columns:
                raise DataGenerationError(
                    f"Cannot partition dataset '{spec.dataset_name}': "
                    f"no timestamp column '{timestamp_col}' found."
                )
            partition_frame = frame.copy()
            timestamps = pd.to_datetime(partition_frame[timestamp_col], utc=True)
            partition_frame["year"] = timestamps.dt.strftime("%Y")
            partition_frame["month"] = timestamps.dt.strftime("%m")
            partition_cols = ["year", "month"]
            if spec.partition_by_plant:
                partition_cols.append("plant_id")
            target.mkdir(parents=True, exist_ok=True)
            partition_frame.to_parquet(
                target,
                partition_cols=partition_cols,
                compression=compression,
                index=False,
            )
            return sorted(target.rglob("*.parquet"))

        target.parent.mkdir(parents=True, exist_ok=True)
        if partition_enabled and frame.empty:
            target.mkdir(parents=True, exist_ok=True)
            file_path = target / _PART_FILE_NAME
        else:
            file_path = target
        frame.to_parquet(file_path, compression=compression, index=False)
        return [file_path]

    def _write_csv(
        self,
        frame: pd.DataFrame,
        target: Path,
    ) -> list[Path]:
        """Write a DataFrame to CSV, returning written file paths."""
        target.parent.mkdir(parents=True, exist_ok=True)
        compression = self._compression_codec()
        if compression is None:
            frame.to_csv(target, index=False)
        else:
            frame.to_csv(target, index=False, compression=compression)
        return [target]

    def _compression_codec(self) -> str | None:
        """Return the pyarrow/pandas compression codec name."""
        codec = self._config.output.compression
        if codec is CompressionCodec.ZSTD:
            return "zstd"
        if codec is CompressionCodec.SNAPPY:
            return "snappy"
        if codec is CompressionCodec.GZIP:
            return "gzip"
        if codec is CompressionCodec.NONE:
            return None
        raise DataGenerationError(f"Unsupported compression codec: {codec}")

    def _file_extension(self) -> str:
        """Return the output file extension for the configured format."""
        if self._config.output.format is OutputFormat.PARQUET:
            return "parquet"
        if self._config.output.format is OutputFormat.CSV:
            return "csv"
        raise DataGenerationError(
            f"Unsupported output format: {self._config.output.format}"
        )


def write_dataset(
    dataset: SyntheticDataset,
    staging: StagedRunDirectory,
    config: GenerationConfig,
    *,
    run_id: str | None = None,
) -> tuple[DatasetWriteResult, ...]:
    """Write a complete synthetic dataset to a staged run directory."""
    writer = DatasetWriter(config, run_id=run_id)
    return writer.write(dataset, staging)


def read_dataset(path: Path) -> pd.DataFrame:
    """Read a Parquet file or partitioned dataset directory."""
    path = Path(path)
    if not path.exists():
        raise DataGenerationError(f"Dataset path does not exist: '{path}'.")
    try:
        return pd.read_parquet(path)
    except Exception as exc:
        raise DataGenerationError(f"Failed to read dataset at '{path}': {exc}") from exc


def publish_run(staging: StagedRunDirectory) -> Path:
    """Atomically publish a completed staging run."""
    return staging.publish()


def latest_pointer(root: Path) -> Path | None:
    """Return the most recently published run directory, or None."""
    runs_dir = Path(root) / _RUNS_DIR_NAME
    if not runs_dir.is_dir():
        return None
    candidates = [path for path in runs_dir.iterdir() if path.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _to_frame(value: Any) -> pd.DataFrame:
    """Convert a SyntheticDataset field to a DataFrame without mutation."""
    if isinstance(value, pd.DataFrame):
        return value
    records = [item.to_record() for item in value]
    return pd.DataFrame.from_records(records)


def _timestamp_bounds(
    frame: pd.DataFrame,
    dataset_name: str,
) -> tuple[datetime | None, datetime | None]:
    """Return min/max timestamps for a dataset when applicable."""
    timestamp_col = _TIMESTAMP_COLUMN_BY_DATASET.get(dataset_name)
    if timestamp_col is None or timestamp_col not in frame.columns or frame.empty:
        return None, None
    timestamps = pd.to_datetime(frame[timestamp_col], utc=True, errors="coerce")
    valid = timestamps.dropna()
    if valid.empty:
        return None, None
    return (
        valid.min().to_pydatetime().astimezone(UTC),
        valid.max().to_pydatetime().astimezone(UTC),
    )


def _artifact_row_count(path: Path) -> int:
    """Return the row count of a written artifact file."""
    if path.suffix == ".parquet":
        try:
            import pyarrow.parquet as pq

            return pq.read_metadata(path).num_rows
        except Exception:
            return 0
    try:
        with path.open("r", encoding="utf-8") as stream:
            return sum(1 for _ in stream) - 1
    except Exception:
        return 0


def _validate_run_id(run_id: str) -> str:
    """Validate and normalize a run identifier."""
    if not isinstance(run_id, str):
        raise TypeError("run_id must be a string.")
    normalized = run_id.strip()
    if not normalized:
        raise ValueError("run_id cannot be blank.")
    if normalized in {".", ".."}:
        raise ValueError("run_id cannot be '.' or '..'.")
    if not _RUN_ID_PATTERN.fullmatch(normalized):
        raise ValueError(
            "run_id contains unsafe characters. Use letters, digits, "
            "'.', '_', or '-' only."
        )
    return normalized


def _next_version_path(path: Path) -> Path:
    """Return the next available versioned path."""
    version = 2
    while True:
        candidate = path.with_name(f"{path.name}-v{version}")
        if not candidate.exists():
            return candidate
        version += 1


def _derive_run_id(config: GenerationConfig) -> str:
    """Derive the deterministic run ID from a generation configuration."""
    timestamp = config.time.start.strftime("%Y%m%dT%H%M%SZ")
    return f"RUN-{timestamp}-{config.seed}"


def _check_parquet_dependency() -> None:
    """Raise a clear EOIP error when pyarrow is unavailable."""
    try:
        import pyarrow  # noqa: F401
    except ImportError as exc:
        raise DataGenerationError(
            "Parquet output requires the 'pyarrow' package. "
            "Install it with: python -m pip install pyarrow"
        ) from exc


__all__ = [
    "DatasetArtifact",
    "DatasetWriteResult",
    "DatasetWriter",
    "StagedRunDirectory",
    "latest_pointer",
    "publish_run",
    "read_dataset",
    "write_dataset",
]
