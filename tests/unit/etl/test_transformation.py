"""Unit tests for EOIP Phase 3 ETL transformation pipeline."""

from __future__ import annotations

import pandas as pd
import pytest

from eoip.etl.transformation import (
    DEFAULT_COPY_DEEP,
    ColumnExpression,
    DataTransformer,
    TransformationConfig,
    TransformationPipeline,
    TransformationResult,
    TransformationStep,
    apply_pipeline,
    transform_dataframe,
    transform_datasets,
)


def _sample_frame() -> pd.DataFrame:
    """Return a representative cleaned ETL DataFrame."""
    return pd.DataFrame(
        {
            "plant_id": [
                "PLANT-002",
                "PLANT-001",
                "PLANT-001",
            ],
            "timestamp": pd.to_datetime(
                [
                    "2026-01-01T00:15:00Z",
                    "2026-01-01T00:00:00Z",
                    "2026-01-01T00:00:00Z",
                ],
                utc=True,
            ),
            "capacity_mw": [
                75.0,
                50.0,
                50.0,
            ],
            "status": [
                "online",
                "online",
                "online",
            ],
        },
        index=[10, 5, 7],
    )


class TestColumnExpression:
    """Tests for ColumnExpression."""

    def test_valid_expression(self) -> None:
        expression = ColumnExpression(
            target_column="capacity_kw",
            function=lambda frame: frame["capacity_mw"] * 1000.0,
        )

        assert expression.target_column == "capacity_kw"
        assert callable(expression.function)

    def test_target_column_is_trimmed(self) -> None:
        expression = ColumnExpression(
            target_column="  capacity_kw  ",
            function=lambda frame: frame["capacity_mw"],
        )

        assert expression.target_column == "capacity_kw"

    def test_empty_target_column_is_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="target_column cannot be empty",
        ):
            ColumnExpression(
                target_column="   ",
                function=lambda frame: frame["capacity_mw"],
            )

    def test_non_callable_function_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="function must be callable",
        ):
            ColumnExpression(
                target_column="capacity_kw",
                function=1,  # type: ignore[arg-type]
            )


class TestTransformationConfig:
    """Tests for TransformationConfig."""

    def test_defaults_are_valid(self) -> None:
        config = TransformationConfig()

        assert config.select_columns == ()
        assert config.drop_columns == ()
        assert config.sort_by == ()
        assert config.drop_duplicate_keys == ()
        assert config.derived_columns == ()
        assert config.reset_index is True

    def test_string_sequences_are_normalized(self) -> None:
        config = TransformationConfig(
            select_columns=[
                " plant_id ",
                " capacity_mw ",
            ],
            sort_by=[" plant_id "],
            drop_duplicate_keys=[" plant_id "],
        )

        assert config.select_columns == (
            "plant_id",
            "capacity_mw",
        )
        assert config.sort_by == ("plant_id",)
        assert config.drop_duplicate_keys == ("plant_id",)

    def test_duplicate_sequence_values_are_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="cannot contain duplicate values",
        ):
            TransformationConfig(
                sort_by=(
                    "plant_id",
                    "plant_id",
                )
            )

    def test_select_drop_overlap_is_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="both selection and dropping",
        ):
            TransformationConfig(
                select_columns=("plant_id",),
                drop_columns=("plant_id",),
            )

    def test_invalid_rename_mapping_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="rename_columns must be a mapping",
        ):
            TransformationConfig(rename_columns=[])  # type: ignore[arg-type]

    def test_empty_rename_key_is_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="keys cannot be empty",
        ):
            TransformationConfig(
                rename_columns={
                    " ": "plant_id",
                }
            )

    def test_empty_rename_value_is_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="values cannot be empty",
        ):
            TransformationConfig(
                rename_columns={
                    "plant": " ",
                }
            )

    def test_invalid_derived_columns_container_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="derived_columns must be a tuple",
        ):
            TransformationConfig(derived_columns=[])  # type: ignore[arg-type]

    def test_invalid_derived_expression_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="ColumnExpression",
        ):
            TransformationConfig(derived_columns=("invalid",))  # type: ignore[arg-type]

    def test_reset_index_requires_bool(self) -> None:
        with pytest.raises(
            TypeError,
            match="reset_index must be a boolean",
        ):
            TransformationConfig(reset_index=1)  # type: ignore[arg-type]


