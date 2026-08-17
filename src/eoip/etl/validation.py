"""Data-validation foundation for EOIP Phase 3 ETL pipelines.

This module validates ingested pandas DataFrames before cleaning,
standardization, transformation, incremental processing, or database loading.

Validation is contract-driven. Dataset-specific schemas are supplied through
``DatasetContract`` objects rather than being guessed inside the validation
engine.

The validator collects issues instead of failing on the first data-quality
problem so downstream orchestration can make deterministic decisions about
whether a dataset is accepted, quarantined, or rejected.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Final

import numpy as np
import pandas as pd

from eoip.etl.config import ETLConfig, FailurePolicy

DEFAULT_MAX_FAILURE_SAMPLES: Final[int] = 10


class ValidationSeverity(StrEnum):
    """Severity assigned to an ETL validation issue."""

    ERROR = "error"
    WARNING = "warning"


class ValidationRule(StrEnum):
    """Stable identifiers for Phase 3 validation rules."""

    DATASET_TYPE = "dataset_type"
    REQUIRED_COLUMNS = "required_columns"
    DUPLICATE_COLUMNS = "duplicate_columns"
    NULL_VALUES = "null_values"
    UNIQUE_KEY = "unique_key"
    TIMESTAMP_PARSE = "timestamp_parse"
    NUMERIC_FINITE = "numeric_finite"
    MINIMUM_VALUE = "minimum_value"
    MAXIMUM_VALUE = "maximum_value"
    EMPTY_DATASET = "empty_dataset"


@dataclass(frozen=True, slots=True)
class NumericRange:
    """Optional numeric bounds for one dataset column."""

    minimum: float | None = None
    maximum: float | None = None

    def __post_init__(self) -> None:
        """Validate range consistency."""
        if self.minimum is not None:
            _validate_finite_number("minimum", self.minimum)

        if self.maximum is not None:
            _validate_finite_number("maximum", self.maximum)

        if (
            self.minimum is not None
            and self.maximum is not None
            and self.minimum > self.maximum
        ):
            raise ValueError("minimum cannot be greater than maximum.")


@dataclass(frozen=True, slots=True)
class DatasetContract:
    """Validation contract for one logical ETL dataset."""

    dataset_name: str
    required_columns: tuple[str, ...] = ()
    nullable_columns: tuple[str, ...] = ()
    unique_key: tuple[str, ...] = ()
    timestamp_columns: tuple[str, ...] = ()
    finite_numeric_columns: tuple[str, ...] = ()
    numeric_ranges: Mapping[str, NumericRange] = field(default_factory=dict)
    allow_empty: bool = False

    def __post_init__(self) -> None:
        """Normalize and validate contract configuration."""
        if not isinstance(self.dataset_name, str):
            raise TypeError("dataset_name must be a string.")

        dataset_name = self.dataset_name.strip()

        if not dataset_name:
            raise ValueError("dataset_name cannot be empty.")

        object.__setattr__(self, "dataset_name", dataset_name)

        for field_name in (
            "required_columns",
            "nullable_columns",
            "unique_key",
            "timestamp_columns",
            "finite_numeric_columns",
        ):
            normalized = _normalize_column_tuple(
                field_name,
                getattr(self, field_name),
            )
            object.__setattr__(self, field_name, normalized)

        if not isinstance(self.numeric_ranges, Mapping):
            raise TypeError("numeric_ranges must be a mapping.")

        normalized_ranges: dict[str, NumericRange] = {}

        for column_name, bounds in self.numeric_ranges.items():
            if not isinstance(column_name, str):
                raise TypeError("numeric_ranges keys must be strings.")

            normalized_column = column_name.strip()

            if not normalized_column:
                raise ValueError("numeric_ranges keys cannot be empty.")

            if not isinstance(bounds, NumericRange):
                raise TypeError("numeric_ranges values must be NumericRange.")

            normalized_ranges[normalized_column] = bounds

        object.__setattr__(
            self,
            "numeric_ranges",
            MappingProxyType(dict(sorted(normalized_ranges.items()))),
        )

        if not isinstance(self.allow_empty, bool):
            raise TypeError("allow_empty must be a boolean.")

        required = set(self.required_columns)

        for field_name in (
            "nullable_columns",
            "unique_key",
            "timestamp_columns",
            "finite_numeric_columns",
        ):
            missing = set(getattr(self, field_name)) - required

            if missing:
                raise ValueError(
                    f"{field_name} contains columns not present "
                    f"in required_columns: {sorted(missing)}"
                )

        missing_range_columns = set(self.numeric_ranges) - required

        if missing_range_columns:
            raise ValueError(
                "numeric_ranges contains columns not present "
                "in required_columns: "
                f"{sorted(missing_range_columns)}"
            )


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One deterministic ETL data-validation issue."""

    dataset_name: str
    rule: ValidationRule
    severity: ValidationSeverity
    message: str
    column: str | None = None
    failure_count: int = 0
    sample_indices: tuple[Any, ...] = ()

    def __post_init__(self) -> None:
        """Validate issue metadata."""
        if not isinstance(self.dataset_name, str):
            raise TypeError("dataset_name must be a string.")

        if not self.dataset_name.strip():
            raise ValueError("dataset_name cannot be empty.")

        if not isinstance(self.rule, ValidationRule):
            raise TypeError("rule must be a ValidationRule.")

        if not isinstance(self.severity, ValidationSeverity):
            raise TypeError("severity must be a ValidationSeverity.")

        if not isinstance(self.message, str):
            raise TypeError("message must be a string.")

        if not self.message.strip():
            raise ValueError("message cannot be empty.")

        _validate_non_negative_int("failure_count", self.failure_count)

    def to_dict(self) -> dict[str, Any]:
        """Return a serialization-ready issue mapping."""
        return {
            "dataset_name": self.dataset_name,
            "rule": self.rule.value,
            "severity": self.severity.value,
            "message": self.message,
            "column": self.column,
            "failure_count": self.failure_count,
            "sample_indices": list(self.sample_indices),
        }


