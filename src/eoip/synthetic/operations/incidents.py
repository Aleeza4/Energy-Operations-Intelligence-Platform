"""
Operational incident generation for EOIP Phase 2.

This module converts event-linked alarm records into deterministic operational
incidents. It groups causally related alarms, assigns incident category,
severity, priority, ownership, lifecycle timestamps, SLA targets, and links
back to alarm and ground-truth event identifiers.

The authoritative ``Incident`` domain model remains the validation boundary for
core incident fields. The returned DataFrame adds operational fields required
by downstream work-order generation and reliability analytics.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol

import numpy as np
import pandas as pd

from eoip.synthetic.models.alarm import AlarmCategory, AlarmSeverity
from eoip.synthetic.models.incident import (
    Incident,
    IncidentCategory,
    IncidentSeverity,
    IncidentStatus,
)


class IncidentPriority(StrEnum):
    """Operational incident priority levels."""

    P1 = "p1"
    P2 = "p2"
    P3 = "p3"
    P4 = "p4"


class IncidentOwnershipTeam(StrEnum):
    """Supported incident ownership teams."""

    GRID_OPERATIONS = "grid_operations"
    PLANT_OPERATIONS = "plant_operations"
    MAINTENANCE = "maintenance"
    NETWORK_OPERATIONS = "network_operations"
    PERFORMANCE_ENGINEERING = "performance_engineering"
    HSE = "hse"


class _RandomContextProtocol(Protocol):
    """Minimal random-context interface used by incident generation."""

    def generator(
        self,
        name: str,
        entity_id: str | None = None,
    ) -> np.random.Generator:
        """Return a deterministic named NumPy generator."""


@dataclass(frozen=True, slots=True)
class IncidentOperationsConfig:
    """Configuration for deterministic incident generation."""

    random_seed: int = 20250201
    grouping_window_minutes: int = 30
    detection_delay_min_minutes: int = 1
    detection_delay_max_minutes: int = 10
    assignment_delay_min_minutes: int = 2
    assignment_delay_max_minutes: int = 20
    investigation_delay_min_minutes: int = 5
    investigation_delay_max_minutes: int = 30
    restoration_delay_min_minutes: int = 5
    restoration_delay_max_minutes: int = 60
    closure_delay_min_minutes: int = 5
    closure_delay_max_minutes: int = 60
    conversion_probability_warning: float = 0.35
    conversion_probability_major: float = 0.85
    conversion_probability_critical: float = 1.0
    include_informational_incidents: bool = False
    group_by_ground_truth_event: bool = True
    schema_version: str = "1.0.0"

    def __post_init__(self) -> None:
        """Validate configuration values."""
        normalized_schema_version = self.schema_version.strip()
        object.__setattr__(self, "schema_version", normalized_schema_version)

        if isinstance(self.random_seed, bool) or not isinstance(
            self.random_seed,
            int,
        ):
            raise TypeError("random_seed must be an integer.")

        if self.random_seed < 0:
            raise ValueError("random_seed must be non-negative.")

        integer_fields = (
            "grouping_window_minutes",
            "detection_delay_min_minutes",
            "detection_delay_max_minutes",
            "assignment_delay_min_minutes",
            "assignment_delay_max_minutes",
            "investigation_delay_min_minutes",
            "investigation_delay_max_minutes",
            "restoration_delay_min_minutes",
            "restoration_delay_max_minutes",
            "closure_delay_min_minutes",
            "closure_delay_max_minutes",
        )
        for field_name in integer_fields:
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer.")
            if value < 0:
                raise ValueError(f"{field_name} must be non-negative.")

        bound_pairs = (
            (
                "detection_delay_min_minutes",
                "detection_delay_max_minutes",
            ),
            (
                "assignment_delay_min_minutes",
                "assignment_delay_max_minutes",
            ),
            (
                "investigation_delay_min_minutes",
                "investigation_delay_max_minutes",
            ),
            (
                "restoration_delay_min_minutes",
                "restoration_delay_max_minutes",
            ),
            (
                "closure_delay_min_minutes",
                "closure_delay_max_minutes",
            ),
        )
        for minimum_name, maximum_name in bound_pairs:
            if getattr(self, maximum_name) < getattr(self, minimum_name):
                raise ValueError(
                    f"{maximum_name} must be greater than or equal to "
                    f"{minimum_name}."
                )

        probability_fields = (
            "conversion_probability_warning",
            "conversion_probability_major",
            "conversion_probability_critical",
        )
        for field_name in probability_fields:
            _validate_probability(
                field_name,
                getattr(self, field_name),
            )

        for field_name in (
            "include_informational_incidents",
            "group_by_ground_truth_event",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be a boolean.")

        if not normalized_schema_version:
            raise ValueError("schema_version cannot be empty.")


@dataclass(frozen=True, slots=True)
class IncidentGenerationSummary:
    """Aggregate metadata for one incident-generation run."""

    input_alarm_count: int
    eligible_alarm_count: int
    generated_incident_count: int
    grouped_alarm_count: int
    skipped_alarm_count: int

    def to_record(self) -> dict[str, int]:
        """Return a serialization-ready summary."""
        return {
            "input_alarm_count": self.input_alarm_count,
            "eligible_alarm_count": self.eligible_alarm_count,
            "generated_incident_count": self.generated_incident_count,
            "grouped_alarm_count": self.grouped_alarm_count,
            "skipped_alarm_count": self.skipped_alarm_count,
        }


@dataclass(frozen=True, slots=True)
class IncidentGenerationResult:
    """Incident DataFrame and summary metadata."""

    frame: pd.DataFrame
    summary: IncidentGenerationSummary


@dataclass(frozen=True, slots=True)
class _IncidentCandidate:
    """Internal grouped incident candidate."""

    plant_id: str
    equipment_id: str
    linked_alarm_ids: tuple[str, ...]
    primary_alarm_id: str
    ground_truth_event_id: str | None
    category: IncidentCategory
    severity: IncidentSeverity
    priority: IncidentPriority
    owner_team: IncidentOwnershipTeam
    occurred_at: datetime
    detected_at: datetime
    assigned_at: datetime
    investigation_started_at: datetime
    restored_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None
    status: IncidentStatus
    incident_name: str
    description: str
    root_cause: str | None
    sla_response_minutes: int
    sla_resolution_minutes: int
    response_sla_breached: bool
    resolution_sla_breached: bool
    is_synthetic_ground_truth: bool
    generation_run_id: str


def generate_incidents(
    alarms: pd.DataFrame,
    config: IncidentOperationsConfig | None = None,
    random_context: _RandomContextProtocol | None = None,
) -> pd.DataFrame:
    """Generate deterministic incidents from operational alarm records."""
    return generate_incident_result(
        alarms,
        config=config,
        random_context=random_context,
    ).frame


def generate_incident_result(
    alarms: pd.DataFrame,
    config: IncidentOperationsConfig | None = None,
    random_context: _RandomContextProtocol | None = None,
) -> IncidentGenerationResult:
    """Generate incidents together with aggregate run metadata."""
    resolved_config = config or IncidentOperationsConfig()
    normalized = _normalize_alarms_frame(alarms)

    eligible = normalized.loc[
        normalized["incident_eligible"].astype(bool)
        & ~normalized["is_nuisance"].astype(bool)
    ].copy()

    groups = _build_alarm_groups(
        eligible,
        config=resolved_config,
    )

    candidates: list[_IncidentCandidate] = []
    skipped_alarm_count = 0

    for group_index, group in enumerate(groups, start=1):
        primary = _select_primary_alarm(group)
        rng = _generator(
            config=resolved_config,
            random_context=random_context,
            stream_name="operations.incidents",
            entity_id=(
                f"{primary['ground_truth_event_id']}|"
                f"{primary['alarm_id']}|{group_index}"
            ),
        )

        if not _should_create_incident(
            primary,
            config=resolved_config,
            rng=rng,
        ):
            skipped_alarm_count += len(group)
            continue

        candidates.append(
            _build_candidate(
                group,
                primary=primary,
                config=resolved_config,
                rng=rng,
            )
        )

    frame = _candidates_to_frame(
        candidates,
        schema_version=resolved_config.schema_version,
    )

    summary = IncidentGenerationSummary(
        input_alarm_count=len(normalized),
        eligible_alarm_count=len(eligible),
        generated_incident_count=len(frame),
        grouped_alarm_count=max(
            0,
            len(eligible) - len(groups),
        ),
        skipped_alarm_count=skipped_alarm_count,
    )
    return IncidentGenerationResult(frame=frame, summary=summary)


def incidents_to_domain_models(
    incidents: pd.DataFrame,
) -> tuple[Incident, ...]:
    """Convert incident output records to authoritative Incident objects."""
    required = {
        "incident_id",
        "plant_id",
        "primary_equipment_id",
        "incident_name",
        "category",
        "severity",
        "occurred_at",
        "status",
        "detected_at",
        "resolved_at",
        "description",
        "root_cause",
        "primary_alarm_id",
        "is_synthetic_ground_truth",
    }
    missing = required.difference(incidents.columns)
    if missing:
        raise ValueError(
            "incidents DataFrame is missing columns: " f"{sorted(missing)}."
        )

    models: list[Incident] = []
    for row in incidents.to_dict(orient="records"):
        models.append(
            Incident(
                incident_id=str(row["incident_id"]),
                plant_id=str(row["plant_id"]),
                equipment_id=str(row["primary_equipment_id"]),
                incident_name=str(row["incident_name"]),
                category=_coerce_incident_category(row["category"]),
                severity=_coerce_incident_severity(row["severity"]),
                occurred_at=_coerce_timestamp(
                    row["occurred_at"],
                    field_name="occurred_at",
                    allow_none=False,
                ),
                status=_coerce_incident_status(row["status"]),
                detected_at=_coerce_timestamp(
                    row["detected_at"],
                    field_name="detected_at",
                    allow_none=True,
                ),
                resolved_at=_coerce_timestamp(
                    row["resolved_at"],
                    field_name="resolved_at",
                    allow_none=True,
                ),
                description=_nullable_text(row["description"]),
                root_cause=_nullable_text(row["root_cause"]),
                linked_alarm_id=str(row["primary_alarm_id"]),
                is_synthetic_ground_truth=bool(row["is_synthetic_ground_truth"]),
            )
        )

    return tuple(models)


def _normalize_alarms_frame(alarms: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize the alarm input contract."""
    if not isinstance(alarms, pd.DataFrame):
        raise TypeError("alarms must be a pandas DataFrame.")

    required = {
        "alarm_id",
        "plant_id",
        "equipment_id",
        "ground_truth_event_id",
        "alarm_code",
        "alarm_name",
        "category",
        "severity",
        "raised_at",
        "status",
        "acknowledged_at",
        "cleared_at",
        "message",
        "is_nuisance",
        "incident_eligible",
        "event_type",
        "event_start_at_utc",
        "event_end_at_utc",
        "generation_run_id",
        "is_synthetic_ground_truth",
    }
    missing = required.difference(alarms.columns)
    if missing:
        raise ValueError("alarms DataFrame is missing columns: " f"{sorted(missing)}.")

    frame = alarms.copy(deep=True)
    for column in (
        "raised_at",
        "acknowledged_at",
        "cleared_at",
        "event_start_at_utc",
        "event_end_at_utc",
    ):
        frame[column] = pd.to_datetime(
            frame[column],
            utc=True,
            errors="coerce",
        )

    if frame["raised_at"].isna().any():
        raise ValueError("raised_at cannot contain missing values.")

    if frame["alarm_id"].duplicated().any():
        raise ValueError("alarm_id values must be unique.")

    return frame.sort_values(
        ["raised_at", "plant_id", "equipment_id", "alarm_id"],
        kind="stable",
    ).reset_index(drop=True)


