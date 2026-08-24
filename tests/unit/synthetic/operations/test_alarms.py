"""
Unit tests for EOIP event-driven operational alarm generation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from eoip.synthetic.events.catalogue import EventScope, EventSeverity, EventType
from eoip.synthetic.events.scheduler import SyntheticEvent
from eoip.synthetic.models.alarm import AlarmSeverity, AlarmStatus
from eoip.synthetic.operations.alarms import (
    AlarmOperationsConfig,
    AlarmSCADAContext,
    alarms_to_domain_models,
    generate_alarm_result,
    generate_alarms,
)


def _event(
    *,
    event_type: EventType = EventType.INVERTER_TRIP,
    event_scope: EventScope = EventScope.INVERTER,
    plant_id: str = "PLANT-001",
    asset_type: str = "inverter",
    asset_id: str = "EQP-00001",
    start_at_utc: datetime | None = None,
    end_at_utc: datetime | None = None,
    severity: EventSeverity = EventSeverity.HIGH,
    expected_alarm_code: str | None = None,
    event_id: str = "GTE-2026-00000001",
) -> SyntheticEvent:
    """Return a compact valid scheduled event."""
    start = start_at_utc or datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    end = end_at_utc or datetime(2026, 1, 1, 14, 0, tzinfo=UTC)

    return SyntheticEvent(
        ground_truth_event_id=event_id,
        event_type=event_type,
        event_scope=event_scope,
        plant_id=plant_id,
        asset_type=asset_type,
        asset_id=asset_id,
        parent_event_id=None,
        start_at_utc=start,
        end_at_utc=end,
        severity=severity,
        severity_score=0.75,
        power_modifier_ratio=0.0,
        measurement_channel=None,
        measurement_bias=None,
        is_planned=event_type is EventType.MAINTENANCE_OUTAGE,
        cause_code=event_type.value.upper(),
        parameters_json="{}",
        expected_alarm_code=expected_alarm_code,
        expected_incident=True,
        expected_work_order=False,
        generation_run_id="RUN-TEST",
        schema_version="1.0.0",
    )


def _deterministic_config(**overrides: object) -> AlarmOperationsConfig:
    """Return config with deterministic acknowledgement and no nuisance."""
    data: dict[str, object] = {
        "random_seed": 42,
        "acknowledgement_probability": 1.0,
        "informational_acknowledgement_probability": 1.0,
        "warning_acknowledgement_probability": 1.0,
        "major_acknowledgement_probability": 1.0,
        "critical_acknowledgement_probability": 1.0,
        "minimum_acknowledgement_minutes": 1,
        "maximum_acknowledgement_minutes": 1,
        "manual_clear_extra_minutes": 0,
        "nuisance_alarm_probability": 0.0,
        "maximum_nuisance_alarms_per_event": 1,
        "generate_nuisance_alarms": False,
        "allow_equipment_id_fallback": True,
        "is_synthetic_ground_truth": True,
        "schema_version": "1.0.0",
    }
    data.update(overrides)
    return AlarmOperationsConfig(**data)


def test_config_defaults() -> None:
    config = AlarmOperationsConfig()

    assert config.random_seed == 20250201
    assert config.generate_nuisance_alarms is True
    assert config.allow_equipment_id_fallback is True
    assert config.schema_version == "1.0.0"


@pytest.mark.parametrize(
    "field_name",
    [
        "acknowledgement_probability",
        "informational_acknowledgement_probability",
        "warning_acknowledgement_probability",
        "major_acknowledgement_probability",
        "critical_acknowledgement_probability",
        "nuisance_alarm_probability",
    ],
)
@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_config_rejects_probability_outside_bounds(
    field_name: str,
    value: float,
) -> None:
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        AlarmOperationsConfig(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "acknowledgement_probability",
        "informational_acknowledgement_probability",
        "warning_acknowledgement_probability",
        "major_acknowledgement_probability",
        "critical_acknowledgement_probability",
        "nuisance_alarm_probability",
    ],
)
@pytest.mark.parametrize("value", [True, "0.5", None])
def test_config_rejects_non_numeric_probability(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(TypeError, match=f"{field_name} must be numeric"):
        AlarmOperationsConfig(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "minimum_acknowledgement_minutes",
        "maximum_acknowledgement_minutes",
        "manual_clear_extra_minutes",
        "maximum_nuisance_alarms_per_event",
    ],
)
@pytest.mark.parametrize("value", [True, 1.5, "1", None])
def test_config_rejects_non_integer_values(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(TypeError, match=f"{field_name} must be an integer"):
        AlarmOperationsConfig(**{field_name: value})


def test_config_rejects_invalid_acknowledgement_bounds() -> None:
    with pytest.raises(
        ValueError,
        match="maximum_acknowledgement_minutes",
    ):
        AlarmOperationsConfig(
            minimum_acknowledgement_minutes=10,
            maximum_acknowledgement_minutes=5,
        )


def test_context_normalizes_mappings() -> None:
    context = AlarmSCADAContext(
        equipment_id_by_asset={" inv-01 ": " eqp-00001 "},
        default_equipment_id_by_plant={" plant-001 ": " eqp-00002 "},
        suppression_rules_by_event_id={
            " gte-2026-00000001 ": (" Planned_Maintenance ",)
        },
    )

    assert context.equipment_id_by_asset == {"INV-01": "EQP-00001"}
    assert context.default_equipment_id_by_plant == {"PLANT-001": "EQP-00002"}
    assert context.suppression_rules_by_event_id == {
        "GTE-2026-00000001": ("planned_maintenance",)
    }


def test_context_rejects_invalid_equipment_mapping() -> None:
    with pytest.raises(ValueError, match="Invalid equipment ID"):
        AlarmSCADAContext(equipment_id_by_asset={"INV-01": "INVALID"})


def test_context_requires_aware_observation_end() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        AlarmSCADAContext(observation_end_at=datetime(2026, 1, 1, 12, 0))


def test_generate_alarms_returns_expected_columns() -> None:
    frame = generate_alarms(
        (_event(),),
        config=_deterministic_config(),
    )

    assert list(frame.columns) == [
        "alarm_id",
        "plant_id",
        "equipment_id",
        "source_asset_id",
        "source_asset_type",
        "event_scope",
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
        "is_open",
        "is_critical",
        "acknowledgement_seconds",
        "resolution_seconds",
        "is_synthetic_ground_truth",
        "is_nuisance",
        "incident_eligible",
        "event_type",
        "event_start_at_utc",
        "event_end_at_utc",
        "generation_run_id",
        "schema_version",
    ]


def test_inverter_trip_generates_catalogue_alarm() -> None:
    frame = generate_alarms(
        (_event(),),
        config=_deterministic_config(),
    )

    assert len(frame) == 1
    row = frame.iloc[0]
    assert row["alarm_id"] == "ALM-0000001"
    assert row["alarm_code"] == "INV-TRIP-001"
    assert row["equipment_id"] == "EQP-00001"
    assert row["ground_truth_event_id"] == "GTE-2026-00000001"
    assert row["status"] == AlarmStatus.CLEARED.value
    assert row["severity"] == AlarmSeverity.MAJOR.value
    assert row["is_synthetic_ground_truth"] == True  # noqa: E712


def test_explicit_expected_alarm_code_takes_priority() -> None:
    event = _event(
        event_type=EventType.STORM_EVENT,
        event_scope=EventScope.PLANT,
        asset_type="plant",
        asset_id="PLANT-001",
        expected_alarm_code="GRID-LOSS-001",
    )

    frame = generate_alarms(
        (event,),
        scada_context=AlarmSCADAContext(
            default_equipment_id_by_plant={"PLANT-001": "EQP-00009"}
        ),
        config=_deterministic_config(),
    )

    assert frame.loc[0, "alarm_code"] == "GRID-LOSS-001"


def test_trigger_delay_is_applied() -> None:
    event = _event(
        event_type=EventType.INVERTER_DERATING,
    )

    frame = generate_alarms(
        (event,),
        config=_deterministic_config(),
    )

    assert frame.loc[0, "raised_at"] == pd.Timestamp(
        event.start_at_utc + timedelta(minutes=30)
    )


def test_clear_delay_is_applied() -> None:
    event = _event(
        event_type=EventType.INVERTER_DERATING,
    )

    frame = generate_alarms(
        (event,),
        config=_deterministic_config(),
    )

    assert frame.loc[0, "cleared_at"] == pd.Timestamp(
        event.end_at_utc + timedelta(minutes=30)
    )


def test_manual_clear_extra_delay_is_applied() -> None:
    event = _event()

    frame = generate_alarms(
        (event,),
        config=_deterministic_config(manual_clear_extra_minutes=20),
    )

    assert frame.loc[0, "cleared_at"] == pd.Timestamp(
        event.end_at_utc + timedelta(minutes=25)
    )


def test_latched_alarm_remains_open() -> None:
    event = _event(
        event_type=EventType.METER_RESET,
        event_scope=EventScope.SENSOR,
        asset_type="meter",
        asset_id="MTR-001",
    )

    frame = generate_alarms(
        (event,),
        scada_context=AlarmSCADAContext(equipment_id_by_asset={"MTR-001": "EQP-00005"}),
        config=_deterministic_config(),
    )

    assert pd.isna(frame.loc[0, "cleared_at"])
    assert frame.loc[0, "status"] == AlarmStatus.ACKNOWLEDGED.value
    assert frame.loc[0, "is_open"] == True  # noqa: E712


def test_observation_end_keeps_alarm_open() -> None:
    event = _event()
    context = AlarmSCADAContext(observation_end_at=event.end_at_utc)

    frame = generate_alarms(
        (event,),
        scada_context=context,
        config=_deterministic_config(),
    )

    assert pd.isna(frame.loc[0, "cleared_at"])
    assert frame.loc[0, "status"] == AlarmStatus.ACKNOWLEDGED.value


def test_acknowledgement_can_be_disabled() -> None:
    frame = generate_alarms(
        (_event(),),
        config=_deterministic_config(
            acknowledgement_probability=0.0,
        ),
    )

    assert pd.isna(frame.loc[0, "acknowledged_at"])
    assert frame.loc[0, "status"] == AlarmStatus.CLEARED.value


def test_acknowledgement_after_clear_is_omitted() -> None:
    event = _event(
        event_type=EventType.GRID_OUTAGE,
        event_scope=EventScope.PLANT,
        asset_type="plant",
        asset_id="PLANT-001",
        start_at_utc=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        end_at_utc=datetime(2026, 1, 1, 12, 1, tzinfo=UTC),
    )

    frame = generate_alarms(
        (event,),
        scada_context=AlarmSCADAContext(
            default_equipment_id_by_plant={"PLANT-001": "EQP-00007"}
        ),
        config=_deterministic_config(
            minimum_acknowledgement_minutes=10,
            maximum_acknowledgement_minutes=10,
        ),
    )

    assert pd.isna(frame.loc[0, "acknowledged_at"])


def test_suppression_rule_prevents_alarm() -> None:
    event = _event()
    context = AlarmSCADAContext(
        suppression_rules_by_event_id={
            event.ground_truth_event_id: ("planned_inverter_maintenance",)
        }
    )

    result = generate_alarm_result(
        (event,),
        scada_context=context,
        config=_deterministic_config(),
    )

    assert result.frame.empty
    assert result.summary.suppressed_alarm_count == 1


def test_unrelated_suppression_rule_does_not_prevent_alarm() -> None:
    event = _event()
    context = AlarmSCADAContext(
        suppression_rules_by_event_id={event.ground_truth_event_id: ("unrelated_rule",)}
    )

    frame = generate_alarms(
        (event,),
        scada_context=context,
        config=_deterministic_config(),
    )

    assert len(frame) == 1


def test_asset_mapping_resolves_equipment_id() -> None:
    event = _event(
        asset_id="INV-001",
    )
    context = AlarmSCADAContext(equipment_id_by_asset={"INV-001": "EQP-00003"})

    frame = generate_alarms(
        (event,),
        scada_context=context,
        config=_deterministic_config(),
    )

    assert frame.loc[0, "equipment_id"] == "EQP-00003"


def test_plant_default_resolves_equipment_id() -> None:
    event = _event(
        event_type=EventType.GRID_OUTAGE,
        event_scope=EventScope.PLANT,
        asset_type="plant",
        asset_id="PLANT-001",
    )
    context = AlarmSCADAContext(
        default_equipment_id_by_plant={"PLANT-001": "EQP-00008"}
    )

    frame = generate_alarms(
        (event,),
        scada_context=context,
        config=_deterministic_config(),
    )

    assert frame.loc[0, "equipment_id"] == "EQP-00008"


def test_fallback_equipment_id_is_stable() -> None:
    event = _event(
        asset_id="INV-UNMAPPED",
    )

    first = generate_alarms(
        (event,),
        config=_deterministic_config(),
    )
    second = generate_alarms(
        (event,),
        config=_deterministic_config(),
    )

    assert first.loc[0, "equipment_id"] == second.loc[0, "equipment_id"]
    assert first.loc[0, "equipment_id"].startswith("EQP-")


def test_fallback_can_be_disabled() -> None:
    event = _event(
        asset_id="INV-UNMAPPED",
    )

    with pytest.raises(ValueError, match="Unable to resolve"):
        generate_alarms(
            (event,),
            config=_deterministic_config(
                allow_equipment_id_fallback=False,
            ),
        )


def test_nuisance_alarm_generation_is_bounded() -> None:
    event = _event(
        event_type=EventType.INVERTER_DERATING,
    )
    config = _deterministic_config(
        generate_nuisance_alarms=True,
        nuisance_alarm_probability=1.0,
        maximum_nuisance_alarms_per_event=1,
    )

    result = generate_alarm_result(
        (event,),
        config=config,
    )

    assert len(result.frame) == 2
    assert result.summary.nuisance_alarm_count == 1
    assert int(result.frame["is_nuisance"].sum()) == 1


def test_non_nuisance_eligible_alarm_creates_no_nuisance() -> None:
    config = _deterministic_config(
        generate_nuisance_alarms=True,
        nuisance_alarm_probability=1.0,
        maximum_nuisance_alarms_per_event=1,
    )

    result = generate_alarm_result(
        (_event(),),
        config=config,
    )

    assert len(result.frame) == 1
    assert result.summary.nuisance_alarm_count == 0


def test_alarm_ids_follow_stable_sorted_order() -> None:
    later = _event(
        event_id="GTE-2026-00000002",
        asset_id="EQP-00002",
        start_at_utc=datetime(2026, 1, 1, 13, 0, tzinfo=UTC),
        end_at_utc=datetime(2026, 1, 1, 15, 0, tzinfo=UTC),
    )
    earlier = _event(
        event_id="GTE-2026-00000001",
        asset_id="EQP-00001",
        start_at_utc=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        end_at_utc=datetime(2026, 1, 1, 14, 0, tzinfo=UTC),
    )

    frame = generate_alarms(
        (later, earlier),
        config=_deterministic_config(),
    )

    assert frame["alarm_id"].tolist() == [
        "ALM-0000001",
        "ALM-0000002",
    ]
    assert frame["equipment_id"].tolist() == [
        "EQP-00001",
        "EQP-00002",
    ]


def test_generation_is_deterministic() -> None:
    events = (
        _event(),
        _event(
            event_id="GTE-2026-00000002",
            asset_id="EQP-00002",
        ),
    )
    config = _deterministic_config(
        minimum_acknowledgement_minutes=1,
        maximum_acknowledgement_minutes=10,
    )

    first = generate_alarms(events, config=config)
    second = generate_alarms(events, config=config)

    pd.testing.assert_frame_equal(first, second)


def test_severity_is_not_lower_than_catalogue_default() -> None:
    event = _event(
        severity=EventSeverity.LOW,
    )

    frame = generate_alarms(
        (event,),
        config=_deterministic_config(),
    )

    assert frame.loc[0, "severity"] == AlarmSeverity.MAJOR.value


def test_critical_event_escalates_alarm_severity() -> None:
    event = _event(
        event_type=EventType.INVERTER_DERATING,
        severity=EventSeverity.CRITICAL,
    )

    frame = generate_alarms(
        (event,),
        config=_deterministic_config(),
    )

    assert frame.loc[0, "severity"] == AlarmSeverity.CRITICAL.value


def test_short_event_can_end_before_trigger_delay() -> None:
    event = _event(
        event_type=EventType.INVERTER_DERATING,
        start_at_utc=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        end_at_utc=datetime(2026, 1, 1, 12, 15, tzinfo=UTC),
    )

    frame = generate_alarms(
        (event,),
        config=_deterministic_config(),
    )

    assert frame.empty


def test_unknown_explicit_code_falls_back_to_event_mapping() -> None:
    event = _event(
        expected_alarm_code="UNKNOWN-001",
    )

    frame = generate_alarms(
        (event,),
        config=_deterministic_config(),
    )

    assert frame.loc[0, "alarm_code"] == "INV-TRIP-001"


def test_event_without_catalogue_mapping_generates_no_alarm() -> None:
    event = _event(
        event_type=EventType.SOILING_ACCUMULATION,
        event_scope=EventScope.PLANT,
        asset_type="plant",
        asset_id="PLANT-001",
    )

    result = generate_alarm_result(
        (event,),
        config=_deterministic_config(),
    )

    assert result.frame.empty
    assert result.summary.generated_alarm_count == 0


def test_generation_summary_counts_events_and_alarms() -> None:
    result = generate_alarm_result(
        (_event(),),
        config=_deterministic_config(),
    )

    assert result.summary.to_record() == {
        "input_event_count": 1,
        "generated_alarm_count": 1,
        "suppressed_alarm_count": 0,
        "nuisance_alarm_count": 0,
    }


def test_mapping_scada_context_is_supported() -> None:
    event = _event(asset_id="INV-001")

    frame = generate_alarms(
        (event,),
        scada_context={"equipment_id_by_asset": {"INV-001": "EQP-00004"}},
        config=_deterministic_config(),
    )

    assert frame.loc[0, "equipment_id"] == "EQP-00004"


def test_invalid_scada_context_type_is_rejected() -> None:
    with pytest.raises(TypeError, match="scada_context"):
        generate_alarms(
            (_event(),),
            scada_context=[],  # type: ignore[arg-type]
            config=_deterministic_config(),
        )


def test_alarms_round_trip_to_domain_models() -> None:
    frame = generate_alarms(
        (_event(),),
        config=_deterministic_config(),
    )

    models = alarms_to_domain_models(frame)

    assert len(models) == 1
    alarm = models[0]
    assert alarm.alarm_id == "ALM-0000001"
    assert alarm.alarm_code == "INV-TRIP-001"
    assert alarm.status is AlarmStatus.CLEARED


def test_alarms_to_domain_models_rejects_missing_columns() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        alarms_to_domain_models(pd.DataFrame({"alarm_id": ["ALM-0000001"]}))


def test_empty_event_collection_returns_empty_contract_frame() -> None:
    result = generate_alarm_result(
        (),
        config=_deterministic_config(),
    )

    assert result.frame.empty
    assert len(result.frame.columns) == 28
    assert result.summary.input_event_count == 0
    assert result.summary.generated_alarm_count == 0


def test_output_datetime_columns_are_utc_aware() -> None:
    frame = generate_alarms(
        (_event(),),
        config=_deterministic_config(),
    )

    for column in (
        "raised_at",
        "acknowledged_at",
        "cleared_at",
        "event_start_at_utc",
        "event_end_at_utc",
    ):
        assert isinstance(frame[column].dtype, pd.DatetimeTZDtype)
        assert str(frame[column].dt.tz) == "UTC"
