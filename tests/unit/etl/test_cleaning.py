"""Unit tests for EOIP Phase 3 ETL cleaning and standardization."""

from __future__ import annotations

from types import MappingProxyType

import pandas as pd
import pytest

from eoip.etl.cleaning import (
    DEFAULT_NULL_TOKENS,
    CleaningConfig,
    CleaningResult,
    DataCleaner,
    clean_dataframe,
    clean_datasets,
)


def _sample_frame() -> pd.DataFrame:
    """Return a representative dirty ETL DataFrame."""
    return pd.DataFrame(
        {
            " Plant ID ": [
                " plant-002 ",
                " plant-001 ",
            ],
            "Timestamp": [
                "2026-01-01 00:15:00",
                "2026-01-01 00:00:00",
            ],
            "Capacity-MW": [
                " 75.5 ",
                " 50.0 ",
            ],
            "Status": [
                " online ",
                " OFFLINE ",
            ],
            "Note": [
                " N/A ",
                " ready ",
            ],
        },
        index=[10, 5],
    )


class TestCleaningConfig:
    """Tests for CleaningConfig."""

    def test_defaults_are_valid(self) -> None:
        config = CleaningConfig()

        assert config.strip_column_names is True
        assert config.lowercase_column_names is True
        assert config.normalize_column_separators is True
        assert config.strip_string_values is True
        assert config.normalize_empty_strings is True
        assert config.null_tokens == DEFAULT_NULL_TOKENS
        assert config.reset_index is True
        assert isinstance(config.rename_columns, MappingProxyType)

    def test_string_sequences_are_normalized(self) -> None:
        config = CleaningConfig(
            timestamp_columns=[" timestamp "],
            numeric_columns=[" capacity_mw "],
            uppercase_columns=[" plant_id "],
            lowercase_columns=[" status "],
            sort_by=[" timestamp "],
        )

        assert config.timestamp_columns == ("timestamp",)
        assert config.numeric_columns == ("capacity_mw",)
        assert config.uppercase_columns == ("plant_id",)
        assert config.lowercase_columns == ("status",)
        assert config.sort_by == ("timestamp",)

    def test_duplicate_sequence_values_are_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="cannot contain duplicate values",
        ):
            CleaningConfig(
                numeric_columns=(
                    "capacity_mw",
                    "capacity_mw",
                )
            )

    def test_string_is_not_accepted_as_sequence(self) -> None:
        with pytest.raises(
            TypeError,
            match="iterable of strings",
        ):
            CleaningConfig(
                numeric_columns="capacity_mw",  # type: ignore[arg-type]
            )

    def test_uppercase_lowercase_overlap_is_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="both uppercase and lowercase",
        ):
            CleaningConfig(
                uppercase_columns=("status",),
                lowercase_columns=("status",),
            )

    def test_rename_mapping_is_normalized_and_immutable(self) -> None:
        config = CleaningConfig(
            rename_columns={
                " old_name ": " new_name ",
            }
        )

        assert config.rename_columns == {"old_name": "new_name"}
        assert isinstance(
            config.rename_columns,
            MappingProxyType,
        )

        with pytest.raises(TypeError):
            config.rename_columns["x"] = "y"  # type: ignore[index]

    def test_empty_rename_key_is_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="keys cannot be empty",
        ):
            CleaningConfig(
                rename_columns={
                    " ": "new_name",
                }
            )

    def test_empty_rename_value_is_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="values cannot be empty",
        ):
            CleaningConfig(
                rename_columns={
                    "old_name": " ",
                }
            )

    @pytest.mark.parametrize(
        "field_name",
        [
            "strip_column_names",
            "lowercase_column_names",
            "normalize_column_separators",
            "strip_string_values",
            "normalize_empty_strings",
            "reset_index",
        ],
    )
    def test_boolean_settings_require_bool(
        self,
        field_name: str,
    ) -> None:
        kwargs = {
            field_name: 1,
        }

        with pytest.raises(TypeError):
            CleaningConfig(**kwargs)


class TestCleaningResult:
    """Tests for CleaningResult."""

    def test_valid_result(self) -> None:
        frame = pd.DataFrame(
            {
                "value": [1],
            }
        )

        result = CleaningResult(
            frame=frame,
            rows_before=1,
            rows_after=1,
            columns_before=("value",),
            columns_after=("value",),
            changes=(),
        )

        assert result.frame is frame
        assert result.rows_before == 1
        assert result.rows_after == 1

    def test_invalid_frame_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="pandas DataFrame",
        ):
            CleaningResult(
                frame=[],  # type: ignore[arg-type]
                rows_before=0,
                rows_after=0,
                columns_before=(),
                columns_after=(),
                changes=(),
            )

    def test_negative_row_count_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            CleaningResult(
                frame=pd.DataFrame(),
                rows_before=-1,
                rows_after=0,
                columns_before=(),
                columns_after=(),
                changes=(),
            )


