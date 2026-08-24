"""Structured audit logging for EOIP Phase 3 ETL pipelines.

This module provides deterministic, in-memory audit records for ETL runs and
pipeline stages. It captures run identifiers, stage names, execution status,
row counts, timing, messages, and structured metadata.

The audit layer deliberately does not persist to a database, configure Python
logging, or perform Prefect orchestration.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Final

import pandas as pd

DEFAULT_AUDIT_VERSION: Final[str] = "1.0"
DEFAULT_PIPELINE_NAME: Final[str] = "eoip-phase3-etl"


class AuditStatus(StrEnum):
    """Execution status for an ETL audit event."""

    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class AuditStage(StrEnum):
    """Stable Phase 3 ETL audit-stage identifiers."""

    PIPELINE = "pipeline"
    INGESTION = "ingestion"
    VALIDATION = "validation"
    CLEANING = "cleaning"
    TRANSFORMATION = "transformation"
    INCREMENTAL = "incremental"
    LOADING = "loading"
    QUALITY = "quality"
    LINEAGE = "lineage"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """One immutable ETL audit event."""

    run_id: str
    pipeline_name: str
    stage: str
    status: AuditStatus
    started_at: datetime
    completed_at: datetime | None = None
    input_rows: int | None = None
    output_rows: int | None = None
    rejected_rows: int | None = None
    dataset_name: str | None = None
    message: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    version: str = DEFAULT_AUDIT_VERSION

    def __post_init__(self) -> None:
        """Normalize and validate audit event."""
        object.__setattr__(
            self,
            "run_id",
            _normalize_required_string(
                "run_id",
                self.run_id,
            ),
        )

        object.__setattr__(
            self,
            "pipeline_name",
            _normalize_required_string(
                "pipeline_name",
                self.pipeline_name,
            ),
        )

        object.__setattr__(
            self,
            "stage",
            _normalize_required_string(
                "stage",
                self.stage,
            ),
        )

        object.__setattr__(
            self,
            "version",
            _normalize_required_string(
                "version",
                self.version,
            ),
        )

        if not isinstance(
            self.status,
            AuditStatus,
        ):
            raise TypeError("status must be an AuditStatus.")

        started_at = _normalize_datetime(
            "started_at",
            self.started_at,
        )

        object.__setattr__(
            self,
            "started_at",
            started_at,
        )

        if self.completed_at is not None:
            completed_at = _normalize_datetime(
                "completed_at",
                self.completed_at,
            )

            if completed_at < started_at:
                raise ValueError("completed_at cannot be earlier than started_at.")

            object.__setattr__(
                self,
                "completed_at",
                completed_at,
            )

        for field_name in (
            "input_rows",
            "output_rows",
            "rejected_rows",
        ):
            value = getattr(
                self,
                field_name,
            )

            if value is not None:
                _validate_non_negative_int(
                    field_name,
                    value,
                )

        for field_name in (
            "dataset_name",
            "message",
            "error_type",
            "error_message",
        ):
            value = getattr(
                self,
                field_name,
            )

            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    _normalize_optional_string(
                        field_name,
                        value,
                    ),
                )

        if not isinstance(
            self.metadata,
            Mapping,
        ):
            raise TypeError("metadata must be a mapping.")

        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(
                dict(
                    sorted(
                        self.metadata.items(),
                        key=lambda item: str(item[0]),
                    )
                )
            ),
        )

        if self.status is AuditStatus.STARTED and self.completed_at is not None:
            raise ValueError("STARTED events cannot have completed_at.")

        if self.status is not AuditStatus.STARTED and self.completed_at is None:
            raise ValueError("Completed audit events require completed_at.")

        if self.status is AuditStatus.FAILED and self.error_message is None:
            raise ValueError("FAILED audit events require error_message.")

    @property
    def duration_seconds(self) -> float | None:
        """Return elapsed duration in seconds."""
        if self.completed_at is None:
            return None

        return (self.completed_at - self.started_at).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Return serialization-ready audit event."""
        return {
            "run_id": self.run_id,
            "pipeline_name": self.pipeline_name,
            "stage": self.stage,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at is not None else None
            ),
            "duration_seconds": self.duration_seconds,
            "input_rows": self.input_rows,
            "output_rows": self.output_rows,
            "rejected_rows": self.rejected_rows,
            "dataset_name": self.dataset_name,
            "message": self.message,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "metadata": dict(self.metadata),
            "version": self.version,
        }


