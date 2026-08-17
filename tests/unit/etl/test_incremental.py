"""Unit tests for EOIP Phase 3 incremental ETL processing."""

from __future__ import annotations

from datetime import UTC, datetime
from types import MappingProxyType

import pandas as pd
import pytest

from eoip.etl.config import ETLConfig, LoadMode
from eoip.etl.incremental import (
    DEFAULT_CHECKPOINT_VERSION,
    DEFAULT_PRIMARY_KEY,
    DEFAULT_WATERMARK_COLUMN,
    DatasetCheckpoint,
    IncrementalConfig,
    IncrementalDecision,
    IncrementalProcessor,
    IncrementalResult,
    process_incremental,
    process_incremental_datasets,
)


def _frame() -> pd.DataFrame:
    """Return a deterministic incremental-processing source frame."""
    return pd.DataFrame(
        {
            "plant_id": [
                "PLANT-002",
                "PLANT-001",
                "PLANT-001",
                "PLANT-003",
            ],
            "timestamp": [
                "2026-01-01T00:15:00Z",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:30:00Z",
            ],
            "value": [
                20.0,
                10.0,
                11.0,
                30.0,
            ],
        },
        index=[10, 5, 7, 20],
    )


def _etl_config(
    *,
    load_mode: LoadMode = LoadMode.INCREMENTAL,
) -> ETLConfig:
    """Return a minimal ETL configuration with selected load mode."""
    return ETLConfig(
        load_mode=load_mode,
    )


def _incremental_config(
    *,
    inclusive_watermark: bool = False,
    primary_key: tuple[str, ...] = ("plant_id", "timestamp"),
    drop_duplicate_keys: bool = True,
    sort_output: bool = True,
    reset_index: bool = True,
) -> IncrementalConfig:
    """Return a representative incremental-processing configuration."""
    return IncrementalConfig(
        watermark_column="timestamp",
        primary_key=primary_key,
        inclusive_watermark=inclusive_watermark,
        drop_duplicate_keys=drop_duplicate_keys,
        sort_output=sort_output,
        reset_index=reset_index,
    )


def _checkpoint(
    watermark: str = "2026-01-01T00:00:00Z",
    *,
    processed_rows: int = 5,
) -> DatasetCheckpoint:
    """Return a deterministic checkpoint."""
    return DatasetCheckpoint(
        dataset_name="plants",
        watermark_column="timestamp",
        watermark_value=pd.Timestamp(watermark),
        processed_rows=processed_rows,
        updated_at=datetime(
            2026,
            1,
            2,
            0,
            0,
            tzinfo=UTC,
        ),
        metadata={
            "source": "unit-test",
        },
    )


class TestIncrementalConfig:
    """Tests for IncrementalConfig."""

    def test_defaults_are_valid(self) -> None:
        config = IncrementalConfig()

        assert config.watermark_column == DEFAULT_WATERMARK_COLUMN
        assert config.primary_key == DEFAULT_PRIMARY_KEY
        assert config.inclusive_watermark is False
        assert config.drop_duplicate_keys is True
        assert config.sort_output is True
        assert config.reset_index is True

    def test_watermark_column_is_trimmed(self) -> None:
        config = IncrementalConfig(
            watermark_column=" timestamp ",
        )

        assert config.watermark_column == "timestamp"

    def test_empty_watermark_column_is_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="watermark_column cannot be empty",
        ):
            IncrementalConfig(
                watermark_column="   ",
            )

    def test_primary_key_is_trimmed(self) -> None:
        config = IncrementalConfig(
            primary_key=(
                " plant_id ",
                " timestamp ",
            )
        )

        assert config.primary_key == (
            "plant_id",
            "timestamp",
        )

    def test_duplicate_primary_key_columns_are_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="cannot contain duplicate values",
        ):
            IncrementalConfig(
                primary_key=(
                    "plant_id",
                    "plant_id",
                )
            )

    def test_primary_key_requires_tuple(self) -> None:
        with pytest.raises(
            TypeError,
            match="primary_key must be a tuple",
        ):
            IncrementalConfig(primary_key=["plant_id"])  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "field_name",
        [
            "inclusive_watermark",
            "drop_duplicate_keys",
            "sort_output",
            "reset_index",
        ],
    )
    def test_boolean_fields_require_bool(
        self,
        field_name: str,
    ) -> None:
        kwargs = {
            field_name: 1,
        }

        with pytest.raises(TypeError):
            IncrementalConfig(**kwargs)


