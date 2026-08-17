"""Unit tests for EOIP Phase 3 ETL audit logging."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from types import MappingProxyType

import pandas as pd
import pytest

from eoip.etl.audit import (
    DEFAULT_AUDIT_VERSION,
    DEFAULT_PIPELINE_NAME,
    AuditEvent,
    AuditLogger,
    AuditRunSummary,
    AuditStage,
    AuditStatus,
    summarize_audit_events,
)


def _started_at() -> datetime:
    """Return a deterministic UTC start time."""
    return datetime(2026, 8, 12, 10, 0, 0, tzinfo=UTC)


def _completed_at() -> datetime:
    """Return a deterministic UTC completion time."""
    return datetime(2026, 8, 12, 10, 0, 5, tzinfo=UTC)


def _successful_event(
    *,
    run_id: str = "RUN-001",
    pipeline_name: str = DEFAULT_PIPELINE_NAME,
    stage: str = "ingestion",
    input_rows: int | None = 100,
    output_rows: int | None = 95,
    rejected_rows: int | None = 5,
) -> AuditEvent:
    """Return a valid successful audit event."""
    return AuditEvent(
        run_id=run_id,
        pipeline_name=pipeline_name,
        stage=stage,
        status=AuditStatus.SUCCEEDED,
        started_at=_started_at(),
        completed_at=_completed_at(),
        input_rows=input_rows,
        output_rows=output_rows,
        rejected_rows=rejected_rows,
    )


class TestAuditStatus:
    """Tests for AuditStatus."""

    def test_values_are_stable(self) -> None:
        assert AuditStatus.STARTED.value == "started"
        assert AuditStatus.SUCCEEDED.value == "succeeded"
        assert AuditStatus.FAILED.value == "failed"
        assert AuditStatus.SKIPPED.value == "skipped"


class TestAuditStage:
    """Tests for AuditStage."""

    def test_values_are_stable(self) -> None:
        assert AuditStage.PIPELINE.value == "pipeline"
        assert AuditStage.INGESTION.value == "ingestion"
        assert AuditStage.VALIDATION.value == "validation"
        assert AuditStage.CLEANING.value == "cleaning"
        assert AuditStage.TRANSFORMATION.value == "transformation"
        assert AuditStage.INCREMENTAL.value == "incremental"
        assert AuditStage.LOADING.value == "loading"
        assert AuditStage.QUALITY.value == "quality"
        assert AuditStage.LINEAGE.value == "lineage"


class TestAuditEvent:
    """Tests for AuditEvent."""

    def test_valid_successful_event(self) -> None:
        event = _successful_event()

        assert event.run_id == "RUN-001"
        assert event.pipeline_name == DEFAULT_PIPELINE_NAME
        assert event.stage == "ingestion"
        assert event.status is AuditStatus.SUCCEEDED
        assert event.input_rows == 100
        assert event.output_rows == 95
        assert event.rejected_rows == 5
        assert event.version == DEFAULT_AUDIT_VERSION

    def test_required_strings_are_trimmed(self) -> None:
        event = AuditEvent(
            run_id="  RUN-001  ",
            pipeline_name="  pipeline  ",
            stage="  ingestion  ",
            status=AuditStatus.SUCCEEDED,
            started_at=_started_at(),
            completed_at=_completed_at(),
            version="  1.0  ",
        )

        assert event.run_id == "RUN-001"
        assert event.pipeline_name == "pipeline"
        assert event.stage == "ingestion"
        assert event.version == "1.0"

    @pytest.mark.parametrize(
        "field_name",
        [
            "run_id",
            "pipeline_name",
            "stage",
            "version",
        ],
    )
    def test_required_strings_reject_empty_values(
        self,
        field_name: str,
    ) -> None:
        values = {
            "run_id": "RUN-001",
            "pipeline_name": "pipeline",
            "stage": "ingestion",
            "version": "1.0",
        }
        values[field_name] = "   "

        with pytest.raises(ValueError):
            AuditEvent(
                run_id=values["run_id"],
                pipeline_name=values["pipeline_name"],
                stage=values["stage"],
                status=AuditStatus.SUCCEEDED,
                started_at=_started_at(),
                completed_at=_completed_at(),
                version=values["version"],
            )

    def test_status_requires_enum(self) -> None:
        with pytest.raises(TypeError):
            AuditEvent(
                run_id="RUN-001",
                pipeline_name="pipeline",
                stage="ingestion",
                status="succeeded",  # type: ignore[arg-type]
                started_at=_started_at(),
                completed_at=_completed_at(),
            )

    def test_naive_datetime_is_normalized_to_utc(self) -> None:
        event = AuditEvent(
            run_id="RUN-001",
            pipeline_name="pipeline",
            stage="ingestion",
            status=AuditStatus.SUCCEEDED,
            started_at=datetime(2026, 8, 12, 10, 0, 0),
            completed_at=datetime(2026, 8, 12, 10, 0, 5),
        )

        assert event.started_at.tzinfo is UTC
        assert event.completed_at is not None
        assert event.completed_at.tzinfo is UTC

    def test_completed_at_cannot_precede_started_at(self) -> None:
        with pytest.raises(ValueError):
            AuditEvent(
                run_id="RUN-001",
                pipeline_name="pipeline",
                stage="ingestion",
                status=AuditStatus.SUCCEEDED,
                started_at=_completed_at(),
                completed_at=_started_at(),
            )

    def test_started_event_cannot_have_completed_at(self) -> None:
        with pytest.raises(ValueError):
            AuditEvent(
                run_id="RUN-001",
                pipeline_name="pipeline",
                stage="ingestion",
                status=AuditStatus.STARTED,
                started_at=_started_at(),
                completed_at=_completed_at(),
            )

    @pytest.mark.parametrize(
        "status",
        [
            AuditStatus.SUCCEEDED,
            AuditStatus.FAILED,
            AuditStatus.SKIPPED,
        ],
    )
    def test_completed_status_requires_completed_at(
        self,
        status: AuditStatus,
    ) -> None:
        kwargs = {}

        if status is AuditStatus.FAILED:
            kwargs["error_message"] = "failure"

        with pytest.raises(ValueError):
            AuditEvent(
                run_id="RUN-001",
                pipeline_name="pipeline",
                stage="ingestion",
                status=status,
                started_at=_started_at(),
                **kwargs,
            )

    def test_failed_event_requires_error_message(self) -> None:
        with pytest.raises(ValueError):
            AuditEvent(
                run_id="RUN-001",
                pipeline_name="pipeline",
                stage="ingestion",
                status=AuditStatus.FAILED,
                started_at=_started_at(),
                completed_at=_completed_at(),
            )

    @pytest.mark.parametrize(
        "field_name",
        [
            "input_rows",
            "output_rows",
            "rejected_rows",
        ],
    )
    def test_row_counts_reject_negative_values(
        self,
        field_name: str,
    ) -> None:
        values = {
            "input_rows": 1,
            "output_rows": 1,
            "rejected_rows": 0,
        }
        values[field_name] = -1

        with pytest.raises(ValueError):
            AuditEvent(
                run_id="RUN-001",
                pipeline_name="pipeline",
                stage="ingestion",
                status=AuditStatus.SUCCEEDED,
                started_at=_started_at(),
                completed_at=_completed_at(),
                **values,
            )

    @pytest.mark.parametrize(
        "field_name",
        [
            "input_rows",
            "output_rows",
            "rejected_rows",
        ],
    )
    def test_row_counts_reject_boolean_values(
        self,
        field_name: str,
    ) -> None:
        values = {
            "input_rows": 1,
            "output_rows": 1,
            "rejected_rows": 0,
        }
        values[field_name] = True

        with pytest.raises(TypeError):
            AuditEvent(
                run_id="RUN-001",
                pipeline_name="pipeline",
                stage="ingestion",
                status=AuditStatus.SUCCEEDED,
                started_at=_started_at(),
                completed_at=_completed_at(),
                **values,
            )

    def test_optional_strings_are_trimmed(self) -> None:
        event = AuditEvent(
            run_id="RUN-001",
            pipeline_name="pipeline",
            stage="validation",
            status=AuditStatus.FAILED,
            started_at=_started_at(),
            completed_at=_completed_at(),
            dataset_name="  plants  ",
            message="  validation failed  ",
            error_type="  ValueError  ",
            error_message="  bad data  ",
        )

        assert event.dataset_name == "plants"
        assert event.message == "validation failed"
        assert event.error_type == "ValueError"
        assert event.error_message == "bad data"

    def test_metadata_is_immutable(self) -> None:
        event = AuditEvent(
            run_id="RUN-001",
            pipeline_name="pipeline",
            stage="ingestion",
            status=AuditStatus.SUCCEEDED,
            started_at=_started_at(),
            completed_at=_completed_at(),
            metadata={
                "source": "synthetic",
                "batch": 1,
            },
        )

        assert isinstance(event.metadata, MappingProxyType)
        assert event.metadata["source"] == "synthetic"

        with pytest.raises(TypeError):
            event.metadata["source"] = "changed"  # type: ignore[index]

    def test_event_is_frozen(self) -> None:
        event = _successful_event()

        with pytest.raises(FrozenInstanceError):
            event.run_id = "RUN-002"  # type: ignore[misc]

    def test_duration_seconds(self) -> None:
        event = _successful_event()

        assert event.duration_seconds == 5.0

    def test_started_duration_is_none(self) -> None:
        event = AuditEvent(
            run_id="RUN-001",
            pipeline_name="pipeline",
            stage="ingestion",
            status=AuditStatus.STARTED,
            started_at=_started_at(),
        )

        assert event.duration_seconds is None

    def test_to_dict_is_serialization_ready(self) -> None:
        event = AuditEvent(
            run_id="RUN-001",
            pipeline_name="pipeline",
            stage="validation",
            status=AuditStatus.SUCCEEDED,
            started_at=_started_at(),
            completed_at=_completed_at(),
            input_rows=100,
            output_rows=98,
            rejected_rows=2,
            dataset_name="plants",
            message="validated",
            metadata={"owner": "energy-team"},
        )

        result = event.to_dict()

        assert result["run_id"] == "RUN-001"
        assert result["status"] == "succeeded"
        assert result["started_at"] == _started_at().isoformat()
        assert result["completed_at"] == _completed_at().isoformat()
        assert result["duration_seconds"] == 5.0
        assert result["metadata"] == {"owner": "energy-team"}


class TestAuditRunSummary:
    """Tests for AuditRunSummary."""

    def test_valid_summary(self) -> None:
        summary = AuditRunSummary(
            run_id="RUN-001",
            pipeline_name="pipeline",
            event_count=3,
            succeeded_count=2,
            failed_count=0,
            skipped_count=1,
            started_count=0,
            total_input_rows=100,
            total_output_rows=90,
            total_rejected_rows=10,
            first_started_at=_started_at(),
            last_completed_at=_completed_at(),
        )

        assert summary.passed is True
        assert summary.event_count == 3
        assert summary.total_output_rows == 90

    def test_failed_summary_does_not_pass(self) -> None:
        summary = AuditRunSummary(
            run_id="RUN-001",
            pipeline_name="pipeline",
            event_count=1,
            succeeded_count=0,
            failed_count=1,
            skipped_count=0,
            started_count=0,
            total_input_rows=10,
            total_output_rows=0,
            total_rejected_rows=10,
            first_started_at=_started_at(),
            last_completed_at=_completed_at(),
        )

        assert summary.passed is False

    def test_summary_to_dict(self) -> None:
        summary = AuditRunSummary(
            run_id="RUN-001",
            pipeline_name="pipeline",
            event_count=1,
            succeeded_count=1,
            failed_count=0,
            skipped_count=0,
            started_count=0,
            total_input_rows=10,
            total_output_rows=10,
            total_rejected_rows=0,
            first_started_at=_started_at(),
            last_completed_at=_completed_at(),
        )

        result = summary.to_dict()

        assert result["run_id"] == "RUN-001"
        assert result["passed"] is True
        assert result["first_started_at"] == _started_at().isoformat()
        assert result["last_completed_at"] == _completed_at().isoformat()


class TestAuditLogger:
    """Tests for AuditLogger."""

    def test_logger_properties_are_normalized(self) -> None:
        logger = AuditLogger(
            "  RUN-001  ",
            pipeline_name="  pipeline  ",
        )

        assert logger.run_id == "RUN-001"
        assert logger.pipeline_name == "pipeline"
        assert logger.events == ()

    def test_record_appends_event(self) -> None:
        logger = AuditLogger("RUN-001")

        event = logger.record(
            stage=AuditStage.INGESTION,
            status=AuditStatus.SUCCEEDED,
            started_at=_started_at(),
            completed_at=_completed_at(),
        )

        assert logger.events == (event,)
        assert event.stage == "ingestion"

    def test_started_records_started_event(self) -> None:
        logger = AuditLogger("RUN-001")

        event = logger.started(
            stage=AuditStage.INGESTION,
            started_at=_started_at(),
            dataset_name="plants",
            input_rows=100,
        )

        assert event.status is AuditStatus.STARTED
        assert event.completed_at is None
        assert event.dataset_name == "plants"

    def test_succeeded_records_successful_event(self) -> None:
        logger = AuditLogger("RUN-001")

        event = logger.succeeded(
            stage=AuditStage.CLEANING,
            started_at=_started_at(),
            completed_at=_completed_at(),
            input_rows=100,
            output_rows=95,
            rejected_rows=5,
        )

        assert event.status is AuditStatus.SUCCEEDED
        assert event.output_rows == 95
        assert event.rejected_rows == 5

    def test_failed_extracts_exception_details(self) -> None:
        logger = AuditLogger("RUN-001")

        error = ValueError("invalid dataset")

        event = logger.failed(
            stage=AuditStage.VALIDATION,
            started_at=_started_at(),
            completed_at=_completed_at(),
            error=error,
        )

        assert event.status is AuditStatus.FAILED
        assert event.error_type == "ValueError"
        assert event.error_message == "invalid dataset"

    def test_failed_accepts_explicit_error_message(self) -> None:
        logger = AuditLogger("RUN-001")

        event = logger.failed(
            stage=AuditStage.LOADING,
            started_at=_started_at(),
            completed_at=_completed_at(),
            error_message="database unavailable",
        )

        assert event.status is AuditStatus.FAILED
        assert event.error_type is None
        assert event.error_message == "database unavailable"

    def test_failed_requires_error_information(self) -> None:
        logger = AuditLogger("RUN-001")

        with pytest.raises(ValueError):
            logger.failed(
                stage=AuditStage.LOADING,
                started_at=_started_at(),
                completed_at=_completed_at(),
            )

    def test_skipped_uses_zero_output_and_rejected_rows(self) -> None:
        logger = AuditLogger("RUN-001")

        event = logger.skipped(
            stage=AuditStage.INCREMENTAL,
            started_at=_started_at(),
            completed_at=_started_at(),
            input_rows=100,
        )

        assert event.status is AuditStatus.SKIPPED
        assert event.output_rows == 0
        assert event.rejected_rows == 0

    def test_events_property_returns_tuple(self) -> None:
        logger = AuditLogger("RUN-001")

        logger.started(
            stage=AuditStage.PIPELINE,
            started_at=_started_at(),
        )

        assert isinstance(logger.events, tuple)
        assert len(logger.events) == 1

    def test_summarize(self) -> None:
        logger = AuditLogger("RUN-001")

        logger.succeeded(
            stage=AuditStage.INGESTION,
            started_at=_started_at(),
            completed_at=_completed_at(),
            input_rows=100,
            output_rows=95,
            rejected_rows=5,
        )

        summary = logger.summarize()

        assert summary.run_id == "RUN-001"
        assert summary.event_count == 1
        assert summary.succeeded_count == 1
        assert summary.failed_count == 0
        assert summary.passed is True

    def test_empty_to_frame_has_expected_columns(self) -> None:
        logger = AuditLogger("RUN-001")

        frame = logger.to_frame()

        assert isinstance(frame, pd.DataFrame)
        assert frame.empty
        assert list(frame.columns) == [
            "run_id",
            "pipeline_name",
            "stage",
            "status",
            "started_at",
            "completed_at",
            "duration_seconds",
            "input_rows",
            "output_rows",
            "rejected_rows",
            "dataset_name",
            "message",
            "error_type",
            "error_message",
            "metadata",
            "version",
        ]

    def test_to_frame_exports_events(self) -> None:
        logger = AuditLogger("RUN-001")

        logger.succeeded(
            stage=AuditStage.INGESTION,
            started_at=_started_at(),
            completed_at=_completed_at(),
            input_rows=100,
            output_rows=95,
            rejected_rows=5,
            metadata={"source": "synthetic"},
        )

        frame = logger.to_frame()

        assert len(frame) == 1
        assert frame.loc[0, "run_id"] == "RUN-001"
        assert frame.loc[0, "stage"] == "ingestion"
        assert frame.loc[0, "status"] == "succeeded"
        assert frame.loc[0, "input_rows"] == 100
        assert frame.loc[0, "metadata"] == {"source": "synthetic"}


class TestSummarizeAuditEvents:
    """Tests for summarize_audit_events."""

    def test_empty_events_return_zero_summary(self) -> None:
        summary = summarize_audit_events(
            (),
            run_id="RUN-001",
        )

        assert summary.event_count == 0
        assert summary.succeeded_count == 0
        assert summary.failed_count == 0
        assert summary.skipped_count == 0
        assert summary.started_count == 0
        assert summary.total_input_rows == 0
        assert summary.total_output_rows == 0
        assert summary.total_rejected_rows == 0
        assert summary.first_started_at is None
        assert summary.last_completed_at is None
        assert summary.passed is True

    def test_summary_aggregates_statuses_and_rows(self) -> None:
        start = _started_at()

        events = (
            AuditEvent(
                run_id="RUN-001",
                pipeline_name=DEFAULT_PIPELINE_NAME,
                stage="ingestion",
                status=AuditStatus.SUCCEEDED,
                started_at=start,
                completed_at=start + timedelta(seconds=2),
                input_rows=100,
                output_rows=95,
                rejected_rows=5,
            ),
            AuditEvent(
                run_id="RUN-001",
                pipeline_name=DEFAULT_PIPELINE_NAME,
                stage="validation",
                status=AuditStatus.SKIPPED,
                started_at=start + timedelta(seconds=3),
                completed_at=start + timedelta(seconds=3),
                input_rows=95,
                output_rows=0,
                rejected_rows=0,
            ),
            AuditEvent(
                run_id="RUN-001",
                pipeline_name=DEFAULT_PIPELINE_NAME,
                stage="loading",
                status=AuditStatus.FAILED,
                started_at=start + timedelta(seconds=4),
                completed_at=start + timedelta(seconds=6),
                input_rows=95,
                output_rows=0,
                rejected_rows=95,
                error_message="load failed",
            ),
        )

        summary = summarize_audit_events(
            events,
            run_id="RUN-001",
        )

        assert summary.event_count == 3
        assert summary.succeeded_count == 1
        assert summary.failed_count == 1
        assert summary.skipped_count == 1
        assert summary.started_count == 0
        assert summary.total_input_rows == 290
        assert summary.total_output_rows == 95
        assert summary.total_rejected_rows == 100
        assert summary.first_started_at == start
        assert summary.last_completed_at == start + timedelta(seconds=6)
        assert summary.passed is False

    def test_mismatched_run_id_is_rejected(self) -> None:
        event = _successful_event(run_id="RUN-002")

        with pytest.raises(ValueError):
            summarize_audit_events(
                (event,),
                run_id="RUN-001",
            )

    def test_mismatched_pipeline_name_is_rejected(self) -> None:
        event = _successful_event(
            pipeline_name="other-pipeline",
        )

        with pytest.raises(ValueError):
            summarize_audit_events(
                (event,),
                run_id="RUN-001",
                pipeline_name=DEFAULT_PIPELINE_NAME,
            )

    def test_invalid_event_type_is_rejected(self) -> None:
        with pytest.raises(TypeError):
            summarize_audit_events(
                ("invalid",),  # type: ignore[arg-type]
                run_id="RUN-001",
            )


class TestAuditConstants:
    """Tests for stable audit constants."""

    def test_default_audit_version(self) -> None:
        assert DEFAULT_AUDIT_VERSION == "1.0"

    def test_default_pipeline_name(self) -> None:
        assert DEFAULT_PIPELINE_NAME == "eoip-phase3-etl"
