"""
Synthetic event-effect engine for EOIP Phase 2.

This module applies scheduled ground-truth events to weather, inverter SCADA,
and plant SCADA DataFrames. It is intentionally pure with respect to scheduling
and file I/O: callers provide source frames and events, and receive transformed
copies plus deterministic effect summaries.

Supported effect families include:

- physical power modifiers;
- grid export limits;
- weather-channel modifiers;
- sensor drift and stuck values;
- telemetry gaps;
- revenue-meter resets;
- quality-flag overlays;
- recovery curves.

The module follows the event-precedence contract from the Phase 2
implementation plan:

- grid outage dominates curtailment;
- trips dominate derating;
- missing telemetry dominates measurement drift;
- planned maintenance remains distinguishable from failure.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

import numpy as np
import pandas as pd

from eoip.synthetic.events.catalogue import EventScope, EventType
from eoip.synthetic.events.scheduler import SyntheticEvent


class EffectTarget(StrEnum):
    """Supported target datasets for event effects."""

    WEATHER = "weather"
    INVERTER_SCADA = "inverter_scada"
    PLANT_SCADA = "plant_scada"


class EffectKind(StrEnum):
    """Canonical effect categories."""

    PHYSICAL = "physical"
    MEASUREMENT = "measurement"
    QUALITY = "quality"
    STRUCTURAL = "structural"


@dataclass(frozen=True, slots=True)
class EffectApplicationConfig:
    """Configuration for deterministic effect application."""

    timestamp_column: str = "timestamp_utc"
    plant_id_column: str = "plant_id"
    inverter_id_column: str = "inverter_id"
    feeder_id_column: str = "feeder_id"
    transformer_id_column: str = "transformer_id"
    meter_id_column: str = "meter_id"
    quality_flag_column: str = "quality_flag"
    ground_truth_event_id_column: str = "ground_truth_event_id"
    default_good_quality: str = "good"
    missing_quality: str = "missing"
    suspect_quality: str = "suspect"
    stuck_quality: str = "stuck"
    drop_rows_for_telemetry_gap: bool = False

    def __post_init__(self) -> None:
        """Validate configuration text fields."""
        text_fields = (
            "timestamp_column",
            "plant_id_column",
            "inverter_id_column",
            "feeder_id_column",
            "transformer_id_column",
            "meter_id_column",
            "quality_flag_column",
            "ground_truth_event_id_column",
            "default_good_quality",
            "missing_quality",
            "suspect_quality",
            "stuck_quality",
        )
        for field_name in text_fields:
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string.")
            if not value.strip():
                raise ValueError(f"{field_name} cannot be empty.")

        if not isinstance(self.drop_rows_for_telemetry_gap, bool):
            raise TypeError("drop_rows_for_telemetry_gap must be a boolean.")


@dataclass(frozen=True, slots=True)
class EffectSummary:
    """Summary of one applied event effect."""

    ground_truth_event_id: str
    event_type: EventType
    target: EffectTarget
    affected_rows: int
    affected_columns: tuple[str, ...]
    start_at_utc: datetime
    end_at_utc: datetime

    def to_record(self) -> dict[str, object]:
        """Return a serialization-ready summary record."""
        return {
            "ground_truth_event_id": self.ground_truth_event_id,
            "event_type": self.event_type.value,
            "target": self.target.value,
            "affected_rows": self.affected_rows,
            "affected_columns": self.affected_columns,
            "start_at_utc": self.start_at_utc,
            "end_at_utc": self.end_at_utc,
        }


@dataclass(frozen=True, slots=True)
class EffectResult:
    """Transformed dataset plus effect summaries."""

    frame: pd.DataFrame
    summaries: tuple[EffectSummary, ...]


def apply_weather_events(
    weather: pd.DataFrame,
    events: Iterable[SyntheticEvent],
    *,
    config: EffectApplicationConfig | None = None,
) -> EffectResult:
    """Apply weather and weather-sensor events to a weather DataFrame."""
    resolved_config = config or EffectApplicationConfig()
    frame = _prepare_frame(weather, resolved_config)
    summaries: list[EffectSummary] = []

    ordered_events = _ordered_events(events)

    for event in ordered_events:
        if event.event_type not in {
            EventType.STORM_EVENT,
            EventType.SENSOR_DRIFT,
            EventType.SENSOR_STUCK,
            EventType.TELEMETRY_GAP,
            EventType.HIGH_TEMPERATURE_STRESS,
        }:
            continue

        mask = build_event_mask(
            frame,
            event,
            target=EffectTarget.WEATHER,
            config=resolved_config,
        )
        if not mask.any():
            continue

        affected_columns: list[str] = []

        if event.event_type is EventType.STORM_EVENT:
            affected_columns.extend(_apply_storm_weather_effect(frame, mask, event))
        elif event.event_type is EventType.HIGH_TEMPERATURE_STRESS:
            affected_columns.extend(_apply_high_temperature_effect(frame, mask, event))
        elif event.event_type is EventType.SENSOR_DRIFT:
            affected_columns.extend(
                _apply_sensor_drift(
                    frame,
                    mask,
                    event,
                    resolved_config,
                )
            )
        elif event.event_type is EventType.SENSOR_STUCK:
            affected_columns.extend(
                _apply_sensor_stuck(
                    frame,
                    mask,
                    event,
                    resolved_config,
                )
            )
        elif event.event_type is EventType.TELEMETRY_GAP:
            frame, columns = _apply_telemetry_gap(
                frame,
                mask,
                event,
                resolved_config,
            )
            affected_columns.extend(columns)

        _stamp_event_id(frame, mask, event, resolved_config)

        summaries.append(
            _summary(
                event=event,
                target=EffectTarget.WEATHER,
                mask=mask,
                columns=affected_columns,
            )
        )

    return EffectResult(frame=frame, summaries=tuple(summaries))


def apply_inverter_scada_events(
    inverter_scada: pd.DataFrame,
    events: Iterable[SyntheticEvent],
    *,
    config: EffectApplicationConfig | None = None,
) -> EffectResult:
    """Apply physical and measurement events to inverter SCADA."""
    resolved_config = config or EffectApplicationConfig()
    frame = _prepare_frame(inverter_scada, resolved_config)
    summaries: list[EffectSummary] = []

    for event in _ordered_events(events):
        if event.event_type not in {
            EventType.GRID_OUTAGE,
            EventType.PLANT_TRIP,
            EventType.FEEDER_TRIP,
            EventType.TRANSFORMER_TRIP,
            EventType.INVERTER_TRIP,
            EventType.INVERTER_DERATING,
            EventType.THERMAL_DERATING,
            EventType.MPPT_FAULT,
            EventType.DC_STRING_LOSS,
            EventType.MAINTENANCE_OUTAGE,
            EventType.SENSOR_DRIFT,
            EventType.SENSOR_STUCK,
            EventType.TELEMETRY_GAP,
        }:
            continue

        mask = build_event_mask(
            frame,
            event,
            target=EffectTarget.INVERTER_SCADA,
            config=resolved_config,
        )
        if not mask.any():
            continue

        affected_columns: list[str] = []

        if event.event_type in {
            EventType.GRID_OUTAGE,
            EventType.PLANT_TRIP,
            EventType.FEEDER_TRIP,
            EventType.TRANSFORMER_TRIP,
            EventType.INVERTER_TRIP,
            EventType.MAINTENANCE_OUTAGE,
        }:
            affected_columns.extend(_apply_trip_effect(frame, mask, event))
        elif event.event_type in {
            EventType.INVERTER_DERATING,
            EventType.THERMAL_DERATING,
            EventType.MPPT_FAULT,
            EventType.DC_STRING_LOSS,
        }:
            affected_columns.extend(_apply_derating_effect(frame, mask, event))
        elif event.event_type is EventType.SENSOR_DRIFT:
            affected_columns.extend(
                _apply_sensor_drift(
                    frame,
                    mask,
                    event,
                    resolved_config,
                )
            )
        elif event.event_type is EventType.SENSOR_STUCK:
            affected_columns.extend(
                _apply_sensor_stuck(
                    frame,
                    mask,
                    event,
                    resolved_config,
                )
            )
        elif event.event_type is EventType.TELEMETRY_GAP:
            frame, columns = _apply_telemetry_gap(
                frame,
                mask,
                event,
                resolved_config,
            )
            affected_columns.extend(columns)

        _stamp_event_id(frame, mask, event, resolved_config)
        _overlay_quality_for_event(
            frame,
            mask,
            event,
            resolved_config,
        )

        summaries.append(
            _summary(
                event=event,
                target=EffectTarget.INVERTER_SCADA,
                mask=mask,
                columns=affected_columns,
            )
        )

    return EffectResult(frame=frame, summaries=tuple(summaries))


def apply_plant_scada_events(
    plant_scada: pd.DataFrame,
    events: Iterable[SyntheticEvent],
    *,
    config: EffectApplicationConfig | None = None,
) -> EffectResult:
    """Apply plant-level physical, grid, meter, and telemetry effects."""
    resolved_config = config or EffectApplicationConfig()
    frame = _prepare_frame(plant_scada, resolved_config)
    summaries: list[EffectSummary] = []

    for event in _ordered_events(events):
        if event.event_type not in {
            EventType.GRID_OUTAGE,
            EventType.GRID_CURTAILMENT,
            EventType.PLANT_TRIP,
            EventType.MAINTENANCE_OUTAGE,
            EventType.METER_RESET,
            EventType.SENSOR_DRIFT,
            EventType.SENSOR_STUCK,
            EventType.TELEMETRY_GAP,
            EventType.SOILING_ACCUMULATION,
            EventType.CLEANING_RECOVERY,
            EventType.STORM_EVENT,
        }:
            continue

        mask = build_event_mask(
            frame,
            event,
            target=EffectTarget.PLANT_SCADA,
            config=resolved_config,
        )
        if not mask.any():
            continue

        affected_columns: list[str] = []

        if event.event_type in {
            EventType.GRID_OUTAGE,
            EventType.PLANT_TRIP,
            EventType.MAINTENANCE_OUTAGE,
        }:
            affected_columns.extend(_apply_plant_trip_effect(frame, mask, event))
        elif event.event_type is EventType.GRID_CURTAILMENT:
            affected_columns.extend(_apply_grid_curtailment(frame, mask, event))
        elif event.event_type in {
            EventType.SOILING_ACCUMULATION,
            EventType.STORM_EVENT,
        }:
            affected_columns.extend(_apply_plant_derating(frame, mask, event))
        elif event.event_type is EventType.CLEANING_RECOVERY:
            affected_columns.extend(_apply_cleaning_recovery(frame, mask, event))
        elif event.event_type is EventType.METER_RESET:
            affected_columns.extend(_apply_meter_reset(frame, mask, event))
        elif event.event_type is EventType.SENSOR_DRIFT:
            affected_columns.extend(
                _apply_sensor_drift(
                    frame,
                    mask,
                    event,
                    resolved_config,
                )
            )
        elif event.event_type is EventType.SENSOR_STUCK:
            affected_columns.extend(
                _apply_sensor_stuck(
                    frame,
                    mask,
                    event,
                    resolved_config,
                )
            )
        elif event.event_type is EventType.TELEMETRY_GAP:
            frame, columns = _apply_telemetry_gap(
                frame,
                mask,
                event,
                resolved_config,
            )
            affected_columns.extend(columns)

        _stamp_event_id(frame, mask, event, resolved_config)
        _overlay_quality_for_event(
            frame,
            mask,
            event,
            resolved_config,
        )

        summaries.append(
            _summary(
                event=event,
                target=EffectTarget.PLANT_SCADA,
                mask=mask,
                columns=affected_columns,
            )
        )

    return EffectResult(frame=frame, summaries=tuple(summaries))


def build_event_mask(
    frame: pd.DataFrame,
    event: SyntheticEvent,
    *,
    target: EffectTarget,
    config: EffectApplicationConfig | None = None,
) -> pd.Series:
    """Build a boolean mask for event time and hierarchy scope."""
    resolved_config = config or EffectApplicationConfig()

    timestamp_column = resolved_config.timestamp_column
    if timestamp_column not in frame.columns:
        raise ValueError(f"Frame is missing timestamp column '{timestamp_column}'.")

    timestamps = pd.to_datetime(
        frame[timestamp_column],
        utc=True,
        errors="raise",
    )
    mask = (timestamps >= pd.Timestamp(event.start_at_utc)) & (
        timestamps < pd.Timestamp(event.end_at_utc)
    )

    if event.event_scope is EventScope.PORTFOLIO:
        return mask

    plant_column = resolved_config.plant_id_column
    if plant_column not in frame.columns:
        raise ValueError(f"Frame is missing plant column '{plant_column}'.")

    mask &= frame[plant_column].astype(str).str.upper() == event.plant_id.upper()

    if event.event_scope is EventScope.PLANT:
        return mask

    scope_column = _scope_column(
        event.event_scope,
        target=target,
        config=resolved_config,
    )
    if scope_column is None:
        return mask

    if scope_column not in frame.columns:
        raise ValueError(
            f"Frame is missing scope column '{scope_column}' "
            f"for event {event.ground_truth_event_id}."
        )

    mask &= frame[scope_column].astype(str).str.upper() == event.asset_id.upper()
    return mask


def power_availability_modifier(
    events: Iterable[SyntheticEvent],
    timestamps: Sequence[Any],
    *,
    plant_id: str,
    asset_ids: Mapping[EventScope, str] | None = None,
) -> np.ndarray:
    """Return combined physical availability modifiers for timestamps."""
    normalized_timestamps = pd.to_datetime(
        pd.Series(timestamps),
        utc=True,
    )
    modifiers = np.ones(len(normalized_timestamps), dtype=float)
    asset_ids = asset_ids or {}

    for event in _ordered_events(events):
        if event.power_modifier_ratio is None:
            continue

        if not _event_matches_asset_context(
            event,
            plant_id=plant_id,
            asset_ids=asset_ids,
        ):
            continue

        mask = (
            (normalized_timestamps >= pd.Timestamp(event.start_at_utc))
            & (normalized_timestamps < pd.Timestamp(event.end_at_utc))
        ).to_numpy()

        event_modifier = recovery_curve(
            event,
            normalized_timestamps,
        )
        modifiers[mask] *= event_modifier[mask]

    return np.clip(modifiers, 0.0, 1.0)


def grid_export_limit(
    events: Iterable[SyntheticEvent],
    timestamps: Sequence[Any],
    *,
    plant_id: str,
    plant_capacity_mw: float,
) -> np.ndarray:
    """Return event-driven plant export limits in MW."""
    if isinstance(plant_capacity_mw, bool) or not isinstance(
        plant_capacity_mw,
        (int, float),
    ):
        raise TypeError("plant_capacity_mw must be numeric.")

    if not math.isfinite(plant_capacity_mw):
        raise ValueError("plant_capacity_mw must be finite.")

    if plant_capacity_mw < 0:
        raise ValueError("plant_capacity_mw must be non-negative.")

    normalized_timestamps = pd.to_datetime(
        pd.Series(timestamps),
        utc=True,
    )
    limits = np.full(
        len(normalized_timestamps),
        float(plant_capacity_mw),
        dtype=float,
    )

    for event in _ordered_events(events):
        if event.plant_id.upper() != plant_id.upper():
            continue

        if event.event_type not in {
            EventType.GRID_OUTAGE,
            EventType.GRID_CURTAILMENT,
            EventType.PLANT_TRIP,
        }:
            continue

        mask = (
            (normalized_timestamps >= pd.Timestamp(event.start_at_utc))
            & (normalized_timestamps < pd.Timestamp(event.end_at_utc))
        ).to_numpy()

        modifier = event.power_modifier_ratio
        if modifier is None:
            continue

        limits[mask] = np.minimum(
            limits[mask],
            plant_capacity_mw * modifier,
        )

    return limits


def recovery_curve(
    event: SyntheticEvent,
    timestamps: Sequence[Any],
) -> np.ndarray:
    """Return a deterministic event modifier/recovery curve."""
    normalized = pd.to_datetime(
        pd.Series(timestamps),
        utc=True,
    )
    curve = np.ones(len(normalized), dtype=float)

    modifier = event.power_modifier_ratio
    if modifier is None:
        return curve

    active_mask = (
        (normalized >= pd.Timestamp(event.start_at_utc))
        & (normalized < pd.Timestamp(event.end_at_utc))
    ).to_numpy()
    curve[active_mask] = modifier

    parameters = _parameters(event)
    recovery_behavior = str(parameters.get("recovery_behavior", "instant"))

    if recovery_behavior == "instant":
        return curve

    duration = event.end_at_utc - event.start_at_utc
    recovery_minutes = max(
        float(parameters.get("recovery_minutes", 60.0)),
        1.0,
    )
    recovery_end = event.end_at_utc + pd.Timedelta(minutes=recovery_minutes)

    recovery_mask = (
        (normalized >= pd.Timestamp(event.end_at_utc))
        & (normalized < pd.Timestamp(recovery_end))
    ).to_numpy()

    if not recovery_mask.any():
        return curve

    elapsed = (
        normalized[recovery_mask] - pd.Timestamp(event.end_at_utc)
    ).dt.total_seconds().to_numpy() / 60.0
    fraction = np.clip(elapsed / recovery_minutes, 0.0, 1.0)

    if recovery_behavior == "linear_ramp":
        curve[recovery_mask] = modifier + (1.0 - modifier) * fraction
    elif recovery_behavior == "exponential":
        curve[recovery_mask] = 1.0 - (1.0 - modifier) * np.exp(-4.0 * fraction)
    elif recovery_behavior == "manual_reset":
        curve[recovery_mask] = modifier

    _ = duration
    return np.clip(curve, 0.0, 1.0)


def quality_flag_overlay(
    base_quality: Sequence[str],
    event_masks: Mapping[str, Sequence[bool]],
    *,
    missing_label: str = "missing",
    stuck_label: str = "stuck",
    suspect_label: str = "suspect",
) -> np.ndarray:
    """Overlay quality states using deterministic precedence."""
    quality = np.asarray(base_quality, dtype=object).copy()

    suspect = np.asarray(
        event_masks.get("suspect", np.zeros(len(quality), dtype=bool)),
        dtype=bool,
    )
    stuck = np.asarray(
        event_masks.get("stuck", np.zeros(len(quality), dtype=bool)),
        dtype=bool,
    )
    missing = np.asarray(
        event_masks.get("missing", np.zeros(len(quality), dtype=bool)),
        dtype=bool,
    )

    quality[suspect] = suspect_label
    quality[stuck] = stuck_label
    quality[missing] = missing_label
    return quality


def _prepare_frame(
    frame: pd.DataFrame,
    config: EffectApplicationConfig,
) -> pd.DataFrame:
    """Return a defensive normalized frame copy."""
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame.")

    result = frame.copy(deep=True)

    if config.timestamp_column not in result.columns:
        raise ValueError(
            f"Frame is missing timestamp column " f"'{config.timestamp_column}'."
        )

    result[config.timestamp_column] = pd.to_datetime(
        result[config.timestamp_column],
        utc=True,
        errors="raise",
    )

    if config.quality_flag_column not in result.columns:
        result[config.quality_flag_column] = config.default_good_quality

    if config.ground_truth_event_id_column not in result.columns:
        result[config.ground_truth_event_id_column] = pd.NA

    return result


def _ordered_events(
    events: Iterable[SyntheticEvent],
) -> tuple[SyntheticEvent, ...]:
    """Return events sorted by explicit precedence and stable keys."""
    precedence = {
        EventType.TELEMETRY_GAP: 0,
        EventType.GRID_OUTAGE: 1,
        EventType.PLANT_TRIP: 2,
        EventType.FEEDER_TRIP: 3,
        EventType.TRANSFORMER_TRIP: 4,
        EventType.INVERTER_TRIP: 5,
        EventType.MAINTENANCE_OUTAGE: 6,
        EventType.GRID_CURTAILMENT: 7,
        EventType.INVERTER_DERATING: 8,
        EventType.THERMAL_DERATING: 9,
        EventType.MPPT_FAULT: 10,
        EventType.DC_STRING_LOSS: 11,
        EventType.SOILING_ACCUMULATION: 12,
        EventType.CLEANING_RECOVERY: 13,
        EventType.STORM_EVENT: 14,
        EventType.HIGH_TEMPERATURE_STRESS: 15,
        EventType.SENSOR_STUCK: 16,
        EventType.SENSOR_DRIFT: 17,
        EventType.METER_RESET: 18,
    }
    return tuple(
        sorted(
            events,
            key=lambda event: (
                precedence.get(event.event_type, 999),
                event.start_at_utc,
                event.asset_id,
                event.ground_truth_event_id,
            ),
        )
    )


def _scope_column(
    scope: EventScope,
    *,
    target: EffectTarget,
    config: EffectApplicationConfig,
) -> str | None:
    """Return the target column corresponding to event scope."""
    if scope is EventScope.INVERTER:
        return config.inverter_id_column

    if scope is EventScope.FEEDER:
        return config.feeder_id_column

    if scope is EventScope.TRANSFORMER:
        return config.transformer_id_column

    if scope is EventScope.SENSOR:
        if target is EffectTarget.PLANT_SCADA:
            return config.meter_id_column
        return None

    return None


def _apply_trip_effect(
    frame: pd.DataFrame,
    mask: pd.Series,
    event: SyntheticEvent,
) -> tuple[str, ...]:
    """Apply zero-power outage behavior to inverter SCADA."""
    candidate_columns = (
        "dc_power_kw",
        "ac_power_kw",
        "interval_energy_kwh",
        "dc_current_a",
        "ac_current_a",
        "reactive_power_kvar",
        "apparent_power_kva",
    )
    affected: list[str] = []

    for column in candidate_columns:
        if column in frame.columns:
            frame.loc[mask, column] = 0.0
            affected.append(column)

    if "availability_ratio" in frame.columns:
        frame.loc[mask, "availability_ratio"] = 0.0
        affected.append("availability_ratio")

    if "operating_state" in frame.columns:
        state = (
            "maintenance"
            if event.event_type is EventType.MAINTENANCE_OUTAGE
            else "fault"
        )
        frame.loc[mask, "operating_state"] = state
        affected.append("operating_state")

    return tuple(affected)


def _apply_derating_effect(
    frame: pd.DataFrame,
    mask: pd.Series,
    event: SyntheticEvent,
) -> tuple[str, ...]:
    """Apply partial physical derating to inverter SCADA."""
    modifier = event.power_modifier_ratio
    if modifier is None:
        return ()

    affected: list[str] = []
    for column in (
        "dc_power_kw",
        "ac_power_kw",
        "interval_energy_kwh",
        "dc_current_a",
        "ac_current_a",
        "reactive_power_kvar",
        "apparent_power_kva",
    ):
        if column in frame.columns:
            frame.loc[mask, column] = (
                pd.to_numeric(
                    frame.loc[mask, column],
                    errors="coerce",
                )
                * modifier
            )
            affected.append(column)

    if "availability_ratio" in frame.columns:
        frame.loc[mask, "availability_ratio"] = np.minimum(
            pd.to_numeric(
                frame.loc[mask, "availability_ratio"],
                errors="coerce",
            ),
            modifier,
        )
        affected.append("availability_ratio")

    if "operating_state" in frame.columns:
        frame.loc[mask, "operating_state"] = "derated"
        affected.append("operating_state")

    return tuple(affected)


def _apply_plant_trip_effect(
    frame: pd.DataFrame,
    mask: pd.Series,
    event: SyntheticEvent,
) -> tuple[str, ...]:
    """Apply zero-export plant outage behavior."""
    affected: list[str] = []

    for column in (
        "gross_inverter_power_mw",
        "export_power_mw",
        "interval_export_energy_mwh",
        "curtailment_loss_mw",
    ):
        if column in frame.columns:
            frame.loc[mask, column] = 0.0
            affected.append(column)

    if "available_capacity_mw" in frame.columns:
        frame.loc[mask, "available_capacity_mw"] = 0.0
        affected.append("available_capacity_mw")

    return tuple(affected)


def _apply_grid_curtailment(
    frame: pd.DataFrame,
    mask: pd.Series,
    event: SyntheticEvent,
) -> tuple[str, ...]:
    """Apply plant export cap and explicit curtailment loss."""
    modifier = event.power_modifier_ratio
    if modifier is None:
        return ()

    affected: list[str] = []

    if "gross_inverter_power_mw" in frame.columns:
        gross = pd.to_numeric(
            frame.loc[mask, "gross_inverter_power_mw"],
            errors="coerce",
        )
    elif "expected_power_mw" in frame.columns:
        gross = pd.to_numeric(
            frame.loc[mask, "expected_power_mw"],
            errors="coerce",
        )
    else:
        gross = pd.Series(
            0.0,
            index=frame.index[mask],
            dtype=float,
        )

    limited = gross * modifier

    if "export_power_mw" in frame.columns:
        previous = pd.to_numeric(
            frame.loc[mask, "export_power_mw"],
            errors="coerce",
        )
        frame.loc[mask, "export_power_mw"] = np.minimum(
            previous,
            limited,
        )
        affected.append("export_power_mw")

    if "curtailment_loss_mw" in frame.columns:
        frame.loc[mask, "curtailment_loss_mw"] = np.maximum(
            gross - limited,
            0.0,
        )
        affected.append("curtailment_loss_mw")

    if (
        "interval_export_energy_mwh" in frame.columns
        and "export_power_mw" in frame.columns
    ):
        frame.loc[mask, "interval_export_energy_mwh"] = (
            pd.to_numeric(
                frame.loc[mask, "export_power_mw"],
                errors="coerce",
            )
            * 0.25
        )
        affected.append("interval_export_energy_mwh")

    return tuple(affected)


def _apply_plant_derating(
    frame: pd.DataFrame,
    mask: pd.Series,
    event: SyntheticEvent,
) -> tuple[str, ...]:
    """Apply plant-level derating for soiling or storm events."""
    modifier = event.power_modifier_ratio
    if modifier is None:
        return ()

    affected: list[str] = []

    for column in (
        "gross_inverter_power_mw",
        "export_power_mw",
        "interval_export_energy_mwh",
    ):
        if column in frame.columns:
            frame.loc[mask, column] = (
                pd.to_numeric(
                    frame.loc[mask, column],
                    errors="coerce",
                )
                * modifier
            )
            affected.append(column)

    return tuple(affected)


def _apply_cleaning_recovery(
    frame: pd.DataFrame,
    mask: pd.Series,
    event: SyntheticEvent,
) -> tuple[str, ...]:
    """Apply bounded cleaning-recovery uplift."""
    modifier = event.power_modifier_ratio
    if modifier is None:
        modifier = 1.0

    uplift = max(modifier, 1.0)
    affected: list[str] = []

    for column in (
        "gross_inverter_power_mw",
        "export_power_mw",
        "interval_export_energy_mwh",
    ):
        if column in frame.columns:
            frame.loc[mask, column] = (
                pd.to_numeric(
                    frame.loc[mask, column],
                    errors="coerce",
                )
                * uplift
            )
            affected.append(column)

    return tuple(affected)


def _apply_storm_weather_effect(
    frame: pd.DataFrame,
    mask: pd.Series,
    event: SyntheticEvent,
) -> tuple[str, ...]:
    """Apply storm effects to irradiance, wind, and rain."""
    modifier = event.power_modifier_ratio
    if modifier is None:
        modifier = 0.5

    affected: list[str] = []

    for column in (
        "ghi_w_m2",
        "dni_w_m2",
        "dhi_w_m2",
        "poa_irradiance_w_m2",
    ):
        if column in frame.columns:
            frame.loc[mask, column] = (
                pd.to_numeric(
                    frame.loc[mask, column],
                    errors="coerce",
                )
                * modifier
            )
            affected.append(column)

    if "wind_speed_m_s" in frame.columns:
        frame.loc[mask, "wind_speed_m_s"] = (
            pd.to_numeric(
                frame.loc[mask, "wind_speed_m_s"],
                errors="coerce",
            )
            * 1.8
        )
        affected.append("wind_speed_m_s")

    if "precipitation_mm" in frame.columns:
        frame.loc[mask, "precipitation_mm"] = np.maximum(
            pd.to_numeric(
                frame.loc[mask, "precipitation_mm"],
                errors="coerce",
            ),
            1.0,
        )
        affected.append("precipitation_mm")

    return tuple(affected)


def _apply_high_temperature_effect(
    frame: pd.DataFrame,
    mask: pd.Series,
    event: SyntheticEvent,
) -> tuple[str, ...]:
    """Apply high-temperature stress to weather channels."""
    parameters = _parameters(event)
    uplift = float(parameters.get("temperature_uplift_c", 8.0))
    affected: list[str] = []

    for column in (
        "ambient_temperature_c",
        "cell_temperature_c",
    ):
        if column in frame.columns:
            frame.loc[mask, column] = (
                pd.to_numeric(
                    frame.loc[mask, column],
                    errors="coerce",
                )
                + uplift
            )
            affected.append(column)

    return tuple(affected)


def _apply_sensor_drift(
    frame: pd.DataFrame,
    mask: pd.Series,
    event: SyntheticEvent,
    config: EffectApplicationConfig,
) -> tuple[str, ...]:
    """Apply gradual multiplicative sensor drift."""
    channel = event.measurement_channel
    if channel is None or channel not in frame.columns:
        return ()

    bias = event.measurement_bias
    if bias is None:
        bias = 0.1

    positions = np.flatnonzero(mask.to_numpy())
    if len(positions) == 0:
        return ()

    ramp = np.linspace(0.0, bias, len(positions))
    values = pd.to_numeric(
        frame.loc[mask, channel],
        errors="coerce",
    ).to_numpy(dtype=float)
    frame.loc[mask, channel] = values * (1.0 + ramp)
    frame.loc[mask, config.quality_flag_column] = config.suspect_quality
    return (channel, config.quality_flag_column)


def _apply_sensor_stuck(
    frame: pd.DataFrame,
    mask: pd.Series,
    event: SyntheticEvent,
    config: EffectApplicationConfig,
) -> tuple[str, ...]:
    """Apply a constant repeated value to one channel."""
    channel = event.measurement_channel
    if channel is None or channel not in frame.columns:
        return ()

    indices = frame.index[mask]
    if len(indices) == 0:
        return ()

    first_value = frame.loc[indices[0], channel]
    frame.loc[mask, channel] = first_value
    frame.loc[mask, config.quality_flag_column] = config.stuck_quality
    return (channel, config.quality_flag_column)


def _apply_telemetry_gap(
    frame: pd.DataFrame,
    mask: pd.Series,
    event: SyntheticEvent,
    config: EffectApplicationConfig,
) -> tuple[pd.DataFrame, tuple[str, ...]]:
    """Apply telemetry missingness or intentional row deletion."""
    _ = event

    if config.drop_rows_for_telemetry_gap:
        return frame.loc[~mask].reset_index(drop=True), ("rows",)

    excluded = {
        config.timestamp_column,
        config.plant_id_column,
        config.inverter_id_column,
        config.feeder_id_column,
        config.transformer_id_column,
        config.meter_id_column,
        config.quality_flag_column,
        config.ground_truth_event_id_column,
    }
    value_columns = tuple(column for column in frame.columns if column not in excluded)

    for column in value_columns:
        frame.loc[mask, column] = pd.NA

    frame.loc[mask, config.quality_flag_column] = config.missing_quality
    return (
        frame,
        (*value_columns, config.quality_flag_column),
    )


def _apply_meter_reset(
    frame: pd.DataFrame,
    mask: pd.Series,
    event: SyntheticEvent,
) -> tuple[str, ...]:
    """Apply a labeled cumulative meter-register discontinuity."""
    column = "cumulative_export_energy_mwh"
    if column not in frame.columns:
        return ()

    indices = frame.index[mask]
    if len(indices) == 0:
        return ()

    reset_value = float(_parameters(event).get("reset_value_mwh", 0.0))
    first_index = indices[0]
    original = pd.to_numeric(
        frame.loc[indices, column],
        errors="coerce",
    )
    baseline = original.iloc[0]
    frame.loc[indices, column] = original - baseline + reset_value
    _ = first_index
    return (column,)


def _stamp_event_id(
    frame: pd.DataFrame,
    mask: pd.Series,
    event: SyntheticEvent,
    config: EffectApplicationConfig,
) -> None:
    """Attach the most recent/highest-precedence truth event ID."""
    column = config.ground_truth_event_id_column
    if column not in frame.columns:
        frame[column] = pd.NA

    frame.loc[mask, column] = event.ground_truth_event_id


def _overlay_quality_for_event(
    frame: pd.DataFrame,
    mask: pd.Series,
    event: SyntheticEvent,
    config: EffectApplicationConfig,
) -> None:
    """Overlay event-driven quality flags with explicit precedence."""
    column = config.quality_flag_column

    if event.event_type is EventType.TELEMETRY_GAP:
        frame.loc[mask, column] = config.missing_quality
    elif event.event_type is EventType.SENSOR_STUCK:
        frame.loc[mask, column] = config.stuck_quality
    elif event.event_type is EventType.SENSOR_DRIFT:
        frame.loc[mask, column] = config.suspect_quality


def _event_matches_asset_context(
    event: SyntheticEvent,
    *,
    plant_id: str,
    asset_ids: Mapping[EventScope, str],
) -> bool:
    """Return whether an event applies to a supplied hierarchy context."""
    if event.event_scope is EventScope.PORTFOLIO:
        return True

    if event.plant_id.upper() != plant_id.upper():
        return False

    if event.event_scope is EventScope.PLANT:
        return True

    expected_asset_id = asset_ids.get(event.event_scope)
    if expected_asset_id is None:
        return False

    return event.asset_id.upper() == expected_asset_id.upper()


def _parameters(event: SyntheticEvent) -> dict[str, Any]:
    """Parse event parameters JSON safely."""
    try:
        parsed = json.loads(event.parameters_json)
    except (TypeError, json.JSONDecodeError):
        return {}

    if not isinstance(parsed, dict):
        return {}

    return parsed


def _summary(
    *,
    event: SyntheticEvent,
    target: EffectTarget,
    mask: pd.Series,
    columns: Iterable[str],
) -> EffectSummary:
    """Build a deterministic effect summary."""
    unique_columns = tuple(dict.fromkeys(columns))
    return EffectSummary(
        ground_truth_event_id=event.ground_truth_event_id,
        event_type=event.event_type,
        target=target,
        affected_rows=int(mask.sum()),
        affected_columns=unique_columns,
        start_at_utc=event.start_at_utc,
        end_at_utc=event.end_at_utc,
    )


def effect_summaries_to_frame(
    summaries: Iterable[EffectSummary],
) -> pd.DataFrame:
    """Convert effect summaries to a stable DataFrame."""
    records = [summary.to_record() for summary in summaries]
    return pd.DataFrame.from_records(
        records,
        columns=(
            "ground_truth_event_id",
            "event_type",
            "target",
            "affected_rows",
            "affected_columns",
            "start_at_utc",
            "end_at_utc",
        ),
    )


__all__ = [
    "EffectApplicationConfig",
    "EffectKind",
    "EffectResult",
    "EffectSummary",
    "EffectTarget",
    "apply_inverter_scada_events",
    "apply_plant_scada_events",
    "apply_weather_events",
    "build_event_mask",
    "effect_summaries_to_frame",
    "grid_export_limit",
    "power_availability_modifier",
    "quality_flag_overlay",
    "recovery_curve",
]