class TestDataCleaner:
    """Tests for DataCleaner."""

    def test_default_cleaner_exposes_config(self) -> None:
        cleaner = DataCleaner()

        assert isinstance(
            cleaner.config,
            CleaningConfig,
        )

    def test_invalid_config_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="CleaningConfig",
        ):
            DataCleaner("invalid")  # type: ignore[arg-type]

    def test_invalid_frame_is_rejected(self) -> None:
        cleaner = DataCleaner()

        with pytest.raises(
            TypeError,
            match="pandas DataFrame",
        ):
            cleaner.clean([])  # type: ignore[arg-type]

    def test_source_frame_is_not_mutated(self) -> None:
        frame = _sample_frame()
        original = frame.copy(deep=True)

        DataCleaner().clean(frame)

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_column_names_are_standardized(self) -> None:
        result = DataCleaner().clean(_sample_frame())

        assert result.columns_after == (
            "plant_id",
            "timestamp",
            "capacity_mw",
            "status",
            "note",
        )
        assert "standardized_columns" in result.changes

    def test_duplicate_columns_after_normalization_are_rejected(
        self,
    ) -> None:
        frame = pd.DataFrame(
            {
                "Plant ID": [1],
                "plant-id": [2],
            }
        )

        with pytest.raises(
            ValueError,
            match="duplicate column names",
        ):
            DataCleaner().clean(frame)

    def test_explicit_column_renames_are_applied(self) -> None:
        frame = pd.DataFrame(
            {
                "plant": ["PLANT-001"],
            }
        )

        result = DataCleaner(
            CleaningConfig(
                rename_columns={
                    "plant": "plant_id",
                }
            )
        ).clean(frame)

        assert result.columns_after == ("plant_id",)
        assert "renamed_columns" in result.changes

    def test_duplicate_columns_after_explicit_rename_are_rejected(
        self,
    ) -> None:
        frame = pd.DataFrame(
            {
                "plant": [1],
                "plant_id": [2],
            }
        )

        cleaner = DataCleaner(
            CleaningConfig(
                rename_columns={
                    "plant": "plant_id",
                }
            )
        )

        with pytest.raises(
            ValueError,
            match="duplicate columns",
        ):
            cleaner.clean(frame)

    def test_string_values_are_stripped(self) -> None:
        result = DataCleaner().clean(_sample_frame())

        assert (
            result.frame.loc[
                0,
                "plant_id",
            ]
            == "plant-002"
        )
        assert "stripped_string_values" in result.changes

    def test_null_tokens_are_normalized(self) -> None:
        result = DataCleaner().clean(_sample_frame())

        assert pd.isna(
            result.frame.loc[
                0,
                "note",
            ]
        )
        assert "normalized_null_tokens" in result.changes

    def test_empty_string_is_normalized_to_na(self) -> None:
        frame = pd.DataFrame(
            {
                "note": [
                    "",
                    "   ",
                    "value",
                ]
            }
        )

        result = DataCleaner().clean(frame)

        assert pd.isna(
            result.frame.loc[
                0,
                "note",
            ]
        )
        assert pd.isna(
            result.frame.loc[
                1,
                "note",
            ]
        )
        assert (
            result.frame.loc[
                2,
                "note",
            ]
            == "value"
        )

    def test_case_normalization_is_applied(self) -> None:
        config = CleaningConfig(
            uppercase_columns=("plant_id",),
            lowercase_columns=("status",),
        )

        result = DataCleaner(config).clean(_sample_frame())

        assert result.frame["plant_id"].tolist() == [
            "PLANT-002",
            "PLANT-001",
        ]

        assert result.frame["status"].tolist() == [
            "online",
            "offline",
        ]

        assert "uppercased_columns" in result.changes
        assert "lowercased_columns" in result.changes

    def test_timestamp_columns_are_normalized_to_utc(self) -> None:
        config = CleaningConfig(
            timestamp_columns=("timestamp",),
        )

        result = DataCleaner(config).clean(_sample_frame())

        assert isinstance(
            result.frame["timestamp"].dtype,
            pd.DatetimeTZDtype,
        )
        assert str(result.frame["timestamp"].dt.tz) == "UTC"
        assert "normalized_timestamps" in result.changes

    def test_invalid_timestamps_are_coerced_to_nat(self) -> None:
        frame = pd.DataFrame(
            {
                "timestamp": [
                    "2026-01-01",
                    "invalid",
                ]
            }
        )

        result = DataCleaner(
            CleaningConfig(
                timestamp_columns=("timestamp",),
            )
        ).clean(frame)

        assert pd.notna(
            result.frame.loc[
                0,
                "timestamp",
            ]
        )
        assert pd.isna(
            result.frame.loc[
                1,
                "timestamp",
            ]
        )

    def test_numeric_columns_are_coerced(self) -> None:
        config = CleaningConfig(
            numeric_columns=("capacity_mw",),
        )

        result = DataCleaner(config).clean(_sample_frame())

        assert result.frame["capacity_mw"].tolist() == [
            75.5,
            50.0,
        ]

        assert pd.api.types.is_numeric_dtype(result.frame["capacity_mw"].dtype)

        assert "normalized_numeric_columns" in result.changes

    def test_invalid_numeric_value_is_coerced_to_nan(self) -> None:
        frame = pd.DataFrame(
            {
                "value": [
                    "10.5",
                    "invalid",
                ]
            }
        )

        result = DataCleaner(
            CleaningConfig(
                numeric_columns=("value",),
            )
        ).clean(frame)

        assert (
            result.frame.loc[
                0,
                "value",
            ]
            == 10.5
        )
        assert pd.isna(
            result.frame.loc[
                1,
                "value",
            ]
        )

    def test_rows_are_sorted_stably(self) -> None:
        config = CleaningConfig(
            sort_by=("timestamp",),
            timestamp_columns=("timestamp",),
        )

        result = DataCleaner(config).clean(_sample_frame())

        assert result.frame["plant_id"].tolist() == [
            "plant-001",
            "plant-002",
        ]
        assert "sorted_rows" in result.changes

    def test_missing_sort_column_is_rejected(self) -> None:
        cleaner = DataCleaner(
            CleaningConfig(
                sort_by=("missing",),
            )
        )

        with pytest.raises(
            KeyError,
            match="missing columns",
        ):
            cleaner.clean(_sample_frame())

    def test_index_is_reset_by_default(self) -> None:
        result = DataCleaner().clean(_sample_frame())

        assert result.frame.index.tolist() == [
            0,
            1,
        ]
        assert "reset_index" in result.changes

    def test_index_can_be_preserved(self) -> None:
        result = DataCleaner(
            CleaningConfig(
                reset_index=False,
            )
        ).clean(_sample_frame())

        assert result.frame.index.tolist() == [
            10,
            5,
        ]
        assert "reset_index" not in result.changes

    def test_row_counts_are_preserved(self) -> None:
        result = DataCleaner().clean(_sample_frame())

        assert result.rows_before == 2
        assert result.rows_after == 2


