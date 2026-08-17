"""Unit tests for EOIP Phase 3 ETL data-lineage utilities."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from types import MappingProxyType

import pandas as pd
import pytest

from eoip.etl.lineage import (
    DEFAULT_LINEAGE_VERSION,
    DatasetLineageSummary,
    LineageAsset,
    LineageRecord,
    LineageRelationship,
    LineageStage,
    LineageTracker,
    build_lineage_asset,
    summarize_lineage,
)


def _recorded_at() -> datetime:
    """Return a deterministic UTC lineage timestamp."""
    return datetime(
        2026,
        8,
        13,
        10,
        0,
        0,
        tzinfo=UTC,
    )


def _source_asset() -> LineageAsset:
    """Return a representative source lineage asset."""
    return LineageAsset(
        dataset_name="plants_raw",
        location="runs/RUN-001/master/plants.parquet",
        format="parquet",
        row_count=10,
        checksum="abc123",
        metadata={
            "layer": "raw",
        },
    )


def _target_asset() -> LineageAsset:
    """Return a representative target lineage asset."""
    return LineageAsset(
        dataset_name="plants",
        location="staging/plants.parquet",
        format="parquet",
        row_count=9,
        checksum="def456",
        metadata={
            "layer": "staging",
        },
    )


def _record(
    *,
    run_id: str = "RUN-001",
    stage: LineageStage = LineageStage.CLEANING,
    relationship: LineageRelationship = LineageRelationship.CLEANED_FROM,
    source: LineageAsset | None = None,
    target: LineageAsset | None = None,
) -> LineageRecord:
    """Return a valid lineage record."""
    return LineageRecord(
        run_id=run_id,
        stage=stage,
        relationship=relationship,
        source=source or _source_asset(),
        target=target or _target_asset(),
        recorded_at=_recorded_at(),
        operation="clean",
        metadata={
            "rows_removed": 1,
        },
    )


class TestLineageStage:
    """Tests for LineageStage."""

    def test_values_are_stable(self) -> None:
        assert LineageStage.INGESTION.value == "ingestion"
        assert LineageStage.VALIDATION.value == "validation"
        assert LineageStage.CLEANING.value == "cleaning"
        assert LineageStage.TRANSFORMATION.value == "transformation"
        assert LineageStage.INCREMENTAL.value == "incremental"
        assert LineageStage.LOADING.value == "loading"
        assert LineageStage.QUALITY.value == "quality"


class TestLineageRelationship:
    """Tests for LineageRelationship."""

    def test_values_are_stable(self) -> None:
        assert LineageRelationship.DERIVED_FROM.value == "derived_from"
        assert LineageRelationship.VALIDATED_FROM.value == "validated_from"
        assert LineageRelationship.CLEANED_FROM.value == "cleaned_from"
        assert LineageRelationship.TRANSFORMED_FROM.value == "transformed_from"
        assert LineageRelationship.FILTERED_FROM.value == "filtered_from"
        assert LineageRelationship.LOADED_FROM.value == "loaded_from"


class TestLineageAsset:
    """Tests for LineageAsset."""

    def test_valid_asset(self) -> None:
        asset = _source_asset()

        assert asset.dataset_name == "plants_raw"
        assert asset.location == "runs/RUN-001/master/plants.parquet"
        assert asset.format == "parquet"
        assert asset.row_count == 10
        assert asset.checksum == "abc123"

    def test_dataset_name_is_trimmed(self) -> None:
        asset = LineageAsset(
            dataset_name="  plants  ",
        )

        assert asset.dataset_name == "plants"

    def test_optional_strings_are_trimmed(self) -> None:
        asset = LineageAsset(
            dataset_name="plants",
            location="  path/file.parquet  ",
            format="  parquet  ",
            checksum="  abc123  ",
        )

        assert asset.location == "path/file.parquet"
        assert asset.format == "parquet"
        assert asset.checksum == "abc123"

    def test_empty_dataset_name_is_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="dataset_name cannot be empty",
        ):
            LineageAsset(
                dataset_name="   ",
            )

    def test_negative_row_count_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            LineageAsset(
                dataset_name="plants",
                row_count=-1,
            )

    def test_boolean_row_count_is_rejected(self) -> None:
        with pytest.raises(TypeError):
            LineageAsset(
                dataset_name="plants",
                row_count=True,  # type: ignore[arg-type]
            )

    def test_metadata_is_normalized_and_immutable(self) -> None:
        asset = LineageAsset(
            dataset_name="plants",
            metadata={
                " owner ": "energy-team",
            },
        )

        assert isinstance(
            asset.metadata,
            MappingProxyType,
        )
        assert asset.metadata == {
            "owner": "energy-team",
        }

        with pytest.raises(TypeError):
            asset.metadata["owner"] = "changed"  # type: ignore[index]

    def test_invalid_metadata_key_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="metadata keys must be strings",
        ):
            LineageAsset(
                dataset_name="plants",
                metadata={
                    1: "invalid",  # type: ignore[dict-item]
                },
            )

    def test_empty_metadata_key_is_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="metadata keys cannot be empty",
        ):
            LineageAsset(
                dataset_name="plants",
                metadata={
                    " ": "invalid",
                },
            )

    def test_asset_is_frozen(self) -> None:
        asset = _source_asset()

        with pytest.raises(FrozenInstanceError):
            asset.dataset_name = "changed"  # type: ignore[misc]

    def test_to_dict(self) -> None:
        asset = _source_asset()

        result = asset.to_dict()

        assert result == {
            "dataset_name": "plants_raw",
            "location": "runs/RUN-001/master/plants.parquet",
            "format": "parquet",
            "row_count": 10,
            "checksum": "abc123",
            "metadata": {
                "layer": "raw",
            },
        }


class TestLineageRecord:
    """Tests for LineageRecord."""

    def test_valid_record(self) -> None:
        record = _record()

        assert record.run_id == "RUN-001"
        assert record.stage is LineageStage.CLEANING
        assert record.relationship is LineageRelationship.CLEANED_FROM
        assert record.operation == "clean"
        assert record.version == DEFAULT_LINEAGE_VERSION

    def test_run_id_and_version_are_trimmed(self) -> None:
        record = LineageRecord(
            run_id="  RUN-001  ",
            stage=LineageStage.CLEANING,
            relationship=LineageRelationship.CLEANED_FROM,
            source=_source_asset(),
            target=_target_asset(),
            recorded_at=_recorded_at(),
            version="  1.0  ",
        )

        assert record.run_id == "RUN-001"
        assert record.version == "1.0"

    def test_invalid_stage_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="stage must be a LineageStage",
        ):
            LineageRecord(
                run_id="RUN-001",
                stage="cleaning",  # type: ignore[arg-type]
                relationship=LineageRelationship.CLEANED_FROM,
                source=_source_asset(),
                target=_target_asset(),
                recorded_at=_recorded_at(),
            )

    def test_invalid_relationship_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="relationship must be a LineageRelationship",
        ):
            LineageRecord(
                run_id="RUN-001",
                stage=LineageStage.CLEANING,
                relationship="cleaned_from",  # type: ignore[arg-type]
                source=_source_asset(),
                target=_target_asset(),
                recorded_at=_recorded_at(),
            )

    def test_invalid_source_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="source must be a LineageAsset",
        ):
            LineageRecord(
                run_id="RUN-001",
                stage=LineageStage.CLEANING,
                relationship=LineageRelationship.CLEANED_FROM,
                source="plants",  # type: ignore[arg-type]
                target=_target_asset(),
                recorded_at=_recorded_at(),
            )

    def test_invalid_target_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="target must be a LineageAsset",
        ):
            LineageRecord(
                run_id="RUN-001",
                stage=LineageStage.CLEANING,
                relationship=LineageRelationship.CLEANED_FROM,
                source=_source_asset(),
                target="plants",  # type: ignore[arg-type]
                recorded_at=_recorded_at(),
            )

    def test_naive_recorded_at_is_normalized_to_utc(self) -> None:
        record = LineageRecord(
            run_id="RUN-001",
            stage=LineageStage.CLEANING,
            relationship=LineageRelationship.CLEANED_FROM,
            source=_source_asset(),
            target=_target_asset(),
            recorded_at=datetime(
                2026,
                8,
                13,
                10,
                0,
                0,
            ),
        )

        assert record.recorded_at.tzinfo is UTC

    def test_operation_is_trimmed(self) -> None:
        record = LineageRecord(
            run_id="RUN-001",
            stage=LineageStage.CLEANING,
            relationship=LineageRelationship.CLEANED_FROM,
            source=_source_asset(),
            target=_target_asset(),
            recorded_at=_recorded_at(),
            operation="  clean  ",
        )

        assert record.operation == "clean"

    def test_metadata_is_immutable(self) -> None:
        record = _record()

        assert isinstance(
            record.metadata,
            MappingProxyType,
        )

        with pytest.raises(TypeError):
            record.metadata["x"] = 1  # type: ignore[index]

    def test_record_is_frozen(self) -> None:
        record = _record()

        with pytest.raises(FrozenInstanceError):
            record.run_id = "RUN-002"  # type: ignore[misc]

    def test_to_dict(self) -> None:
        record = _record()

        result = record.to_dict()

        assert result["run_id"] == "RUN-001"
        assert result["stage"] == "cleaning"
        assert result["relationship"] == "cleaned_from"
        assert result["source"]["dataset_name"] == "plants_raw"
        assert result["target"]["dataset_name"] == "plants"
        assert result["recorded_at"] == _recorded_at().isoformat()
        assert result["operation"] == "clean"
        assert result["metadata"] == {
            "rows_removed": 1,
        }
        assert result["version"] == "1.0"


class TestDatasetLineageSummary:
    """Tests for DatasetLineageSummary."""

    def test_valid_summary(self) -> None:
        summary = DatasetLineageSummary(
            dataset_name="plants",
            record_count=2,
            source_datasets=("plants_raw",),
            target_datasets=(
                "plants",
                "plants_clean",
            ),
            stages=(
                LineageStage.CLEANING,
                LineageStage.TRANSFORMATION,
            ),
        )

        assert summary.dataset_name == "plants"
        assert summary.record_count == 2

    def test_duplicate_source_datasets_are_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="cannot contain duplicate values",
        ):
            DatasetLineageSummary(
                dataset_name="plants",
                record_count=1,
                source_datasets=(
                    "plants",
                    "plants",
                ),
                target_datasets=(),
                stages=(),
            )

    def test_stages_requires_tuple(self) -> None:
        with pytest.raises(
            TypeError,
            match="stages must be a tuple",
        ):
            DatasetLineageSummary(
                dataset_name="plants",
                record_count=1,
                source_datasets=(),
                target_datasets=(),
                stages=[LineageStage.CLEANING],  # type: ignore[arg-type]
            )

    def test_stages_require_lineage_stage_values(self) -> None:
        with pytest.raises(
            TypeError,
            match="LineageStage values",
        ):
            DatasetLineageSummary(
                dataset_name="plants",
                record_count=1,
                source_datasets=(),
                target_datasets=(),
                stages=("cleaning",),  # type: ignore[arg-type]
            )

    def test_to_dict(self) -> None:
        summary = DatasetLineageSummary(
            dataset_name="plants",
            record_count=1,
            source_datasets=("plants_raw",),
            target_datasets=("plants",),
            stages=(LineageStage.CLEANING,),
        )

        result = summary.to_dict()

        assert result == {
            "dataset_name": "plants",
            "record_count": 1,
            "source_datasets": ["plants_raw"],
            "target_datasets": ["plants"],
            "stages": ["cleaning"],
        }


class TestLineageTracker:
    """Tests for LineageTracker."""

    def test_tracker_properties(self) -> None:
        tracker = LineageTracker("  RUN-001  ")

        assert tracker.run_id == "RUN-001"
        assert tracker.records == ()

    def test_record_appends_lineage_record(self) -> None:
        tracker = LineageTracker("RUN-001")

        record = tracker.record(
            stage=LineageStage.CLEANING,
            relationship=LineageRelationship.CLEANED_FROM,
            source=_source_asset(),
            target=_target_asset(),
            recorded_at=_recorded_at(),
        )

        assert tracker.records == (record,)

    def test_derived_helper(self) -> None:
        tracker = LineageTracker("RUN-001")

        record = tracker.derived(
            stage=LineageStage.QUALITY,
            source=_source_asset(),
            target=_target_asset(),
            recorded_at=_recorded_at(),
            operation="quality_check",
        )

        assert record.relationship is LineageRelationship.DERIVED_FROM
        assert record.stage is LineageStage.QUALITY
        assert record.operation == "quality_check"

    def test_validated_helper(self) -> None:
        tracker = LineageTracker("RUN-001")

        record = tracker.validated(
            source=_source_asset(),
            target=_target_asset(),
            recorded_at=_recorded_at(),
        )

        assert record.stage is LineageStage.VALIDATION
        assert record.relationship is LineageRelationship.VALIDATED_FROM
        assert record.operation == "validate"

    def test_cleaned_helper(self) -> None:
        tracker = LineageTracker("RUN-001")

        record = tracker.cleaned(
            source=_source_asset(),
            target=_target_asset(),
            recorded_at=_recorded_at(),
        )

        assert record.stage is LineageStage.CLEANING
        assert record.relationship is LineageRelationship.CLEANED_FROM
        assert record.operation == "clean"

    def test_transformed_helper(self) -> None:
        tracker = LineageTracker("RUN-001")

        record = tracker.transformed(
            source=_source_asset(),
            target=_target_asset(),
            recorded_at=_recorded_at(),
        )

        assert record.stage is LineageStage.TRANSFORMATION
        assert record.relationship is LineageRelationship.TRANSFORMED_FROM
        assert record.operation == "transform"

    def test_incremental_helper(self) -> None:
        tracker = LineageTracker("RUN-001")

        record = tracker.incremental(
            source=_source_asset(),
            target=_target_asset(),
            recorded_at=_recorded_at(),
        )

        assert record.stage is LineageStage.INCREMENTAL
        assert record.relationship is LineageRelationship.FILTERED_FROM
        assert record.operation == "incremental_filter"

    def test_loaded_helper(self) -> None:
        tracker = LineageTracker("RUN-001")

        record = tracker.loaded(
            source=_source_asset(),
            target=_target_asset(),
            recorded_at=_recorded_at(),
        )

        assert record.stage is LineageStage.LOADING
        assert record.relationship is LineageRelationship.LOADED_FROM
        assert record.operation == "load"

    def test_records_for_dataset_matches_source_or_target(
        self,
    ) -> None:
        tracker = LineageTracker("RUN-001")

        raw = _source_asset()
        cleaned = _target_asset()
        transformed = LineageAsset(
            dataset_name="plants_analytics",
            row_count=9,
        )

        tracker.cleaned(
            source=raw,
            target=cleaned,
            recorded_at=_recorded_at(),
        )
        tracker.transformed(
            source=cleaned,
            target=transformed,
            recorded_at=_recorded_at(),
        )

        records = tracker.records_for_dataset("plants")

        assert len(records) == 2

    def test_records_for_unknown_dataset_returns_empty_tuple(
        self,
    ) -> None:
        tracker = LineageTracker("RUN-001")

        tracker.cleaned(
            source=_source_asset(),
            target=_target_asset(),
            recorded_at=_recorded_at(),
        )

        assert tracker.records_for_dataset("weather") == ()

    def test_summarize_dataset(self) -> None:
        tracker = LineageTracker("RUN-001")

        raw = _source_asset()
        cleaned = _target_asset()
        transformed = LineageAsset(
            dataset_name="plants_analytics",
            row_count=9,
        )

        tracker.cleaned(
            source=raw,
            target=cleaned,
            recorded_at=_recorded_at(),
        )
        tracker.transformed(
            source=cleaned,
            target=transformed,
            recorded_at=_recorded_at(),
        )

        summary = tracker.summarize_dataset("plants")

        assert summary.dataset_name == "plants"
        assert summary.record_count == 2
        assert summary.source_datasets == (
            "plants",
            "plants_raw",
        )
        assert summary.target_datasets == (
            "plants",
            "plants_analytics",
        )
        assert summary.stages == (
            LineageStage.CLEANING,
            LineageStage.TRANSFORMATION,
        )

    def test_empty_to_frame_has_expected_columns(self) -> None:
        frame = LineageTracker("RUN-001").to_frame()

        assert frame.empty
        assert list(frame.columns) == [
            "run_id",
            "stage",
            "relationship",
            "source_dataset",
            "source_location",
            "source_format",
            "source_row_count",
            "source_checksum",
            "target_dataset",
            "target_location",
            "target_format",
            "target_row_count",
            "target_checksum",
            "recorded_at",
            "operation",
            "metadata",
            "version",
        ]

    def test_to_frame_exports_records(self) -> None:
        tracker = LineageTracker("RUN-001")

        tracker.cleaned(
            source=_source_asset(),
            target=_target_asset(),
            recorded_at=_recorded_at(),
            metadata={
                "reason": "standardization",
            },
        )

        frame = tracker.to_frame()

        assert len(frame) == 1
        assert (
            frame.loc[
                0,
                "run_id",
            ]
            == "RUN-001"
        )
        assert (
            frame.loc[
                0,
                "stage",
            ]
            == "cleaning"
        )
        assert (
            frame.loc[
                0,
                "relationship",
            ]
            == "cleaned_from"
        )
        assert (
            frame.loc[
                0,
                "source_dataset",
            ]
            == "plants_raw"
        )
        assert (
            frame.loc[
                0,
                "target_dataset",
            ]
            == "plants"
        )
        assert frame.loc[
            0,
            "metadata",
        ] == {
            "reason": "standardization",
        }


class TestBuildLineageAsset:
    """Tests for build_lineage_asset."""

    def test_builds_asset_from_frame(self) -> None:
        frame = pd.DataFrame(
            {
                "plant_id": [
                    "PLANT-001",
                    "PLANT-002",
                ],
            }
        )

        asset = build_lineage_asset(
            "plants",
            frame=frame,
            location="plants.parquet",
            format="parquet",
            checksum="abc",
            metadata={
                "layer": "clean",
            },
        )

        assert asset.dataset_name == "plants"
        assert asset.row_count == 2
        assert asset.location == "plants.parquet"
        assert asset.format == "parquet"
        assert asset.checksum == "abc"

    def test_builds_asset_without_frame(self) -> None:
        asset = build_lineage_asset("plants")

        assert asset.row_count is None

    def test_invalid_frame_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="pandas DataFrame or None",
        ):
            build_lineage_asset(
                "plants",
                frame=[],  # type: ignore[arg-type]
            )


class TestSummarizeLineage:
    """Tests for summarize_lineage."""

    def test_summarizes_relevant_records(self) -> None:
        raw = _source_asset()
        plants = _target_asset()
        analytics = LineageAsset(
            dataset_name="plants_analytics",
        )

        records = (
            _record(
                stage=LineageStage.CLEANING,
                relationship=(LineageRelationship.CLEANED_FROM),
                source=raw,
                target=plants,
            ),
            _record(
                stage=LineageStage.TRANSFORMATION,
                relationship=(LineageRelationship.TRANSFORMED_FROM),
                source=plants,
                target=analytics,
            ),
        )

        summary = summarize_lineage(
            records,
            "plants",
        )

        assert summary.record_count == 2
        assert summary.source_datasets == (
            "plants",
            "plants_raw",
        )
        assert summary.target_datasets == (
            "plants",
            "plants_analytics",
        )
        assert summary.stages == (
            LineageStage.CLEANING,
            LineageStage.TRANSFORMATION,
        )

    def test_unknown_dataset_returns_empty_summary(self) -> None:
        summary = summarize_lineage(
            (_record(),),
            "weather",
        )

        assert summary.dataset_name == "weather"
        assert summary.record_count == 0
        assert summary.source_datasets == ()
        assert summary.target_datasets == ()
        assert summary.stages == ()

    def test_invalid_record_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="LineageRecord objects",
        ):
            summarize_lineage(
                ("invalid",),  # type: ignore[arg-type]
                "plants",
            )


class TestLineageConstants:
    """Tests for stable lineage constants."""

    def test_default_lineage_version(self) -> None:
        assert DEFAULT_LINEAGE_VERSION == "1.0"