class TestDatasetCheckpoint:
    """Tests for DatasetCheckpoint."""

    def test_valid_checkpoint(self) -> None:
        checkpoint = _checkpoint()

        assert checkpoint.dataset_name == "plants"
        assert checkpoint.watermark_column == "timestamp"
        assert checkpoint.watermark_value == pd.Timestamp("2026-01-01T00:00:00Z")
        assert checkpoint.processed_rows == 5
        assert checkpoint.updated_at.tzinfo is not None
        assert isinstance(
            checkpoint.metadata,
            MappingProxyType,
        )

    def test_names_are_trimmed(self) -> None:
        checkpoint = DatasetCheckpoint(
            dataset_name=" plants ",
            watermark_column=" timestamp ",
            version=" 1.0 ",
        )

        assert checkpoint.dataset_name == "plants"
        assert checkpoint.watermark_column == "timestamp"
        assert checkpoint.version == "1.0"

    def test_watermark_is_normalized_to_utc(self) -> None:
        checkpoint = DatasetCheckpoint(
            dataset_name="plants",
            watermark_column="timestamp",
            watermark_value=pd.Timestamp("2026-01-01 00:00:00"),
        )

        assert str(checkpoint.watermark_value.tz) == "UTC"

    def test_naive_updated_at_is_normalized_to_utc(self) -> None:
        checkpoint = DatasetCheckpoint(
            dataset_name="plants",
            watermark_column="timestamp",
            updated_at=datetime(
                2026,
                1,
                1,
            ),
        )

        assert checkpoint.updated_at.tzinfo is UTC

    def test_negative_processed_rows_are_rejected(self) -> None:
        with pytest.raises(ValueError):
            DatasetCheckpoint(
                dataset_name="plants",
                watermark_column="timestamp",
                processed_rows=-1,
            )

    def test_metadata_is_immutable(self) -> None:
        checkpoint = _checkpoint()

        with pytest.raises(TypeError):
            checkpoint.metadata["x"] = 1  # type: ignore[index]

    def test_to_dict_serializes_checkpoint(self) -> None:
        checkpoint = _checkpoint()

        result = checkpoint.to_dict()

        assert result["dataset_name"] == "plants"
        assert result["watermark_column"] == "timestamp"
        assert result["watermark_value"] == ("2026-01-01T00:00:00+00:00")
        assert result["processed_rows"] == 5
        assert result["version"] == DEFAULT_CHECKPOINT_VERSION
        assert result["metadata"] == {"source": "unit-test"}

    def test_round_trip_from_dict(self) -> None:
        checkpoint = _checkpoint()

        restored = DatasetCheckpoint.from_dict(checkpoint.to_dict())

        assert restored.dataset_name == checkpoint.dataset_name
        assert restored.watermark_column == checkpoint.watermark_column
        assert restored.watermark_value == checkpoint.watermark_value
        assert restored.processed_rows == checkpoint.processed_rows
        assert restored.metadata == checkpoint.metadata

    def test_from_dict_rejects_invalid_value(self) -> None:
        with pytest.raises(
            TypeError,
            match="value must be a mapping",
        ):
            DatasetCheckpoint.from_dict([])  # type: ignore[arg-type]


class TestIncrementalResult:
    """Tests for IncrementalResult."""

    def test_has_rows(self) -> None:
        checkpoint = _checkpoint()

        result = IncrementalResult(
            dataset_name="plants",
            frame=pd.DataFrame(
                {
                    "plant_id": ["PLANT-001"],
                }
            ),
            decision=IncrementalDecision.INCREMENTAL_LOAD,
            input_rows=1,
            output_rows=1,
            previous_watermark=checkpoint.watermark_value,
            new_watermark=checkpoint.watermark_value,
            checkpoint=checkpoint,
        )

        assert result.has_rows is True

    def test_empty_result_has_no_rows(self) -> None:
        checkpoint = _checkpoint()

        result = IncrementalResult(
            dataset_name="plants",
            frame=pd.DataFrame(),
            decision=IncrementalDecision.NO_NEW_ROWS,
            input_rows=1,
            output_rows=0,
            previous_watermark=checkpoint.watermark_value,
            new_watermark=checkpoint.watermark_value,
            checkpoint=checkpoint,
        )

        assert result.has_rows is False


