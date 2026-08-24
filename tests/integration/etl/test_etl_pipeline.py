"""Integration tests for the EOIP Phase 3 ETL pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from eoip.etl.cleaning import CleaningConfig
from eoip.etl.config import ETLConfig, LoadMode
from eoip.etl.incremental import IncrementalConfig
from eoip.etl.pipeline import DatasetPipelineConfig, ETLPipeline
from eoip.etl.transformation import TransformationConfig
from eoip.etl.validation import DatasetContract


def _plants_frame() -> pd.DataFrame:
    """Return a deterministic integration-test plants dataset."""
    return pd.DataFrame(
        {
            "plant_id": [
                "PLANT-001",
                "PLANT-002",
                "PLANT-003",
            ],
            "timestamp": [
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:15:00Z",
                "2026-01-01T00:30:00Z",
            ],
            "capacity_mw": [
                50.0,
                75.0,
                100.0,
            ],
        }
    )


def _weather_frame() -> pd.DataFrame:
    """Return a deterministic integration-test weather dataset."""
    return pd.DataFrame(
        {
            "plant_id": [
                "PLANT-001",
                "PLANT-001",
                "PLANT-002",
            ],
            "timestamp": [
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:15:00Z",
                "2026-01-01T00:00:00Z",
            ],
            "irradiance_wm2": [
                0.0,
                10.0,
                0.0,
            ],
        }
    )


def _plants_contract() -> DatasetContract:
    """Return the plants validation contract."""
    return DatasetContract(
        dataset_name="plants",
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


def _weather_contract() -> DatasetContract:
    """Return the weather validation contract."""
    return DatasetContract(
        dataset_name="weather",
        required_columns=(
            "plant_id",
            "timestamp",
            "irradiance_wm2",
        ),
        unique_key=(
            "plant_id",
            "timestamp",
        ),
        timestamp_columns=("timestamp",),
        finite_numeric_columns=("irradiance_wm2",),
    )


def _dataset_config(
    contract: DatasetContract,
) -> DatasetPipelineConfig:
    """Return a complete dataset pipeline configuration."""
    return DatasetPipelineConfig(
        contract=contract,
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


def _pipeline(
    *,
    load_mode: LoadMode = LoadMode.FULL,
) -> ETLPipeline:
    """Return an ETL pipeline configured for integration tests."""
    return ETLPipeline(
        ETLConfig(
            load_mode=load_mode,
        ),
        {
            "plants": _dataset_config(_plants_contract()),
            "weather": _dataset_config(_weather_contract()),
        },
    )


class TestETLPipelineIntegration:
    """End-to-end integration tests for Phase 3 ETL orchestration."""

    def test_multiple_datasets_run_end_to_end(self) -> None:
        result = _pipeline().run(
            {
                "plants": _plants_frame(),
                "weather": _weather_frame(),
            },
            run_id="RUN-INTEGRATION-001",
        )

        assert result.run_id == "RUN-INTEGRATION-001"
        assert result.passed is True
        assert list(result.datasets) == [
            "plants",
            "weather",
        ]

        assert len(result.output_frames["plants"]) == 3
        assert len(result.output_frames["weather"]) == 3

        assert result.datasets["plants"].passed_validation is True
        assert result.datasets["weather"].passed_validation is True

    def test_pipeline_preserves_source_frames(self) -> None:
        plants = _plants_frame()
        weather = _weather_frame()

        expected_plants = plants.copy(deep=True)
        expected_weather = weather.copy(deep=True)

        _pipeline().run(
            {
                "plants": plants,
                "weather": weather,
            },
            run_id="RUN-INTEGRATION-002",
        )

        pd.testing.assert_frame_equal(
            plants,
            expected_plants,
        )
        pd.testing.assert_frame_equal(
            weather,
            expected_weather,
        )

    def test_audit_and_lineage_are_generated(self) -> None:
        result = _pipeline().run(
            {
                "plants": _plants_frame(),
            },
            run_id="RUN-INTEGRATION-003",
        )

        assert result.audit_events
        assert result.lineage_records

        dataset_result = result.datasets["plants"]

        assert dataset_result.audit_events
        assert dataset_result.lineage_records

        assert all(
            event.run_id == "RUN-INTEGRATION-003" for event in result.audit_events
        )

        assert all(
            record.run_id == "RUN-INTEGRATION-003" for record in result.lineage_records
        )

    def test_output_and_checkpoint_contracts_are_consistent(
        self,
    ) -> None:
        result = _pipeline().run(
            {
                "plants": _plants_frame(),
            },
            run_id="RUN-INTEGRATION-004",
        )

        output = result.output_frames["plants"]
        checkpoint = result.checkpoints["plants"]

        assert len(output) == 3
        assert checkpoint.dataset_name == "plants"
        assert checkpoint.processed_rows == 3

    def test_invalid_dataset_marks_run_as_failed_validation(
        self,
    ) -> None:
        plants = _plants_frame()
        plants.loc[
            0,
            "capacity_mw",
        ] = float("inf")

        result = _pipeline().run(
            {
                "plants": plants,
            },
            run_id="RUN-INTEGRATION-005",
        )

        assert result.passed is False
        assert result.datasets["plants"].passed_validation is False

    def test_unknown_dataset_is_rejected(self) -> None:
        with pytest.raises(
            KeyError,
            match="No pipeline configuration registered",
        ):
            _pipeline().run(
                {
                    "unknown": pd.DataFrame(
                        {
                            "id": [
                                1,
                            ]
                        }
                    )
                },
                run_id="RUN-INTEGRATION-006",
            )

    def test_pipeline_outputs_can_be_written_and_read(
        self,
        tmp_path: Path,
    ) -> None:
        result = _pipeline().run(
            {
                "plants": _plants_frame(),
            },
            run_id="RUN-INTEGRATION-007",
        )

        output = result.output_frames["plants"]

        path = tmp_path / "plants.parquet"

        output.to_parquet(
            path,
            index=False,
        )

        restored = pd.read_parquet(path)

        pd.testing.assert_frame_equal(
            restored,
            output,
            check_dtype=False,
        )

    def test_repeated_full_runs_are_deterministic(self) -> None:
        datasets = {
            "plants": _plants_frame(),
            "weather": _weather_frame(),
        }

        first = _pipeline().run(
            datasets,
            run_id="RUN-INTEGRATION-008-A",
        )

        second = _pipeline().run(
            datasets,
            run_id="RUN-INTEGRATION-008-B",
        )

        pd.testing.assert_frame_equal(
            first.output_frames["plants"],
            second.output_frames["plants"],
        )
        pd.testing.assert_frame_equal(
            first.output_frames["weather"],
            second.output_frames["weather"],
        )

    def test_incremental_run_filters_previously_processed_rows(
        self,
    ) -> None:
        full_result = _pipeline().run(
            {
                "plants": _plants_frame(),
            },
            run_id="RUN-INTEGRATION-009-FULL",
        )

        checkpoint = full_result.checkpoints["plants"]

        newer = pd.DataFrame(
            {
                "plant_id": [
                    "PLANT-003",
                    "PLANT-004",
                ],
                "timestamp": [
                    "2026-01-01T00:30:00Z",
                    "2026-01-01T00:45:00Z",
                ],
                "capacity_mw": [
                    100.0,
                    125.0,
                ],
            }
        )

        incremental_result = _pipeline(load_mode=LoadMode.INCREMENTAL).run(
            {
                "plants": newer,
            },
            run_id="RUN-INTEGRATION-009-INCREMENTAL",
            checkpoints={
                "plants": checkpoint,
            },
        )

        output = incremental_result.output_frames["plants"]

        assert len(output) == 1
        assert output.iloc[0]["plant_id"] == "PLANT-004"
        assert incremental_result.checkpoints["plants"].processed_rows == 4