@dataclass(frozen=True, slots=True)
class DatasetValidationResult:
    """Validation result for one logical dataset."""

    dataset_name: str
    row_count: int
    issues: tuple[ValidationIssue, ...] = ()

    def __post_init__(self) -> None:
        """Validate result metadata."""
        if not isinstance(self.dataset_name, str):
            raise TypeError("dataset_name must be a string.")

        if not self.dataset_name.strip():
            raise ValueError("dataset_name cannot be empty.")

        _validate_non_negative_int("row_count", self.row_count)

        if not isinstance(self.issues, tuple):
            raise TypeError("issues must be a tuple.")

        for issue in self.issues:
            if not isinstance(issue, ValidationIssue):
                raise TypeError("issues must contain ValidationIssue objects.")

    @property
    def error_count(self) -> int:
        """Return the number of error-level issues."""
        return sum(issue.severity is ValidationSeverity.ERROR for issue in self.issues)

    @property
    def warning_count(self) -> int:
        """Return the number of warning-level issues."""
        return sum(
            issue.severity is ValidationSeverity.WARNING for issue in self.issues
        )

    @property
    def passed(self) -> bool:
        """Return whether the dataset has no validation errors."""
        return self.error_count == 0

    def to_dict(self) -> dict[str, Any]:
        """Return a serialization-ready validation result."""
        return {
            "dataset_name": self.dataset_name,
            "row_count": self.row_count,
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issue_count": len(self.issues),
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True, slots=True)
class RunValidationResult:
    """Validation summary for multiple ETL datasets."""

    datasets: tuple[DatasetValidationResult, ...]

    def __post_init__(self) -> None:
        """Validate run-level results."""
        if not isinstance(self.datasets, tuple):
            raise TypeError("datasets must be a tuple.")

        for result in self.datasets:
            if not isinstance(result, DatasetValidationResult):
                raise TypeError(
                    "datasets must contain DatasetValidationResult objects."
                )

        names = [result.dataset_name for result in self.datasets]

        if len(names) != len(set(names)):
            raise ValueError("datasets contains duplicate dataset names.")

    @property
    def passed(self) -> bool:
        """Return whether every dataset passed validation."""
        return all(result.passed for result in self.datasets)

    @property
    def error_count(self) -> int:
        """Return total validation error count."""
        return sum(result.error_count for result in self.datasets)

    @property
    def warning_count(self) -> int:
        """Return total validation warning count."""
        return sum(result.warning_count for result in self.datasets)

    @property
    def issue_count(self) -> int:
        """Return total validation issue count."""
        return sum(len(result.issues) for result in self.datasets)

    def to_dict(self) -> dict[str, Any]:
        """Return a serialization-ready run result."""
        return {
            "passed": self.passed,
            "dataset_count": len(self.datasets),
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issue_count": self.issue_count,
            "datasets": [result.to_dict() for result in self.datasets],
        }