class TestTransformationResult:
    """Tests for TransformationResult."""

    def test_valid_result(self) -> None:
        frame = pd.DataFrame(
            {
                "plant_id": ["PLANT-001"],
            }
        )

        result = TransformationResult(
            frame=frame,
            rows_before=1,
            rows_after=1,
            columns_before=("plant_id",),
            columns_after=("plant_id",),
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
            TransformationResult(
                frame=[],  # type: ignore[arg-type]
                rows_before=0,
                rows_after=0,
                columns_before=(),
                columns_after=(),
                changes=(),
            )

    def test_negative_row_count_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            TransformationResult(
                frame=pd.DataFrame(),
                rows_before=-1,
                rows_after=0,
                columns_before=(),
                columns_after=(),
                changes=(),
            )


class TestDataTransformer:
    """Tests for DataTransformer."""

    def test_default_transformer_exposes_config(self) -> None:
        transformer = DataTransformer()

        assert isinstance(
            transformer.config,
            TransformationConfig,
        )

    def test_invalid_config_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="TransformationConfig",
        ):
            DataTransformer("invalid")  # type: ignore[arg-type]

    def test_invalid_frame_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="pandas DataFrame",
        ):
            DataTransformer().transform([])  # type: ignore[arg-type]

    def test_source_frame_is_not_mutated(self) -> None:
        frame = _sample_frame()
        original = frame.copy(deep=True)

        DataTransformer().transform(frame)

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_select_columns_preserves_configured_order(self) -> None:
        config = TransformationConfig(
            select_columns=(
                "capacity_mw",
                "plant_id",
            )
        )

        result = DataTransformer(config).transform(_sample_frame())

        assert result.columns_after == (
            "capacity_mw",
            "plant_id",
        )
        assert "selected_columns" in result.changes

    def test_missing_selected_column_is_rejected(self) -> None:
        transformer = DataTransformer(
            TransformationConfig(
                select_columns=("missing",),
            )
        )

        with pytest.raises(
            KeyError,
            match="Cannot select missing columns",
        ):
            transformer.transform(_sample_frame())

    def test_drop_columns_removes_existing_columns(self) -> None:
        config = TransformationConfig(
            drop_columns=("status",),
        )

        result = DataTransformer(config).transform(_sample_frame())

        assert "status" not in result.frame.columns
        assert "dropped_columns" in result.changes

    def test_missing_drop_column_is_ignored(self) -> None:
        config = TransformationConfig(
            drop_columns=("missing",),
        )

        result = DataTransformer(config).transform(_sample_frame())

        assert "dropped_columns" not in result.changes

    def test_rename_columns_is_applied(self) -> None:
        config = TransformationConfig(
            rename_columns={
                "capacity_mw": "capacity_ac_mw",
            }
        )

        result = DataTransformer(config).transform(_sample_frame())

        assert "capacity_ac_mw" in result.frame.columns
        assert "capacity_mw" not in result.frame.columns
        assert "renamed_columns" in result.changes

    def test_duplicate_columns_after_rename_are_rejected(self) -> None:
        config = TransformationConfig(
            rename_columns={
                "capacity_mw": "plant_id",
            }
        )

        with pytest.raises(
            ValueError,
            match="duplicate column names",
        ):
            DataTransformer(config).transform(_sample_frame())

    def test_derived_column_is_created(self) -> None:
        config = TransformationConfig(
            derived_columns=(
                ColumnExpression(
                    target_column="capacity_kw",
                    function=lambda frame: (frame["capacity_mw"] * 1000.0),
                ),
            )
        )

        result = DataTransformer(config).transform(_sample_frame())

        assert result.frame["capacity_kw"].tolist() == [
            75000.0,
            50000.0,
            50000.0,
        ]
        assert "derived_columns" in result.changes

    def test_derived_column_can_replace_existing_column(self) -> None:
        config = TransformationConfig(
            derived_columns=(
                ColumnExpression(
                    target_column="capacity_mw",
                    function=lambda frame: (frame["capacity_mw"] * 2),
                ),
            )
        )

        result = DataTransformer(config).transform(_sample_frame())

        assert result.frame["capacity_mw"].tolist() == [
            150.0,
            100.0,
            100.0,
        ]

    def test_derived_function_must_return_series(self) -> None:
        config = TransformationConfig(
            derived_columns=(
                ColumnExpression(
                    target_column="bad",
                    function=lambda frame: 1,  # type: ignore[arg-type]
                ),
            )
        )

        with pytest.raises(
            TypeError,
            match="must return a pandas Series",
        ):
            DataTransformer(config).transform(_sample_frame())

    def test_derived_series_length_must_match(self) -> None:
        config = TransformationConfig(
            derived_columns=(
                ColumnExpression(
                    target_column="bad",
                    function=lambda frame: pd.Series([1]),
                ),
            )
        )

        with pytest.raises(
            ValueError,
            match="length must match",
        ):
            DataTransformer(config).transform(_sample_frame())

    def test_duplicates_are_removed_by_business_key(self) -> None:
        config = TransformationConfig(
            drop_duplicate_keys=(
                "plant_id",
                "timestamp",
            )
        )

        result = DataTransformer(config).transform(_sample_frame())

        assert result.rows_before == 3
        assert result.rows_after == 2
        assert "dropped_duplicates" in result.changes

    def test_missing_deduplication_key_is_rejected(self) -> None:
        config = TransformationConfig(
            drop_duplicate_keys=("missing",),
        )

        with pytest.raises(
            KeyError,
            match="missing columns",
        ):
            DataTransformer(config).transform(_sample_frame())

    def test_rows_are_sorted_stably(self) -> None:
        config = TransformationConfig(
            sort_by=(
                "timestamp",
                "plant_id",
            )
        )

        result = DataTransformer(config).transform(_sample_frame())

        assert result.frame["plant_id"].tolist() == [
            "PLANT-001",
            "PLANT-001",
            "PLANT-002",
        ]
        assert "sorted_rows" in result.changes

    def test_missing_sort_column_is_rejected(self) -> None:
        config = TransformationConfig(
            sort_by=("missing",),
        )

        with pytest.raises(
            KeyError,
            match="Cannot sort by missing columns",
        ):
            DataTransformer(config).transform(_sample_frame())

    def test_index_is_reset_by_default(self) -> None:
        result = DataTransformer().transform(_sample_frame())

        assert result.frame.index.tolist() == [
            0,
            1,
            2,
        ]
        assert "reset_index" in result.changes

    def test_index_can_be_preserved(self) -> None:
        result = DataTransformer(
            TransformationConfig(
                reset_index=False,
            )
        ).transform(_sample_frame())

        assert result.frame.index.tolist() == [
            10,
            5,
            7,
        ]
        assert "reset_index" not in result.changes