def _build_alarm_groups(
    alarms: pd.DataFrame,
    *,
    config: IncidentOperationsConfig,
) -> tuple[pd.DataFrame, ...]:
    """Group alarms by causal lineage or bounded time proximity."""
    if alarms.empty:
        return ()

    groups: list[pd.DataFrame] = []

    if config.group_by_ground_truth_event:
        with_truth = alarms.loc[alarms["ground_truth_event_id"].notna()]
        without_truth = alarms.loc[alarms["ground_truth_event_id"].isna()]

        for _, group in with_truth.groupby(
            ["plant_id", "ground_truth_event_id"],
            sort=True,
            dropna=False,
        ):
            groups.append(group.copy())

        groups.extend(
            _time_window_groups(
                without_truth,
                window_minutes=config.grouping_window_minutes,
            )
        )
    else:
        groups.extend(
            _time_window_groups(
                alarms,
                window_minutes=config.grouping_window_minutes,
            )
        )

    return tuple(
        sorted(
            groups,
            key=lambda group: (
                group["raised_at"].min(),
                str(group.iloc[0]["plant_id"]),
                str(group.iloc[0]["alarm_id"]),
            ),
        )
    )


def _time_window_groups(
    alarms: pd.DataFrame,
    *,
    window_minutes: int,
) -> list[pd.DataFrame]:
    """Group same-plant alarms occurring within a rolling time window."""
    result: list[pd.DataFrame] = []

    for _, plant_group in alarms.groupby("plant_id", sort=True):
        ordered = plant_group.sort_values("raised_at", kind="stable")
        current_indices: list[int] = []
        previous_time: pd.Timestamp | None = None

        for index, row in ordered.iterrows():
            raised_at = pd.Timestamp(row["raised_at"])
            if previous_time is not None and raised_at - previous_time > pd.Timedelta(
                minutes=window_minutes
            ):
                result.append(ordered.loc[current_indices].copy())
                current_indices = []

            current_indices.append(index)
            previous_time = raised_at

        if current_indices:
            result.append(ordered.loc[current_indices].copy())

    return result


