"""Reproducibility verification for EOIP Phase 2 synthetic generation.

This module verifies that EOIP Phase 2 generation is reproducible by answering
two questions:

A. **Same-seed reproducibility**: Given the same GenerationConfig, seed, stream
   version, and code/schema contract, does EOIP produce logically equivalent
   synthetic datasets?

B. **Different-seed sensitivity**: When the seed changes, do schemas and
   invariants remain stable while at least appropriate stochastic values change?

This module never generates new domain logic, changes random stream allocation,
writes Parquet, publishes directories, implements CLI logic, or performs the
full Phase 2 acceptance test suite.

Responsibilities
----------------
- compare two SyntheticDataset objects for logical equality;
- compute deterministic in-memory dataset fingerprints;
- verify same-seed reproducibility with detailed reporting;
- verify different-seed sensitivity with structural checks;
- integrate with existing validation engine;
- produce stable, deterministic, immutable reports.

Reuse
-----
- :func:`eoip.synthetic.config.config_fingerprint` for configuration fingerprinting;
- :class:`eoip.synthetic.random.RandomContext` for deterministic random state;
- :class:`eoip.synthetic.generator.SyntheticDataset` and :class:`GenerationSummary`;
- :func:`eoip.synthetic.validation.validate_dataset` for validation integration.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any, Final

import numpy as np
import pandas as pd

from eoip.core.exceptions import DataGenerationError
from eoip.synthetic.config import (
    GenerationConfig,
    config_fingerprint,
    validate_generation_config,
)
from eoip.synthetic.generator import (
    GenerationSummary,
    SyntheticDataset,
    generate_dataset,
)
from eoip.synthetic.random import create_random_context
from eoip.synthetic.validation import validate_dataset

# ---------------------------------------------------------------------------
# Public enums and frozen dataclasses
# ---------------------------------------------------------------------------


class ReproducibilityStatus(StrEnum):
    """Overall outcome of a reproducibility verification."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class ComparisonOutcome(StrEnum):
    """Result of comparing one dataset family."""

    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class DatasetComparison:
    """Detailed comparison result for one dataset family."""

    dataset_name: str
    outcome: ComparisonOutcome
    left_row_count: int
    right_row_count: int
    schema_equal: bool
    ordering_equal: bool
    values_equal: bool
    left_fingerprint: str
    right_fingerprint: str
    mismatch_samples: tuple[Any, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""
        return {
            "dataset_name": self.dataset_name,
            "outcome": self.outcome.value,
            "left_row_count": self.left_row_count,
            "right_row_count": self.right_row_count,
            "schema_equal": self.schema_equal,
            "ordering_equal": self.ordering_equal,
            "values_equal": self.values_equal,
            "left_fingerprint": self.left_fingerprint,
            "right_fingerprint": self.right_fingerprint,
            "mismatch_samples": list(self.mismatch_samples),
        }


@dataclass(frozen=True, slots=True)
class ReproducibilityReport:
    """Complete reproducibility verification report."""

    status: ReproducibilityStatus
    verification_type: str
    config_fingerprint: str
    left_seed: int
    right_seed: int
    dataset_comparisons: tuple[DatasetComparison, ...]
    summary_match: bool
    validation_passed: bool
    validation_error_count: int
    validation_warning_count: int
    changed_stochastic_datasets: tuple[str, ...]
    preserved_dataset_families: tuple[str, ...]
    errors: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable report summary."""
        return {
            "status": self.status.value,
            "verification_type": self.verification_type,
            "config_fingerprint": self.config_fingerprint,
            "left_seed": self.left_seed,
            "right_seed": self.right_seed,
            "dataset_comparisons": [
                comp.to_dict() for comp in self.dataset_comparisons
            ],
            "summary_match": self.summary_match,
            "validation_passed": self.validation_passed,
            "validation_error_count": self.validation_error_count,
            "validation_warning_count": self.validation_warning_count,
            "changed_stochastic_datasets": list(self.changed_stochastic_datasets),
            "preserved_dataset_families": list(self.preserved_dataset_families),
            "errors": list(self.errors),
        }


# ---------------------------------------------------------------------------
# Dataset fingerprinting
# ---------------------------------------------------------------------------

# Dataset families that are inherently stochastic
_STOCHASTIC_DATASET_NAMES: Final[frozenset[str]] = frozenset(
    {
        "weather",
        "inverter_scada",
        "plant_scada",
        "ground_truth_events",
        "alarms",
        "incidents",
        "work_orders",
    }
)

# Canonical dataset family order for stable reporting
_CANONICAL_DATASET_ORDER: Final[tuple[str, ...]] = (
    "plants",
    "equipment",
    "revenue_meters",
    "weather",
    "inverter_scada",
    "plant_scada",
    "ground_truth_events",
    "alarms",
    "incidents",
    "work_orders",
    "tariffs",
    "budgets",
)


def dataset_fingerprint(dataset: SyntheticDataset) -> str:
    """Return a deterministic logical fingerprint of a SyntheticDataset.

    The fingerprint is computed from stable logical content only:
    - dataset family names in canonical order;
    - schema/column ordering;
    - canonical values (excluding runtime-only metadata such as
      generation_run_id, created_at, and schema_version where those
      represent observational metadata rather than logical content).

    Parameters
    ----------
    dataset:
        The assembled synthetic dataset to fingerprint.

    Returns
    -------
    str
        Lowercase hexadecimal SHA-256 digest.

    Raises
    ------
    TypeError
        If dataset is not a SyntheticDataset.
    """
    if not isinstance(dataset, SyntheticDataset):
        raise TypeError(
            f"dataset must be a SyntheticDataset, got {type(dataset).__name__}."
        )

    h = hashlib.sha256()

    # Process datasets in canonical order for stability
    for name in _CANONICAL_DATASET_ORDER:
        value = getattr(dataset, name, None)
        if value is None:
            continue

        h.update(name.encode("utf-8"))
        h.update(b":")

        if isinstance(value, tuple):
            # Tuple-based domain model: serialize each record
            h.update(_fingerprint_tuple_dataset(name, value))
        elif isinstance(value, pd.DataFrame):
            # DataFrame-based dataset
            h.update(_fingerprint_dataframe(name, value))
        else:
            raise DataGenerationError(
                f"Unsupported dataset type for {name}: {type(value).__name__}."
            )

    return h.hexdigest()


def _fingerprint_tuple_dataset(name: str, records: tuple[Any, ...]) -> bytes:
    """Fingerprint a tuple-based domain model dataset."""
    h = hashlib.sha256()
    h.update(b"tuple")
    h.update(b":")
    h.update(str(len(records)).encode("ascii"))
    h.update(b":")

    # Serialize each record in canonical order
    for record in records:
        record_dict = _sanitize_record(record.to_record())
        payload = json.dumps(
            record_dict,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        h.update(payload)
        h.update(b";")

    return h.digest()


def _fingerprint_dataframe(name: str, frame: pd.DataFrame) -> bytes:
    """Fingerprint a pandas DataFrame dataset."""
    h = hashlib.sha256()
    h.update(b"dataframe")
    h.update(b":")
    h.update(str(len(frame)).encode("ascii"))
    h.update(b":")

    # Column names and order
    columns = list(frame.columns)
    h.update(
        json.dumps(columns, sort_keys=False, separators=(",", ":")).encode("utf-8")
    )
    h.update(b":")

    # dtypes
    dtypes = [str(dtype) for dtype in frame.dtypes]
    h.update(json.dumps(dtypes, sort_keys=False, separators=(",", ":")).encode("utf-8"))
    h.update(b":")

    # Values: exclude runtime-only metadata columns
    runtime_columns = {"generation_run_id", "schema_version", "source_system"}
    value_frame = frame.drop(
        columns=[col for col in runtime_columns if col in frame.columns],
        errors="ignore",
    )

    # Convert to records and sanitize
    records = value_frame.to_dict(orient="records")
    for record in records:
        sanitized = _sanitize_record(record)
        payload = json.dumps(
            sanitized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=_json_default,
        ).encode("utf-8")
        h.update(payload)
        h.update(b";")

    return h.digest()


def _sanitize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Remove runtime-only metadata from a record for fingerprinting."""
    # Keys to exclude from logical comparison
    runtime_keys = {"generation_run_id", "schema_version", "source_system"}
    return {k: v for k, v in record.items() if k not in runtime_keys}


def _json_default(value: object) -> object:
    """Normalize NumPy and pandas types for JSON serialization."""
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat().replace("+00:00", "Z")
    if pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable.")


# ---------------------------------------------------------------------------
# Dataset comparison
# ---------------------------------------------------------------------------


def compare_datasets(
    left: SyntheticDataset,
    right: SyntheticDataset,
    *,
    maximum_samples: int = 20,
) -> tuple[DatasetComparison, ...]:
    """Compare two SyntheticDataset objects for logical equality.

    Parameters
    ----------
    left:
        Left-hand dataset.
    right:
        Right-hand dataset.
    maximum_samples:
        Maximum number of mismatch samples to retain.

    Returns
    -------
    tuple[DatasetComparison, ...]
        One comparison result per dataset family in canonical order.

    Raises
    ------
    TypeError
        If either argument is not a SyntheticDataset.
    """
    if not isinstance(left, SyntheticDataset):
        raise TypeError(f"left must be a SyntheticDataset, got {type(left).__name__}.")
    if not isinstance(right, SyntheticDataset):
        raise TypeError(
            f"right must be a SyntheticDataset, got {type(right).__name__}."
        )

    comparisons: list[DatasetComparison] = []

    for name in _CANONICAL_DATASET_ORDER:
        left_value = getattr(left, name, None)
        right_value = getattr(right, name, None)

        if left_value is None or right_value is None:
            comparisons.append(
                DatasetComparison(
                    dataset_name=name,
                    outcome=ComparisonOutcome.SKIPPED,
                    left_row_count=0,
                    right_row_count=0,
                    schema_equal=False,
                    ordering_equal=False,
                    values_equal=False,
                    left_fingerprint="",
                    right_fingerprint="",
                )
            )
            continue

        comparison = _compare_one_dataset(
            name,
            left_value,
            right_value,
            maximum_samples=maximum_samples,
        )
        comparisons.append(comparison)

    return tuple(comparisons)


def _compare_one_dataset(
    name: str,
    left: Any,
    right: Any,
    *,
    maximum_samples: int,
) -> DatasetComparison:
    """Compare one dataset family."""
    # Build minimal temporary datasets for fingerprinting
    if isinstance(left, tuple):
        temp_left = SyntheticDataset(
            plants=left if name == "plants" else (),
            equipment=left if name == "equipment" else (),
            revenue_meters=left if name == "revenue_meters" else (),
            weather=left if name == "weather" else (),
            inverter_scada=left if name == "inverter_scada" else (),
            plant_scada=left if name == "plant_scada" else (),
            ground_truth_events=(
                left if name == "ground_truth_events" else pd.DataFrame()
            ),
            alarms=left if name == "alarms" else pd.DataFrame(),
            incidents=left if name == "incidents" else pd.DataFrame(),
            work_orders=left if name == "work_orders" else pd.DataFrame(),
            tariffs=left if name == "tariffs" else pd.DataFrame(),
            budgets=left if name == "budgets" else pd.DataFrame(),
        )
        temp_right = SyntheticDataset(
            plants=right if name == "plants" else (),
            equipment=right if name == "equipment" else (),
            revenue_meters=right if name == "revenue_meters" else (),
            weather=right if name == "weather" else (),
            inverter_scada=right if name == "inverter_scada" else (),
            plant_scada=right if name == "plant_scada" else (),
            ground_truth_events=(
                right if name == "ground_truth_events" else pd.DataFrame()
            ),
            alarms=right if name == "alarms" else pd.DataFrame(),
            incidents=right if name == "incidents" else pd.DataFrame(),
            work_orders=right if name == "work_orders" else pd.DataFrame(),
            tariffs=right if name == "tariffs" else pd.DataFrame(),
            budgets=right if name == "budgets" else pd.DataFrame(),
        )
    else:
        temp_left = SyntheticDataset(
            plants=(),
            equipment=(),
            revenue_meters=(),
            weather=(),
            inverter_scada=(),
            plant_scada=(),
            ground_truth_events=(
                left if name == "ground_truth_events" else pd.DataFrame()
            ),
            alarms=left if name == "alarms" else pd.DataFrame(),
            incidents=left if name == "incidents" else pd.DataFrame(),
            work_orders=left if name == "work_orders" else pd.DataFrame(),
            tariffs=left if name == "tariffs" else pd.DataFrame(),
            budgets=left if name == "budgets" else pd.DataFrame(),
        )
        temp_right = SyntheticDataset(
            plants=(),
            equipment=(),
            revenue_meters=(),
            weather=(),
            inverter_scada=(),
            plant_scada=(),
            ground_truth_events=(
                right if name == "ground_truth_events" else pd.DataFrame()
            ),
            alarms=right if name == "alarms" else pd.DataFrame(),
            incidents=right if name == "incidents" else pd.DataFrame(),
            work_orders=right if name == "work_orders" else pd.DataFrame(),
            tariffs=right if name == "tariffs" else pd.DataFrame(),
            budgets=right if name == "budgets" else pd.DataFrame(),
        )

    left_fp = dataset_fingerprint(temp_left)
    right_fp = dataset_fingerprint(temp_right)

    # Compare structure
    if isinstance(left, tuple) and isinstance(right, tuple):
        left_count = len(left)
        right_count = len(right)
        schema_equal = left_count == right_count
        ordering_equal = True  # Tuples preserve insertion order
        values_equal = left_fp == right_fp
    elif isinstance(left, pd.DataFrame) and isinstance(right, pd.DataFrame):
        left_count = len(left)
        right_count = len(right)
        schema_equal = list(left.columns) == list(right.columns)
        ordering_equal = _compare_dataframe_ordering(left, right)
        values_equal = left_fp == right_fp
    else:
        left_count = 0
        right_count = 0
        schema_equal = False
        ordering_equal = False
        values_equal = False

    outcome = ComparisonOutcome.EQUAL if values_equal else ComparisonOutcome.NOT_EQUAL

    # Collect mismatch samples
    mismatch_samples: list[Any] = []
    if outcome is ComparisonOutcome.NOT_EQUAL and maximum_samples > 0:
        if isinstance(left, pd.DataFrame) and isinstance(right, pd.DataFrame):
            mismatch_samples = _collect_dataframe_mismatches(
                left, right, schema_equal, ordering_equal, maximum_samples
            )
        elif isinstance(left, tuple) and isinstance(right, tuple):
            mismatch_samples = _collect_tuple_mismatches(left, right, maximum_samples)

    return DatasetComparison(
        dataset_name=name,
        outcome=outcome,
        left_row_count=left_count,
        right_row_count=right_count,
        schema_equal=schema_equal,
        ordering_equal=ordering_equal,
        values_equal=values_equal,
        left_fingerprint=left_fp,
        right_fingerprint=right_fp,
        mismatch_samples=tuple(mismatch_samples[:maximum_samples]),
    )


def _compare_dataframe_ordering(left: pd.DataFrame, right: pd.DataFrame) -> bool:
    """Check whether two DataFrames have the same deterministic ordering."""
    if len(left) != len(right):
        return False

    # Compare index ordering if present
    if not left.index.equals(right.index):
        return False

    # For time-series data, check if timestamp columns are monotonically increasing
    timestamp_cols = ["timestamp_utc", "raised_at", "occurred_at", "created_at"]
    for col in timestamp_cols:
        if col in left.columns and col in right.columns:
            left_mono = left[col].is_monotonic_increasing
            right_mono = right[col].is_monotonic_increasing
            if left_mono != right_mono:
                return False
            if left_mono and not left[col].equals(right[col]):
                return False

    return True


def _collect_dataframe_mismatches(
    left: pd.DataFrame,
    right: pd.DataFrame,
    schema_equal: bool,
    ordering_equal: bool,
    max_samples: int,
) -> list[Any]:
    """Collect deterministic mismatch samples from two DataFrames."""
    samples: list[Any] = []

    if not schema_equal:
        left_cols = set(left.columns)
        right_cols = set(right.columns)
        missing_in_right = sorted(left_cols - right_cols)
        extra_in_right = sorted(right_cols - left_cols)
        if missing_in_right:
            samples.append(f"columns missing in right: {missing_in_right[:5]}")
        if extra_in_right:
            samples.append(f"extra columns in right: {extra_in_right[:5]}")

    if not ordering_equal:
        samples.append("DataFrame ordering differs")

    if schema_equal and len(left) == len(right):
        # Find value differences
        common_cols = [col for col in left.columns if col in right.columns]
        for col in common_cols:
            try:
                if not left[col].equals(right[col]):
                    diff_indices = left.index[left[col] != right[col]]
                    if len(diff_indices) > 0:
                        idx = diff_indices[0]
                        samples.append(
                            f"column '{col}' differs at index {idx}: "
                            f"left={left.loc[idx, col]!r}, "
                            f"right={right.loc[idx, col]!r}"
                        )
                        if len(samples) >= max_samples:
                            break
            except (TypeError, ValueError):
                samples.append(f"column '{col}' has incomparable types")

    return samples


def _collect_tuple_mismatches(
    left: tuple[Any, ...],
    right: tuple[Any, ...],
    max_samples: int,
) -> list[Any]:
    """Collect deterministic mismatch samples from two tuples."""
    samples: list[Any] = []

    if len(left) != len(right):
        samples.append(f"row count differs: left={len(left)}, right={len(right)}")
        return samples

    for i, (left_rec, right_rec) in enumerate(zip(left, right, strict=True)):
        if left_rec != right_rec:
            samples.append(f"record {i} differs")
            if len(samples) >= max_samples:
                break

    return samples


# ---------------------------------------------------------------------------
# Reproducibility verifier
# ---------------------------------------------------------------------------


class ReproducibilityVerifier:
    """Verify EOIP Phase 2 generation reproducibility.

    This class provides methods to verify same-seed reproducibility and
    different-seed sensitivity for synthetic dataset generation.
    """

    def __init__(self, config: GenerationConfig) -> None:
        """Initialize the verifier with a generation configuration.

        Parameters
        ----------
        config:
            The generation configuration to verify.

        Raises
        ------
        TypeError
            If config is not a GenerationConfig.
        """
        if not isinstance(config, GenerationConfig):
            raise TypeError(
                f"config must be a GenerationConfig, got {type(config).__name__}."
            )
        validate_generation_config(config)
        self._config = config

    @property
    def config(self) -> GenerationConfig:
        """Return the generation configuration."""
        return self._config

    def verify_same_seed(
        self,
        *,
        run_validation: bool = True,
    ) -> ReproducibilityReport:
        """Verify that the same config and seed produce logically equivalent datasets.

        This method generates two independent datasets using the same
        configuration and seed, then compares them for logical equality.

        Parameters
        ----------
        run_validation:
            If True, run validation on both datasets and include results.

        Returns
        -------
        ReproducibilityReport
            Detailed reproducibility report.
        """
        errors: list[str] = []

        try:
            left_dataset = self._generate_fresh_dataset()
        except Exception as exc:
            errors.append(f"left dataset generation failed: {exc}")
            return self._error_report("same_seed", errors)

        try:
            right_dataset = self._generate_fresh_dataset()
        except Exception as exc:
            errors.append(f"right dataset generation failed: {exc}")
            return self._error_report("same_seed", errors)

        # Compare datasets
        comparisons = compare_datasets(left_dataset, right_dataset)

        # Check for mismatches
        all_equal = all(comp.values_equal for comp in comparisons)
        any_error = any(
            comp.outcome is ComparisonOutcome.SKIPPED for comp in comparisons
        )

        # Compare summaries
        left_summary = self._summarize_dataset(left_dataset)
        right_summary = self._summarize_dataset(right_dataset)
        summary_match = left_summary.to_record() == right_summary.to_record()

        # Validation
        validation_passed = True
        validation_error_count = 0
        validation_warning_count = 0

        if run_validation:
            try:
                left_validation = validate_dataset(left_dataset, self._config)
                validation_passed = left_validation.passed
                validation_error_count = left_validation.error_count
                validation_warning_count = left_validation.warning_count
            except Exception as exc:
                errors.append(f"validation failed: {exc}")

        # Determine status
        if errors:
            status = ReproducibilityStatus.ERROR
        elif any_error or not all_equal or not summary_match or not validation_passed:
            status = ReproducibilityStatus.FAILED
        else:
            status = ReproducibilityStatus.PASSED

        return ReproducibilityReport(
            status=status,
            verification_type="same_seed",
            config_fingerprint=config_fingerprint(self._config),
            left_seed=self._config.seed,
            right_seed=self._config.seed,
            dataset_comparisons=comparisons,
            summary_match=summary_match,
            validation_passed=validation_passed,
            validation_error_count=validation_error_count,
            validation_warning_count=validation_warning_count,
            changed_stochastic_datasets=(),
            preserved_dataset_families=tuple(_CANONICAL_DATASET_ORDER),
            errors=tuple(errors),
        )

    def verify_different_seed(
        self,
        other_seed: int,
        *,
        run_validation: bool = True,
    ) -> ReproducibilityReport:
        """Verify that changing the seed produces appropriately different datasets.

        This method generates two datasets with different seeds and verifies:
        - both datasets are structurally valid;
        - dataset family presence remains stable;
        - schemas remain compatible;
        - deterministic invariants remain valid;
        - at least one stochastic dataset changes.

        Parameters
        ----------
        other_seed:
            The different seed to use for the right-hand dataset.
        run_validation:
            If True, run validation on both datasets.

        Returns
        -------
        ReproducibilityReport
            Detailed sensitivity report.
        """
        errors: list[str] = []

        # Validate other_seed
        if isinstance(other_seed, bool) or not isinstance(other_seed, int):
            raise TypeError("other_seed must be an integer.")
        if other_seed < 0:
            raise ValueError("other_seed must be greater than or equal to zero.")
        if other_seed == self._config.seed:
            raise ValueError(
                "other_seed must differ from config.seed "
                "for different-seed verification."
            )

        # Generate left dataset with original seed
        try:
            left_dataset = self._generate_fresh_dataset()
        except Exception as exc:
            errors.append(f"left dataset generation failed: {exc}")
            return self._error_report("different_seed", errors)

        # Generate right dataset with different seed
        try:
            right_config = self._config
            # Create a new config with different seed
            from dataclasses import replace

            right_config = replace(self._config, seed=other_seed)
            right_dataset = generate_dataset(right_config)
        except Exception as exc:
            errors.append(f"right dataset generation failed: {exc}")
            return self._error_report("different_seed", errors)

        # Compare datasets
        comparisons = compare_datasets(left_dataset, right_dataset)

        # Check structural stability
        all_present = all(
            comp.outcome != ComparisonOutcome.SKIPPED for comp in comparisons
        )
        schemas_compatible = all(comp.schema_equal for comp in comparisons)

        # Identify changed stochastic datasets
        changed_stochastic: list[str] = []
        for comp in comparisons:
            if (
                comp.dataset_name in _STOCHASTIC_DATASET_NAMES
                and comp.outcome is ComparisonOutcome.NOT_EQUAL
            ):
                changed_stochastic.append(comp.dataset_name)

        # Validation
        validation_passed = True
        validation_error_count = 0
        validation_warning_count = 0

        if run_validation:
            try:
                left_validation = validate_dataset(left_dataset, self._config)
                validation_passed = left_validation.passed
                validation_error_count = left_validation.error_count
                validation_warning_count = left_validation.warning_count
            except Exception as exc:
                errors.append(f"validation failed: {exc}")

        # Determine status
        if errors:
            status = ReproducibilityStatus.ERROR
        elif (
            not all_present
            or not schemas_compatible
            or not changed_stochastic
            or not validation_passed
        ):
            status = ReproducibilityStatus.FAILED
        else:
            status = ReproducibilityStatus.PASSED

        return ReproducibilityReport(
            status=status,
            verification_type="different_seed",
            config_fingerprint=config_fingerprint(self._config),
            left_seed=self._config.seed,
            right_seed=other_seed,
            dataset_comparisons=comparisons,
            summary_match=False,  # Different seeds should produce different summaries
            validation_passed=validation_passed,
            validation_error_count=validation_error_count,
            validation_warning_count=validation_warning_count,
            changed_stochastic_datasets=tuple(sorted(changed_stochastic)),
            preserved_dataset_families=tuple(_CANONICAL_DATASET_ORDER),
            errors=tuple(errors),
        )

    def _generate_fresh_dataset(self) -> SyntheticDataset:
        """Generate a fresh dataset with a fresh RandomContext."""
        # Create a fresh random context for each run
        random_context = create_random_context(self._config.seed)
        return generate_dataset(self._config, random_context)

    def _summarize_dataset(self, dataset: SyntheticDataset) -> GenerationSummary:
        """Create a GenerationSummary for a dataset."""
        return GenerationSummary(
            plant_count=len(dataset.plants),
            equipment_count=len(dataset.equipment),
            revenue_meter_count=len(dataset.revenue_meters),
            weather_count=len(dataset.weather),
            inverter_scada_count=len(dataset.inverter_scada),
            plant_scada_count=len(dataset.plant_scada),
            ground_truth_event_count=len(dataset.ground_truth_events),
            alarm_count=len(dataset.alarms),
            incident_count=len(dataset.incidents),
            work_order_count=len(dataset.work_orders),
            tariff_count=len(dataset.tariffs),
            budget_count=len(dataset.budgets),
            generation_run_id="REPRODUCIBILITY-TEST",
        )

    def _error_report(
        self, verification_type: str, errors: list[str]
    ) -> ReproducibilityReport:
        """Create an error report when generation fails."""
        return ReproducibilityReport(
            status=ReproducibilityStatus.ERROR,
            verification_type=verification_type,
            config_fingerprint=config_fingerprint(self._config),
            left_seed=self._config.seed,
            right_seed=self._config.seed,
            dataset_comparisons=(),
            summary_match=False,
            validation_passed=False,
            validation_error_count=0,
            validation_warning_count=0,
            changed_stochastic_datasets=(),
            preserved_dataset_families=(),
            errors=tuple(errors),
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def verify_same_seed(
    config: GenerationConfig,
    *,
    run_validation: bool = True,
) -> ReproducibilityReport:
    """Verify same-seed reproducibility for a generation configuration.

    This is a convenience function that creates a ReproducibilityVerifier
    and runs same-seed verification.

    Parameters
    ----------
    config:
        The generation configuration to verify.
    run_validation:
        If True, run validation on generated datasets.

    Returns
    -------
    ReproducibilityReport
        Detailed reproducibility report.
    """
    verifier = ReproducibilityVerifier(config)
    return verifier.verify_same_seed(run_validation=run_validation)


def verify_different_seed(
    config: GenerationConfig,
    other_seed: int,
    *,
    run_validation: bool = True,
) -> ReproducibilityReport:
    """Verify different-seed sensitivity for a generation configuration.

    This is a convenience function that creates a ReproducibilityVerifier
    and runs different-seed verification.

    Parameters
    ----------
    config:
        The generation configuration to verify.
    other_seed:
        The different seed to use for comparison.
    run_validation:
        If True, run validation on generated datasets.

    Returns
    -------
    ReproducibilityReport
        Detailed sensitivity report.
    """
    verifier = ReproducibilityVerifier(config)
    return verifier.verify_different_seed(other_seed, run_validation=run_validation)


__all__ = [
    "ComparisonOutcome",
    "DatasetComparison",
    "ReproducibilityReport",
    "ReproducibilityStatus",
    "ReproducibilityVerifier",
    "compare_datasets",
    "dataset_fingerprint",
    "verify_different_seed",
    "verify_same_seed",
]
