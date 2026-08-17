"""Source-data ingestion for EOIP Phase 3 ETL pipelines.

This module discovers Phase 2 synthetic run artifacts, validates portable
source paths, reads supported file formats, and exposes deterministic bounded
batch ingestion for downstream ETL validation and transformation.

It deliberately does not perform business-rule validation, cleaning,
transformation, database loading, or Prefect orchestration.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import pandas as pd

from eoip.etl.config import ETLConfig, SourceFormat

MANIFEST_FILE_NAME: Final[str] = "manifest.json"

_SUPPORTED_SUFFIXES: Final[Mapping[SourceFormat, tuple[str, ...]]] = {
    SourceFormat.PARQUET: (".parquet",),
    SourceFormat.CSV: (".csv",),
    SourceFormat.JSON: (".json",),
}


@dataclass(frozen=True, slots=True)
class SourceArtifact:
    """Metadata describing one discovered ETL source artifact."""

    dataset_name: str
    path: Path
    format: SourceFormat
    size_bytes: int

    def __post_init__(self) -> None:
        """Validate and normalize artifact metadata."""
        if not isinstance(self.dataset_name, str):
            raise TypeError("dataset_name must be a string.")

        normalized_name = self.dataset_name.strip()

        if not normalized_name:
            raise ValueError("dataset_name cannot be empty.")

        object.__setattr__(
            self,
            "dataset_name",
            normalized_name,
        )
        object.__setattr__(
            self,
            "path",
            Path(self.path),
        )

        if not isinstance(self.format, SourceFormat):
            raise TypeError("format must be a SourceFormat.")

        if isinstance(self.size_bytes, bool) or not isinstance(
            self.size_bytes,
            int,
        ):
            raise TypeError("size_bytes must be an integer.")

        if self.size_bytes < 0:
            raise ValueError("size_bytes must be greater than or equal to zero.")


@dataclass(frozen=True, slots=True)
class IngestionBatch:
    """One bounded batch returned by source ingestion."""

    dataset_name: str
    source_path: Path
    batch_number: int
    row_offset: int
    frame: pd.DataFrame

    def __post_init__(self) -> None:
        """Validate and normalize batch metadata."""
        if not isinstance(self.dataset_name, str):
            raise TypeError("dataset_name must be a string.")

        normalized_name = self.dataset_name.strip()

        if not normalized_name:
            raise ValueError("dataset_name cannot be empty.")

        object.__setattr__(
            self,
            "dataset_name",
            normalized_name,
        )
        object.__setattr__(
            self,
            "source_path",
            Path(self.source_path),
        )

        _validate_non_negative_int(
            "batch_number",
            self.batch_number,
        )
        _validate_non_negative_int(
            "row_offset",
            self.row_offset,
        )

        if not isinstance(self.frame, pd.DataFrame):
            raise TypeError("frame must be a pandas DataFrame.")

    @property
    def row_count(self) -> int:
        """Return the number of rows in this batch."""
        return len(self.frame)


@dataclass(frozen=True, slots=True)
class SourceRun:
    """Discovered Phase 2 source run and its portable manifest."""

    run_id: str
    root: Path
    manifest_path: Path
    manifest: Mapping[str, Any]

    def __post_init__(self) -> None:
        """Validate and normalize source-run metadata."""
        if not isinstance(self.run_id, str):
            raise TypeError("run_id must be a string.")

        normalized_run_id = self.run_id.strip()

        if not normalized_run_id:
            raise ValueError("run_id cannot be empty.")

        object.__setattr__(
            self,
            "run_id",
            normalized_run_id,
        )
        object.__setattr__(
            self,
            "root",
            Path(self.root),
        )
        object.__setattr__(
            self,
            "manifest_path",
            Path(self.manifest_path),
        )

        if not isinstance(self.manifest, Mapping):
            raise TypeError("manifest must be a mapping.")


class SourceIngestor:
    """Discover and ingest Phase 2 dataset artifacts."""

    def __init__(self, config: ETLConfig) -> None:
        """Create an ingestor from validated ETL configuration."""
        if not isinstance(config, ETLConfig):
            raise TypeError("config must be an ETLConfig.")

        self._config = config

    @property
    def config(self) -> ETLConfig:
        """Return the immutable ETL configuration."""
        return self._config

    def discover_runs(self) -> tuple[Path, ...]:
        """Return deterministic available Phase 2 run directories."""
        root = self._config.ingestion.source_root

        if not root.exists():
            return ()

        if not root.is_dir():
            raise ValueError(f"Configured source_root is not a directory: {root}")

        return tuple(
            sorted(
                (child for child in root.iterdir() if child.is_dir()),
                key=lambda path: path.name,
            )
        )

    def load_run(
        self,
        run_id: str,
    ) -> SourceRun:
        """Load one source run and its manifest."""
        normalized_run_id = _normalize_run_id(run_id)

        root = self._config.ingestion.source_root
        run_root = _safe_child(
            root,
            normalized_run_id,
        )

        if not run_root.exists():
            raise FileNotFoundError(f"Source run does not exist: {run_root}")

        if not run_root.is_dir():
            raise ValueError(f"Source run path is not a directory: {run_root}")

        manifest_path = run_root / MANIFEST_FILE_NAME

        if self._config.quality.require_manifest and not manifest_path.exists():
            raise FileNotFoundError(
                f"Required manifest does not exist: {manifest_path}"
            )

        manifest: Mapping[str, Any] = (
            _read_json_mapping(manifest_path) if manifest_path.exists() else {}
        )

        return SourceRun(
            run_id=normalized_run_id,
            root=run_root,
            manifest_path=manifest_path,
            manifest=manifest,
        )

    def discover_artifacts(
        self,
        run: SourceRun,
    ) -> tuple[SourceArtifact, ...]:
        """Discover supported data artifacts below a source run."""
        if not isinstance(run, SourceRun):
            raise TypeError("run must be a SourceRun.")

        _ensure_within_root(
            run.root,
            self._config.ingestion.source_root,
        )

        expected_format = self._config.ingestion.source_format
        allowed_suffixes = _SUPPORTED_SUFFIXES[expected_format]

        iterator: Iterator[Path]

        if self._config.ingestion.recursive:
            iterator = run.root.rglob("*")
        else:
            iterator = run.root.glob("*")

        artifacts: list[SourceArtifact] = []

        for path in iterator:
            if not path.is_file():
                continue

            if path.name == MANIFEST_FILE_NAME:
                continue

            if path.suffix.lower() not in allowed_suffixes:
                continue

            _ensure_within_root(
                path,
                run.root,
            )

            artifacts.append(
                SourceArtifact(
                    dataset_name=_dataset_name_from_path(
                        path=path,
                        run_root=run.root,
                    ),
                    path=path,
                    format=expected_format,
                    size_bytes=path.stat().st_size,
                )
            )

        artifacts.sort(
            key=lambda artifact: artifact.path.relative_to(run.root).as_posix()
        )

        return tuple(artifacts)

    def read_artifact(
        self,
        artifact: SourceArtifact,
    ) -> pd.DataFrame:
        """Read one source artifact into a new DataFrame."""
        if not isinstance(artifact, SourceArtifact):
            raise TypeError("artifact must be a SourceArtifact.")

        _ensure_within_root(
            artifact.path,
            self._config.ingestion.source_root,
        )

        if not artifact.path.exists():
            raise FileNotFoundError(f"Source artifact does not exist: {artifact.path}")

        if not artifact.path.is_file():
            raise ValueError(f"Source artifact is not a file: {artifact.path}")

        if artifact.format is SourceFormat.PARQUET:
            frame = pd.read_parquet(artifact.path)
        elif artifact.format is SourceFormat.CSV:
            frame = pd.read_csv(artifact.path)
        elif artifact.format is SourceFormat.JSON:
            frame = pd.read_json(artifact.path)
        else:
            raise ValueError(f"Unsupported source format: {artifact.format}")

        if not isinstance(frame, pd.DataFrame):
            raise TypeError(f"Reader did not return a DataFrame for {artifact.path}")

        return frame.copy(deep=True)

    def iter_batches(
        self,
        artifact: SourceArtifact,
    ) -> Iterator[IngestionBatch]:
        """Yield deterministic bounded batches for one source artifact."""
        frame = self.read_artifact(artifact)
        batch_size = self._config.ingestion.batch_size

        if frame.empty:
            yield IngestionBatch(
                dataset_name=artifact.dataset_name,
                source_path=artifact.path,
                batch_number=0,
                row_offset=0,
                frame=frame.copy(deep=True),
            )
            return

        offsets = range(
            0,
            len(frame),
            batch_size,
        )

        for batch_number, row_offset in enumerate(offsets):
            batch = frame.iloc[row_offset : row_offset + batch_size].copy(deep=True)

            yield IngestionBatch(
                dataset_name=artifact.dataset_name,
                source_path=artifact.path,
                batch_number=batch_number,
                row_offset=row_offset,
                frame=batch,
            )

    def ingest_run(
        self,
        run_id: str,
    ) -> dict[str, pd.DataFrame]:
        """Read every supported artifact from one source run."""
        run = self.load_run(run_id)
        artifacts = self.discover_artifacts(run)

        datasets: dict[str, list[pd.DataFrame]] = {}

        for artifact in artifacts:
            frame = self.read_artifact(artifact)

            datasets.setdefault(
                artifact.dataset_name,
                [],
            ).append(frame)

        combined: dict[str, pd.DataFrame] = {}

        for dataset_name in sorted(datasets):
            frames = datasets[dataset_name]

            if len(frames) == 1:
                combined[dataset_name] = frames[0].copy(deep=True)
            else:
                combined[dataset_name] = pd.concat(
                    frames,
                    axis=0,
                    ignore_index=True,
                    copy=False,
                )

        return combined


def discover_source_runs(
    config: ETLConfig,
) -> tuple[Path, ...]:
    """Return available source-run directories."""
    return SourceIngestor(config).discover_runs()


def load_source_run(
    config: ETLConfig,
    run_id: str,
) -> SourceRun:
    """Load one source run."""
    return SourceIngestor(config).load_run(run_id)


def discover_source_artifacts(
    config: ETLConfig,
    run: SourceRun,
) -> tuple[SourceArtifact, ...]:
    """Discover supported artifacts in one run."""
    return SourceIngestor(config).discover_artifacts(run)


def read_source_artifact(
    config: ETLConfig,
    artifact: SourceArtifact,
) -> pd.DataFrame:
    """Read one source artifact."""
    return SourceIngestor(config).read_artifact(artifact)


def iter_source_batches(
    config: ETLConfig,
    artifact: SourceArtifact,
) -> Iterator[IngestionBatch]:
    """Yield bounded batches from one source artifact."""
    yield from SourceIngestor(config).iter_batches(artifact)


def ingest_source_run(
    config: ETLConfig,
    run_id: str,
) -> dict[str, pd.DataFrame]:
    """Ingest all supported datasets from one source run."""
    return SourceIngestor(config).ingest_run(run_id)


def _normalize_run_id(
    run_id: str,
) -> str:
    """Normalize and validate a portable source run identifier."""
    if not isinstance(run_id, str):
        raise TypeError("run_id must be a string.")

    normalized = run_id.strip()

    if not normalized:
        raise ValueError("run_id cannot be empty.")

    if normalized in {".", ".."}:
        raise ValueError("run_id is unsafe.")

    if "/" in normalized or "\\" in normalized:
        raise ValueError("run_id cannot contain path separators.")

    return normalized


def _safe_child(
    root: Path,
    child_name: str,
) -> Path:
    """Return a child path guaranteed to remain below root."""
    child = root / child_name

    _ensure_within_root(
        child,
        root,
    )

    return child


def _ensure_within_root(
    path: Path,
    root: Path,
) -> None:
    """Reject filesystem paths outside an expected root."""
    resolved_root = root.resolve()
    resolved_path = path.resolve()

    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"Path is outside configured source root: {path}") from exc


def _read_json_mapping(
    path: Path,
) -> Mapping[str, Any]:
    """Read a UTF-8 JSON object from disk."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise OSError(f"Unable to read manifest: {path}") from exc

    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Manifest contains invalid JSON: {path}") from exc

    if not isinstance(value, dict):
        raise ValueError(f"Manifest root must be a JSON object: {path}")

    return value