class TestIncrementalProcessor:
    """Tests for IncrementalProcessor."""

    def test_exposes_configs(self) -> None:
        etl_config = _etl_config()
        incremental_config = _incremental_config()

        processor = IncrementalProcessor(
            etl_config,
            incremental_config,
        )

        assert processor.etl_config is etl_config
        assert processor.config is incremental_config

    def test_invalid_etl_config_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="etl_config must be an ETLConfig",
        ):
            IncrementalProcessor(
                "invalid",  # type: ignore[arg-type]
            )

    def test_invalid_incremental_config_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="IncrementalConfig",
        ):
            IncrementalProcessor(
                _etl_config(),
                "invalid",  # type: ignore[arg-type]
            )

    def test_full_load_returns_all_rows(self) -> None:
        processor = IncrementalProcessor(
            _etl_config(load_mode=LoadMode.FULL),
            _incremental_config(),
        )

        result = processor.process(
            "plants",
            _frame(),
            _checkpoint(),
        )

        assert result.decision is IncrementalDecision.FULL_LOAD
        assert result.input_rows == 4
        assert result.output_rows == 3
        assert result.new_watermark == pd.Timestamp("2026-01-01T00:30:00Z")

    def test_incremental_without_checkpoint_processes_all_rows(
        self,
    ) -> None:
        result = IncrementalProcessor(
            _etl_config(),
            _incremental_config(),
        ).process(
            "plants",
            _frame(),
        )

        assert result.decision is IncrementalDecision.INCREMENTAL_LOAD
        assert result.output_rows == 3

    def test_incremental_filters_rows_after_watermark(self) -> None:
        result = IncrementalProcessor(
            _etl_config(),
            _incremental_config(),
        ).process(
            "plants",
            _frame(),
            _checkpoint("2026-01-01T00:00:00Z"),
        )

        assert result.frame["plant_id"].tolist() == [
            "PLANT-002",
            "PLANT-003",
        ]
        assert result.output_rows == 2
        assert result.previous_watermark == pd.Timestamp("2026-01-01T00:00:00Z")
        assert result.new_watermark == pd.Timestamp("2026-01-01T00:30:00Z")

    def test_inclusive_watermark_reprocesses_equal_rows(
        self,
    ) -> None:
        result = IncrementalProcessor(
            _etl_config(),
            _incremental_config(inclusive_watermark=True),
        ).process(
            "plants",
            _frame(),
            _checkpoint("2026-01-01T00:00:00Z"),
        )

        assert result.output_rows == 3
        assert result.frame["plant_id"].tolist() == [
            "PLANT-001",
            "PLANT-002",
            "PLANT-003",
        ]

    def test_no_new_rows_returns_no_new_rows_decision(self) -> None:
        result = IncrementalProcessor(
            _etl_config(),
            _incremental_config(),
        ).process(
            "plants",
            _frame(),
            _checkpoint("2026-01-01T00:30:00Z"),
        )

        assert result.decision is IncrementalDecision.NO_NEW_ROWS
        assert result.output_rows == 0
        assert result.new_watermark == pd.Timestamp("2026-01-01T00:30:00Z")

    def test_checkpoint_processed_rows_accumulate(self) -> None:
        result = IncrementalProcessor(
            _etl_config(),
            _incremental_config(),
        ).process(
            "plants",
            _frame(),
            _checkpoint(processed_rows=10),
        )

        assert result.checkpoint.processed_rows == 12

    def test_duplicate_business_keys_keep_last(self) -> None:
        result = IncrementalProcessor(
            _etl_config(),
            _incremental_config(),
        ).process(
            "plants",
            _frame(),
        )

        plant_one = result.frame.loc[result.frame["plant_id"] == "PLANT-001"]

        assert len(plant_one) == 1
        assert plant_one.iloc[0]["value"] == 11.0

    def test_deduplication_can_be_disabled(self) -> None:
        result = IncrementalProcessor(
            _etl_config(),
            _incremental_config(drop_duplicate_keys=False),
        ).process(
            "plants",
            _frame(),
        )

        assert result.output_rows == 4

    def test_output_is_sorted_by_watermark_and_key(self) -> None:
        result = IncrementalProcessor(
            _etl_config(),
            _incremental_config(),
        ).process(
            "plants",
            _frame(),
        )

        assert result.frame["plant_id"].tolist() == [
            "PLANT-001",
            "PLANT-002",
            "PLANT-003",
        ]

    def test_sorting_can_be_disabled(self) -> None:
        result = IncrementalProcessor(
            _etl_config(),
            _incremental_config(
                sort_output=False,
                drop_duplicate_keys=False,
            ),
        ).process(
            "plants",
            _frame(),
        )

        assert result.frame["plant_id"].tolist() == [
            "PLANT-002",
            "PLANT-001",
            "PLANT-001",
            "PLANT-003",
        ]

    def test_index_is_reset_by_default(self) -> None:
        result = IncrementalProcessor(
            _etl_config(),
            _incremental_config(),
        ).process(
            "plants",
            _frame(),
        )

        assert result.frame.index.tolist() == [
            0,
            1,
            2,
        ]

    def test_index_can_be_preserved(self) -> None:
        result = IncrementalProcessor(
            _etl_config(),
            _incremental_config(
                reset_index=False,
                sort_output=False,
                drop_duplicate_keys=False,
            ),
        ).process(
            "plants",
            _frame(),
        )

        assert result.frame.index.tolist() == [
            10,
            5,
            7,
            20,
        ]

    def test_missing_watermark_column_is_rejected(self) -> None:
        frame = _frame().drop(columns=["timestamp"])

        with pytest.raises(
            KeyError,
            match="Watermark column is missing",
        ):
            IncrementalProcessor(
                _etl_config(),
                _incremental_config(),
            ).process(
                "plants",
                frame,
            )

    def test_invalid_watermark_value_is_rejected(self) -> None:
        frame = _frame()
        frame.loc[0, "timestamp"] = "invalid"

        with pytest.raises(
            ValueError,
            match="null or unparseable",
        ):
            IncrementalProcessor(
                _etl_config(),
                _incremental_config(),
            ).process(
                "plants",
                frame,
            )

    def test_checkpoint_dataset_must_match(self) -> None:
        checkpoint = DatasetCheckpoint(
            dataset_name="weather",
            watermark_column="timestamp",
        )

        with pytest.raises(
            ValueError,
            match="dataset_name does not match",
        ):
            IncrementalProcessor(
                _etl_config(),
                _incremental_config(),
            ).process(
                "plants",
                _frame(),
                checkpoint,
            )

    def test_checkpoint_watermark_column_must_match(self) -> None:
        checkpoint = DatasetCheckpoint(
            dataset_name="plants",
            watermark_column="event_time",
        )

        with pytest.raises(
            ValueError,
            match="watermark_column does not match",
        ):
            IncrementalProcessor(
                _etl_config(),
                _incremental_config(),
            ).process(
                "plants",
                _frame(),
                checkpoint,
            )

    def test_missing_primary_key_column_is_rejected(self) -> None:
        frame = _frame().drop(columns=["plant_id"])

        with pytest.raises(
            KeyError,
            match="Primary-key columns are missing",
        ):
            IncrementalProcessor(
                _etl_config(),
                _incremental_config(),
            ).process(
                "plants",
                frame,
            )


