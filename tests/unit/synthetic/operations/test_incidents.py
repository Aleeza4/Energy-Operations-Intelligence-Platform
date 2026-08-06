"""
Unit tests for EOIP operational incident generation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from eoip.synthetic.models.incident import (
    IncidentCategory,
    IncidentSeverity,
    IncidentStatus,
)
from eoip.synthetic.operations.incidents import (
    IncidentOperationsConfig,
    IncidentOwnershipTeam,
    IncidentPriority,
    generate_incident_result,
    generate_incidents,
    incidents_to_domain_models,
)


def _alarm_row(
    *,
    alarm_id: str = "ALM-0000001",
    plant_id: str = "PLANT-001",
    equipment_id: str = "EQP-00001",
    ground_truth_event_id: str | None = "GTE-2026-00000001",
    alarm_code: str = "INV-TRIP-001",
    alarm_name: str = "Inverter Trip",
    category: str = "equipment",
    severity: str = "major",
    raised_at: datetime | None = None,
    status: str = "cleared",
    acknowledged_at: datetime | None = None,
    cleared_at: datetime | None = None,
    message: str = "Inverter trip detected.",
    is_nuisance: bool = False,
    incident_eligible: bool = True,
    event_type: str = "inverter_trip",
    event_start_at_utc: datetime | None = None,
    event_end_at_utc: datetime | None = None,
    generation_run_id: str = "RUN-TEST",
    is_synthetic_ground_truth: bool = True,
) -> dict[str, object]:
    """Return one valid alarm-output record."""
    raised = raised_at or datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    acknowledged = acknowledged_at or raised + timedelta(minutes=2)
    cleared = cleared_at or raised + timedelta(minutes=30)
    event_start = event_start_at_utc or raised - timedelta(minutes=5)
    event_end = event_end_at_utc or cleared - timedelta(minutes=5)

    return {
        "alarm_id": alarm_id,
        "plant_id": plant_id,
        "equipment_id": equipment_id,
        "ground_truth_event_id": ground_truth_event_id,
        "alarm_code": alarm_code,
        "alarm_name": alarm_name,
        "category": category,
        "severity": severity,
        "raised_at": raised,
        "status": status,
        "acknowledged_at": acknowledged,
        "cleared_at": cleared,
        "message": message,
        "is_nuisance": is_nuisance,
        "incident_eligible": incident_eligible,
        "event_type": event_type,
        "event_start_at_utc": event_start,
        "event_end_at_utc": event_end,
        "generation_run_id": generation_run_id,
        "is_synthetic_ground_truth": is_synthetic_ground_truth,
    }


def _alarms_frame(*rows: dict[str, object]) -> pd.DataFrame:
    """Return a DataFrame using the incident input contract."""
    return pd.DataFrame(list(rows or (_alarm_row(),)))


def _deterministic_config(
    **overrides: object,
) -> IncidentOperationsConfig:
    """Return fully deterministic incident-generation settings."""
    data: dict[str, object] = {
        "random_seed": 42,
        "grouping_window_minutes": 30,
        "detection_delay_min_minutes": 1,
        "detection_delay_max_minutes": 1,
        "assignment_delay_min_minutes": 2,
        "assignment_delay_max_minutes": 2,
        "investigation_delay_min_minutes": 3,
        "investigation_delay_max_minutes": 3,
        "restoration_delay_min_minutes": 4,
        "restoration_delay_max_minutes": 4,
        "closure_delay_min_minutes": 5,
        "closure_delay_max_minutes": 5,
        "conversion_probability_warning": 1.0,
        "conversion_probability_major": 1.0,
        "conversion_probability_critical": 1.0,
        "include_informational_incidents": False,
        "group_by_ground_truth_event": True,
        "schema_version": "1.0.0",
    }
    data.update(overrides)
    return IncidentOperationsConfig(**data)


def test_config_defaults() -> None:
    config = IncidentOperationsConfig()

    assert config.random_seed == 20250201
    assert config.grouping_window_minutes == 30
    assert config.group_by_ground_truth_event is True
    assert config.schema_version == "1.0.0"


@pytest.mark.parametrize(
    "field_name",
    [
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
    ],
)
@pytest.mark.parametrize("value", [True, 1.5, "1", None])
def test_config_rejects_non_integer_values(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(TypeError, match=f"{field_name} must be an integer"):
        IncidentOperationsConfig(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "grouping_window_minutes",
        "detection_delay_min_minutes",
        "assignment_delay_min_minutes",
        "investigation_delay_min_minutes",
        "restoration_delay_min_minutes",
        "closure_delay_min_minutes",
    ],
)
def test_config_rejects_negative_integers(field_name: str) -> None:
    with pytest.raises(ValueError, match=f"{field_name} must be non-negative"):
        IncidentOperationsConfig(**{field_name: -1})


@pytest.mark.parametrize(
    ("minimum_name", "maximum_name"),
    [
        ("detection_delay_min_minutes", "detection_delay_max_minutes"),
        ("assignment_delay_min_minutes", "assignment_delay_max_minutes"),
        (
            "investigation_delay_min_minutes",
            "investigation_delay_max_minutes",
        ),
        ("restoration_delay_min_minutes", "restoration_delay_max_minutes"),
        ("closure_delay_min_minutes", "closure_delay_max_minutes"),
    ],
)
def test_config_rejects_reversed_delay_bounds(
    minimum_name: str,
    maximum_name: str,
) -> None:
    with pytest.raises(ValueError, match=maximum_name):
        IncidentOperationsConfig(
            **{
                minimum_name: 10,
                maximum_name: 5,
            }
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "conversion_probability_warning",
        "conversion_probability_major",
        "conversion_probability_critical",
    ],
)
@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_config_rejects_probability_outside_bounds(
    field_name: str,
    value: float,
) -> None:
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        IncidentOperationsConfig(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "conversion_probability_warning",
        "conversion_probability_major",
        "conversion_probability_critical",
    ],
)
@pytest.mark.parametrize("value", [True, "0.5", None])
def test_config_rejects_non_numeric_probability(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(TypeError, match=f"{field_name} must be numeric"):
        IncidentOperationsConfig(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "include_informational_incidents",
        "group_by_ground_truth_event",
    ],
)
def test_config_requires_boolean_flags(field_name: str) -> None:
    with pytest.raises(TypeError, match=f"{field_name} must be a boolean"):
        IncidentOperationsConfig(**{field_name: 1})


def test_generate_incidents_returns_expected_columns() -> None:
    frame = generate_incidents(
        _alarms_frame(),
        config=_deterministic_config(),
    )

    assert list(frame.columns) == [
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
    ]


def test_major_equipment_alarm_generates_incident() -> None:
    frame = generate_incidents(
        _alarms_frame(),
        config=_deterministic_config(),
    )

    assert len(frame) == 1
    row = frame.iloc[0]
    assert row["incident_id"] == "INC-0000001"
    assert row["category"] == IncidentCategory.EQUIPMENT_FAILURE.value
    assert row["severity"] == IncidentSeverity.HIGH.value
    assert row["priority"] == IncidentPriority.P2.value
    assert row["owner_team"] == IncidentOwnershipTeam.MAINTENANCE.value
    assert row["primary_alarm_id"] == "ALM-0000001"


@pytest.mark.parametrize(
    ("alarm_category", "expected_category", "expected_owner"),
    [
        (
            "equipment",
            IncidentCategory.EQUIPMENT_FAILURE,
            IncidentOwnershipTeam.MAINTENANCE,
        ),
        (
            "grid",
            IncidentCategory.GRID_EVENT,
            IncidentOwnershipTeam.GRID_OPERATIONS,
        ),
        (
            "communication",
            IncidentCategory.COMMUNICATION_FAILURE,
            IncidentOwnershipTeam.NETWORK_OPERATIONS,
        ),
        (
            "performance",
            IncidentCategory.PERFORMANCE_DEGRADATION,
            IncidentOwnershipTeam.PERFORMANCE_ENGINEERING,
        ),
        (
            "environmental",
            IncidentCategory.ENVIRONMENTAL_EVENT,
            IncidentOwnershipTeam.PLANT_OPERATIONS,
        ),
        (
            "safety",
            IncidentCategory.SAFETY_EVENT,
            IncidentOwnershipTeam.HSE,
        ),
    ],
)
def test_category_and_owner_mapping(
    alarm_category: str,
    expected_category: IncidentCategory,
    expected_owner: IncidentOwnershipTeam,
) -> None:
    row = _alarm_row(category=alarm_category)

    frame = generate_incidents(
        _alarms_frame(row),
        config=_deterministic_config(),
    )

    assert frame.loc[0, "category"] == expected_category.value
    assert frame.loc[0, "owner_team"] == expected_owner.value


@pytest.mark.parametrize(
    ("alarm_severity", "expected_severity", "expected_priority"),
    [
        (
            "warning",
            IncidentSeverity.MODERATE,
            IncidentPriority.P3,
        ),
        (
            "major",
            IncidentSeverity.HIGH,
            IncidentPriority.P2,
        ),
        (
            "critical",
            IncidentSeverity.CRITICAL,
            IncidentPriority.P1,
        ),
    ],
)
def test_severity_and_priority_mapping(
    alarm_severity: str,
    expected_severity: IncidentSeverity,
    expected_priority: IncidentPriority,
) -> None:
    frame = generate_incidents(
        _alarms_frame(_alarm_row(severity=alarm_severity)),
        config=_deterministic_config(),
    )

    assert frame.loc[0, "severity"] == expected_severity.value
    assert frame.loc[0, "priority"] == expected_priority.value


def test_informational_alarm_is_skipped_by_default() -> None:
    result = generate_incident_result(
        _alarms_frame(
            _alarm_row(
                severity="informational",
                category="equipment",
            )
        ),
        config=_deterministic_config(),
    )

    assert result.frame.empty
    assert result.summary.skipped_alarm_count == 1


def test_informational_alarm_can_be_included() -> None:
    frame = generate_incidents(
        _alarms_frame(
            _alarm_row(
                severity="informational",
                category="equipment",
            )
        ),
        config=_deterministic_config(
            include_informational_incidents=True,
        ),
    )

    assert len(frame) == 1
    assert frame.loc[0, "priority"] == IncidentPriority.P4.value
    assert frame.loc[0, "severity"] == IncidentSeverity.LOW.value


def test_ineligible_alarm_is_excluded() -> None:
    result = generate_incident_result(
        _alarms_frame(_alarm_row(incident_eligible=False)),
        config=_deterministic_config(),
    )

    assert result.frame.empty
    assert result.summary.eligible_alarm_count == 0


def test_nuisance_alarm_is_excluded() -> None:
    result = generate_incident_result(
        _alarms_frame(_alarm_row(is_nuisance=True)),
        config=_deterministic_config(),
    )

    assert result.frame.empty
    assert result.summary.eligible_alarm_count == 0


def test_related_alarms_group_by_ground_truth_event() -> None:
    first = _alarm_row(
        alarm_id="ALM-0000001",
        severity="major",
        equipment_id="EQP-00001",
    )
    second = _alarm_row(
        alarm_id="ALM-0000002",
        severity="warning",
        equipment_id="EQP-00002",
        raised_at=datetime(2026, 1, 1, 12, 10, tzinfo=UTC),
    )

    frame = generate_incidents(
        _alarms_frame(first, second),
        config=_deterministic_config(),
    )

    assert len(frame) == 1
    assert frame.loc[0, "linked_alarm_count"] == 2
    assert frame.loc[0, "linked_alarm_ids"] == (
        "ALM-0000001",
        "ALM-0000002",
    )


def test_highest_severity_alarm_becomes_primary() -> None:
    warning = _alarm_row(
        alarm_id="ALM-0000001",
        severity="warning",
        alarm_name="Warning Alarm",
    )
    critical = _alarm_row(
        alarm_id="ALM-0000002",
        severity="critical",
        alarm_name="Critical Alarm",
        equipment_id="EQP-00002",
        raised_at=datetime(2026, 1, 1, 12, 5, tzinfo=UTC),
    )

    frame = generate_incidents(
        _alarms_frame(warning, critical),
        config=_deterministic_config(),
    )

    assert frame.loc[0, "primary_alarm_id"] == "ALM-0000002"
    assert frame.loc[0, "primary_equipment_id"] == "EQP-00002"
    assert frame.loc[0, "incident_name"] == "Critical Alarm Incident"


def test_without_truth_ids_groups_by_time_window() -> None:
    first = _alarm_row(
        alarm_id="ALM-0000001",
        ground_truth_event_id=None,
        raised_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    second = _alarm_row(
        alarm_id="ALM-0000002",
        ground_truth_event_id=None,
        equipment_id="EQP-00002",
        raised_at=datetime(2026, 1, 1, 12, 20, tzinfo=UTC),
    )

    frame = generate_incidents(
        _alarms_frame(first, second),
        config=_deterministic_config(),
    )

    assert len(frame) == 1
    assert frame.loc[0, "linked_alarm_count"] == 2
    assert pd.isna(frame.loc[0, "ground_truth_event_id"])


def test_alarms_outside_window_create_separate_incidents() -> None:
    first = _alarm_row(
        alarm_id="ALM-0000001",
        ground_truth_event_id=None,
        raised_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    second = _alarm_row(
        alarm_id="ALM-0000002",
        ground_truth_event_id=None,
        equipment_id="EQP-00002",
        raised_at=datetime(2026, 1, 1, 13, 0, tzinfo=UTC),
    )

    frame = generate_incidents(
        _alarms_frame(first, second),
        config=_deterministic_config(),
    )

    assert len(frame) == 2
    assert frame["incident_id"].tolist() == [
        "INC-0000001",
        "INC-0000002",
    ]


def test_grouping_by_truth_can_be_disabled() -> None:
    first = _alarm_row(
        alarm_id="ALM-0000001",
        ground_truth_event_id="GTE-2026-00000001",
        raised_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    second = _alarm_row(
        alarm_id="ALM-0000002",
        ground_truth_event_id="GTE-2026-00000001",
        equipment_id="EQP-00002",
        raised_at=datetime(2026, 1, 1, 13, 0, tzinfo=UTC),
    )

    frame = generate_incidents(
        _alarms_frame(first, second),
        config=_deterministic_config(
            group_by_ground_truth_event=False,
        ),
    )

    assert len(frame) == 2


def test_lifecycle_timestamps_follow_configured_delays() -> None:
    alarm = _alarm_row(
        event_start_at_utc=datetime(2026, 1, 1, 11, 55, tzinfo=UTC),
        cleared_at=datetime(2026, 1, 1, 12, 30, tzinfo=UTC),
    )

    frame = generate_incidents(
        _alarms_frame(alarm),
        config=_deterministic_config(),
    )

    assert frame.loc[0, "occurred_at"] == pd.Timestamp(
        datetime(2026, 1, 1, 11, 55, tzinfo=UTC)
    )
    assert frame.loc[0, "detected_at"] == pd.Timestamp(
        datetime(2026, 1, 1, 11, 56, tzinfo=UTC)
    )
    assert frame.loc[0, "assigned_at"] == pd.Timestamp(
        datetime(2026, 1, 1, 11, 58, tzinfo=UTC)
    )
    assert frame.loc[0, "investigation_started_at"] == pd.Timestamp(
        datetime(2026, 1, 1, 12, 1, tzinfo=UTC)
    )
    assert frame.loc[0, "restored_at"] == pd.Timestamp(
        datetime(2026, 1, 1, 12, 34, tzinfo=UTC)
    )
    assert frame.loc[0, "closed_at"] == pd.Timestamp(
        datetime(2026, 1, 1, 12, 39, tzinfo=UTC)
    )


def test_cleared_alarm_generates_resolved_incident() -> None:
    frame = generate_incidents(
        _alarms_frame(),
        config=_deterministic_config(),
    )

    assert frame.loc[0, "status"] == IncidentStatus.RESOLVED.value
    assert frame.loc[0, "is_open"] == False  # noqa: E712
    assert pd.notna(frame.loc[0, "resolved_at"])


def test_open_alarm_generates_investigating_incident() -> None:
    row = _alarm_row(
        status="acknowledged",
        cleared_at=pd.NaT,
    )

    frame = generate_incidents(
        _alarms_frame(row),
        config=_deterministic_config(),
    )

    assert frame.loc[0, "status"] == IncidentStatus.INVESTIGATING.value
    assert frame.loc[0, "is_open"] == True  # noqa: E712
    assert pd.isna(frame.loc[0, "resolved_at"])


def test_sla_targets_match_priority() -> None:
    critical = _alarm_row(severity="critical")

    frame = generate_incidents(
        _alarms_frame(critical),
        config=_deterministic_config(),
    )

    assert frame.loc[0, "priority"] == IncidentPriority.P1.value
    assert frame.loc[0, "sla_response_minutes"] == 5
    assert frame.loc[0, "sla_resolution_minutes"] == 60


def test_response_sla_breach_is_calculated() -> None:
    frame = generate_incidents(
        _alarms_frame(_alarm_row(severity="critical")),
        config=_deterministic_config(
            assignment_delay_min_minutes=10,
            assignment_delay_max_minutes=10,
        ),
    )

    assert frame.loc[0, "response_sla_breached"] == True  # noqa: E712


def test_resolution_sla_breach_is_calculated() -> None:
    alarm = _alarm_row(
        severity="critical",
        cleared_at=datetime(2026, 1, 1, 15, 0, tzinfo=UTC),
    )

    frame = generate_incidents(
        _alarms_frame(alarm),
        config=_deterministic_config(),
    )

    assert frame.loc[0, "resolution_sla_breached"] == True  # noqa: E712


def test_generation_summary_counts_records() -> None:
    first = _alarm_row(alarm_id="ALM-0000001")
    second = _alarm_row(
        alarm_id="ALM-0000002",
        is_nuisance=True,
        equipment_id="EQP-00002",
    )

    result = generate_incident_result(
        _alarms_frame(first, second),
        config=_deterministic_config(),
    )

    assert result.summary.to_record() == {
        "input_alarm_count": 2,
        "eligible_alarm_count": 1,
        "generated_incident_count": 1,
        "grouped_alarm_count": 0,
        "skipped_alarm_count": 0,
    }


def test_warning_conversion_probability_can_skip_incident() -> None:
    result = generate_incident_result(
        _alarms_frame(_alarm_row(severity="warning")),
        config=_deterministic_config(
            conversion_probability_warning=0.0,
        ),
    )

    assert result.frame.empty
    assert result.summary.skipped_alarm_count == 1


def test_generation_is_deterministic() -> None:
    alarms = _alarms_frame(
        _alarm_row(alarm_id="ALM-0000001"),
        _alarm_row(
            alarm_id="ALM-0000002",
            equipment_id="EQP-00002",
            ground_truth_event_id="GTE-2026-00000002",
        ),
    )
    config = IncidentOperationsConfig(random_seed=99)

    first = generate_incidents(alarms, config=config)
    second = generate_incidents(alarms, config=config)

    pd.testing.assert_frame_equal(first, second)


def test_incident_ids_follow_stable_order() -> None:
    later = _alarm_row(
        alarm_id="ALM-0000002",
        equipment_id="EQP-00002",
        ground_truth_event_id="GTE-2026-00000002",
        raised_at=datetime(2026, 1, 1, 13, 0, tzinfo=UTC),
        event_start_at_utc=datetime(2026, 1, 1, 12, 55, tzinfo=UTC),
    )
    earlier = _alarm_row(
        alarm_id="ALM-0000001",
        equipment_id="EQP-00001",
        ground_truth_event_id="GTE-2026-00000001",
        raised_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        event_start_at_utc=datetime(2026, 1, 1, 11, 55, tzinfo=UTC),
    )

    frame = generate_incidents(
        _alarms_frame(later, earlier),
        config=_deterministic_config(),
    )

    assert frame["incident_id"].tolist() == [
        "INC-0000001",
        "INC-0000002",
    ]
    assert frame["primary_equipment_id"].tolist() == [
        "EQP-00001",
        "EQP-00002",
    ]


def test_incident_name_and_root_cause_are_derived() -> None:
    frame = generate_incidents(
        _alarms_frame(),
        config=_deterministic_config(),
    )

    assert frame.loc[0, "incident_name"] == "Inverter Trip Incident"
    assert frame.loc[0, "root_cause"] == "Inverter Trip"
    assert "Primary alarm code: INV-TRIP-001" in frame.loc[0, "description"]


def test_incidents_round_trip_to_domain_models() -> None:
    frame = generate_incidents(
        _alarms_frame(),
        config=_deterministic_config(),
    )

    models = incidents_to_domain_models(frame)

    assert len(models) == 1
    incident = models[0]
    assert incident.incident_id == "INC-0000001"
    assert incident.linked_alarm_id == "ALM-0000001"
    assert incident.status is IncidentStatus.RESOLVED


def test_incidents_to_domain_models_rejects_missing_columns() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        incidents_to_domain_models(pd.DataFrame({"incident_id": ["INC-0000001"]}))


def test_input_must_be_dataframe() -> None:
    with pytest.raises(TypeError, match="pandas DataFrame"):
        generate_incidents(  # type: ignore[arg-type]
            [],
            config=_deterministic_config(),
        )


def test_missing_alarm_columns_are_rejected() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        generate_incidents(
            pd.DataFrame({"alarm_id": ["ALM-0000001"]}),
            config=_deterministic_config(),
        )


def test_duplicate_alarm_ids_are_rejected() -> None:
    duplicated = _alarms_frame(
        _alarm_row(),
        _alarm_row(equipment_id="EQP-00002"),
    )

    with pytest.raises(ValueError, match="must be unique"):
        generate_incidents(
            duplicated,
            config=_deterministic_config(),
        )


def test_missing_raised_at_is_rejected() -> None:
    row = _alarm_row()
    row["raised_at"] = pd.NaT

    with pytest.raises(ValueError, match="raised_at"):
        generate_incidents(
            _alarms_frame(row),
            config=_deterministic_config(),
        )


def test_empty_alarm_frame_returns_empty_contract() -> None:
    empty = _alarms_frame().iloc[0:0]

    result = generate_incident_result(
        empty,
        config=_deterministic_config(),
    )

    assert result.frame.empty
    assert len(result.frame.columns) == 33
    assert result.summary.input_alarm_count == 0
    assert result.summary.generated_incident_count == 0


def test_output_datetime_columns_are_utc_aware() -> None:
    frame = generate_incidents(
        _alarms_frame(),
        config=_deterministic_config(),
    )

    for column in (
        "occurred_at",
        "detected_at",
        "assigned_at",
        "investigation_started_at",
        "restored_at",
        "resolved_at",
        "closed_at",
    ):
        assert isinstance(frame[column].dtype, pd.DatetimeTZDtype)
        assert str(frame[column].dt.tz) == "UTC"
