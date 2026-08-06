"""
Unit tests for EOIP synthetic event effects.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest

from eoip.synthetic.events.catalogue import EventScope, EventSeverity, EventType
from eoip.synthetic.events.effects import (
    EffectApplicationConfig,
    EffectKind,
    EffectSummary,
    EffectTarget,
    apply_inverter_scada_events,
    apply_plant_scada_events,
    apply_weather_events,
    build_event_mask,
    effect_summaries_to_frame,
    grid_export_limit,
    power_availability_modifier,
    quality_flag_overlay,
    recovery_curve,
)
from eoip.synthetic.events.scheduler import SyntheticEvent


def _event(
    *,
    event_type: EventType,
    scope: EventScope = EventScope.PLANT,
    asset_id: str = "PLANT-001",
    plant_id: str = "PLANT-001",
    start: datetime | None = None,
    end: datetime | None = None,
    power_modifier_ratio: float | None = 0.0,
    measurement_channel: str | None = None,
    measurement_bias: float | None = None,
    parameters_json: str = "{}",
    event_id: str = "GTE-2026-00000001",
) -> SyntheticEvent:
    start_at = start or datetime(2026, 1, 1, 0, 15, tzinfo=UTC)
    end_at = end or datetime(2026, 1, 1, 0, 45, tzinfo=UTC)

    return SyntheticEvent(
        ground_truth_event_id=event_id,
        event_type=event_type,
        event_scope=scope,
        plant_id=plant_id,
        asset_type=scope.value,
        asset_id=asset_id,
        parent_event_id=None,
        start_at_utc=start_at,
        end_at_utc=end_at,
        severity=EventSeverity.HIGH,
        severity_score=0.7,
        power_modifier_ratio=power_modifier_ratio,
        measurement_channel=measurement_channel,
        measurement_bias=measurement_bias,
        is_planned=event_type is EventType.MAINTENANCE_OUTAGE,
        cause_code=event_type.value.upper(),
        parameters_json=parameters_json,
        expected_alarm_code=None,
        expected_incident=False,
        expected_work_order=False,
        generation_run_id="RUN-TEST",
        schema_version="1.0.0",
    )


def _timestamps() -> pd.DatetimeIndex:
    return pd.date_range(
        datetime(2026, 1, 1, tzinfo=UTC),
        periods=5,
        freq="15min",
    )


def _weather_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp_utc": _timestamps(),
            "plant_id": ["PLANT-001"] * 5,
            "ghi_w_m2": [100.0, 200.0, 300.0, 400.0, 500.0],
            "dni_w_m2": [80.0, 160.0, 240.0, 320.0, 400.0],
            "dhi_w_m2": [20.0, 40.0, 60.0, 80.0, 100.0],
            "poa_irradiance_w_m2": [90.0, 180.0, 270.0, 360.0, 450.0],
            "ambient_temperature_c": [25.0] * 5,
            "cell_temperature_c": [35.0] * 5,
            "wind_speed_m_s": [2.0] * 5,
            "precipitation_mm": [0.0] * 5,
        }
    )


def _inverter_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp_utc": _timestamps(),
            "plant_id": ["PLANT-001"] * 5,
            "inverter_id": ["INV-001"] * 5,
            "feeder_id": ["FDR-001"] * 5,
            "transformer_id": ["TX-001"] * 5,
            "dc_power_kw": [100.0] * 5,
            "ac_power_kw": [95.0] * 5,
            "interval_energy_kwh": [23.75] * 5,
            "dc_current_a": [20.0] * 5,
            "ac_current_a": [18.0] * 5,
            "reactive_power_kvar": [5.0] * 5,
            "apparent_power_kva": [96.0] * 5,
            "availability_ratio": [1.0] * 5,
            "operating_state": ["running"] * 5,
        }
    )


def _plant_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp_utc": _timestamps(),
            "plant_id": ["PLANT-001"] * 5,
            "meter_id": ["MTR-001"] * 5,
            "gross_inverter_power_mw": [10.0] * 5,
            "export_power_mw": [9.0] * 5,
            "interval_export_energy_mwh": [2.25] * 5,
            "curtailment_loss_mw": [0.0] * 5,
            "available_capacity_mw": [10.0] * 5,
            "cumulative_export_energy_mwh": [
                100.0,
                102.25,
                104.5,
                106.75,
                109.0,
            ],
        }
    )


def test_effect_enums_expose_expected_values() -> None:
    assert EffectTarget.WEATHER.value == "weather"
    assert EffectTarget.INVERTER_SCADA.value == "inverter_scada"
    assert EffectTarget.PLANT_SCADA.value == "plant_scada"
    assert EffectKind.PHYSICAL.value == "physical"
    assert EffectKind.MEASUREMENT.value == "measurement"


def test_effect_config_defaults() -> None:
    config = EffectApplicationConfig()

    assert config.timestamp_column == "timestamp_utc"
    assert config.quality_flag_column == "quality_flag"
    assert config.drop_rows_for_telemetry_gap is False


@pytest.mark.parametrize("field_name", ["timestamp_column", "plant_id_column"])
def test_effect_config_rejects_blank_text(field_name: str) -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        EffectApplicationConfig(**{field_name: " "})


def test_effect_config_requires_boolean_gap_option() -> None:
    with pytest.raises(TypeError, match="must be a boolean"):
        EffectApplicationConfig(
            drop_rows_for_telemetry_gap=1,  # type: ignore[arg-type]
        )


def test_build_event_mask_matches_time_and_plant() -> None:
    frame = _weather_frame()
    event = _event(event_type=EventType.STORM_EVENT)

    mask = build_event_mask(
        frame,
        event,
        target=EffectTarget.WEATHER,
    )

    assert mask.tolist() == [False, True, True, False, False]


def test_build_event_mask_matches_inverter_scope() -> None:
    frame = _inverter_frame()
    event = _event(
        event_type=EventType.INVERTER_TRIP,
        scope=EventScope.INVERTER,
        asset_id="INV-001",
    )

    mask = build_event_mask(
        frame,
        event,
        target=EffectTarget.INVERTER_SCADA,
    )

    assert int(mask.sum()) == 2


def test_build_event_mask_rejects_missing_timestamp_column() -> None:
    frame = _weather_frame().drop(columns="timestamp_utc")
    event = _event(event_type=EventType.STORM_EVENT)

    with pytest.raises(ValueError, match="missing timestamp column"):
        build_event_mask(
            frame,
            event,
            target=EffectTarget.WEATHER,
        )


def test_storm_reduces_irradiance_and_increases_weather_severity() -> None:
    frame = _weather_frame()
    event = _event(
        event_type=EventType.STORM_EVENT,
        power_modifier_ratio=0.5,
    )

    result = apply_weather_events(frame, (event,))

    assert result.frame.loc[1, "ghi_w_m2"] == 100.0
    assert result.frame.loc[2, "ghi_w_m2"] == 150.0
    assert result.frame.loc[1, "wind_speed_m_s"] == 3.6
    assert result.frame.loc[1, "precipitation_mm"] == 1.0
    assert len(result.summaries) == 1
    assert result.summaries[0].affected_rows == 2


def test_high_temperature_event_adds_temperature_uplift() -> None:
    frame = _weather_frame()
    event = _event(
        event_type=EventType.HIGH_TEMPERATURE_STRESS,
        power_modifier_ratio=0.9,
        parameters_json='{"temperature_uplift_c":5.0}',
    )

    result = apply_weather_events(frame, (event,))

    assert result.frame.loc[1, "ambient_temperature_c"] == 30.0
    assert result.frame.loc[2, "cell_temperature_c"] == 40.0


def test_sensor_drift_applies_ramped_bias() -> None:
    frame = _weather_frame()
    event = _event(
        event_type=EventType.SENSOR_DRIFT,
        scope=EventScope.SENSOR,
        asset_id="SENSOR-001",
        power_modifier_ratio=None,
        measurement_channel="ghi_w_m2",
        measurement_bias=0.10,
    )

    result = apply_weather_events(frame, (event,))

    assert result.frame.loc[1, "ghi_w_m2"] == pytest.approx(200.0)
    assert result.frame.loc[2, "ghi_w_m2"] == pytest.approx(330.0)
    assert result.frame.loc[1, "quality_flag"] == "suspect"
    assert result.frame.loc[2, "quality_flag"] == "suspect"


def test_sensor_stuck_repeats_first_value() -> None:
    frame = _weather_frame()
    event = _event(
        event_type=EventType.SENSOR_STUCK,
        scope=EventScope.SENSOR,
        asset_id="SENSOR-001",
        power_modifier_ratio=None,
        measurement_channel="ghi_w_m2",
    )

    result = apply_weather_events(frame, (event,))

    assert result.frame.loc[1, "ghi_w_m2"] == 200.0
    assert result.frame.loc[2, "ghi_w_m2"] == 200.0
    assert result.frame.loc[2, "quality_flag"] == "stuck"


def test_weather_telemetry_gap_sets_values_missing() -> None:
    frame = _weather_frame()
    event = _event(
        event_type=EventType.TELEMETRY_GAP,
        scope=EventScope.SENSOR,
        asset_id="SENSOR-001",
        power_modifier_ratio=None,
        measurement_channel="weather",
    )

    result = apply_weather_events(frame, (event,))

    assert pd.isna(result.frame.loc[1, "ghi_w_m2"])
    assert pd.isna(result.frame.loc[2, "ambient_temperature_c"])
    assert result.frame.loc[1, "quality_flag"] == "missing"


@pytest.mark.parametrize(
    "event_type",
    [
        EventType.GRID_OUTAGE,
        EventType.PLANT_TRIP,
        EventType.FEEDER_TRIP,
        EventType.TRANSFORMER_TRIP,
        EventType.INVERTER_TRIP,
        EventType.MAINTENANCE_OUTAGE,
    ],
)
def test_trip_events_zero_inverter_power(event_type: EventType) -> None:
    frame = _inverter_frame()
    scope = {
        EventType.GRID_OUTAGE: EventScope.PLANT,
        EventType.PLANT_TRIP: EventScope.PLANT,
        EventType.FEEDER_TRIP: EventScope.FEEDER,
        EventType.TRANSFORMER_TRIP: EventScope.TRANSFORMER,
        EventType.INVERTER_TRIP: EventScope.INVERTER,
        EventType.MAINTENANCE_OUTAGE: EventScope.INVERTER,
    }[event_type]
    asset_id = {
        EventScope.PLANT: "PLANT-001",
        EventScope.FEEDER: "FDR-001",
        EventScope.TRANSFORMER: "TX-001",
        EventScope.INVERTER: "INV-001",
    }[scope]

    event = _event(
        event_type=event_type,
        scope=scope,
        asset_id=asset_id,
    )

    result = apply_inverter_scada_events(frame, (event,))

    assert result.frame.loc[1, "ac_power_kw"] == 0.0
    assert result.frame.loc[2, "dc_power_kw"] == 0.0
    assert result.frame.loc[1, "availability_ratio"] == 0.0


@pytest.mark.parametrize(
    "event_type",
    [
        EventType.INVERTER_DERATING,
        EventType.THERMAL_DERATING,
        EventType.MPPT_FAULT,
        EventType.DC_STRING_LOSS,
    ],
)
def test_derating_events_scale_inverter_power(event_type: EventType) -> None:
    frame = _inverter_frame()
    event = _event(
        event_type=event_type,
        scope=EventScope.INVERTER,
        asset_id="INV-001",
        power_modifier_ratio=0.5,
    )

    result = apply_inverter_scada_events(frame, (event,))

    assert result.frame.loc[1, "ac_power_kw"] == 47.5
    assert result.frame.loc[1, "dc_power_kw"] == 50.0
    assert result.frame.loc[1, "availability_ratio"] == 0.5
    assert result.frame.loc[1, "operating_state"] == "derated"


def test_grid_curtailment_caps_export_and_records_loss() -> None:
    frame = _plant_frame()
    event = _event(
        event_type=EventType.GRID_CURTAILMENT,
        power_modifier_ratio=0.5,
    )

    result = apply_plant_scada_events(frame, (event,))

    assert result.frame.loc[1, "export_power_mw"] == 5.0
    assert result.frame.loc[1, "curtailment_loss_mw"] == 5.0
    assert result.frame.loc[1, "interval_export_energy_mwh"] == 1.25


def test_plant_trip_zeroes_export() -> None:
    frame = _plant_frame()
    event = _event(event_type=EventType.PLANT_TRIP)

    result = apply_plant_scada_events(frame, (event,))

    assert result.frame.loc[1, "export_power_mw"] == 0.0
    assert result.frame.loc[1, "available_capacity_mw"] == 0.0


def test_soiling_scales_plant_power() -> None:
    frame = _plant_frame()
    event = _event(
        event_type=EventType.SOILING_ACCUMULATION,
        power_modifier_ratio=0.8,
    )

    result = apply_plant_scada_events(frame, (event,))

    assert result.frame.loc[1, "gross_inverter_power_mw"] == 8.0
    assert result.frame.loc[1, "export_power_mw"] == 7.2


def test_meter_reset_rebases_cumulative_register() -> None:
    frame = _plant_frame()
    event = _event(
        event_type=EventType.METER_RESET,
        scope=EventScope.SENSOR,
        asset_id="MTR-001",
        power_modifier_ratio=None,
        parameters_json='{"reset_value_mwh":0.0}',
    )

    result = apply_plant_scada_events(frame, (event,))

    assert result.frame.loc[1, "cumulative_export_energy_mwh"] == 0.0
    assert result.frame.loc[2, "cumulative_export_energy_mwh"] == 2.25


def test_apply_functions_do_not_mutate_input_frames() -> None:
    weather = _weather_frame()
    original = weather.copy(deep=True)
    event = _event(
        event_type=EventType.STORM_EVENT,
        power_modifier_ratio=0.5,
    )

    _ = apply_weather_events(weather, (event,))

    pd.testing.assert_frame_equal(weather, original)


def test_power_availability_modifier_combines_matching_events() -> None:
    timestamps = _timestamps()
    events = (
        _event(
            event_type=EventType.INVERTER_DERATING,
            scope=EventScope.INVERTER,
            asset_id="INV-001",
            power_modifier_ratio=0.8,
        ),
        _event(
            event_type=EventType.THERMAL_DERATING,
            scope=EventScope.INVERTER,
            asset_id="INV-001",
            power_modifier_ratio=0.5,
            event_id="GTE-2026-00000002",
        ),
    )

    values = power_availability_modifier(
        events,
        timestamps,
        plant_id="PLANT-001",
        asset_ids={EventScope.INVERTER: "INV-001"},
    )

    assert values.tolist() == [1.0, 0.4, 0.4, 1.0, 1.0]


def test_grid_export_limit_applies_curtailment() -> None:
    events = (
        _event(
            event_type=EventType.GRID_CURTAILMENT,
            power_modifier_ratio=0.6,
        ),
    )

    limits = grid_export_limit(
        events,
        _timestamps(),
        plant_id="PLANT-001",
        plant_capacity_mw=10.0,
    )

    assert limits.tolist() == [10.0, 6.0, 6.0, 10.0, 10.0]


@pytest.mark.parametrize("value", [True, "10", None])
def test_grid_export_limit_rejects_invalid_capacity_type(value: object) -> None:
    with pytest.raises(TypeError, match="must be numeric"):
        grid_export_limit(
            (),
            _timestamps(),
            plant_id="PLANT-001",
            plant_capacity_mw=value,  # type: ignore[arg-type]
        )


def test_grid_export_limit_rejects_negative_capacity() -> None:
    with pytest.raises(ValueError, match="must be non-negative"):
        grid_export_limit(
            (),
            _timestamps(),
            plant_id="PLANT-001",
            plant_capacity_mw=-1.0,
        )


def test_recovery_curve_supports_linear_ramp() -> None:
    event = _event(
        event_type=EventType.INVERTER_DERATING,
        power_modifier_ratio=0.5,
        parameters_json=(
            '{"recovery_behavior":"linear_ramp",' '"recovery_minutes":30}'
        ),
    )
    timestamps = pd.date_range(
        datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        periods=6,
        freq="15min",
    )

    curve = recovery_curve(event, timestamps)

    assert curve[1] == 0.5
    assert curve[2] == 0.5
    assert curve[3] == 0.5
    assert curve[4] == pytest.approx(0.75)
    assert curve[5] == 1.0


def test_quality_flag_overlay_obeys_precedence() -> None:
    quality = quality_flag_overlay(
        ["good", "good", "good"],
        {
            "suspect": [True, True, True],
            "stuck": [False, True, True],
            "missing": [False, False, True],
        },
    )

    assert quality.tolist() == ["suspect", "stuck", "missing"]


def test_effect_summary_serializes_values() -> None:
    summary = EffectSummary(
        ground_truth_event_id="GTE-2026-00000001",
        event_type=EventType.GRID_OUTAGE,
        target=EffectTarget.PLANT_SCADA,
        affected_rows=2,
        affected_columns=("export_power_mw",),
        start_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
        end_at_utc=datetime(2026, 1, 1, 1, tzinfo=UTC),
    )

    record = summary.to_record()

    assert record["event_type"] == "grid_outage"
    assert record["target"] == "plant_scada"
    assert record["affected_rows"] == 2


def test_effect_summaries_to_frame() -> None:
    summary = EffectSummary(
        ground_truth_event_id="GTE-2026-00000001",
        event_type=EventType.GRID_OUTAGE,
        target=EffectTarget.PLANT_SCADA,
        affected_rows=2,
        affected_columns=("export_power_mw",),
        start_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
        end_at_utc=datetime(2026, 1, 1, 1, tzinfo=UTC),
    )

    frame = effect_summaries_to_frame((summary,))

    assert list(frame.columns) == [
        "ground_truth_event_id",
        "event_type",
        "target",
        "affected_rows",
        "affected_columns",
        "start_at_utc",
        "end_at_utc",
    ]
    assert frame.loc[0, "event_type"] == "grid_outage"


def test_empty_event_collection_returns_prepared_copy() -> None:
    frame = _weather_frame()

    result = apply_weather_events(frame, ())

    assert result.summaries == ()
    assert "quality_flag" in result.frame.columns
    assert "ground_truth_event_id" in result.frame.columns
    assert len(result.frame) == len(frame)


def test_apply_weather_events_rejects_non_dataframe() -> None:
    with pytest.raises(TypeError, match="must be a pandas DataFrame"):
        apply_weather_events(  # type: ignore[arg-type]
            [],
            (),
        )