def _dataset_name_from_path(
    *,
    path: Path,
    run_root: Path,
) -> str:
    """Derive a logical dataset name from a Phase 2 artifact path."""
    relative = path.relative_to(run_root)

    ignored_parts = {
        "master",
        "timeseries",
        "operations",
        "commercial",
        "truth",
        "validation",
    }

    candidate_parts: Sequence[str] = relative.parts[:-1]

    for part in reversed(candidate_parts):
        normalized = part.strip()

        if not normalized:
            continue

        if normalized.lower() in ignored_parts:
            continue

        if "=" in normalized:
            continue

        return normalized

    filename = path.stem

    if filename.startswith("part-"):
        parent = path.parent.name

        if parent and parent.lower() not in ignored_parts and "=" not in parent:
            return parent

    return filename


def _validate_non_negative_int(
    name: str,
    value: int,
) -> None:
    """Validate a non-negative integer."""
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError(f"{name} must be an integer.")

    if value < 0:
        raise ValueError(f"{name} must be greater than or equal to zero.")


__all__ = [
    "IngestionBatch",
    "MANIFEST_FILE_NAME",
    "SourceArtifact",
    "SourceIngestor",
    "SourceRun",
    "discover_source_artifacts",
    "discover_source_runs",
    "ingest_source_run",
    "iter_source_batches",
    "load_source_run",
    "read_source_artifact",
]