class TestTransformationStep:
    """Tests for TransformationStep."""

    def test_valid_step(self) -> None:
        step = TransformationStep(
            name="add_flag",
            function=lambda frame: frame.assign(flag=True),
        )

        assert step.name == "add_flag"
        assert callable(step.function)

    def test_name_is_trimmed(self) -> None:
        step = TransformationStep(
            name="  add_flag  ",
            function=lambda frame: frame,
        )

        assert step.name == "add_flag"

    def test_empty_name_is_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="name cannot be empty",
        ):
            TransformationStep(
                name="   ",
                function=lambda frame: frame,
            )

    def test_non_callable_step_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="function must be callable",
        ):
            TransformationStep(
                name="bad",
                function=1,  # type: ignore[arg-type]
            )


class TestTransformationPipeline:
    """Tests for TransformationPipeline."""

    def test_empty_pipeline_returns_copy(self) -> None:
        frame = _sample_frame()
        result = TransformationPipeline().run(frame)

        pd.testing.assert_frame_equal(
            result,
            frame,
        )
        assert result is not frame

    def test_steps_run_in_order(self) -> None:
        pipeline = TransformationPipeline(
            (
                TransformationStep(
                    name="double",
                    function=lambda frame: frame.assign(
                        capacity_mw=frame["capacity_mw"] * 2
                    ),
                ),
                TransformationStep(
                    name="add_one",
                    function=lambda frame: frame.assign(
                        capacity_mw=frame["capacity_mw"] + 1
                    ),
                ),
            )
        )

        result = pipeline.run(_sample_frame())

        assert result["capacity_mw"].tolist() == [
            151.0,
            101.0,
            101.0,
        ]

    def test_duplicate_step_names_are_rejected(self) -> None:
        step = TransformationStep(
            name="same",
            function=lambda frame: frame,
        )

        with pytest.raises(
            ValueError,
            match="step names must be unique",
        ):
            TransformationPipeline(
                (
                    step,
                    step,
                )
            )

    def test_invalid_step_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="TransformationStep",
        ):
            TransformationPipeline(("invalid",))  # type: ignore[arg-type]

    def test_step_must_return_dataframe(self) -> None:
        pipeline = TransformationPipeline(
            (
                TransformationStep(
                    name="bad",
                    function=lambda frame: frame["plant_id"],
                ),
            )
        )

        with pytest.raises(
            TypeError,
            match="must return a pandas DataFrame",
        ):
            pipeline.run(_sample_frame())

    def test_pipeline_does_not_mutate_source(self) -> None:
        frame = _sample_frame()
        original = frame.copy(deep=True)

        pipeline = TransformationPipeline(
            (
                TransformationStep(
                    name="add_flag",
                    function=lambda data: data.assign(flag=True),
                ),
            )
        )

        pipeline.run(frame)

        pd.testing.assert_frame_equal(
            frame,
            original,
        )


