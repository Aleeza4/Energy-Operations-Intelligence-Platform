"""Unit tests for the Phase 3 ETL configuration."""

from pathlib import Path
from types import MappingProxyType

import pytest

from eoip.etl import config as etl_config_module
from eoip.etl.config import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_FLOW_RETRIES,
    DEFAULT_MAX_BAD_RECORDS,
    DEFAULT_RETRY_DELAY_SECONDS,
    DEFAULT_TASK_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    ETLConfig,
    ETLEnvironment,
    FailurePolicy,
    IngestionConfig,
    LoadMode,
    QualityConfig,
    RetryConfig,
    SourceFormat,
    StagingConfig,
    development_config,
    production_config,
)


class TestRetryConfig:
    """Tests for retry configuration."""

    def test_defaults_are_correct(self) -> None:
        config = RetryConfig()

        assert config.flow_retries == DEFAULT_FLOW_RETRIES
        assert config.task_retries == DEFAULT_TASK_RETRIES
        assert config.retry_delay_seconds == DEFAULT_RETRY_DELAY_SECONDS
        assert config.timeout_seconds == DEFAULT_TIMEOUT_SECONDS

    @pytest.mark.parametrize(
        "field_name",
        ["flow_retries", "task_retries"],
    )
    def test_retry_counts_reject_negative_values(
        self,
        field_name: str,
    ) -> None:
        kwargs = {field_name: -1}

        with pytest.raises(ValueError):
            RetryConfig(**kwargs)

    @pytest.mark.parametrize(
        "field_name",
        ["flow_retries", "task_retries"],
    )
    def test_retry_counts_reject_boolean_values(
        self,
        field_name: str,
    ) -> None:
        kwargs = {field_name: True}

        with pytest.raises(TypeError):
            RetryConfig(**kwargs)

    @pytest.mark.parametrize(
        "field_name",
        ["retry_delay_seconds", "timeout_seconds"],
    )
    @pytest.mark.parametrize(
        "invalid_value",
        [0.0, -1.0, float("inf"), float("-inf"), float("nan")],
    )
    def test_numeric_retry_settings_reject_invalid_values(
        self,
        field_name: str,
        invalid_value: float,
    ) -> None:
        kwargs = {field_name: invalid_value}

        with pytest.raises(ValueError):
            RetryConfig(**kwargs)


class TestIngestionConfig:
    """Tests for ingestion configuration."""

    def test_defaults_are_correct(self) -> None:
        config = IngestionConfig()

        assert config.source_root == Path("data/synthetic/runs")
        assert config.source_format is SourceFormat.PARQUET
        assert config.batch_size == DEFAULT_BATCH_SIZE
        assert config.recursive is True

    def test_source_root_is_normalized_to_path(self) -> None:
        config = IngestionConfig(source_root="data/custom")

        assert config.source_root == Path("data/custom")

    def test_batch_size_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            IngestionConfig(batch_size=0)

    def test_batch_size_rejects_boolean(self) -> None:
        with pytest.raises(TypeError):
            IngestionConfig(batch_size=True)

    def test_source_format_requires_enum(self) -> None:
        with pytest.raises(TypeError):
            IngestionConfig(source_format="parquet")  # type: ignore[arg-type]

    def test_recursive_requires_boolean(self) -> None:
        with pytest.raises(TypeError):
            IngestionConfig(recursive=1)  # type: ignore[arg-type]


class TestStagingConfig:
    """Tests for ETL staging configuration."""

    def test_defaults_are_correct(self) -> None:
        config = StagingConfig()

        assert config.staging_root == Path("data/etl/staging")
        assert config.quarantine_root == Path("data/etl/quarantine")
        assert config.checkpoint_root == Path("data/etl/checkpoints")

    def test_paths_are_normalized(self) -> None:
        config = StagingConfig(
            staging_root="tmp/staging",
            quarantine_root="tmp/quarantine",
            checkpoint_root="tmp/checkpoints",
        )

        assert config.staging_root == Path("tmp/staging")
        assert config.quarantine_root == Path("tmp/quarantine")
        assert config.checkpoint_root == Path("tmp/checkpoints")

    def test_paths_must_be_distinct(self) -> None:
        with pytest.raises(ValueError):
            StagingConfig(
                staging_root=Path("tmp/shared"),
                quarantine_root=Path("tmp/shared"),
                checkpoint_root=Path("tmp/checkpoints"),
            )


