"""Operational work-order generation for EOIP Phase 2."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol

import numpy as np
import pandas as pd

from eoip.synthetic.models.work_order import (
    WorkOrder,
    WorkOrderPriority,
    WorkOrderStatus,
    WorkOrderType,
)


class MaintenanceTeam(StrEnum):
    ELECTRICAL = "electrical_maintenance"
    NETWORK = "network_maintenance"
    GRID = "grid_operations"
    PERFORMANCE = "performance_engineering"
    HSE = "hse"
    GENERAL = "general_maintenance"


class _RandomContextProtocol(Protocol):
    def generator(
        self,
        name: str,
        entity_id: str | None = None,
    ) -> np.random.Generator: ...


@dataclass(frozen=True, slots=True)
class WorkOrderOperationsConfig:
    random_seed: int = 20250201
    conversion_probability_p1: float = 1.0
    conversion_probability_p2: float = 0.95
    conversion_probability_p3: float = 0.70
    conversion_probability_p4: float = 0.35
    include_open_incidents: bool = True
    include_resolved_incidents: bool = True
    minimum_schedule_delay_hours: int = 1
    maximum_schedule_delay_hours: int = 24
    minimum_start_delay_hours: int = 0
    maximum_start_delay_hours: int = 8
    minimum_duration_hours: int = 1
    maximum_duration_hours: int = 72
    minimum_estimated_labor_hours: float = 1.0
    maximum_estimated_labor_hours: float = 48.0
    labor_variance_ratio: float = 0.20
    cost_per_labor_hour: float = 50.0
    material_cost_ratio: float = 0.35
    cost_variance_ratio: float = 0.15
    cancellation_probability: float = 0.02
    schema_version: str = "1.0.0"

    def __post_init__(self) -> None:
        schema_version = self.schema_version.strip()
        object.__setattr__(self, "schema_version", schema_version)

        if isinstance(self.random_seed, bool) or not isinstance(self.random_seed, int):
            raise TypeError("random_seed must be an integer.")
        if self.random_seed < 0:
            raise ValueError("random_seed must be non-negative.")

        for name in (
            "conversion_probability_p1",
            "conversion_probability_p2",
            "conversion_probability_p3",
            "conversion_probability_p4",
            "cancellation_probability",
        ):
            _validate_probability(name, getattr(self, name))

        for name in (
            "minimum_schedule_delay_hours",
            "maximum_schedule_delay_hours",
            "minimum_start_delay_hours",
            "maximum_start_delay_hours",
            "minimum_duration_hours",
            "maximum_duration_hours",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer.")
            if value < 0:
                raise ValueError(f"{name} must be non-negative.")

        for minimum, maximum in (
            (
                "minimum_schedule_delay_hours",
                "maximum_schedule_delay_hours",
            ),
            (
                "minimum_start_delay_hours",
                "maximum_start_delay_hours",
            ),
            ("minimum_duration_hours", "maximum_duration_hours"),
        ):
            if getattr(self, maximum) < getattr(self, minimum):
                raise ValueError(
                    f"{maximum} must be greater than or equal to {minimum}."
                )

        for name in (
            "minimum_estimated_labor_hours",
            "maximum_estimated_labor_hours",
            "labor_variance_ratio",
            "cost_per_labor_hour",
            "material_cost_ratio",
            "cost_variance_ratio",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be numeric.")
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite.")
            if value < 0:
                raise ValueError(f"{name} must be non-negative.")

        if self.maximum_estimated_labor_hours < self.minimum_estimated_labor_hours:
            raise ValueError(
                "maximum_estimated_labor_hours must be greater than or equal "
                "to minimum_estimated_labor_hours."
            )
        if self.labor_variance_ratio > 1.0:
            raise ValueError("labor_variance_ratio must not exceed 1.0.")
        if self.cost_variance_ratio > 1.0:
            raise ValueError("cost_variance_ratio must not exceed 1.0.")

        for name in ("include_open_incidents", "include_resolved_incidents"):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be a boolean.")
        if not schema_version:
            raise ValueError("schema_version cannot be empty.")


@dataclass(frozen=True, slots=True)
class WorkOrderGenerationSummary:
    input_incident_count: int
    eligible_incident_count: int
    generated_work_order_count: int
    skipped_incident_count: int
    cancelled_work_order_count: int

    def to_record(self) -> dict[str, int]:
        return {
            "input_incident_count": self.input_incident_count,
            "eligible_incident_count": self.eligible_incident_count,
            "generated_work_order_count": self.generated_work_order_count,
            "skipped_incident_count": self.skipped_incident_count,
            "cancelled_work_order_count": self.cancelled_work_order_count,
        }


@dataclass(frozen=True, slots=True)
class WorkOrderGenerationResult:
    frame: pd.DataFrame
    summary: WorkOrderGenerationSummary


def generate_work_orders(
    incidents: pd.DataFrame,
    config: WorkOrderOperationsConfig | None = None,
    random_context: _RandomContextProtocol | None = None,
) -> pd.DataFrame:
    return generate_work_order_result(
        incidents,
        config=config,
        random_context=random_context,
    ).frame


def generate_work_order_result(
    incidents: pd.DataFrame,
    config: WorkOrderOperationsConfig | None = None,
    random_context: _RandomContextProtocol | None = None,
) -> WorkOrderGenerationResult:
    cfg = config or WorkOrderOperationsConfig()
    frame = _normalize_incidents_frame(incidents)

    eligible_mask = pd.Series(True, index=frame.index)
    if not cfg.include_open_incidents:
        eligible_mask &= ~frame["is_open"].astype(bool)
    if not cfg.include_resolved_incidents:
        eligible_mask &= frame["is_open"].astype(bool)
    eligible = frame.loc[eligible_mask].copy()

    records: list[dict[str, object]] = []
    skipped = 0
    cancelled = 0

    for row in eligible.to_dict(orient="records"):
        rng = _generator(
            cfg,
            random_context,
            "operations.work_orders",
            str(row["incident_id"]),
        )
        probability = {
            "p1": cfg.conversion_probability_p1,
            "p2": cfg.conversion_probability_p2,
            "p3": cfg.conversion_probability_p3,
            "p4": cfg.conversion_probability_p4,
        }.get(str(row["priority"]).lower(), 0.0)
        if float(rng.random()) >= probability:
            skipped += 1
            continue

        record = _build_record(row, cfg, rng)
        records.append(record)
        cancelled += int(record["status"] == WorkOrderStatus.CANCELLED.value)

    records.sort(
        key=lambda item: (
            item["created_at"],
            item["plant_id"],
            item["equipment_id"],
            item["linked_incident_id"],
        )
    )
    for index, record in enumerate(records, start=1):
        record["work_order_id"] = f"WO-{index:07d}"

    output = pd.DataFrame.from_records(records, columns=_output_columns())
    if not output.empty:
        for column in (
            "created_at",
            "scheduled_at",
            "started_at",
            "completed_at",
            "cancelled_at",
        ):
            output[column] = pd.to_datetime(output[column], utc=True)
        output = output.sort_values(
            ["created_at", "plant_id", "work_order_id"],
            kind="stable",
        ).reset_index(drop=True)

    return WorkOrderGenerationResult(
        frame=output,
        summary=WorkOrderGenerationSummary(
            input_incident_count=len(frame),
            eligible_incident_count=len(eligible),
            generated_work_order_count=len(output),
            skipped_incident_count=skipped,
            cancelled_work_order_count=cancelled,
        ),
    )


def work_orders_to_domain_models(
    work_orders: pd.DataFrame,
) -> tuple[WorkOrder, ...]:
    required = {
        "work_order_id",
        "plant_id",
        "equipment_id",
        "work_order_name",
        "work_order_type",
        "priority",
        "created_at",
        "status",
        "linked_incident_id",
        "assigned_team",
        "scheduled_at",
        "started_at",
        "completed_at",
        "cancelled_at",
        "estimated_labor_hours",
        "actual_labor_hours",
        "estimated_cost",
        "actual_cost",
        "description",
        "completion_notes",
        "is_synthetic_ground_truth",
    }
    missing = required.difference(work_orders.columns)
    if missing:
        raise ValueError(
            f"work_orders DataFrame is missing columns: {sorted(missing)}."
        )

    result: list[WorkOrder] = []
    for row in work_orders.to_dict(orient="records"):
        result.append(
            WorkOrder(
                work_order_id=str(row["work_order_id"]),
                plant_id=str(row["plant_id"]),
                equipment_id=str(row["equipment_id"]),
                work_order_name=str(row["work_order_name"]),
                work_order_type=WorkOrderType(str(row["work_order_type"])),
                priority=WorkOrderPriority(str(row["priority"])),
                created_at=_required_timestamp(row["created_at"], "created_at"),
                status=WorkOrderStatus(str(row["status"])),
                linked_incident_id=_nullable_text(row["linked_incident_id"]),
                assigned_team=_nullable_text(row["assigned_team"]),
                scheduled_at=_optional_timestamp(row["scheduled_at"]),
                started_at=_optional_timestamp(row["started_at"]),
                completed_at=_optional_timestamp(row["completed_at"]),
                cancelled_at=_optional_timestamp(row["cancelled_at"]),
                estimated_labor_hours=_nullable_float(row["estimated_labor_hours"]),
                actual_labor_hours=_nullable_float(row["actual_labor_hours"]),
                estimated_cost=_nullable_float(row["estimated_cost"]),
                actual_cost=_nullable_float(row["actual_cost"]),
                description=_nullable_text(row["description"]),
                completion_notes=_nullable_text(row["completion_notes"]),
                is_synthetic_ground_truth=bool(row["is_synthetic_ground_truth"]),
            )
        )
    return tuple(result)


def _normalize_incidents_frame(incidents: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(incidents, pd.DataFrame):
        raise TypeError("incidents must be a pandas DataFrame.")

    required = {
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
        "resolved_at",
        "closed_at",
        "linked_alarm_ids",
        "ground_truth_event_id",
        "description",
        "root_cause",
        "is_open",
        "is_synthetic_ground_truth",
        "generation_run_id",
    }
    missing = required.difference(incidents.columns)
    if missing:
        raise ValueError(f"incidents DataFrame is missing columns: {sorted(missing)}.")

    frame = incidents.copy(deep=True)
    for column in (
        "occurred_at",
        "detected_at",
        "assigned_at",
        "resolved_at",
        "closed_at",
    ):
        frame[column] = pd.to_datetime(frame[column], utc=True, errors="coerce")

    if frame["incident_id"].duplicated().any():
        raise ValueError("incident_id values must be unique.")
    if frame["occurred_at"].isna().any():
        raise ValueError("occurred_at cannot contain missing values.")
    if frame["detected_at"].isna().any():
        raise ValueError("detected_at cannot contain missing values.")

    return frame.sort_values(
        ["occurred_at", "plant_id", "incident_id"],
        kind="stable",
    ).reset_index(drop=True)


def _build_record(
    incident: dict[str, object],
    cfg: WorkOrderOperationsConfig,
    rng: np.random.Generator,
) -> dict[str, object]:
    priority = {
        "p1": WorkOrderPriority.CRITICAL,
        "p2": WorkOrderPriority.HIGH,
        "p3": WorkOrderPriority.MEDIUM,
        "p4": WorkOrderPriority.LOW,
    }.get(str(incident["priority"]).lower(), WorkOrderPriority.MEDIUM)

    work_type = _work_type(incident)
    team = _team(incident)
    created_at = _first_timestamp(incident, "assigned_at", "detected_at", "occurred_at")
    scheduled_at = created_at + timedelta(
        hours=_sample_int(
            rng,
            cfg.minimum_schedule_delay_hours,
            cfg.maximum_schedule_delay_hours,
        )
    )
    started_at = scheduled_at + timedelta(
        hours=_sample_int(
            rng,
            cfg.minimum_start_delay_hours,
            cfg.maximum_start_delay_hours,
        )
    )
    duration = _sample_int(rng, cfg.minimum_duration_hours, cfg.maximum_duration_hours)
    planned_end = started_at + timedelta(hours=duration)

    estimated_labor = round(
        float(
            rng.uniform(
                cfg.minimum_estimated_labor_hours,
                cfg.maximum_estimated_labor_hours,
            )
        ),
        3,
    )
    estimated_cost = round(
        estimated_labor * cfg.cost_per_labor_hour * (1.0 + cfg.material_cost_ratio),
        2,
    )

    cancelled_at = None
    completed_at = None
    actual_labor = None
    actual_cost = None
    completion_notes = None

    if float(rng.random()) < cfg.cancellation_probability:
        status = WorkOrderStatus.CANCELLED
        cancelled_at = scheduled_at
        started_at = None
        completion_notes = "Work order cancelled before execution."
    elif _optional_timestamp(incident["resolved_at"]) is not None:
        status = WorkOrderStatus.COMPLETED
        completed_at = max(
            planned_end,
            _optional_timestamp(incident["closed_at"])
            or _required_timestamp(incident["resolved_at"], "resolved_at"),
        )
        actual_labor = round(
            max(
                0.0,
                estimated_labor
                * (
                    1.0
                    + float(
                        rng.uniform(
                            -cfg.labor_variance_ratio,
                            cfg.labor_variance_ratio,
                        )
                    )
                ),
            ),
            3,
        )
        actual_cost = round(
            max(
                0.0,
                estimated_cost
                * (
                    1.0
                    + float(
                        rng.uniform(
                            -cfg.cost_variance_ratio,
                            cfg.cost_variance_ratio,
                        )
                    )
                ),
            ),
            2,
        )
        completion_notes = "Maintenance action completed."
    elif bool(incident["is_open"]):
        status = WorkOrderStatus.IN_PROGRESS
    else:
        status = WorkOrderStatus.ASSIGNED
        started_at = None

    model = WorkOrder(
        work_order_id="WO-0000001",
        plant_id=str(incident["plant_id"]),
        equipment_id=str(incident["primary_equipment_id"]),
        work_order_name=(
            f"{work_type.value.replace('_', ' ').title()}: "
            f"{incident['incident_name']}"
        )[:150],
        work_order_type=work_type,
        priority=priority,
        created_at=created_at,
        status=status,
        linked_incident_id=str(incident["incident_id"]),
        assigned_team=team.value,
        scheduled_at=scheduled_at,
        started_at=started_at,
        completed_at=completed_at,
        cancelled_at=cancelled_at,
        estimated_labor_hours=estimated_labor,
        actual_labor_hours=actual_labor,
        estimated_cost=estimated_cost,
        actual_cost=actual_cost,
        description=_description(incident),
        completion_notes=completion_notes,
        is_synthetic_ground_truth=bool(incident["is_synthetic_ground_truth"]),
    )

    sla_target = {
        WorkOrderPriority.CRITICAL: 4.0,
        WorkOrderPriority.HIGH: 24.0,
        WorkOrderPriority.MEDIUM: 72.0,
        WorkOrderPriority.LOW: 168.0,
    }[priority]
    sla_end = completed_at or cancelled_at or started_at or scheduled_at
    sla_breached = ((sla_end - created_at).total_seconds() / 3600.0) > sla_target

    return {
        "work_order_id": model.work_order_id,
        "linked_incident_id": model.linked_incident_id,
        "plant_id": model.plant_id,
        "equipment_id": model.equipment_id,
        "work_order_name": model.work_order_name,
        "work_order_type": model.work_order_type.value,
        "priority": model.priority.value,
        "assigned_team": model.assigned_team,
        "status": model.status.value,
        "created_at": model.created_at,
        "scheduled_at": model.scheduled_at,
        "started_at": model.started_at,
        "completed_at": model.completed_at,
        "cancelled_at": model.cancelled_at,
        "estimated_labor_hours": model.estimated_labor_hours,
        "actual_labor_hours": model.actual_labor_hours,
        "estimated_cost": model.estimated_cost,
        "actual_cost": model.actual_cost,
        "description": model.description,
        "completion_notes": model.completion_notes,
        "is_open": model.is_open,
        "is_over_budget": model.is_over_budget,
        "labor_variance_hours": model.labor_variance_hours,
        "cost_variance": model.cost_variance,
        "completion_seconds": model.completion_seconds,
        "linked_alarm_ids": _alarm_ids(incident["linked_alarm_ids"]),
        "linked_alarm_count": len(_alarm_ids(incident["linked_alarm_ids"])),
        "ground_truth_event_id": _nullable_text(incident["ground_truth_event_id"]),
        "sla_target_hours": sla_target,
        "sla_breached": sla_breached,
        "is_synthetic_ground_truth": model.is_synthetic_ground_truth,
        "generation_run_id": str(incident["generation_run_id"]),
        "schema_version": cfg.schema_version,
    }


def _work_type(incident: dict[str, object]) -> WorkOrderType:
    severity = str(incident["severity"]).lower()
    category = str(incident["category"]).lower()
    if severity == "critical":
        return WorkOrderType.EMERGENCY
    if category in {"performance_degradation", "communication_failure"}:
        return WorkOrderType.INSPECTION
    if category == "planned_maintenance":
        return WorkOrderType.PREVENTIVE
    if bool(incident["is_open"]):
        return WorkOrderType.CORRECTIVE
    return WorkOrderType.PREDICTIVE


def _team(incident: dict[str, object]) -> MaintenanceTeam:
    owner = str(incident["owner_team"]).lower()
    return {
        "grid_operations": MaintenanceTeam.GRID,
        "network_operations": MaintenanceTeam.NETWORK,
        "performance_engineering": MaintenanceTeam.PERFORMANCE,
        "hse": MaintenanceTeam.HSE,
        "maintenance": MaintenanceTeam.GENERAL,
        "plant_operations": MaintenanceTeam.GENERAL,
    }.get(owner, MaintenanceTeam.ELECTRICAL)


def _description(incident: dict[str, object]) -> str:
    parts = [f"Created from incident {incident['incident_id']}."]
    root_cause = _nullable_text(incident["root_cause"])
    description = _nullable_text(incident["description"])
    if root_cause:
        parts.append(f"Root cause: {root_cause}.")
    if description:
        parts.append(description)
    return " ".join(parts)[:1000]


def _alarm_ids(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value.strip().upper(),)
    if isinstance(value, (tuple, list, set)):
        return tuple(
            sorted({str(item).strip().upper() for item in value if str(item).strip()})
        )
    if value is None or pd.isna(value):
        return ()
    return (str(value).strip().upper(),)


def _first_timestamp(row: dict[str, object], *fields: str) -> datetime:
    for field in fields:
        value = _optional_timestamp(row.get(field))
        if value is not None:
            return value
    raise ValueError("Incident has no usable lifecycle timestamp.")


def _sample_int(rng: np.random.Generator, minimum: int, maximum: int) -> int:
    if minimum == maximum:
        return minimum
    return int(rng.integers(minimum, maximum + 1))


def _generator(
    cfg: WorkOrderOperationsConfig,
    random_context: _RandomContextProtocol | None,
    stream_name: str,
    entity_id: str,
) -> np.random.Generator:
    if random_context is not None:
        return random_context.generator(stream_name, entity_id=entity_id)
    digest = hashlib.sha256(
        f"{cfg.random_seed}|{stream_name}|{entity_id}".encode()
    ).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "big", signed=False))


def _validate_probability(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric.")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0.")


def _optional_timestamp(value: object) -> datetime | None:
    if value is None or pd.isna(value):
        return None
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise ValueError("Timestamps must be timezone-aware.")
    return timestamp.to_pydatetime().astimezone(UTC)


def _required_timestamp(value: object, name: str) -> datetime:
    timestamp = _optional_timestamp(value)
    if timestamp is None:
        raise ValueError(f"{name} cannot be missing.")
    return timestamp


def _nullable_text(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    return str(value)


def _nullable_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _output_columns() -> tuple[str, ...]:
    return (
        "work_order_id",
        "linked_incident_id",
        "plant_id",
        "equipment_id",
        "work_order_name",
        "work_order_type",
        "priority",
        "assigned_team",
        "status",
        "created_at",
        "scheduled_at",
        "started_at",
        "completed_at",
        "cancelled_at",
        "estimated_labor_hours",
        "actual_labor_hours",
        "estimated_cost",
        "actual_cost",
        "description",
        "completion_notes",
        "is_open",
        "is_over_budget",
        "labor_variance_hours",
        "cost_variance",
        "completion_seconds",
        "linked_alarm_ids",
        "linked_alarm_count",
        "ground_truth_event_id",
        "sla_target_hours",
        "sla_breached",
        "is_synthetic_ground_truth",
        "generation_run_id",
        "schema_version",
    )


__all__ = [
    "MaintenanceTeam",
    "WorkOrderGenerationResult",
    "WorkOrderGenerationSummary",
    "WorkOrderOperationsConfig",
    "generate_work_order_result",
    "generate_work_orders",
    "work_orders_to_domain_models",
]