@dataclass(frozen=True, slots=True)
class AuditRunSummary:
    """Aggregated audit summary for one ETL run."""

    run_id: str
    pipeline_name: str
    event_count: int
    succeeded_count: int
    failed_count: int
    skipped_count: int
    started_count: int
    total_input_rows: int
    total_output_rows: int
    total_rejected_rows: int
    first_started_at: datetime | None
    last_completed_at: datetime | None

    def __post_init__(self) -> None:
        """Validate summary metadata."""
        object.__setattr__(
            self,
            "run_id",
            _normalize_required_string(
                "run_id",
                self.run_id,
            ),
        )

        object.__setattr__(
            self,
            "pipeline_name",
            _normalize_required_string(
                "pipeline_name",
                self.pipeline_name,
            ),
        )

        for field_name in (
            "event_count",
            "succeeded_count",
            "failed_count",
            "skipped_count",
            "started_count",
            "total_input_rows",
            "total_output_rows",
            "total_rejected_rows",
        ):
            _validate_non_negative_int(
                field_name,
                getattr(
                    self,
                    field_name,
                ),
            )

        if self.first_started_at is not None:
            object.__setattr__(
                self,
                "first_started_at",
                _normalize_datetime(
                    "first_started_at",
                    self.first_started_at,
                ),
            )

        if self.last_completed_at is not None:
            object.__setattr__(
                self,
                "last_completed_at",
                _normalize_datetime(
                    "last_completed_at",
                    self.last_completed_at,
                ),
            )

    @property
    def passed(self) -> bool:
        """Return whether no failed events were recorded."""
        return self.failed_count == 0

    def to_dict(self) -> dict[str, Any]:
        """Return serialization-ready summary."""
        return {
            "run_id": self.run_id,
            "pipeline_name": self.pipeline_name,
            "passed": self.passed,
            "event_count": self.event_count,
            "succeeded_count": self.succeeded_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "started_count": self.started_count,
            "total_input_rows": self.total_input_rows,
            "total_output_rows": self.total_output_rows,
            "total_rejected_rows": self.total_rejected_rows,
            "first_started_at": (
                self.first_started_at.isoformat()
                if self.first_started_at is not None
                else None
            ),
            "last_completed_at": (
                self.last_completed_at.isoformat()
                if self.last_completed_at is not None
                else None
            ),
        }


