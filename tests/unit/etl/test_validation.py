"""Unit tests for EOIP Phase 3 ETL data validation."""

from __future__ import annotations

from types import MappingProxyType

import numpy as np
import pandas as pd
import pytest

from eoip.etl.config import ETLConfig, FailurePolicy, QualityConfig
from eoip.etl.validation import (
    DEFAULT_MAX_FAILURE_SAMPLES,
    DatasetContract,
    DatasetValidationResult,
    ETLValidator,
    NumericRange,
    RunValidationResult,
    ValidationIssue,
    ValidationRule,
    ValidationSeverity,
    validate_dataset,
    validate_datasets,
)


def _config(
    *,
    failure_policy: FailurePolicy = FailurePolicy.QUARANTINE,
    max_bad_records: int = 100,
) -> ETLConfig:
    """Build a deterministic ETL validation configuration."""
    return ETLConfig(
        quality=QualityConfig(
            failure_policy=failure_policy,
            max_bad_records=max_bad_records,
        )
    )


def _plant_contract(
    *,
    allow_empty: bool = False,
) -> DatasetContract:
    """Return a representative plant validation contract."""
    return DatasetContract(
        dataset_name="plants",
        required_columns=(
            "plant_id",
            "timestamp",
            "capacity_mw",
            "optional_note",
        ),
        nullable_columns=("optional_note",),
        unique_key=("plant_id",),
        timestamp_columns=("timestamp",),
        finite_numeric_columns=("capacity_mw",),
        numeric_ranges={
            "capacity_mw": NumericRange(
                minimum=0.0,
                maximum=500.0,
            )
        },
        allow_empty=allow_empty,
    )


def _valid_plants() -> pd.DataFrame:
    """Return a valid plant DataFrame."""
    return pd.DataFrame(
        {
            "plant_id": ["PLANT-001", "PLANT-002"],
            "timestamp": [
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:15:00Z",
            ],
            "capacity_mw": [50.0, 75.0],
            "optional_note": [None, "ok"],
        }
    )


class TestNumericRange:
    """Tests for NumericRange."""

    def test_valid_range(self) -> None:
        bounds = NumericRange(minimum=0.0, maximum=100.0)
        assert bounds.minimum == 0.0
        assert bounds.maximum == 100.0

    def test_open_range_is_valid(self) -> None:
        bounds = NumericRange()
        assert bounds.minimum is None
        assert bounds.maximum is None

    def test_minimum_greater_than_maximum_is_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="minimum cannot be greater than maximum",
        ):
            NumericRange(minimum=10.0, maximum=5.0)

    @pytest.mark.parametrize(
        "value",
        [float("inf"), float("-inf"), float("nan")],
    )
    def test_non_finite_bounds_are_rejected(
        self,
        value: float,
    ) -> None:
        with pytest.raises(ValueError):
            NumericRange(minimum=value)


class TestDatasetContract:
    """Tests for DatasetContract."""

    def test_valid_contract(self) -> None:
        contract = _plant_contract()
        assert contract.dataset_name == "plants"
        assert contract.unique_key == ("plant_id",)
        assert isinstance(contract.numeric_ranges, MappingProxyType)

    def test_dataset_name_is_trimmed(self) -> None:
        contract = DatasetContract(dataset_name="  plants  ")
        assert contract.dataset_name == "plants"

    def test_empty_dataset_name_is_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="dataset_name cannot be empty",
        ):
            DatasetContract(dataset_name="   ")

    def test_list_columns_are_normalized_to_tuple(self) -> None:
        contract = DatasetContract(
            dataset_name="plants",
            required_columns=["plant_id", "capacity_mw"],
        )
        assert contract.required_columns == (
            "plant_id",
            "capacity_mw",
        )

    def test_duplicate_contract_columns_are_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="cannot contain duplicate columns",
        ):
            DatasetContract(
                dataset_name="plants",
                required_columns=("plant_id", "plant_id"),
            )

    def test_unique_key_must_be_required(self) -> None:
        with pytest.raises(
            ValueError,
            match="unique_key contains columns not present",
        ):
            DatasetContract(
                dataset_name="plants",
                required_columns=("plant_id",),
                unique_key=("missing_id",),
            )

    def test_numeric_range_column_must_be_required(self) -> None:
        with pytest.raises(
            ValueError,
            match="numeric_ranges contains columns not present",
        ):
            DatasetContract(
                dataset_name="plants",
                required_columns=("plant_id",),
                numeric_ranges={"capacity_mw": NumericRange(minimum=0.0)},
            )

    def test_invalid_numeric_range_value_is_rejected(self) -> None:
        with pytest.raises(TypeError, match="NumericRange"):
            DatasetContract(
                dataset_name="plants",
                required_columns=("capacity_mw",),
                numeric_ranges={"capacity_mw": (0.0, 100.0)},  # type: ignore[dict-item]
            )


