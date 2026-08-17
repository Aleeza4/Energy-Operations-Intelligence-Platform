"""Unit tests for EOIP Phase 3 ETL pipeline orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from types import MappingProxyType

import pandas as pd
import pytest

from eoip.etl.audit import AuditEvent, AuditStage, AuditStatus
from eoip.etl.cleaning import CleaningConfig
from eoip.etl.config import ETLConfig, LoadMode
from eoip.etl.incremental import DatasetCheckpoint, IncrementalConfig
from eoip.etl.lineage import LineageRecord, LineageStage
from eoip.etl.pipeline import (
    DEFAULT_CLEAN_LAYER,
    DEFAULT_INCREMENTAL_LAYER,
    DEFAULT_PIPELINE_RUN_PREFIX,
    DEFAULT_SOURCE_LAYER,
    DEFAULT_TRANSFORMED_LAYER,
    DEFAULT_VALIDATED_LAYER,
    DatasetPipelineConfig,
    DatasetPipelineResult,
    ETLPipeline,
    PipelineRunResult,
    run_pipeline,
)
from eoip.etl.transformation import TransformationConfig
from eoip.etl.validation import DatasetContract


def _frame() -> pd.DataFrame:
    """Return a deterministic source dataset."""
    return pd.DataFrame(
        {
            "plant_id": [
                "PLANT-001",
                "PLANT-002",
            ],
            "timestamp": [
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:15:00Z",
            ],
            "capacity_mw": [
                50.0,
                75.0,
            ],
        }
    )


def _contract(
    dataset_name: str = "plants",
) -> DatasetContract:
    """Return a simple valid dataset contract."""
    return DatasetContract(
        dataset_name=dataset_name,
        required_columns=(
            "plant_id",
            "timestamp",
            "capacity_mw",
        ),
        unique_key=(
            "plant_id",
            "timestamp",
        ),
        timestamp_columns=("timestamp",),
        finite_numeric_columns=("capacity_mw",),
    )


def _dataset_config(
    dataset_name: str = "plants",
) -> DatasetPipelineConfig:
    """Return a no-op-oriented pipeline configuration."""
    return DatasetPipelineConfig(
        contract=_contract(dataset_name),
        cleaning=CleaningConfig(),
        transformation=TransformationConfig(),
        incremental=IncrementalConfig(
            watermark_column="timestamp",
            primary_key=(
                "plant_id",
                "timestamp",
            ),
        ),
    )


def _etl_config(
    *,
    load_mode: LoadMode = LoadMode.FULL,
) -> ETLConfig:
    """Return deterministic ETL configuration."""
    return ETLConfig(
        load_mode=load_mode,
    )


class TestDatasetPipelineConfig:
    """Tests for DatasetPipelineConfig."""

    def test_valid_configuration(self) -> None:
        config = _dataset_config()

        assert config.contract.dataset_name == "plants"
        assert isinstance(
            config.cleaning,
            CleaningConfig,
        )
        assert isinstance(
            config.transformation,
            TransformationConfig,
        )
        assert isinstance(
            config.incremental,
            IncrementalConfig,
        )

    def test_invalid_contract_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="contract must be a DatasetContract",
        ):
            DatasetPipelineConfig(
                contract="plants",  # type: ignore[arg-type]
            )

    def test_invalid_cleaning_config_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="cleaning must be a CleaningConfig",
        ):
            DatasetPipelineConfig(
                contract=_contract(),
                cleaning="invalid",  # type: ignore[arg-type]
            )

    def test_invalid_transformation_config_is_rejected(
        self,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="transformation must be a TransformationConfig",
        ):
            DatasetPipelineConfig(
                contract=_contract(),
                transformation="invalid",  # type: ignore[arg-type]
            )

    def test_invalid_incremental_config_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="incremental must be an IncrementalConfig",
        ):
            DatasetPipelineConfig(
                contract=_contract(),
                incremental="invalid",  # type: ignore[arg-type]
            )


class TestETLPipelineConstruction:
    """Tests for ETLPipeline construction."""

    def test_valid_pipeline(self) -> None:
        config = _etl_config()
        dataset_config = _dataset_config()

        pipeline = ETLPipeline(
            config,
            {
                "plants": dataset_config,
            },
        )

        assert pipeline.config is config
        assert isinstance(
            pipeline.dataset_configs,
            MappingProxyType,
        )
        assert pipeline.dataset_configs["plants"] is dataset_config

    def test_dataset_configs_are_sorted(self) -> None:
        pipeline = ETLPipeline(
            _etl_config(),
            {
                "weather": _dataset_config("weather"),
                "plants": _dataset_config("plants"),
            },
        )

        assert list(pipeline.dataset_configs) == [
            "plants",
            "weather",
        ]

    def test_invalid_etl_config_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="config must be an ETLConfig",
        ):
            ETLPipeline(
                "invalid",  # type: ignore[arg-type]
                {},
            )

    def test_invalid_dataset_config_mapping_is_rejected(
        self,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="dataset_configs must be a mapping",
        ):
            ETLPipeline(
                _etl_config(),
                [],  # type: ignore[arg-type]
            )

    def test_invalid_dataset_config_value_is_rejected(
        self,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="DatasetPipelineConfig",
        ):
            ETLPipeline(
                _etl_config(),
                {
                    "plants": "invalid",
                },  # type: ignore[dict-item]
            )

    def test_mapping_key_must_match_contract_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="contract.dataset_name",
        ):
            ETLPipeline(
                _etl_config(),
                {
                    "weather": _dataset_config("plants"),
                },
            )


class TestETLPipelineExecution:
    """Tests for complete dataset and run execution."""

    def test_single_dataset_run(self) -> None:
        pipeline = ETLPipeline(
            _etl_config(),
            {
                "plants": _dataset_config(),
            },
        )

        result = pipeline.run(
            {
                "plants": _frame(),
            },
            run_id="RUN-001",
        )

        assert isinstance(
            result,
            PipelineRunResult,
        )
        assert result.run_id == "RUN-001"
        assert result.passed is True
        assert list(result.datasets) == [
            "plants",
        ]

        dataset_result = result.datasets["plants"]

        assert isinstance(
            dataset_result,
            DatasetPipelineResult,
        )
        assert dataset_result.passed_validation is True
        assert len(dataset_result.output_frame) == 2
        assert dataset_result.checkpoint.dataset_name == "plants"

    def test_pipeline_does_not_mutate_source_frame(self) -> None:
        source = _frame()
        expected = source.copy(deep=True)

        ETLPipeline(
            _etl_config(),
            {
                "plants": _dataset_config(),
            },
        ).run(
            {
                "plants": source,
            },
            run_id="RUN-001",
        )

        pd.testing.assert_frame_equal(
            source,
            expected,
        )

    def test_generated_dataset_results_are_sorted(self) -> None:
        plants = _frame()

        weather = pd.DataFrame(
            {
                "plant_id": [
                    "PLANT-001",
                ],
                "timestamp": [
                    "2026-01-01T00:00:00Z",
                ],
                "capacity_mw": [
                    1.0,
                ],
            }
        )

        result = ETLPipeline(
            _etl_config(),
            {
                "weather": _dataset_config("weather"),
                "plants": _dataset_config("plants"),
            },
        ).run(
            {
                "weather": weather,
                "plants": plants,
            },
            run_id="RUN-001",
        )

        assert list(result.datasets) == [
            "plants",
            "weather",
        ]

    def test_unknown_dataset_is_rejected(self) -> None:
        pipeline = ETLPipeline(
            _etl_config(),
            {
                "plants": _dataset_config(),
            },
        )

        with pytest.raises(
            KeyError,
            match="No pipeline configuration registered",
        ):
            pipeline.run(
                {
                    "weather": _frame(),
                },
                run_id="RUN-001",
            )

    def test_non_dataframe_dataset_is_rejected(self) -> None:
        pipeline = ETLPipeline(
            _etl_config(),
            {
                "plants": _dataset_config(),
            },
        )

        with pytest.raises(
            TypeError,
            match="must be a pandas DataFrame",
        ):
            pipeline.run(
                {
                    "plants": [],  # type: ignore[dict-item]
                },
                run_id="RUN-001",
            )

    def test_invalid_datasets_container_is_rejected(self) -> None:
        pipeline = ETLPipeline(
            _etl_config(),
            {
                "plants": _dataset_config(),
            },
        )

        with pytest.raises(
            TypeError,
            match="datasets must be a mapping",
        ):
            pipeline.run(
                [],  # type: ignore[arg-type]
                run_id="RUN-001",
            )

    def test_invalid_checkpoint_mapping_is_rejected(self) -> None:
        pipeline = ETLPipeline(
            _etl_config(),
            {
                "plants": _dataset_config(),
            },
        )

        with pytest.raises(
            TypeError,
            match="checkpoints must be a mapping or None",
        ):
            pipeline.run(
                {
                    "plants": _frame(),
                },
                run_id="RUN-001",
                checkpoints=[],  # type: ignore[arg-type]
            )

    def test_incremental_checkpoint_filters_old_rows(self) -> None:
        checkpoint = DatasetCheckpoint(
            dataset_name="plants",
            watermark_column="timestamp",
            watermark_value=pd.Timestamp("2026-01-01T00:00:00Z"),
            processed_rows=1,
        )

        result = ETLPipeline(
            _etl_config(load_mode=LoadMode.INCREMENTAL),
            {
                "plants": _dataset_config(),
            },
        ).run(
            {
                "plants": _frame(),
            },
            run_id="RUN-001",
            checkpoints={
                "plants": checkpoint,
            },
        )

        dataset_result = result.datasets["plants"]

        assert len(dataset_result.output_frame) == 1
        assert dataset_result.output_frame.iloc[0]["plant_id"] == "PLANT-002"
        assert dataset_result.checkpoint.processed_rows == 2

    def test_pipeline_records_stage_audit_events(self) -> None:
        result = ETLPipeline(
            _etl_config(),
            {
                "plants": _dataset_config(),
            },
        ).run(
            {
                "plants": _frame(),
            },
            run_id="RUN-001",
        )

        assert all(
            isinstance(
                event,
                AuditEvent,
            )
            for event in result.audit_events
        )

        succeeded_stages = {
            event.stage
            for event in result.audit_events
            if (event.status is AuditStatus.SUCCEEDED)
        }

        assert AuditStage.PIPELINE.value in succeeded_stages
        assert AuditStage.VALIDATION.value in succeeded_stages
        assert AuditStage.CLEANING.value in succeeded_stages
        assert AuditStage.TRANSFORMATION.value in succeeded_stages
        assert AuditStage.INCREMENTAL.value in succeeded_stages

    def test_dataset_result_contains_only_dataset_stage_audit_events(
        self,
    ) -> None:
        result = ETLPipeline(
            _etl_config(),
            {
                "plants": _dataset_config(),
            },
        ).run(
            {
                "plants": _frame(),
            },
            run_id="RUN-001",
        )

        dataset_events = result.datasets["plants"].audit_events

        assert dataset_events
        assert all(event.dataset_name == "plants" for event in dataset_events)

    def test_pipeline_records_lineage_for_processing_stages(
        self,
    ) -> None:
        result = ETLPipeline(
            _etl_config(),
            {
                "plants": _dataset_config(),
            },
        ).run(
            {
                "plants": _frame(),
            },
            run_id="RUN-001",
        )

        assert all(
            isinstance(
                record,
                LineageRecord,
            )
            for record in result.lineage_records
        )

        stages = {record.stage for record in result.lineage_records}

        assert LineageStage.VALIDATION in stages
        assert LineageStage.CLEANING in stages
        assert LineageStage.TRANSFORMATION in stages
        assert LineageStage.INCREMENTAL in stages

    def test_output_frames_property(self) -> None:
        result = ETLPipeline(
            _etl_config(),
            {
                "plants": _dataset_config(),
            },
        ).run(
            {
                "plants": _frame(),
            },
            run_id="RUN-001",
        )

        assert list(result.output_frames) == [
            "plants",
        ]
        assert len(result.output_frames["plants"]) == 2

    def test_checkpoints_property(self) -> None:
        result = ETLPipeline(
            _etl_config(),
            {
                "plants": _dataset_config(),
            },
        ).run(
            {
                "plants": _frame(),
            },
            run_id="RUN-001",
        )

        checkpoints = result.checkpoints

        assert list(checkpoints) == [
            "plants",
        ]
        assert isinstance(
            checkpoints["plants"],
            DatasetCheckpoint,
        )

    def test_invalid_data_marks_run_as_not_passed(self) -> None:
        frame = _frame()
        frame.loc[
            0,
            "capacity_mw",
        ] = float("inf")

        result = ETLPipeline(
            _etl_config(),
            {
                "plants": _dataset_config(),
            },
        ).run(
            {
                "plants": frame,
            },
            run_id="RUN-001",
        )

        assert result.datasets["plants"].passed_validation is False
        assert result.passed is False


class TestRunPipelineHelper:
    """Tests for run_pipeline."""

    def test_helper_executes_pipeline(self) -> None:
        result = run_pipeline(
            _etl_config(),
            {
                "plants": _dataset_config(),
            },
            {
                "plants": _frame(),
            },
            run_id="RUN-HELPER",
        )

        assert isinstance(
            result,
            PipelineRunResult,
        )
        assert result.run_id == "RUN-HELPER"


class TestPipelineRunResult:
    """Tests for PipelineRunResult validation."""

    def test_naive_datetimes_are_normalized_to_utc(self) -> None:
        result = ETLPipeline(
            _etl_config(),
            {
                "plants": _dataset_config(),
            },
        ).run(
            {
                "plants": _frame(),
            },
            run_id="RUN-001",
        )

        reconstructed = PipelineRunResult(
            run_id=result.run_id,
            datasets=result.datasets,
            audit_events=result.audit_events,
            lineage_records=result.lineage_records,
            started_at=datetime(
                2026,
                1,
                1,
            ),
            completed_at=datetime(
                2026,
                1,
                1,
                0,
                1,
            ),
        )

        assert reconstructed.started_at.tzinfo is UTC
        assert reconstructed.completed_at.tzinfo is UTC

    def test_completed_at_cannot_precede_started_at(self) -> None:
        with pytest.raises(
            ValueError,
            match="cannot be earlier",
        ):
            PipelineRunResult(
                run_id="RUN-001",
                datasets={},
                audit_events=(),
                lineage_records=(),
                started_at=datetime(
                    2026,
                    1,
                    2,
                    tzinfo=UTC,
                ),
                completed_at=datetime(
                    2026,
                    1,
                    1,
                    tzinfo=UTC,
                ),
            )


class TestPipelineConstants:
    """Tests for stable pipeline constants."""

    def test_constants_are_stable(self) -> None:
        assert DEFAULT_PIPELINE_RUN_PREFIX == "ETL"
        assert DEFAULT_SOURCE_LAYER == "ingested"
        assert DEFAULT_VALIDATED_LAYER == "validated"
        assert DEFAULT_CLEAN_LAYER == "clean"
        assert DEFAULT_TRANSFORMED_LAYER == "transformed"
        assert DEFAULT_INCREMENTAL_LAYER == "incremental"