def _select_primary_alarm(group: pd.DataFrame) -> Mapping[str, Any]:
    """Select the highest-severity earliest alarm as primary."""
    severity_rank = {
        AlarmSeverity.INFORMATIONAL.value: 0,
        AlarmSeverity.WARNING.value: 1,
        AlarmSeverity.MAJOR.value: 2,
        AlarmSeverity.CRITICAL.value: 3,
    }
    ranked = group.assign(
        _severity_rank=group["severity"].map(severity_rank).fillna(-1)
    ).sort_values(
        ["_severity_rank", "raised_at", "alarm_id"],
        ascending=[False, True, True],
        kind="stable",
    )
    return ranked.iloc[0].to_dict()


def _should_create_incident(
    primary: Mapping[str, Any],
    *,
    config: IncidentOperationsConfig,
    rng: np.random.Generator,
) -> bool:
    """Return whether the primary alarm converts to an incident."""
    severity = str(primary["severity"])

    if severity == AlarmSeverity.INFORMATIONAL.value:
        return config.include_informational_incidents

    probability = {
        AlarmSeverity.WARNING.value: (config.conversion_probability_warning),
        AlarmSeverity.MAJOR.value: config.conversion_probability_major,
        AlarmSeverity.CRITICAL.value: (config.conversion_probability_critical),
    }.get(severity, 0.0)

    return float(rng.random()) < probability