class TestValidationIssue:
    """Tests for ValidationIssue."""

    def test_serialization(self) -> None:
        issue = ValidationIssue(
            dataset_name="plants",
            rule=ValidationRule.NULL_VALUES,
            severity=ValidationSeverity.ERROR,
            message="Null values found.",
            column="plant_id",
            failure_count=2,
            sample_indices=(1, 3),
        )

        assert issue.to_dict() == {
            "dataset_name": "plants",
            "rule": "null_values",
            "severity": "error",
            "message": "Null values found.",
            "column": "plant_id",
            "failure_count": 2,
            "sample_indices": [1, 3],
        }

    def test_negative_failure_count_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            ValidationIssue(
                dataset_name="plants",
                rule=ValidationRule.NULL_VALUES,
                severity=ValidationSeverity.ERROR,
                message="Invalid.",
                failure_count=-1,
            )


class TestDatasetValidationResult:
    """Tests for DatasetValidationResult."""

    def test_passed_result(self) -> None:
        result = DatasetValidationResult(
            dataset_name="plants",
            row_count=2,
        )
        assert result.passed is True
        assert result.error_count == 0
        assert result.warning_count == 0

    def test_error_and_warning_counts(self) -> None:
        result = DatasetValidationResult(
            dataset_name="plants",
            row_count=2,
            issues=(
                ValidationIssue(
                    dataset_name="plants",
                    rule=ValidationRule.NULL_VALUES,
                    severity=ValidationSeverity.ERROR,
                    message="Error.",
                ),
                ValidationIssue(
                    dataset_name="plants",
                    rule=ValidationRule.EMPTY_DATASET,
                    severity=ValidationSeverity.WARNING,
                    message="Warning.",
                ),
            ),
        )
        assert result.passed is False
        assert result.error_count == 1
        assert result.warning_count == 1
        assert result.to_dict()["issue_count"] == 2


class TestRunValidationResult:
    """Tests for RunValidationResult."""

    def test_run_summary(self) -> None:
        first = DatasetValidationResult(
            dataset_name="plants",
            row_count=2,
        )
        second = DatasetValidationResult(
            dataset_name="equipment",
            row_count=1,
        )
        result = RunValidationResult(datasets=(first, second))

        assert result.passed is True
        assert result.issue_count == 0
        assert result.to_dict()["dataset_count"] == 2

    def test_duplicate_dataset_names_are_rejected(self) -> None:
        result = DatasetValidationResult(
            dataset_name="plants",
            row_count=1,
        )
        with pytest.raises(
            ValueError,
            match="duplicate dataset names",
        ):
            RunValidationResult(datasets=(result, result))


class TestETLValidatorConstruction:
    """Tests for ETLValidator construction."""

    def test_valid_validator(self) -> None:
        validator = ETLValidator(
            _config(),
            contracts=(_plant_contract(),),
        )
        assert validator.config.quality.require_manifest is True
        assert "plants" in validator.contracts

    def test_duplicate_contracts_are_rejected(self) -> None:
        contract = _plant_contract()

        with pytest.raises(
            ValueError,
            match="Duplicate dataset contract",
        ):
            ETLValidator(
                _config(),
                contracts=(contract, contract),
            )

    def test_invalid_config_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="config must be an ETLConfig",
        ):
            ETLValidator(
                "invalid",  # type: ignore[arg-type]
                contracts=(),
            )

    def test_zero_failure_samples_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            ETLValidator(
                _config(),
                contracts=(),
                maximum_failure_samples=0,
            )


