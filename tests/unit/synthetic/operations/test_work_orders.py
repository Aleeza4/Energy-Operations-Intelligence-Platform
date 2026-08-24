"""
Unit tests for EOIP operational work-order generation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from eoip.synthetic.models.work_order import (
    WorkOrderPriority,
    WorkOrderStatus,
    WorkOrderType,
)
from eoip.synthetic.operations.work_orders import (
    MaintenanceTeam,
    WorkOrderOperationsConfig,
    generate_work_order_result,
    generate_work_orders,
    work_orders_to_domain_models,
)


def _incident_row(
    *,
    incident_id: str = "INC-0000001",
    plant_id: str = "PLANT-001",
    equipment_id: str = "EQP-00001",
    incident_name: str = "Inverter Trip Incident",
    category: str = "equipment_failure",
    severity: str = "high",
    priority: str = "p2",
    status: str = "resolved",
    owner_team: str = "maintenance",
    occurred_at: datetime | None = None,
    detected_at: datetime | None = None,
    assigned_at: datetime | None = None,
    resolved_at: datetime | pd.Timestamp | None = None,
    closed_at: datetime | pd.Timestamp | None = None,
    linked_alarm_ids: tuple[str, ...] = ("ALM-0000001",),
    ground_truth_event_id: str | None = "GTE-2026-00000001",
    description: str = "Operational incident from inverter trip.",
    root_cause: str = "Inverter Trip",
    is_open: bool = False,
    is_synthetic_ground_truth: bool = True,
    generation_run_id: str = "RUN-TEST",
) -> dict[str, object]:
    """Return one valid incident-output record."""
    occurred = occurred_at or datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    detected = detected_at or occurred + timedelta(minutes=1)
    assigned = assigned_at or detected + timedelta(minutes=2)
    resolved = resolved_at if resolved_at is not None else occurred + timedelta(hours=2)
    closed = closed_at if closed_at is not None else occurred + timedelta(hours=3)

    return {
        "incident_id": incident_id,
        "plant_id": plant_id,
        "primary_equipment_id": equipment_id,
        "incident_name": incident_name,
        "category": category,
        "severity": severity,
        "priority": priority,
        "status": status,
        "owner_team": owner_team,
        "occurred_at": occurred,
        "detected_at": detected,
        "assigned_at": assigned,
        "resolved_at": resolved,
        "closed_at": closed,
        "linked_alarm_ids": linked_alarm_ids,
        "ground_truth_event_id": ground_truth_event_id,
        "description": description,
        "root_cause": root_cause,
        "is_open": is_open,
        "is_synthetic_ground_truth": is_synthetic_ground_truth,
        "generation_run_id": generation_run_id,
    }


def _incidents_frame(*rows: dict[str, object]) -> pd.DataFrame:
    """Return a DataFrame using the work-order input contract."""
    return pd.DataFrame(list(rows or (_incident_row(),)))


def _config(**overrides: object) -> WorkOrderOperationsConfig:
    """Return deterministic work-order settings."""
    data: dict[str, object] = {
        "random_seed": 42,
        "conversion_probability_p1": 1.0,
        "conversion_probability_p2": 1.0,
        "conversion_probability_p3": 1.0,
        "conversion_probability_p4": 1.0,
        "include_open_incidents": True,
        "include_resolved_incidents": True,
        "minimum_schedule_delay_hours": 1,
        "maximum_schedule_delay_hours": 1,
        "minimum_start_delay_hours": 1,
        "maximum_start_delay_hours": 1,
        "minimum_duration_hours": 2,
        "maximum_duration_hours": 2,
        "minimum_estimated_labor_hours": 8.0,
        "maximum_estimated_labor_hours": 8.0,
        "labor_variance_ratio": 0.0,
        "cost_per_labor_hour": 50.0,
        "material_cost_ratio": 0.25,
        "cost_variance_ratio": 0.0,
        "cancellation_probability": 0.0,
        "schema_version": "1.0.0",
    }
    data.update(overrides)
    return WorkOrderOperationsConfig(**data)


def test_config_defaults() -> None:
    config = WorkOrderOperationsConfig()

    assert config.random_seed == 20250201
    assert config.include_open_incidents is True
    assert config.include_resolved_incidents is True
    assert config.schema_version == "1.0.0"


@pytest.mark.parametrize(
    "field_name",
    [
        "conversion_probability_p1",
        "conversion_probability_p2",
        "conversion_probability_p3",
        "conversion_probability_p4",
        "cancellation_probability",
    ],
)
@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_config_rejects_probability_outside_bounds(
    field_name: str,
    value: float,
) -> None:
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        WorkOrderOperationsConfig(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "conversion_probability_p1",
        "conversion_probability_p2",
        "conversion_probability_p3",
        "conversion_probability_p4",
        "cancellation_probability",
    ],
)
@pytest.mark.parametrize("value", [True, "0.5", None])
def test_config_rejects_non_numeric_probability(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(TypeError, match=f"{field_name} must be numeric"):
        WorkOrderOperationsConfig(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "minimum_schedule_delay_hours",
        "maximum_schedule_delay_hours",
        "minimum_start_delay_hours",
        "maximum_start_delay_hours",
        "minimum_duration_hours",
        "maximum_duration_hours",
    ],
)
@pytest.mark.parametrize("value", [True, 1.5, "1", None])
def test_config_rejects_non_integer_fields(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(TypeError, match=f"{field_name} must be an integer"):
        WorkOrderOperationsConfig(**{field_name: value})


@pytest.mark.parametrize(
    ("minimum_name", "maximum_name"),
    [
        (
            "minimum_schedule_delay_hours",
            "maximum_schedule_delay_hours",
        ),
        (
            "minimum_start_delay_hours",
            "maximum_start_delay_hours",
        ),
        ("minimum_duration_hours", "maximum_duration_hours"),
    ],
)
def test_config_rejects_reversed_integer_bounds(
    minimum_name: str,
    maximum_name: str,
) -> None:
    with pytest.raises(ValueError, match=maximum_name):
        WorkOrderOperationsConfig(
            **{
                minimum_name: 10,
                maximum_name: 5,
            }
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "minimum_estimated_labor_hours",
        "maximum_estimated_labor_hours",
        "labor_variance_ratio",
        "cost_per_labor_hour",
        "material_cost_ratio",
        "cost_variance_ratio",
    ],
)
@pytest.mark.parametrize("value", [True, "10", None])
def test_config_rejects_non_numeric_cost_fields(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(TypeError, match=f"{field_name} must be numeric"):
        WorkOrderOperationsConfig(**{field_name: value})


def test_config_rejects_reversed_labor_bounds() -> None:
    with pytest.raises(
        ValueError,
        match="maximum_estimated_labor_hours",
    ):
        WorkOrderOperationsConfig(
            minimum_estimated_labor_hours=10.0,
            maximum_estimated_labor_hours=5.0,
        )


@pytest.mark.parametrize(
    "field_name",
    ["labor_variance_ratio", "cost_variance_ratio"],
)
def test_config_rejects_variance_above_one(field_name: str) -> None:
    with pytest.raises(ValueError, match="must not exceed 1.0"):
        WorkOrderOperationsConfig(**{field_name: 1.1})


@pytest.mark.parametrize(
    "field_name",
    ["include_open_incidents", "include_resolved_incidents"],
)
def test_config_requires_boolean_flags(field_name: str) -> None:
    with pytest.raises(TypeError, match=f"{field_name} must be a boolean"):
        WorkOrderOperationsConfig(**{field_name: 1})


def test_generate_work_orders_returns_expected_columns() -> None:
    frame = generate_work_orders(
        _incidents_frame(),
        config=_config(),
    )

    assert list(frame.columns) == [
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
    ]


def test_resolved_incident_generates_completed_work_order() -> None:
    frame = generate_work_orders(
        _incidents_frame(),
        config=_config(),
    )

    assert len(frame) == 1
    row = frame.iloc[0]
    assert row["work_order_id"] == "WO-0000001"
    assert row["linked_incident_id"] == "INC-0000001"
    assert row["status"] == WorkOrderStatus.COMPLETED.value
    assert row["priority"] == WorkOrderPriority.HIGH.value
    assert row["work_order_type"] == WorkOrderType.PREDICTIVE.value
    assert row["is_open"] == False  # noqa: E712


def test_open_incident_generates_in_progress_work_order() -> None:
    incident = _incident_row(
        status="investigating",
        resolved_at=pd.NaT,
        closed_at=pd.NaT,
        is_open=True,
    )

    frame = generate_work_orders(
        _incidents_frame(incident),
        config=_config(),
    )

    assert frame.loc[0, "status"] == WorkOrderStatus.IN_PROGRESS.value
    assert frame.loc[0, "work_order_type"] == WorkOrderType.CORRECTIVE.value
    assert pd.notna(frame.loc[0, "started_at"])
    assert pd.isna(frame.loc[0, "completed_at"])


def test_non_open_unresolved_incident_generates_assigned_work_order() -> None:
    incident = _incident_row(
        status="assigned",
        resolved_at=pd.NaT,
        closed_at=pd.NaT,
        is_open=False,
    )

    frame = generate_work_orders(
        _incidents_frame(incident),
        config=_config(),
    )

    assert frame.loc[0, "status"] == WorkOrderStatus.ASSIGNED.value
    assert pd.isna(frame.loc[0, "started_at"])
    assert pd.isna(frame.loc[0, "completed_at"])


@pytest.mark.parametrize(
    ("incident_priority", "expected_priority", "expected_sla"),
    [
        ("p1", WorkOrderPriority.CRITICAL, 4.0),
        ("p2", WorkOrderPriority.HIGH, 24.0),
        ("p3", WorkOrderPriority.MEDIUM, 72.0),
        ("p4", WorkOrderPriority.LOW, 168.0),
    ],
)
def test_priority_and_sla_mapping(
    incident_priority: str,
    expected_priority: WorkOrderPriority,
    expected_sla: float,
) -> None:
    frame = generate_work_orders(
        _incidents_frame(_incident_row(priority=incident_priority)),
        config=_config(),
    )

    assert frame.loc[0, "priority"] == expected_priority.value
    assert frame.loc[0, "sla_target_hours"] == expected_sla


@pytest.mark.parametrize(
    ("category", "severity", "is_open", "expected_type"),
    [
        (
            "equipment_failure",
            "critical",
            True,
            WorkOrderType.EMERGENCY,
        ),
        (
            "performance_degradation",
            "moderate",
            False,
            WorkOrderType.INSPECTION,
        ),
        (
            "communication_failure",
            "high",
            False,
            WorkOrderType.INSPECTION,
        ),
        (
            "planned_maintenance",
            "moderate",
            False,
            WorkOrderType.PREVENTIVE,
        ),
        (
            "equipment_failure",
            "high",
            True,
            WorkOrderType.CORRECTIVE,
        ),
        (
            "equipment_failure",
            "high",
            False,
            WorkOrderType.PREDICTIVE,
        ),
    ],
)
def test_work_order_type_mapping(
    category: str,
    severity: str,
    is_open: bool,
    expected_type: WorkOrderType,
) -> None:
    frame = generate_work_orders(
        _incidents_frame(
            _incident_row(
                category=category,
                severity=severity,
                is_open=is_open,
                resolved_at=(
                    pd.NaT if is_open else datetime(2026, 1, 1, 14, 0, tzinfo=UTC)
                ),
                closed_at=(
                    pd.NaT if is_open else datetime(2026, 1, 1, 15, 0, tzinfo=UTC)
                ),
            )
        ),
        config=_config(),
    )

    assert frame.loc[0, "work_order_type"] == expected_type.value


@pytest.mark.parametrize(
    ("owner_team", "expected_team"),
    [
        ("grid_operations", MaintenanceTeam.GRID),
        ("network_operations", MaintenanceTeam.NETWORK),
        ("performance_engineering", MaintenanceTeam.PERFORMANCE),
        ("hse", MaintenanceTeam.HSE),
        ("maintenance", MaintenanceTeam.GENERAL),
        ("plant_operations", MaintenanceTeam.GENERAL),
        ("unknown", MaintenanceTeam.ELECTRICAL),
    ],
)
def test_team_mapping(
    owner_team: str,
    expected_team: MaintenanceTeam,
) -> None:
    frame = generate_work_orders(
        _incidents_frame(_incident_row(owner_team=owner_team)),
        config=_config(),
    )

    assert frame.loc[0, "assigned_team"] == expected_team.value


def test_lifecycle_timestamps_use_configured_delays() -> None:
    incident = _incident_row(
        assigned_at=datetime(2026, 1, 1, 12, 3, tzinfo=UTC),
        resolved_at=datetime(2026, 1, 1, 14, 0, tzinfo=UTC),
        closed_at=datetime(2026, 1, 1, 15, 0, tzinfo=UTC),
    )

    frame = generate_work_orders(
        _incidents_frame(incident),
        config=_config(),
    )

    assert frame.loc[0, "created_at"] == pd.Timestamp(
        datetime(2026, 1, 1, 12, 3, tzinfo=UTC)
    )
    assert frame.loc[0, "scheduled_at"] == pd.Timestamp(
        datetime(2026, 1, 1, 13, 3, tzinfo=UTC)
    )
    assert frame.loc[0, "started_at"] == pd.Timestamp(
        datetime(2026, 1, 1, 14, 3, tzinfo=UTC)
    )
    assert frame.loc[0, "completed_at"] == pd.Timestamp(
        datetime(2026, 1, 1, 16, 3, tzinfo=UTC)
    )


def test_labor_and_cost_are_calculated() -> None:
    frame = generate_work_orders(
        _incidents_frame(),
        config=_config(),
    )

    assert frame.loc[0, "estimated_labor_hours"] == 8.0
    assert frame.loc[0, "actual_labor_hours"] == 8.0
    assert frame.loc[0, "estimated_cost"] == 500.0
    assert frame.loc[0, "actual_cost"] == 500.0
    assert frame.loc[0, "labor_variance_hours"] == 0.0
    assert frame.loc[0, "cost_variance"] == 0.0
    assert frame.loc[0, "is_over_budget"] == False  # noqa: E712


def test_cancellation_workflow() -> None:
    frame = generate_work_orders(
        _incidents_frame(),
        config=_config(cancellation_probability=1.0),
    )

    assert frame.loc[0, "status"] == WorkOrderStatus.CANCELLED.value
    assert pd.notna(frame.loc[0, "cancelled_at"])
    assert pd.isna(frame.loc[0, "started_at"])
    assert pd.isna(frame.loc[0, "completed_at"])
    assert frame.loc[0, "completion_notes"] == (
        "Work order cancelled before execution."
    )


def test_open_incidents_can_be_excluded() -> None:
    incident = _incident_row(
        is_open=True,
        resolved_at=pd.NaT,
        closed_at=pd.NaT,
    )

    result = generate_work_order_result(
        _incidents_frame(incident),
        config=_config(include_open_incidents=False),
    )

    assert result.frame.empty
    assert result.summary.eligible_incident_count == 0


def test_resolved_incidents_can_be_excluded() -> None:
    result = generate_work_order_result(
        _incidents_frame(),
        config=_config(include_resolved_incidents=False),
    )

    assert result.frame.empty
    assert result.summary.eligible_incident_count == 0


def test_conversion_probability_can_skip_incident() -> None:
    result = generate_work_order_result(
        _incidents_frame(_incident_row(priority="p2")),
        config=_config(conversion_probability_p2=0.0),
    )

    assert result.frame.empty
    assert result.summary.skipped_incident_count == 1


def test_generation_summary_counts_records() -> None:
    first = _incident_row(incident_id="INC-0000001")
    second = _incident_row(
        incident_id="INC-0000002",
        equipment_id="EQP-00002",
        priority="p4",
    )

    result = generate_work_order_result(
        _incidents_frame(first, second),
        config=_config(conversion_probability_p4=0.0),
    )

    assert result.summary.to_record() == {
        "input_incident_count": 2,
        "eligible_incident_count": 2,
        "generated_work_order_count": 1,
        "skipped_incident_count": 1,
        "cancelled_work_order_count": 0,
    }


def test_linked_alarm_lineage_is_preserved() -> None:
    frame = generate_work_orders(
        _incidents_frame(
            _incident_row(
                linked_alarm_ids=(
                    "ALM-0000002",
                    "ALM-0000001",
                )
            )
        ),
        config=_config(),
    )

    assert frame.loc[0, "linked_alarm_ids"] == (
        "ALM-0000001",
        "ALM-0000002",
    )
    assert frame.loc[0, "linked_alarm_count"] == 2
    assert frame.loc[0, "ground_truth_event_id"] == "GTE-2026-00000001"


def test_work_order_ids_follow_stable_order() -> None:
    later = _incident_row(
        incident_id="INC-0000002",
        equipment_id="EQP-00002",
        occurred_at=datetime(2026, 1, 1, 13, 0, tzinfo=UTC),
        detected_at=datetime(2026, 1, 1, 13, 1, tzinfo=UTC),
        assigned_at=datetime(2026, 1, 1, 13, 3, tzinfo=UTC),
    )
    earlier = _incident_row(
        incident_id="INC-0000001",
        equipment_id="EQP-00001",
        occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        detected_at=datetime(2026, 1, 1, 12, 1, tzinfo=UTC),
        assigned_at=datetime(2026, 1, 1, 12, 3, tzinfo=UTC),
    )

    frame = generate_work_orders(
        _incidents_frame(later, earlier),
        config=_config(),
    )

    assert frame["work_order_id"].tolist() == [
        "WO-0000001",
        "WO-0000002",
    ]
    assert frame["equipment_id"].tolist() == [
        "EQP-00001",
        "EQP-00002",
    ]


def test_generation_is_deterministic() -> None:
    incidents = _incidents_frame(
        _incident_row(incident_id="INC-0000001"),
        _incident_row(
            incident_id="INC-0000002",
            equipment_id="EQP-00002",
        ),
    )
    config = WorkOrderOperationsConfig(
        random_seed=99,
        conversion_probability_p1=1.0,
        conversion_probability_p2=1.0,
        conversion_probability_p3=1.0,
        conversion_probability_p4=1.0,
        cancellation_probability=0.0,
    )

    first = generate_work_orders(incidents, config=config)
    second = generate_work_orders(incidents, config=config)

    pd.testing.assert_frame_equal(first, second)


def test_description_contains_incident_and_root_cause() -> None:
    frame = generate_work_orders(
        _incidents_frame(),
        config=_config(),
    )

    assert "INC-0000001" in frame.loc[0, "description"]
    assert "Root cause: Inverter Trip." in frame.loc[0, "description"]


def test_work_orders_round_trip_to_domain_models() -> None:
    frame = generate_work_orders(
        _incidents_frame(),
        config=_config(),
    )

    models = work_orders_to_domain_models(frame)

    assert len(models) == 1
    work_order = models[0]
    assert work_order.work_order_id == "WO-0000001"
    assert work_order.linked_incident_id == "INC-0000001"
    assert work_order.status is WorkOrderStatus.COMPLETED


def test_domain_conversion_rejects_missing_columns() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        work_orders_to_domain_models(pd.DataFrame({"work_order_id": ["WO-0000001"]}))


def test_input_must_be_dataframe() -> None:
    with pytest.raises(TypeError, match="pandas DataFrame"):
        generate_work_orders(  # type: ignore[arg-type]
            [],
            config=_config(),
        )


def test_missing_incident_columns_are_rejected() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        generate_work_orders(
            pd.DataFrame({"incident_id": ["INC-0000001"]}),
            config=_config(),
        )


def test_duplicate_incident_ids_are_rejected() -> None:
    duplicated = _incidents_frame(
        _incident_row(),
        _incident_row(equipment_id="EQP-00002"),
    )

    with pytest.raises(ValueError, match="must be unique"):
        generate_work_orders(
            duplicated,
            config=_config(),
        )


def test_missing_occurred_at_is_rejected() -> None:
    row = _incident_row()
    row["occurred_at"] = pd.NaT

    with pytest.raises(ValueError, match="occurred_at"):
        generate_work_orders(
            _incidents_frame(row),
            config=_config(),
        )


def test_missing_detected_at_is_rejected() -> None:
    row = _incident_row()
    row["detected_at"] = pd.NaT

    with pytest.raises(ValueError, match="detected_at"):
        generate_work_orders(
            _incidents_frame(row),
            config=_config(),
        )


def test_empty_incident_frame_returns_empty_contract() -> None:
    empty = _incidents_frame().iloc[0:0]

    result = generate_work_order_result(
        empty,
        config=_config(),
    )

    assert result.frame.empty
    assert len(result.frame.columns) == 33
    assert result.summary.input_incident_count == 0
    assert result.summary.generated_work_order_count == 0


def test_output_datetime_columns_are_utc_aware() -> None:
    frame = generate_work_orders(
        _incidents_frame(),
        config=_config(),
    )

    for column in (
        "created_at",
        "scheduled_at",
        "started_at",
        "completed_at",
        "cancelled_at",
    ):
        assert isinstance(frame[column].dtype, pd.DatetimeTZDtype)
        assert str(frame[column].dt.tz) == "UTC"