def _build_candidate(
    group: pd.DataFrame,
    *,
    primary: Mapping[str, Any],
    config: IncidentOperationsConfig,
    rng: np.random.Generator,
) -> _IncidentCandidate:
    """Build one grouped incident candidate."""
    occurred_at = _minimum_timestamp(
        group["event_start_at_utc"],
        fallback=group["raised_at"].min(),
    )
    detected_at = occurred_at + timedelta(
        minutes=_sample_delay(
            rng,
            config.detection_delay_min_minutes,
            config.detection_delay_max_minutes,
        )
    )
    assigned_at = detected_at + timedelta(
        minutes=_sample_delay(
            rng,
            config.assignment_delay_min_minutes,
            config.assignment_delay_max_minutes,
        )
    )
    investigation_started_at = assigned_at + timedelta(
        minutes=_sample_delay(
            rng,
            config.investigation_delay_min_minutes,
            config.investigation_delay_max_minutes,
        )
    )

    last_clear = _maximum_optional_timestamp(group["cleared_at"])
    category = _map_category(str(primary["category"]))
    severity = _map_severity(str(primary["severity"]))
    priority = _priority_for_severity(severity)
    owner_team = _owner_for_category(category)
    response_sla, resolution_sla = _sla_targets(priority)

    restored_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None

    if last_clear is not None:
        restored_at = max(
            last_clear,
            investigation_started_at,
        ) + timedelta(
            minutes=_sample_delay(
                rng,
                config.restoration_delay_min_minutes,
                config.restoration_delay_max_minutes,
            )
        )
        resolved_at = restored_at
        closed_at = resolved_at + timedelta(
            minutes=_sample_delay(
                rng,
                config.closure_delay_min_minutes,
                config.closure_delay_max_minutes,
            )
        )
        status = IncidentStatus.RESOLVED
    else:
        status = IncidentStatus.INVESTIGATING

    response_minutes = (assigned_at - detected_at).total_seconds() / 60.0
    resolution_minutes = (
        None
        if resolved_at is None
        else (resolved_at - occurred_at).total_seconds() / 60.0
    )

    linked_alarm_ids = tuple(sorted(str(value) for value in group["alarm_id"]))
    event_ids = tuple(
        sorted(
            {
                str(value)
                for value in group["ground_truth_event_id"]
                if not pd.isna(value)
            }
        )
    )

    return _IncidentCandidate(
        plant_id=str(primary["plant_id"]),
        equipment_id=str(primary["equipment_id"]),
        linked_alarm_ids=linked_alarm_ids,
        primary_alarm_id=str(primary["alarm_id"]),
        ground_truth_event_id=event_ids[0] if event_ids else None,
        category=category,
        severity=severity,
        priority=priority,
        owner_team=owner_team,
        occurred_at=occurred_at,
        detected_at=detected_at,
        assigned_at=assigned_at,
        investigation_started_at=investigation_started_at,
        restored_at=restored_at,
        resolved_at=resolved_at,
        closed_at=closed_at,
        status=status,
        incident_name=_incident_name(primary, category),
        description=_incident_description(group, primary),
        root_cause=_root_cause(primary),
        sla_response_minutes=response_sla,
        sla_resolution_minutes=resolution_sla,
        response_sla_breached=response_minutes > response_sla,
        resolution_sla_breached=(
            resolution_minutes is not None and resolution_minutes > resolution_sla
        ),
        is_synthetic_ground_truth=bool(group["is_synthetic_ground_truth"].all()),
        generation_run_id=str(primary["generation_run_id"]),
    )