class ETLValidator:
    """Contract-driven validator for Phase 3 ETL datasets."""

    def __init__(
        self,
        config: ETLConfig,
        contracts: Iterable[DatasetContract],
        *,
        maximum_failure_samples: int = DEFAULT_MAX_FAILURE_SAMPLES,
    ) -> None:
        """Create an ETL validator."""
        if not isinstance(config, ETLConfig):
            raise TypeError("config must be an ETLConfig.")

        _validate_positive_int(
            "maximum_failure_samples",
            maximum_failure_samples,
        )

        contract_map: dict[str, DatasetContract] = {}

        for contract in contracts:
            if not isinstance(contract, DatasetContract):
                raise TypeError("contracts must contain DatasetContract objects.")

            if contract.dataset_name in contract_map:
                raise ValueError(f"Duplicate dataset contract: {contract.dataset_name}")

            contract_map[contract.dataset_name] = contract

        self._config = config
        self._contracts = MappingProxyType(dict(sorted(contract_map.items())))
        self._maximum_failure_samples = maximum_failure_samples

    @property
    def config(self) -> ETLConfig:
        """Return immutable ETL configuration."""
        return self._config

    @property
    def contracts(self) -> Mapping[str, DatasetContract]:
        """Return registered dataset contracts."""
        return self._contracts

    def validate_dataset(
        self,
        dataset_name: str,
        frame: pd.DataFrame,
    ) -> DatasetValidationResult:
        """Validate one dataset against its registered contract."""
        if not isinstance(dataset_name, str):
            raise TypeError("dataset_name must be a string.")

        normalized_name = dataset_name.strip()

        if not normalized_name:
            raise ValueError("dataset_name cannot be empty.")

        if not isinstance(frame, pd.DataFrame):
            raise TypeError("frame must be a pandas DataFrame.")

        try:
            contract = self._contracts[normalized_name]
        except KeyError as exc:
            raise KeyError(
                "No validation contract registered " f"for dataset: {normalized_name}"
            ) from exc

        issues: list[ValidationIssue] = []

        self._validate_structure(
            frame,
            contract,
            issues,
        )

        required_present = all(
            column in frame.columns for column in contract.required_columns
        )
        duplicate_columns_present = bool(frame.columns.duplicated().any())

        if required_present and not duplicate_columns_present:
            self._validate_nulls(
                frame,
                contract,
                issues,
            )
            self._validate_unique_key(
                frame,
                contract,
                issues,
            )
            self._validate_timestamps(
                frame,
                contract,
                issues,
            )
            self._validate_finite_numeric(
                frame,
                contract,
                issues,
            )
            self._validate_numeric_ranges(
                frame,
                contract,
                issues,
            )

        ordered_issues = tuple(
            sorted(
                issues,
                key=_issue_sort_key,
            )
        )

        return DatasetValidationResult(
            dataset_name=normalized_name,
            row_count=len(frame),
            issues=ordered_issues,
        )

    def validate_run(
        self,
        datasets: Mapping[str, pd.DataFrame],
    ) -> RunValidationResult:
        """Validate multiple ingested datasets deterministically."""
        if not isinstance(datasets, Mapping):
            raise TypeError("datasets must be a mapping.")

        results = [
            self.validate_dataset(
                dataset_name,
                datasets[dataset_name],
            )
            for dataset_name in sorted(datasets)
        ]

        return RunValidationResult(datasets=tuple(results))

    def should_quarantine(
        self,
        result: DatasetValidationResult,
    ) -> bool:
        """Return whether a failed dataset should be quarantined."""
        if not isinstance(result, DatasetValidationResult):
            raise TypeError("result must be a DatasetValidationResult.")

        if result.passed:
            return False

        return self._config.quality.failure_policy is FailurePolicy.QUARANTINE

    def should_fail(
        self,
        result: DatasetValidationResult,
    ) -> bool:
        """Return whether validation should fail pipeline execution."""
        if not isinstance(result, DatasetValidationResult):
            raise TypeError("result must be a DatasetValidationResult.")

        if result.passed:
            return False

        if self._config.quality.failure_policy is FailurePolicy.FAIL_FAST:
            return True

        failure_rows = sum(
            issue.failure_count
            for issue in result.issues
            if issue.severity is ValidationSeverity.ERROR
        )

        return failure_rows > self._config.quality.max_bad_records

    def _validate_structure(
        self,
        frame: pd.DataFrame,
        contract: DatasetContract,
        issues: list[ValidationIssue],
    ) -> None:
        """Validate required columns and dataset structure."""
        if frame.empty and not contract.allow_empty:
            issues.append(
                ValidationIssue(
                    dataset_name=contract.dataset_name,
                    rule=ValidationRule.EMPTY_DATASET,
                    severity=ValidationSeverity.ERROR,
                    message="Dataset is empty.",
                    failure_count=1,
                )
            )

        duplicated_columns = tuple(
            str(column) for column in frame.columns[frame.columns.duplicated()]
        )

        if duplicated_columns:
            issues.append(
                ValidationIssue(
                    dataset_name=contract.dataset_name,
                    rule=ValidationRule.DUPLICATE_COLUMNS,
                    severity=ValidationSeverity.ERROR,
                    message=(
                        "Dataset contains duplicate columns: "
                        f"{list(duplicated_columns)}"
                    ),
                    failure_count=len(duplicated_columns),
                )
            )

        missing_columns = [
            column
            for column in contract.required_columns
            if column not in frame.columns
        ]

        if missing_columns:
            issues.append(
                ValidationIssue(
                    dataset_name=contract.dataset_name,
                    rule=ValidationRule.REQUIRED_COLUMNS,
                    severity=ValidationSeverity.ERROR,
                    message=("Missing required columns: " f"{missing_columns}"),
                    failure_count=len(missing_columns),
                )
            )

    def _validate_nulls(
        self,
        frame: pd.DataFrame,
        contract: DatasetContract,
        issues: list[ValidationIssue],
    ) -> None:
        """Validate nullability constraints."""
        nullable = set(contract.nullable_columns)

        for column in contract.required_columns:
            if column in nullable:
                continue

            null_mask = frame[column].isna()

            if not null_mask.any():
                continue

            issues.append(
                self._column_issue(
                    contract=contract,
                    rule=ValidationRule.NULL_VALUES,
                    message=(f"Column '{column}' contains null values."),
                    column=column,
                    mask=null_mask,
                    frame=frame,
                )
            )

    def _validate_unique_key(
        self,
        frame: pd.DataFrame,
        contract: DatasetContract,
        issues: list[ValidationIssue],
    ) -> None:
        """Validate contract-level unique keys."""
        if not contract.unique_key:
            return

        duplicate_mask = frame.duplicated(
            subset=list(contract.unique_key),
            keep=False,
        )

        if not duplicate_mask.any():
            return

        issues.append(
            self._column_issue(
                contract=contract,
                rule=ValidationRule.UNIQUE_KEY,
                message=(
                    "Duplicate unique-key rows detected for "
                    f"{list(contract.unique_key)}."
                ),
                column=",".join(contract.unique_key),
                mask=duplicate_mask,
                frame=frame,
            )
        )

    def _validate_timestamps(
        self,
        frame: pd.DataFrame,
        contract: DatasetContract,
        issues: list[ValidationIssue],
    ) -> None:
        """Validate timestamp columns are parseable."""
        for column in contract.timestamp_columns:
            converted = pd.to_datetime(
                frame[column],
                errors="coerce",
                utc=True,
            )

            invalid_mask = frame[column].notna() & converted.isna()

            if not invalid_mask.any():
                continue

            issues.append(
                self._column_issue(
                    contract=contract,
                    rule=ValidationRule.TIMESTAMP_PARSE,
                    message=(f"Column '{column}' contains " "unparseable timestamps."),
                    column=column,
                    mask=invalid_mask,
                    frame=frame,
                )
            )

    def _validate_finite_numeric(
        self,
        frame: pd.DataFrame,
        contract: DatasetContract,
        issues: list[ValidationIssue],
    ) -> None:
        """Validate configured numeric columns contain finite values."""
        for column in contract.finite_numeric_columns:
            numeric = pd.to_numeric(
                frame[column],
                errors="coerce",
            )

            invalid_mask = frame[column].notna() & (
                numeric.isna()
                | ~np.isfinite(
                    numeric.to_numpy(
                        dtype=float,
                        na_value=np.nan,
                    )
                )
            )

            if not invalid_mask.any():
                continue

            issues.append(
                self._column_issue(
                    contract=contract,
                    rule=ValidationRule.NUMERIC_FINITE,
                    message=(
                        f"Column '{column}' contains " "non-finite numeric values."
                    ),
                    column=column,
                    mask=invalid_mask,
                    frame=frame,
                )
            )

    def _validate_numeric_ranges(
        self,
        frame: pd.DataFrame,
        contract: DatasetContract,
        issues: list[ValidationIssue],
    ) -> None:
        """Validate configured numeric minimum and maximum bounds."""
        for column, bounds in contract.numeric_ranges.items():
            numeric = pd.to_numeric(
                frame[column],
                errors="coerce",
            )

            if bounds.minimum is not None:
                minimum_mask = numeric.notna() & (numeric < bounds.minimum)

                if minimum_mask.any():
                    issues.append(
                        self._column_issue(
                            contract=contract,
                            rule=ValidationRule.MINIMUM_VALUE,
                            message=(
                                f"Column '{column}' contains "
                                "values below minimum "
                                f"{bounds.minimum}."
                            ),
                            column=column,
                            mask=minimum_mask,
                            frame=frame,
                        )
                    )

            if bounds.maximum is not None:
                maximum_mask = numeric.notna() & (numeric > bounds.maximum)

                if maximum_mask.any():
                    issues.append(
                        self._column_issue(
                            contract=contract,
                            rule=ValidationRule.MAXIMUM_VALUE,
                            message=(
                                f"Column '{column}' contains "
                                "values above maximum "
                                f"{bounds.maximum}."
                            ),
                            column=column,
                            mask=maximum_mask,
                            frame=frame,
                        )
                    )

    def _column_issue(
        self,
        *,
        contract: DatasetContract,
        rule: ValidationRule,
        message: str,
        column: str,
        mask: pd.Series,
        frame: pd.DataFrame,
    ) -> ValidationIssue:
        """Build a sampled deterministic column validation issue."""
        failing_indices = tuple(
            frame.index[mask][: self._maximum_failure_samples].tolist()
        )

        return ValidationIssue(
            dataset_name=contract.dataset_name,
            rule=rule,
            severity=ValidationSeverity.ERROR,
            message=message,
            column=column,
            failure_count=int(mask.sum()),
            sample_indices=failing_indices,
        )