class TestQualityConfig:
    """Tests for data-quality configuration."""

    def test_defaults_are_correct(self) -> None:
        config = QualityConfig()

        assert config.failure_policy is FailurePolicy.QUARANTINE
        assert config.max_bad_records == DEFAULT_MAX_BAD_RECORDS
        assert config.reject_duplicate_rows is True
        assert config.require_manifest is True
        assert config.verify_source_checksums is True

    def test_max_bad_records_allows_zero(self) -> None:
        config = QualityConfig(max_bad_records=0)

        assert config.max_bad_records == 0

    def test_max_bad_records_rejects_negative_value(self) -> None:
        with pytest.raises(ValueError):
            QualityConfig(max_bad_records=-1)

    def test_failure_policy_requires_enum(self) -> None:
        with pytest.raises(TypeError):
            QualityConfig(
                failure_policy="quarantine",  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize(
        "field_name",
        [
            "reject_duplicate_rows",
            "require_manifest",
            "verify_source_checksums",
        ],
    )
    def test_boolean_settings_require_boolean(
        self,
        field_name: str,
    ) -> None:
        kwargs = {field_name: 1}

        with pytest.raises(TypeError):
            QualityConfig(**kwargs)


class TestETLConfig:
    """Tests for the complete Phase 3 ETL configuration."""

    def test_defaults_are_correct(self) -> None:
        config = ETLConfig()

        assert config.environment is ETLEnvironment.DEVELOPMENT
        assert config.load_mode is LoadMode.FULL
        assert config.pipeline_name == "eoip-phase3-etl"
        assert isinstance(config.ingestion, IngestionConfig)
        assert isinstance(config.staging, StagingConfig)
        assert isinstance(config.quality, QualityConfig)
        assert isinstance(config.retry, RetryConfig)

    def test_pipeline_name_is_trimmed(self) -> None:
        config = ETLConfig(pipeline_name="  eoip-etl  ")

        assert config.pipeline_name == "eoip-etl"

    def test_empty_pipeline_name_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            ETLConfig(pipeline_name="   ")

    def test_environment_requires_enum(self) -> None:
        with pytest.raises(TypeError):
            ETLConfig(
                environment="development",  # type: ignore[arg-type]
            )

    def test_load_mode_requires_enum(self) -> None:
        with pytest.raises(TypeError):
            ETLConfig(load_mode="full")  # type: ignore[arg-type]

    def test_fail_fast_requires_zero_bad_records(self) -> None:
        quality = QualityConfig(
            failure_policy=FailurePolicy.FAIL_FAST,
            max_bad_records=1,
        )

        with pytest.raises(ValueError):
            ETLConfig(quality=quality)

    def test_fail_fast_accepts_zero_bad_records(self) -> None:
        quality = QualityConfig(
            failure_policy=FailurePolicy.FAIL_FAST,
            max_bad_records=0,
        )

        config = ETLConfig(quality=quality)

        assert config.quality.failure_policy is FailurePolicy.FAIL_FAST
        assert config.quality.max_bad_records == 0

    def test_metadata_is_normalized_and_immutable(self) -> None:
        config = ETLConfig(
            metadata={
                " owner ": " energy-team ",
                "purpose": " phase-3 ",
            }
        )

        assert isinstance(config.metadata, MappingProxyType)
        assert config.metadata["owner"] == "energy-team"
        assert config.metadata["purpose"] == "phase-3"

        with pytest.raises(TypeError):
            config.metadata["owner"] = "changed"  # type: ignore[index]

    def test_invalid_metadata_key_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            ETLConfig(metadata={" ": "value"})

    def test_invalid_metadata_value_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            ETLConfig(metadata={"owner": " "})

    def test_configuration_is_immutable(self) -> None:
        config = ETLConfig()

        with pytest.raises(AttributeError):
            config.pipeline_name = "changed"  # type: ignore[misc]

    def test_to_dict_normalizes_enums_paths_and_metadata(self) -> None:
        config = ETLConfig(
            environment=ETLEnvironment.TEST,
            load_mode=LoadMode.INCREMENTAL,
            metadata={"owner": "energy-team"},
        )

        result = config.to_dict()

        assert result["environment"] == "test"
        assert result["load_mode"] == "incremental"
        assert result["ingestion"]["source_format"] == "parquet"
        assert result["ingestion"]["source_root"] == "data/synthetic/runs"
        assert result["metadata"] == {"owner": "energy-team"}


class TestConfigurationProfiles:
    """Tests for predefined Phase 3 configuration profiles."""

    def test_development_profile(self) -> None:
        config = development_config()

        assert config.environment is ETLEnvironment.DEVELOPMENT
        assert config.pipeline_name == "eoip-phase3-etl"

    def test_test_profile(self) -> None:
        config = etl_config_module.test_config()

        assert config.environment is ETLEnvironment.TEST
        assert config.ingestion.batch_size == 100
        assert config.retry.flow_retries == 0
        assert config.retry.task_retries == 0
        assert config.pipeline_name == "eoip-phase3-etl-test"

    def test_production_profile(self) -> None:
        config = production_config()

        assert config.environment is ETLEnvironment.PRODUCTION
        assert config.ingestion.batch_size == 100_000
        assert config.retry.flow_retries == 2
        assert config.retry.task_retries == 3