def _candidates_to_frame(
    candidates: list[_IncidentCandidate],
    *,
    schema_version: str,
) -> pd.DataFrame:
    """Assign stable IDs and build the incident output DataFrame."""
    ordered = sorted(
        candidates,
        key=lambda item: (
            item.occurred_at,
            item.plant_id,
            item.equipment_id,
            item.primary_alarm_id,
        ),
    )
    records: list[dict[str, object]] = []

    for index, candidate in enumerate(ordered, start=1):
        incident_id = f"INC-{index:07d}"
        model = Incident(
            incident_id=incident_id,
            plant_id=candidate.plant_id,
            equipment_id=candidate.equipment_id,
            incident_name=candidate.incident_name,
            category=candidate.category,
            severity=candidate.severity,
            occurred_at=candidate.occurred_at,
            status=candidate.status,
            detected_at=candidate.detected_at,
            resolved_at=candidate.resolved_at,
            description=candidate.description,
            root_cause=candidate.root_cause,
            linked_alarm_id=candidate.primary_alarm_id,
            is_synthetic_ground_truth=(candidate.is_synthetic_ground_truth),
        )
        records.append(
            {
                "incident_id": model.incident_id,
                "plant_id": model.plant_id,
                "primary_equipment_id": model.equipment_id,
                "incident_name": model.incident_name,
                "category": model.category.value,
                "severity": model.severity.value,
                "priority": candidate.priority.value,
                "status": model.status.value,
                "owner_team": candidate.owner_team.value,
                "occurred_at": model.occurred_at,
                "detected_at": model.detected_at,
                "assigned_at": candidate.assigned_at,
                "investigation_started_at": (candidate.investigation_started_at),
                "restored_at": candidate.restored_at,
                "resolved_at": model.resolved_at,
                "closed_at": candidate.closed_at,
                "primary_alarm_id": candidate.primary_alarm_id,
                "linked_alarm_ids": candidate.linked_alarm_ids,
                "linked_alarm_count": len(candidate.linked_alarm_ids),
                "ground_truth_event_id": (candidate.ground_truth_event_id),
                "description": model.description,
                "root_cause": model.root_cause,
                "sla_response_minutes": (candidate.sla_response_minutes),
                "sla_resolution_minutes": (candidate.sla_resolution_minutes),
                "response_sla_breached": (candidate.response_sla_breached),
                "resolution_sla_breached": (candidate.resolution_sla_breached),
                "detection_seconds": model.detection_seconds,
                "resolution_seconds": model.resolution_seconds,
                "is_open": model.is_open,
                "is_critical": model.is_critical,
                "is_synthetic_ground_truth": (model.is_synthetic_ground_truth),
                "generation_run_id": candidate.generation_run_id,
                "schema_version": schema_version,
            }
        )

    frame = pd.DataFrame.from_records(
        records,
        columns=_output_columns(),
    )
    if frame.empty:
        return frame

    for column in (
        "occurred_at",
        "detected_at",
        "assigned_at",
        "investigation_started_at",
        "restored_at",
        "resolved_at",
        "closed_at",
    ):
        frame[column] = pd.to_datetime(
            frame[column],
            utc=True,
            errors="coerce",
        )

    return frame.sort_values(
        ["occurred_at", "plant_id", "incident_id"],
        kind="stable",
    ).reset_index(drop=True)


