"""
Deterministic manifest generation and artifact integrity for EOIP Phase 2.

This module owns manifest construction, SHA-256 checksum calculation, and
manifest JSON serialization for one completed synthetic generation run.

Responsibilities
----------------
- build a machine-readable manifest describing the generation run;
- compute per-file SHA-256 checksums for all written artifacts;
- compute a deterministic aggregate dataset fingerprint;
- write the manifest atomically as UTF-8 JSON with deterministic key ordering;
- read back and validate a previously written manifest.

This module never generates synthetic data, mutates generated data, performs
dataset validation, writes Parquet datasets, publishes staging directories,
accesses PostgreSQL, or implements CLI behavior.
"""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eoip.core.exceptions import DataGenerationError
from eoip.synthetic.config import GenerationConfig
from eoip.synthetic.generator import GenerationSummary
from eoip.synthetic.io import DatasetWriteResult
from eoip.synthetic.random import RandomContext
from eoip.synthetic.validation import ValidationReport

# ---------------------------------------------------------------------------
# Manifest schema version
# ---------------------------------------------------------------------------

MANIFEST_SCHEMA_VERSION: str = "1.0.0"

# ---------------------------------------------------------------------------
# Frozen manifest dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ArtifactManifest:
    """Portable metadata for one written artifact file."""

    relative_path: str
    dataset_name: str
    dataset_family: str
    row_count: int
    column_names: tuple[str, ...]
    byte_size: int
    sha256: str
    min_timestamp: datetime | None = None
    max_timestamp: datetime | None = None


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    """Portable metadata for one written dataset."""

    dataset_name: str
    family: str
    row_count: int
    column_names: tuple[str, ...]
    file_count: int
    total_bytes: int
    min_timestamp: datetime | None = None
    max_timestamp: datetime | None = None
    artifacts: tuple[ArtifactManifest, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Manifest:
    """Complete immutable manifest for one generation run."""

    # A. Manifest identity
    manifest_schema_version: str
    generation_run_id: str
    created_at: datetime
    project_name: str
    project_version: str

    # B. Generation configuration
    profile_name: str
    seed: int
    generation_start: str
    generation_end: str
    interval_minutes: int
    plant_count: int
    config_fingerprint: str
    normalized_config: dict[str, Any]

    # C. Randomness metadata
    random_context_manifest: dict[str, Any]

    # D. Dataset summary
    generation_summary: dict[str, Any]

    # E. Validation summary
    validation_passed: bool
    validation_error_count: int
    validation_warning_count: int
    validation_issue_count: int
    validation_results: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    validation_issues: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    # F. Artifact inventory
    datasets: tuple[DatasetManifest, ...] = field(default_factory=tuple)

    # G. Aggregate run integrity (deterministic, excludes created_at)
    aggregate_dataset_fingerprint: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""
        return _manifest_to_dict(self)


# ---------------------------------------------------------------------------
# Checksum helper
# ---------------------------------------------------------------------------


def sha256_file(path: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
    """Return the lowercase hexadecimal SHA-256 of a file, streamed in chunks.

    Parameters
    ----------
    path:
        Path to the file to hash.
    chunk_size:
        Number of bytes to read per chunk. Defaults to 4 MiB.

    Returns
    -------
    str
        Lowercase hexadecimal SHA-256 digest.

    Raises
    ------
    DataGenerationError
        If the file cannot be read.
    """
    path = Path(path)
    if not path.is_file():
        raise DataGenerationError(f"Cannot checksum missing file: '{path}'.")
    h = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while True:
                chunk = stream.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
    except OSError as exc:
        raise DataGenerationError(
            f"Failed to read '{path}' for checksum: {exc}"
        ) from exc
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Manifest builder
# ---------------------------------------------------------------------------


def build_manifest(
    *,
    config: GenerationConfig,
    random_context: RandomContext,
    summary: GenerationSummary,
    validation_report: ValidationReport,
    write_results: tuple[DatasetWriteResult, ...],
    created_at: datetime | None = None,
) -> Manifest:
    """Build a deterministic manifest for one completed generation run.

    Parameters
    ----------
    config:
        The generation configuration used for this run.
    random_context:
        The random context used for this run.
    summary:
        Row-count summary for every generated dataset.
    validation_report:
        Complete validation report for this run.
    write_results:
        Structured write results for every published dataset artifact.
    created_at:
        Observational creation timestamp. Defaults to ``datetime.now(UTC)``.

    Returns
    -------
    Manifest
        Immutable manifest dataclass.

    Raises
    ------
    TypeError
        If any argument has the wrong type.
    """
    if not isinstance(config, GenerationConfig):
        raise TypeError(
            f"config must be a GenerationConfig, got {type(config).__name__}."
        )
    if not isinstance(random_context, RandomContext):
        raise TypeError(
            f"random_context must be a RandomContext, "
            f"got {type(random_context).__name__}."
        )
    if not isinstance(summary, GenerationSummary):
        raise TypeError(
            f"summary must be a GenerationSummary, got {type(summary).__name__}."
        )
    if not isinstance(validation_report, ValidationReport):
        raise TypeError(
            f"validation_report must be a ValidationReport, "
            f"got {type(validation_report).__name__}."
        )
    if not isinstance(write_results, tuple):
        raise TypeError(
            f"write_results must be a tuple, got {type(write_results).__name__}."
        )
    for idx, result in enumerate(write_results):
        if not isinstance(result, DatasetWriteResult):
            raise TypeError(
                f"write_results[{idx}] must be a DatasetWriteResult, "
                f"got {type(result).__name__}."
            )

    if created_at is None:
        created_at = datetime.now(UTC)

    # Early validation complete - proceed with manifest construction

    # A. Manifest identity
    generation_run_id = summary.generation_run_id

    # B. Normalized configuration (already JSON-compatible)
    normalized_config = config.to_dict()

    # C. Randomness metadata (reuse RandomContext.manifest())
    random_manifest = random_context.manifest()

    # D. Generation summary (reuse GenerationSummary.to_record())
    summary_record = summary.to_record()

    # E. Validation summary
    validation_passed = validation_report.passed
    validation_results = tuple(result.to_dict() for result in validation_report.results)
    validation_issues = tuple(issue.to_dict() for issue in validation_report.issues)

    # F. Artifact inventory
    datasets = _build_dataset_manifests(write_results)

    # G. Deterministic aggregate dataset fingerprint
    aggregate_fingerprint = _compute_aggregate_fingerprint(
        configuration_fingerprint=config.fingerprint(),
        datasets=datasets,
        summary=summary_record,
    )

    return Manifest(
        manifest_schema_version=MANIFEST_SCHEMA_VERSION,
        generation_run_id=generation_run_id,
        created_at=created_at,
        project_name="Energy Operations Intelligence Platform",
        project_version="0.1.0",
        profile_name=config.profile_name.value,
        seed=config.seed,
        generation_start=config.time.start.isoformat().replace("+00:00", "Z"),
        generation_end=config.time.end.isoformat().replace("+00:00", "Z"),
        interval_minutes=config.time.interval_minutes,
        plant_count=config.portfolio.plant_count,
        config_fingerprint=config.fingerprint(),
        normalized_config=normalized_config,
        random_context_manifest=random_manifest,
        generation_summary=summary_record,
        validation_passed=validation_passed,
        validation_error_count=validation_report.error_count,
        validation_warning_count=validation_report.warning_count,
        validation_issue_count=validation_report.issue_count,
        validation_results=validation_results,
        validation_issues=validation_issues,
        datasets=datasets,
        aggregate_dataset_fingerprint=aggregate_fingerprint,
    )


# ---------------------------------------------------------------------------
# Manifest writing
# ---------------------------------------------------------------------------


def write_manifest(manifest: Manifest, path: Path) -> Path:
    """Write *manifest* to *path* atomically as deterministic UTF-8 JSON.

    The manifest is first written to ``<path>.tmp`` and then moved into
    place with :func:`os.replace` so that a partially written manifest is
    never observed.

    Parameters
    ----------
    manifest:
        The manifest to serialize.
    path:
        Target manifest file path (typically ``manifest.json``).

    Returns
    -------
    Path
        The resolved path where the manifest was written.

    Raises
    ------
    DataGenerationError
        If the write or atomic move fails.
    """
    path = Path(path)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        payload = json.dumps(
            manifest.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        tmp_path.write_bytes(payload + b"\n")
        os.replace(tmp_path, path)
    except OSError as exc:
        # Clean up temp file if it still exists
        if tmp_path.exists():
            with suppress(OSError):
                tmp_path.unlink()
        raise DataGenerationError(
            f"Failed to write manifest to '{path}': {exc}"
        ) from exc
    return path


# ---------------------------------------------------------------------------
# Manifest reading
# ---------------------------------------------------------------------------


def read_manifest(path: Path) -> Manifest:
    """Read and validate a previously written manifest.

    Parameters
    ----------
    path:
        Path to a ``manifest.json`` file.

    Returns
    -------
    Manifest
        The deserialized immutable manifest.

    Raises
    ------
    DataGenerationError
        If the file is missing, malformed, or has an unsupported schema version.
    """
    path = Path(path)
    if not path.is_file():
        raise DataGenerationError(f"Manifest file not found: '{path}'.")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise DataGenerationError(f"Failed to read manifest '{path}': {exc}") from exc
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise DataGenerationError(
            f"Malformed JSON in manifest '{path}': {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise DataGenerationError(
            f"Manifest '{path}' must be a JSON object, got {type(data).__name__}."
        )
    version = data.get("manifest_schema_version")
    if version != MANIFEST_SCHEMA_VERSION:
        raise DataGenerationError(
            f"Unsupported manifest schema version '{version}'. "
            f"Expected '{MANIFEST_SCHEMA_VERSION}'."
        )
    try:
        return _dict_to_manifest(data)
    except (TypeError, ValueError, KeyError) as exc:
        raise DataGenerationError(
            f"Invalid manifest structure in '{path}': {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Artifact verification helper
# ---------------------------------------------------------------------------


def verify_manifest_artifacts(
    manifest: Manifest, run_root: Path
) -> tuple[bool, list[str]]:
    """Verify that all physical artifacts described in *manifest* exist and
    match their recorded SHA-256 checksums.

    Parameters
    ----------
    manifest:
        The manifest to verify.
    run_root:
        Root directory of the published run (parent of ``manifest.json``).

    Returns
    -------
    tuple[bool, list[str]]
        A tuple of ``(all_ok, errors)`` where *all_ok* is ``True`` when every
        artifact is present and matches its checksum, and *errors* is a list
        of human-readable problem descriptions.
    """
    errors: list[str] = []
    for dataset in manifest.datasets:
        for artifact in dataset.artifacts:
            artifact_path = run_root / artifact.relative_path
            if not artifact_path.is_file():
                errors.append(
                    f"Missing artifact: '{artifact.relative_path}' "
                    f"(dataset '{dataset.dataset_name}')."
                )
                continue
            actual_checksum = sha256_file(artifact_path)
            if actual_checksum != artifact.sha256:
                errors.append(
                    f"Checksum mismatch for '{artifact.relative_path}': "
                    f"expected {artifact.sha256}, got {actual_checksum}."
                )
    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_dataset_manifests(
    write_results: tuple[DatasetWriteResult, ...],
) -> tuple[DatasetManifest, ...]:
    """Convert DatasetWriteResult objects into immutable DatasetManifest objects."""
    datasets: list[DatasetManifest] = []
    for result in write_results:
        artifacts = tuple(
            ArtifactManifest(
                relative_path=str(
                    result_path.relative_to(result_path.anchor)
                    if result_path.is_absolute()
                    else result_path
                ),
                dataset_name=result.dataset_name,
                dataset_family=result.family,
                row_count=artifact.row_count,
                column_names=result.column_names,
                byte_size=artifact.byte_size,
                sha256=sha256_file(artifact.path),
                min_timestamp=result.min_timestamp,
                max_timestamp=result.max_timestamp,
            )
            for artifact, result_path in zip(
                result.artifacts, result.relative_paths, strict=True
            )
        )
        datasets.append(
            DatasetManifest(
                dataset_name=result.dataset_name,
                family=result.family,
                row_count=result.row_count,
                column_names=result.column_names,
                file_count=result.file_count,
                total_bytes=result.total_bytes,
                min_timestamp=result.min_timestamp,
                max_timestamp=result.max_timestamp,
                artifacts=artifacts,
            )
        )
    return tuple(datasets)


def _compute_aggregate_fingerprint(
    *,
    configuration_fingerprint: str,
    datasets: tuple[DatasetManifest, ...],
    summary: dict[str, Any],
) -> str:
    """Compute a deterministic aggregate fingerprint for the published dataset.

    The fingerprint is derived from stable information only:
    - configuration fingerprint
    - sorted artifact relative paths
    - artifact SHA-256 values
    - row counts from the generation summary

    It deliberately excludes observational metadata such as ``created_at``.
    """
    h = hashlib.sha256()
    h.update(configuration_fingerprint.encode("ascii"))
    h.update(b".")
    # Stable ordering: sort by dataset name, then by relative path within dataset
    for dataset in sorted(datasets, key=lambda d: d.dataset_name):
        h.update(dataset.dataset_name.encode("utf-8"))
        h.update(b":")
        h.update(str(dataset.row_count).encode("ascii"))
        h.update(b":")
        for artifact in sorted(dataset.artifacts, key=lambda a: a.relative_path):
            h.update(artifact.relative_path.encode("utf-8"))
            h.update(b"=")
            h.update(artifact.sha256.encode("ascii"))
            h.update(b";")
    # Include summary row counts for additional stability
    h.update(b"summary:")
    for key in sorted(summary):
        h.update(key.encode("utf-8"))
        h.update(b"=")
        h.update(str(summary[key]).encode("utf-8"))
        h.update(b";")
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _manifest_to_dict(manifest: Manifest) -> dict[str, Any]:
    """Convert a Manifest to a JSON-serializable dictionary."""
    return {
        "manifest_schema_version": manifest.manifest_schema_version,
        "generation_run_id": manifest.generation_run_id,
        "created_at": manifest.created_at.isoformat().replace("+00:00", "Z"),
        "project_name": manifest.project_name,
        "project_version": manifest.project_version,
        "profile_name": manifest.profile_name,
        "seed": manifest.seed,
        "generation_start": manifest.generation_start,
        "generation_end": manifest.generation_end,
        "interval_minutes": manifest.interval_minutes,
        "plant_count": manifest.plant_count,
        "config_fingerprint": manifest.config_fingerprint,
        "normalized_config": manifest.normalized_config,
        "random_context_manifest": manifest.random_context_manifest,
        "generation_summary": manifest.generation_summary,
        "validation_passed": manifest.validation_passed,
        "validation_error_count": manifest.validation_error_count,
        "validation_warning_count": manifest.validation_warning_count,
        "validation_issue_count": manifest.validation_issue_count,
        "validation_results": list(manifest.validation_results),
        "validation_issues": list(manifest.validation_issues),
        "datasets": [_dataset_manifest_to_dict(d) for d in manifest.datasets],
        "aggregate_dataset_fingerprint": manifest.aggregate_dataset_fingerprint,
    }


def _dataset_manifest_to_dict(dataset: DatasetManifest) -> dict[str, Any]:
    """Convert a DatasetManifest to a JSON-serializable dictionary."""
    return {
        "dataset_name": dataset.dataset_name,
        "family": dataset.family,
        "row_count": dataset.row_count,
        "column_names": list(dataset.column_names),
        "file_count": dataset.file_count,
        "total_bytes": dataset.total_bytes,
        "min_timestamp": _datetime_to_iso(dataset.min_timestamp),
        "max_timestamp": _datetime_to_iso(dataset.max_timestamp),
        "artifacts": [_artifact_manifest_to_dict(a) for a in dataset.artifacts],
    }


def _artifact_manifest_to_dict(artifact: ArtifactManifest) -> dict[str, Any]:
    """Convert an ArtifactManifest to a JSON-serializable dictionary."""
    return {
        "relative_path": artifact.relative_path,
        "dataset_name": artifact.dataset_name,
        "dataset_family": artifact.dataset_family,
        "row_count": artifact.row_count,
        "column_names": list(artifact.column_names),
        "byte_size": artifact.byte_size,
        "sha256": artifact.sha256,
        "min_timestamp": _datetime_to_iso(artifact.min_timestamp),
        "max_timestamp": _datetime_to_iso(artifact.max_timestamp),
    }


def _datetime_to_iso(value: datetime | None) -> str | None:
    """Convert a datetime to ISO-8601 with Z suffix, or None."""
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Deserialization helpers
# ---------------------------------------------------------------------------


def _dict_to_manifest(data: dict[str, Any]) -> Manifest:
    """Reconstruct a Manifest from a validated dictionary."""
    datasets = tuple(_dict_to_dataset_manifest(d) for d in data.get("datasets", []))
    return Manifest(
        manifest_schema_version=data["manifest_schema_version"],
        generation_run_id=data["generation_run_id"],
        created_at=_iso_to_datetime(data["created_at"]),
        project_name=data["project_name"],
        project_version=data["project_version"],
        profile_name=data["profile_name"],
        seed=data["seed"],
        generation_start=data["generation_start"],
        generation_end=data["generation_end"],
        interval_minutes=data["interval_minutes"],
        plant_count=data["plant_count"],
        config_fingerprint=data["config_fingerprint"],
        normalized_config=data["normalized_config"],
        random_context_manifest=data["random_context_manifest"],
        generation_summary=data["generation_summary"],
        validation_passed=data["validation_passed"],
        validation_error_count=data["validation_error_count"],
        validation_warning_count=data["validation_warning_count"],
        validation_issue_count=data["validation_issue_count"],
        validation_results=tuple(data.get("validation_results", [])),
        validation_issues=tuple(data.get("validation_issues", [])),
        datasets=datasets,
        aggregate_dataset_fingerprint=data["aggregate_dataset_fingerprint"],
    )


def _dict_to_dataset_manifest(data: dict[str, Any]) -> DatasetManifest:
    """Reconstruct a DatasetManifest from a dictionary."""
    artifacts = tuple(
        ArtifactManifest(
            relative_path=a["relative_path"],
            dataset_name=a["dataset_name"],
            dataset_family=a["dataset_family"],
            row_count=a["row_count"],
            column_names=tuple(a["column_names"]),
            byte_size=a["byte_size"],
            sha256=a["sha256"],
            min_timestamp=_iso_to_datetime(a.get("min_timestamp")),
            max_timestamp=_iso_to_datetime(a.get("max_timestamp")),
        )
        for a in data.get("artifacts", [])
    )
    return DatasetManifest(
        dataset_name=data["dataset_name"],
        family=data["family"],
        row_count=data["row_count"],
        column_names=tuple(data["column_names"]),
        file_count=data["file_count"],
        total_bytes=data["total_bytes"],
        min_timestamp=_iso_to_datetime(data.get("min_timestamp")),
        max_timestamp=_iso_to_datetime(data.get("max_timestamp")),
        artifacts=artifacts,
    )


def _iso_to_datetime(value: str | None) -> datetime | None:
    """Parse an ISO-8601 datetime string with Z suffix, or return None."""
    if value is None:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return dt.astimezone(UTC)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "MANIFEST_SCHEMA_VERSION",
    "ArtifactManifest",
    "DatasetManifest",
    "Manifest",
    "build_manifest",
    "sha256_file",
    "verify_manifest_artifacts",
    "write_manifest",
    "read_manifest",
]