class TestDatasetValidation:
    """Tests for dataset validation behavior."""

    def test_valid_dataset_passes(self) -> None:
        validator = ETLValidator(
            _config(),
            contracts=(_plant_contract(),),
        )
        result = validator.validate_dataset(
            "plants",
            _valid_plants(),
        )

        assert result.passed is True
        assert result.row_count == 2
        assert result.issues == ()

    def test_missing_required_column_is_detected(self) -> None:
        frame = _valid_plants().drop(columns=["plant_id"])
        result = validate_dataset(
            _config(),
            _plant_contract(),
            frame,
        )

        assert result.passed is False
        assert result.issues[0].rule is ValidationRule.REQUIRED_COLUMNS
        assert result.issues[0].failure_count == 1

    def test_empty_dataset_is_rejected_by_default(self) -> None:
        frame = _valid_plants().iloc[0:0].copy()
        result = validate_dataset(
            _config(),
            _plant_contract(),
            frame,
        )

        assert result.passed is False
        assert any(
            issue.rule is ValidationRule.EMPTY_DATASET for issue in result.issues
        )

    def test_empty_dataset_can_be_allowed(self) -> None:
        frame = _valid_plants().iloc[0:0].copy()
        result = validate_dataset(
            _config(),
            _plant_contract(allow_empty=True),
            frame,
        )
        assert result.passed is True

    def test_duplicate_columns_are_detected(self) -> None:
        frame = _valid_plants()
        frame.columns = [
            "plant_id",
            "timestamp",
            "capacity_mw",
            "capacity_mw",
        ]

        contract = DatasetContract(
            dataset_name="plants",
            required_columns=(
                "plant_id",
                "timestamp",
                "capacity_mw",
            ),
        )
        result = validate_dataset(
            _config(),
            contract,
            frame,
        )

        assert result.passed is False
        assert any(
            issue.rule is ValidationRule.DUPLICATE_COLUMNS for issue in result.issues
        )

    def test_non_nullable_null_is_detected(self) -> None:
        frame = _valid_plants()
        frame.loc[1, "plant_id"] = None

        result = validate_dataset(
            _config(),
            _plant_contract(),
            frame,
        )

        issue = next(
            issue for issue in result.issues if issue.rule is ValidationRule.NULL_VALUES
        )

        assert issue.column == "plant_id"
        assert issue.failure_count == 1
        assert issue.sample_indices == (1,)

    def test_nullable_null_is_allowed(self) -> None:
        frame = _valid_plants()
        frame["optional_note"] = None

        result = validate_dataset(
            _config(),
            _plant_contract(),
            frame,
        )

        assert not any(
            issue.rule is ValidationRule.NULL_VALUES and issue.column == "optional_note"
            for issue in result.issues
        )

    def test_duplicate_unique_key_is_detected(self) -> None:
        frame = _valid_plants()
        frame.loc[1, "plant_id"] = "PLANT-001"

        result = validate_dataset(
            _config(),
            _plant_contract(),
            frame,
        )

        issue = next(
            issue for issue in result.issues if issue.rule is ValidationRule.UNIQUE_KEY
        )

        assert issue.failure_count == 2
        assert issue.sample_indices == (0, 1)

    def test_invalid_timestamp_is_detected(self) -> None:
        frame = _valid_plants()
        frame.loc[1, "timestamp"] = "not-a-timestamp"

        result = validate_dataset(
            _config(),
            _plant_contract(),
            frame,
        )

        issue = next(
            issue
            for issue in result.issues
            if issue.rule is ValidationRule.TIMESTAMP_PARSE
        )

        assert issue.column == "timestamp"
        assert issue.failure_count == 1

    @pytest.mark.parametrize(
        "value",
        [
            np.inf,
            -np.inf,
            "not-a-number",
        ],
    )
    def test_non_finite_numeric_is_detected(
        self,
        value: object,
    ) -> None:
        frame = _valid_plants()

        if isinstance(value, str):
            frame["capacity_mw"] = frame["capacity_mw"].astype(object)

        frame.loc[1, "capacity_mw"] = value

        result = validate_dataset(
            _config(),
            _plant_contract(),
            frame,
        )

        assert any(
            issue.rule is ValidationRule.NUMERIC_FINITE for issue in result.issues
        )

    def test_below_minimum_is_detected(self) -> None:
        frame = _valid_plants()
        frame.loc[0, "capacity_mw"] = -1.0

        result = validate_dataset(
            _config(),
            _plant_contract(),
            frame,
        )

        assert any(
            issue.rule is ValidationRule.MINIMUM_VALUE for issue in result.issues
        )

    def test_above_maximum_is_detected(self) -> None:
        frame = _valid_plants()
        frame.loc[0, "capacity_mw"] = 501.0

        result = validate_dataset(
            _config(),
            _plant_contract(),
            frame,
        )

        assert any(
            issue.rule is ValidationRule.MAXIMUM_VALUE for issue in result.issues
        )

    def test_failure_samples_are_capped(self) -> None:
        frame = pd.DataFrame(
            {
                "plant_id": [None, None, None, None],
                "timestamp": ["2026-01-01T00:00:00Z"] * 4,
                "capacity_mw": [10.0, 20.0, 30.0, 40.0],
                "optional_note": [None, None, None, None],
            }
        )

        result = validate_dataset(
            _config(),
            _plant_contract(),
            frame,
            maximum_failure_samples=2,
        )

        issue = next(
            issue
            for issue in result.issues
            if issue.rule is ValidationRule.NULL_VALUES and issue.column == "plant_id"
        )

        assert issue.failure_count == 4
        assert issue.sample_indices == (0, 1)

    def test_validation_does_not_mutate_source_frame(self) -> None:
        frame = _valid_plants()
        original = frame.copy(deep=True)

        validate_dataset(
            _config(),
            _plant_contract(),
            frame,
        )

        pd.testing.assert_frame_equal(frame, original)

    def test_unknown_contract_is_rejected(self) -> None:
        validator = ETLValidator(
            _config(),
            contracts=(_plant_contract(),),
        )

        with pytest.raises(
            KeyError,
            match="No validation contract registered",
        ):
            validator.validate_dataset(
                "equipment",
                pd.DataFrame(),
            )