def _map_category(value: str) -> IncidentCategory:
    """Map alarm categories to incident categories."""
    mapping = {
        AlarmCategory.EQUIPMENT.value: (IncidentCategory.EQUIPMENT_FAILURE),
        AlarmCategory.GRID.value: IncidentCategory.GRID_EVENT,
        AlarmCategory.COMMUNICATION.value: (IncidentCategory.COMMUNICATION_FAILURE),
        AlarmCategory.PERFORMANCE.value: (IncidentCategory.PERFORMANCE_DEGRADATION),
        AlarmCategory.ENVIRONMENTAL.value: (IncidentCategory.ENVIRONMENTAL_EVENT),
        AlarmCategory.SAFETY.value: IncidentCategory.SAFETY_EVENT,
    }
    return mapping.get(
        value,
        IncidentCategory.EQUIPMENT_FAILURE,
    )


def _map_severity(value: str) -> IncidentSeverity:
    """Map alarm severity to incident severity."""
    mapping = {
        AlarmSeverity.INFORMATIONAL.value: IncidentSeverity.LOW,
        AlarmSeverity.WARNING.value: IncidentSeverity.MODERATE,
        AlarmSeverity.MAJOR.value: IncidentSeverity.HIGH,
        AlarmSeverity.CRITICAL.value: IncidentSeverity.CRITICAL,
    }
    return mapping[value]


def _priority_for_severity(
    severity: IncidentSeverity,
) -> IncidentPriority:
    """Map incident severity to priority."""
    return {
        IncidentSeverity.CRITICAL: IncidentPriority.P1,
        IncidentSeverity.HIGH: IncidentPriority.P2,
        IncidentSeverity.MODERATE: IncidentPriority.P3,
        IncidentSeverity.LOW: IncidentPriority.P4,
    }[severity]


def _owner_for_category(
    category: IncidentCategory,
) -> IncidentOwnershipTeam:
    """Assign an operational ownership team."""
    return {
        IncidentCategory.GRID_EVENT: (IncidentOwnershipTeam.GRID_OPERATIONS),
        IncidentCategory.EQUIPMENT_FAILURE: (IncidentOwnershipTeam.MAINTENANCE),
        IncidentCategory.COMMUNICATION_FAILURE: (
            IncidentOwnershipTeam.NETWORK_OPERATIONS
        ),
        IncidentCategory.PERFORMANCE_DEGRADATION: (
            IncidentOwnershipTeam.PERFORMANCE_ENGINEERING
        ),
        IncidentCategory.ENVIRONMENTAL_EVENT: (IncidentOwnershipTeam.PLANT_OPERATIONS),
        IncidentCategory.SAFETY_EVENT: IncidentOwnershipTeam.HSE,
        IncidentCategory.PLANNED_MAINTENANCE: (IncidentOwnershipTeam.MAINTENANCE),
    }[category]


def _sla_targets(
    priority: IncidentPriority,
) -> tuple[int, int]:
    """Return response and resolution SLA targets in minutes."""
    return {
        IncidentPriority.P1: (5, 60),
        IncidentPriority.P2: (15, 240),
        IncidentPriority.P3: (30, 480),
        IncidentPriority.P4: (60, 1_440),
    }[priority]


def _incident_name(
    primary: Mapping[str, Any],
    category: IncidentCategory,
) -> str:
    """Return a bounded incident name."""
    alarm_name = str(primary["alarm_name"]).strip()
    if alarm_name:
        return f"{alarm_name} Incident"[:150]

    return f"{category.value.replace('_', ' ').title()} Incident"[:150]


def _incident_description(
    group: pd.DataFrame,
    primary: Mapping[str, Any],
) -> str:
    """Return a concise grouped incident description."""
    count = len(group)
    code = str(primary["alarm_code"])
    return (
        f"Operational incident created from {count} linked alarm(s). "
        f"Primary alarm code: {code}."
    )[:1_000]