class TestPublicCleaningHelpers:
    """Tests for public cleaning helper functions."""

    def test_clean_dataframe_helper(self) -> None:
        result = clean_dataframe(_sample_frame())

        assert isinstance(
            result,
            CleaningResult,
        )

    def test_clean_datasets_returns_sorted_keys(self) -> None:
        datasets = {
            "weather": pd.DataFrame(
                {
                    "value": [" 1 "],
                }
            ),
            "plants": pd.DataFrame(
                {
                    "value": [" 2 "],
                }
            ),
        }

        results = clean_datasets(datasets)

        assert list(results) == [
            "plants",
            "weather",
        ]

    def test_clean_datasets_supports_per_dataset_configs(
        self,
    ) -> None:
        datasets = {
            "plants": pd.DataFrame(
                {
                    "plant_id": [" plant-001 "],
                }
            )
        }

        configs = {"plants": CleaningConfig(uppercase_columns=("plant_id",))}

        results = clean_datasets(
            datasets,
            configs,
        )

        assert (
            results["plants"].frame.loc[
                0,
                "plant_id",
            ]
            == "PLANT-001"
        )

    def test_clean_datasets_rejects_invalid_mapping(
        self,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="datasets must be a mapping",
        ):
            clean_datasets([])  # type: ignore[arg-type]

    def test_clean_datasets_rejects_invalid_configs(
        self,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="configs must be a mapping or None",
        ):
            clean_datasets(
                {"plants": pd.DataFrame()},
                configs=[],  # type: ignore[arg-type]
            )

    def test_default_null_tokens_are_stable(self) -> None:
        assert DEFAULT_NULL_TOKENS == (
            "",
            "na",
            "n/a",
            "nan",
            "none",
            "null",
        )