class TestPublicTransformationHelpers:
    """Tests for public transformation helper functions."""

    def test_transform_dataframe_helper(self) -> None:
        result = transform_dataframe(_sample_frame())

        assert isinstance(
            result,
            TransformationResult,
        )

    def test_transform_datasets_returns_sorted_keys(self) -> None:
        datasets = {
            "weather": pd.DataFrame(
                {
                    "value": [1],
                }
            ),
            "plants": pd.DataFrame(
                {
                    "value": [2],
                }
            ),
        }

        results = transform_datasets(datasets)

        assert list(results) == [
            "plants",
            "weather",
        ]

    def test_transform_datasets_supports_per_dataset_config(
        self,
    ) -> None:
        datasets = {
            "plants": pd.DataFrame(
                {
                    "plant_id": ["PLANT-001"],
                    "status": ["online"],
                }
            )
        }

        configs = {
            "plants": TransformationConfig(
                drop_columns=("status",),
            )
        }

        results = transform_datasets(
            datasets,
            configs,
        )

        assert results["plants"].columns_after == ("plant_id",)

    def test_transform_datasets_rejects_invalid_datasets(
        self,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="datasets must be a mapping",
        ):
            transform_datasets([])  # type: ignore[arg-type]

    def test_transform_datasets_rejects_invalid_configs(
        self,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="configs must be a mapping or None",
        ):
            transform_datasets(
                {"plants": pd.DataFrame()},
                configs=[],  # type: ignore[arg-type]
            )

    def test_apply_pipeline_helper(self) -> None:
        result = apply_pipeline(
            _sample_frame(),
            (
                TransformationStep(
                    name="add_flag",
                    function=lambda frame: frame.assign(flag=True),
                ),
            ),
        )

        assert result["flag"].tolist() == [
            True,
            True,
            True,
        ]

    def test_default_copy_deep_constant_is_true(self) -> None:
        assert DEFAULT_COPY_DEEP is True