def _root_cause(primary: Mapping[str, Any]) -> str:
    """Derive a stable root-cause label from event and alarm context."""
    event_type = str(primary["event_type"]).strip()
    if event_type:
        return event_type.replace("_", " ").title()[:500]

    return str(primary["alarm_code"]).replace("-", " ").title()[:500]


def _minimum_timestamp(
    values: pd.Series,
    *,
    fallback: object,
) -> datetime:
    """Return minimum non-null aware timestamp."""
    non_null = pd.to_datetime(
        values.dropna(),
        utc=True,
        errors="coerce",
    ).dropna()
    selected = pd.Timestamp(fallback) if non_null.empty else non_null.min()
    return selected.to_pydatetime().astimezone(UTC)


def _maximum_optional_timestamp(
    values: pd.Series,
) -> datetime | None:
    """Return maximum non-null timestamp or None."""
    non_null = pd.to_datetime(
        values.dropna(),
        utc=True,
        errors="coerce",
    ).dropna()
    if non_null.empty:
        return None
    return non_null.max().to_pydatetime().astimezone(UTC)


def _sample_delay(
    rng: np.random.Generator,
    minimum: int,
    maximum: int,
) -> int:
    """Sample an inclusive integer delay."""
    if minimum == maximum:
        return minimum
    return int(rng.integers(minimum, maximum + 1))


def _generator(
    *,
    config: IncidentOperationsConfig,
    random_context: _RandomContextProtocol | None,
    stream_name: str,
    entity_id: str,
) -> np.random.Generator:
    """Return a deterministic named generator."""
    if random_context is not None:
        return random_context.generator(
            stream_name,
            entity_id=entity_id,
        )

    payload = (f"{config.random_seed}|{stream_name}|{entity_id}").encode()
    digest = hashlib.sha256(payload).digest()
    entropy = int.from_bytes(
        digest[:8],
        "big",
        signed=False,
    )
    return np.random.default_rng(entropy)


def _validate_probability(
    field_name: str,
    value: object,
) -> None:
    """Validate a finite probability."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric.")

    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite.")

    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0.")


def _coerce_timestamp(
    value: object,
    *,
    field_name: str,
    allow_none: bool,
) -> datetime | None:
    """Coerce an aware timestamp to a Python datetime."""
    if value is None or pd.isna(value):
        if allow_none:
            return None
        raise ValueError(f"{field_name} cannot be missing.")

    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware.")
    return timestamp.to_pydatetime().astimezone(UTC)


def _coerce_incident_category(
    value: object,
) -> IncidentCategory:
    """Coerce a category value."""
    return (
        value if isinstance(value, IncidentCategory) else IncidentCategory(str(value))
    )


def _coerce_incident_severity(
    value: object,
) -> IncidentSeverity:
    """Coerce a severity value."""
    return (
        value if isinstance(value, IncidentSeverity) else IncidentSeverity(str(value))
    )


def _coerce_incident_status(
    value: object,
) -> IncidentStatus:
    """Coerce a status value."""
    return value if isinstance(value, IncidentStatus) else IncidentStatus(str(value))


def _nullable_text(value: object) -> str | None:
    """Normalize nullable text from a DataFrame row."""
    if value is None or pd.isna(value):
        return None
    return str(value)


def _output_columns() -> tuple[str, ...]:
    """Return the stable incident output contract."""
    return (
        "incident_id",
        "plant_id",
        "primary_equipment_id",
        "incident_name",
        "category",
        "severity",
        "priority",
        "status",
        "owner_team",
        "occurred_at",
        "detected_at",
        "assigned_at",
        "investigation_started_at",
        "restored_at",
        "resolved_at",
        "closed_at",
        "primary_alarm_id",
        "linked_alarm_ids",
        "linked_alarm_count",
        "ground_truth_event_id",
        "description",
        "root_cause",
        "sla_response_minutes",
        "sla_resolution_minutes",
        "response_sla_breached",
        "resolution_sla_breached",
        "detection_seconds",
        "resolution_seconds",
        "is_open",
        "is_critical",
        "is_synthetic_ground_truth",
        "generation_run_id",
        "schema_version",
    )


__all__ = [
    "IncidentGenerationResult",
    "IncidentGenerationSummary",
    "IncidentOperationsConfig",
    "IncidentOwnershipTeam",
    "IncidentPriority",
    "generate_incident_result",
    "generate_incidents",
    "incidents_to_domain_models",
]