def validate_dataset(
    config: ETLConfig,
    contract: DatasetContract,
    frame: pd.DataFrame,
    *,
    maximum_failure_samples: int = DEFAULT_MAX_FAILURE_SAMPLES,
) -> DatasetValidationResult:
    """Validate one dataset using one explicit contract."""
    validator = ETLValidator(
        config,
        contracts=(contract,),
        maximum_failure_samples=maximum_failure_samples,
    )

    return validator.validate_dataset(
        contract.dataset_name,
        frame,
    )


def validate_datasets(
    config: ETLConfig,
    contracts: Iterable[DatasetContract],
    datasets: Mapping[str, pd.DataFrame],
    *,
    maximum_failure_samples: int = DEFAULT_MAX_FAILURE_SAMPLES,
) -> RunValidationResult:
    """Validate multiple datasets using explicit contracts."""
    validator = ETLValidator(
        config,
        contracts=contracts,
        maximum_failure_samples=maximum_failure_samples,
    )

    return validator.validate_run(datasets)


def _normalize_column_tuple(
    field_name: str,
    values: Sequence[str],
) -> tuple[str, ...]:
    """Normalize a sequence of unique column names."""
    if not isinstance(
        values,
        (tuple, list),
    ):
        raise TypeError(f"{field_name} must be a tuple or list.")

    normalized: list[str] = []

    for value in values:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must contain strings.")

        column_name = value.strip()

        if not column_name:
            raise ValueError(f"{field_name} cannot contain empty columns.")

        normalized.append(column_name)

    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} cannot contain duplicate columns.")

    return tuple(normalized)


def _issue_sort_key(
    issue: ValidationIssue,
) -> tuple[str, str, str]:
    """Return deterministic sorting key for validation issues."""
    return (
        issue.severity.value,
        issue.rule.value,
        issue.column or "",
    )


def _validate_positive_int(
    name: str,
    value: int,
) -> None:
    """Validate a strictly positive integer."""
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError(f"{name} must be an integer.")

    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")


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


def _validate_finite_number(
    name: str,
    value: float,
) -> None:
    """Validate a finite numeric value."""
    if isinstance(value, bool) or not isinstance(
        value,
        (int, float),
    ):
        raise TypeError(f"{name} must be numeric.")

    if not np.isfinite(value):
        raise ValueError(f"{name} must be finite.")


__all__ = [
    "DEFAULT_MAX_FAILURE_SAMPLES",
    "DatasetContract",
    "DatasetValidationResult",
    "ETLValidator",
    "NumericRange",
    "RunValidationResult",
    "ValidationIssue",
    "ValidationRule",
    "ValidationSeverity",
    "validate_dataset",
    "validate_datasets",
]