class TestPublicIncrementalHelpers:
    """Tests for public incremental-processing helpers."""

    def test_process_incremental_helper(self) -> None:
        result = process_incremental(
            _etl_config(),
            "plants",
            _frame(),
            config=_incremental_config(),
        )

        assert isinstance(
            result,
            IncrementalResult,
        )

    def test_process_incremental_datasets_returns_sorted_keys(
        self,
    ) -> None:
        datasets = {
            "weather": pd.DataFrame(
                {
                    "timestamp": ["2026-01-01T00:00:00Z"],
                    "value": [1],
                }
            ),
            "plants": pd.DataFrame(
                {
                    "timestamp": ["2026-01-01T00:00:00Z"],
                    "value": [2],
                }
            ),
        }

        configs = {
            "weather": IncrementalConfig(),
            "plants": IncrementalConfig(),
        }

        results = process_incremental_datasets(
            _etl_config(),
            datasets,
            configs=configs,
        )

        assert list(results) == [
            "plants",
            "weather",
        ]

    def test_process_incremental_datasets_supports_checkpoints(
        self,
    ) -> None:
        datasets = {
            "plants": _frame(),
        }

        checkpoints = {"plants": _checkpoint("2026-01-01T00:15:00Z")}

        configs = {"plants": _incremental_config()}

        results = process_incremental_datasets(
            _etl_config(),
            datasets,
            checkpoints=checkpoints,
            configs=configs,
        )

        assert results["plants"].output_rows == 1

    def test_invalid_dataset_mapping_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="datasets must be a mapping",
        ):
            process_incremental_datasets(
                _etl_config(),
                [],  # type: ignore[arg-type]
            )

    def test_invalid_checkpoint_mapping_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="checkpoints must be a mapping or None",
        ):
            process_incremental_datasets(
                _etl_config(),
                {},
                checkpoints=[],  # type: ignore[arg-type]
            )

    def test_invalid_config_mapping_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="configs must be a mapping or None",
        ):
            process_incremental_datasets(
                _etl_config(),
                {},
                configs=[],  # type: ignore[arg-type]
            )

    def test_default_constants_are_stable(self) -> None:
        assert DEFAULT_WATERMARK_COLUMN == "timestamp"
        assert DEFAULT_PRIMARY_KEY == ()
        assert DEFAULT_CHECKPOINT_VERSION == "1.0"