class TestRunValidation:
    """Tests for run-level validation."""

    def test_datasets_are_validated_in_sorted_order(self) -> None:
        contracts = (
            DatasetContract(
                dataset_name="weather",
                required_columns=("weather_id",),
            ),
            DatasetContract(
                dataset_name="plants",
                required_columns=("plant_id",),
            ),
        )

        datasets = {
            "weather": pd.DataFrame({"weather_id": ["WEATHER-001"]}),
            "plants": pd.DataFrame({"plant_id": ["PLANT-001"]}),
        }

        result = validate_datasets(
            _config(),
            contracts,
            datasets,
        )

        assert [item.dataset_name for item in result.datasets] == [
            "plants",
            "weather",
        ]
        assert result.passed is True

    def test_invalid_dataset_type_is_rejected(self) -> None:
        validator = ETLValidator(
            _config(),
            contracts=(_plant_contract(),),
        )

        with pytest.raises(
            TypeError,
            match="pandas DataFrame",
        ):
            validator.validate_dataset(
                "plants",
                [],  # type: ignore[arg-type]
            )


class TestFailurePolicy:
    """Tests for quarantine and pipeline-failure decisions."""

    def test_passing_dataset_is_not_quarantined_or_failed(self) -> None:
        validator = ETLValidator(
            _config(),
            contracts=(_plant_contract(),),
        )
        result = validator.validate_dataset(
            "plants",
            _valid_plants(),
        )

        assert validator.should_quarantine(result) is False
        assert validator.should_fail(result) is False

    def test_quarantine_policy_quarantines_failed_dataset(self) -> None:
        validator = ETLValidator(
            _config(
                failure_policy=FailurePolicy.QUARANTINE,
                max_bad_records=10,
            ),
            contracts=(_plant_contract(),),
        )

        frame = _valid_plants()
        frame.loc[0, "plant_id"] = None
        result = validator.validate_dataset(
            "plants",
            frame,
        )

        assert validator.should_quarantine(result) is True
        assert validator.should_fail(result) is False

    def test_quarantine_policy_fails_when_bad_record_limit_exceeded(
        self,
    ) -> None:
        validator = ETLValidator(
            _config(
                failure_policy=FailurePolicy.QUARANTINE,
                max_bad_records=0,
            ),
            contracts=(_plant_contract(),),
        )

        frame = _valid_plants()
        frame.loc[0, "plant_id"] = None
        result = validator.validate_dataset(
            "plants",
            frame,
        )

        assert validator.should_fail(result) is True

    def test_fail_fast_policy_fails_any_invalid_dataset(self) -> None:
        validator = ETLValidator(
            _config(
                failure_policy=FailurePolicy.FAIL_FAST,
                max_bad_records=0,
            ),
            contracts=(_plant_contract(),),
        )

        frame = _valid_plants()
        frame.loc[0, "plant_id"] = None
        result = validator.validate_dataset(
            "plants",
            frame,
        )

        assert validator.should_fail(result) is True
        assert validator.should_quarantine(result) is False


class TestPublicValidationHelpers:
    """Tests for public convenience functions."""

    def test_validate_dataset_helper(self) -> None:
        result = validate_dataset(
            _config(),
            _plant_contract(),
            _valid_plants(),
        )

        assert isinstance(result, DatasetValidationResult)
        assert result.passed is True

    def test_validate_datasets_helper(self) -> None:
        result = validate_datasets(
            _config(),
            contracts=(_plant_contract(),),
            datasets={"plants": _valid_plants()},
        )

        assert isinstance(result, RunValidationResult)
        assert result.passed is True

    def test_default_failure_sample_constant_is_positive(self) -> None:
        assert DEFAULT_MAX_FAILURE_SAMPLES > 0