class AuditLogger:
    """Deterministic in-memory audit collector."""

    def __init__(
        self,
        run_id: str,
        *,
        pipeline_name: str = DEFAULT_PIPELINE_NAME,
    ) -> None:
        """Create an audit logger."""
        self._run_id = _normalize_required_string(
            "run_id",
            run_id,
        )

        self._pipeline_name = _normalize_required_string(
            "pipeline_name",
            pipeline_name,
        )

        self._events: list[AuditEvent] = []

    @property
    def run_id(self) -> str:
        """Return run identifier."""
        return self._run_id

    @property
    def pipeline_name(self) -> str:
        """Return pipeline name."""
        return self._pipeline_name

    @property
    def events(self) -> tuple[AuditEvent, ...]:
        """Return immutable audit events."""
        return tuple(self._events)

    def record(
        self,
        *,
        stage: str | AuditStage,
        status: AuditStatus,
        started_at: datetime,
        completed_at: datetime | None = None,
        input_rows: int | None = None,
        output_rows: int | None = None,
        rejected_rows: int | None = None,
        dataset_name: str | None = None,
        message: str | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> AuditEvent:
        """Record one audit event."""
        stage_name = (
            stage.value
            if isinstance(
                stage,
                AuditStage,
            )
            else stage
        )

        event = AuditEvent(
            run_id=self._run_id,
            pipeline_name=self._pipeline_name,
            stage=stage_name,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            input_rows=input_rows,
            output_rows=output_rows,
            rejected_rows=rejected_rows,
            dataset_name=dataset_name,
            message=message,
            error_type=error_type,
            error_message=error_message,
            metadata=(metadata if metadata is not None else {}),
        )

        self._events.append(event)

        return event

    def started(
        self,
        *,
        stage: str | AuditStage,
        started_at: datetime | None = None,
        dataset_name: str | None = None,
        input_rows: int | None = None,
        message: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> AuditEvent:
        """Record a stage-start event."""
        return self.record(
            stage=stage,
            status=AuditStatus.STARTED,
            started_at=(started_at if started_at is not None else datetime.now(UTC)),
            input_rows=input_rows,
            dataset_name=dataset_name,
            message=message,
            metadata=metadata,
        )

    def succeeded(
        self,
        *,
        stage: str | AuditStage,
        started_at: datetime,
        completed_at: datetime | None = None,
        dataset_name: str | None = None,
        input_rows: int | None = None,
        output_rows: int | None = None,
        rejected_rows: int | None = None,
        message: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> AuditEvent:
        """Record a successful completion."""
        return self.record(
            stage=stage,
            status=AuditStatus.SUCCEEDED,
            started_at=started_at,
            completed_at=(
                completed_at if completed_at is not None else datetime.now(UTC)
            ),
            input_rows=input_rows,
            output_rows=output_rows,
            rejected_rows=rejected_rows,
            dataset_name=dataset_name,
            message=message,
            metadata=metadata,
        )

    def failed(
        self,
        *,
        stage: str | AuditStage,
        started_at: datetime,
        error: BaseException | None = None,
        error_message: str | None = None,
        completed_at: datetime | None = None,
        dataset_name: str | None = None,
        input_rows: int | None = None,
        output_rows: int | None = None,
        rejected_rows: int | None = None,
        message: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> AuditEvent:
        """Record a failed completion."""
        resolved_error_message = error_message
        resolved_error_type: str | None = None

        if error is not None:
            if not isinstance(
                error,
                BaseException,
            ):
                raise TypeError("error must be an exception or None.")

            resolved_error_type = type(error).__name__

            if resolved_error_message is None:
                resolved_error_message = str(error)

        if resolved_error_message is None:
            raise ValueError("error or error_message is required.")

        return self.record(
            stage=stage,
            status=AuditStatus.FAILED,
            started_at=started_at,
            completed_at=(
                completed_at if completed_at is not None else datetime.now(UTC)
            ),
            input_rows=input_rows,
            output_rows=output_rows,
            rejected_rows=rejected_rows,
            dataset_name=dataset_name,
            message=message,
            error_type=resolved_error_type,
            error_message=resolved_error_message,
            metadata=metadata,
        )

    def skipped(
        self,
        *,
        stage: str | AuditStage,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        dataset_name: str | None = None,
        input_rows: int | None = None,
        message: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> AuditEvent:
        """Record a skipped stage."""
        resolved_started_at = (
            started_at if started_at is not None else datetime.now(UTC)
        )

        return self.record(
            stage=stage,
            status=AuditStatus.SKIPPED,
            started_at=resolved_started_at,
            completed_at=(
                completed_at if completed_at is not None else resolved_started_at
            ),
            input_rows=input_rows,
            output_rows=0,
            rejected_rows=0,
            dataset_name=dataset_name,
            message=message,
            metadata=metadata,
        )

    def summarize(self) -> AuditRunSummary:
        """Return aggregate run summary."""
        return summarize_audit_events(
            self._events,
            run_id=self._run_id,
            pipeline_name=self._pipeline_name,
        )

    def to_frame(self) -> pd.DataFrame:
        """Return audit events as a DataFrame."""
        columns = [
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

        if not self._events:
            return pd.DataFrame(columns=columns)

        return pd.DataFrame(
            [event.to_dict() for event in self._events],
            columns=columns,
        )


def summarize_audit_events(
    events: Iterable[AuditEvent],
    *,
    run_id: str,
    pipeline_name: str = DEFAULT_PIPELINE_NAME,
) -> AuditRunSummary:
    """Summarize audit events for one ETL run."""
    normalized_run_id = _normalize_required_string(
        "run_id",
        run_id,
    )

    normalized_pipeline_name = _normalize_required_string(
        "pipeline_name",
        pipeline_name,
    )

    normalized_events = tuple(events)

    for event in normalized_events:
        if not isinstance(
            event,
            AuditEvent,
        ):
            raise TypeError("events must contain AuditEvent objects.")

        if event.run_id != normalized_run_id:
            raise ValueError("All events must match the requested run_id.")

        if event.pipeline_name != normalized_pipeline_name:
            raise ValueError("All events must match the requested pipeline_name.")

    succeeded_count = sum(
        event.status is AuditStatus.SUCCEEDED for event in normalized_events
    )

    failed_count = sum(
        event.status is AuditStatus.FAILED for event in normalized_events
    )

    skipped_count = sum(
        event.status is AuditStatus.SKIPPED for event in normalized_events
    )

    started_count = sum(
        event.status is AuditStatus.STARTED for event in normalized_events
    )

    total_input_rows = sum(event.input_rows or 0 for event in normalized_events)

    total_output_rows = sum(event.output_rows or 0 for event in normalized_events)

    total_rejected_rows = sum(event.rejected_rows or 0 for event in normalized_events)

    first_started_at = (
        min(event.started_at for event in normalized_events)
        if normalized_events
        else None
    )

    completed_times = tuple(
        event.completed_at
        for event in normalized_events
        if event.completed_at is not None
    )

    last_completed_at = max(completed_times) if completed_times else None

    return AuditRunSummary(
        run_id=normalized_run_id,
        pipeline_name=normalized_pipeline_name,
        event_count=len(normalized_events),
        succeeded_count=succeeded_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        started_count=started_count,
        total_input_rows=total_input_rows,
        total_output_rows=total_output_rows,
        total_rejected_rows=total_rejected_rows,
        first_started_at=first_started_at,
        last_completed_at=last_completed_at,
    )


def _normalize_required_string(
    name: str,
    value: str,
) -> str:
    """Normalize a required non-empty string."""
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(f"{name} must be a string.")

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{name} cannot be empty.")

    return normalized


def _normalize_optional_string(
    name: str,
    value: str,
) -> str:
    """Normalize an optional string."""
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(f"{name} must be a string.")

    return value.strip()


def _normalize_datetime(
    name: str,
    value: datetime,
) -> datetime:
    """Normalize datetime values to UTC."""
    if not isinstance(
        value,
        datetime,
    ):
        raise TypeError(f"{name} must be a datetime.")

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def _validate_non_negative_int(
    name: str,
    value: int,
) -> None:
    """Validate a non-negative integer."""
    if isinstance(
        value,
        bool,
    ) or not isinstance(
        value,
        int,
    ):
        raise TypeError(f"{name} must be an integer.")

    if value < 0:
        raise ValueError(f"{name} must be greater than or equal to zero.")


__all__ = [
    "DEFAULT_AUDIT_VERSION",
    "DEFAULT_PIPELINE_NAME",
    "AuditEvent",
    "AuditLogger",
    "AuditRunSummary",
    "AuditStage",
    "AuditStatus",
    "summarize_audit_events",
]
