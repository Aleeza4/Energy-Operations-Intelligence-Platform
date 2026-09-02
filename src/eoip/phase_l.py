"""Reproducible representative-evidence utilities for EOIP Phase L."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from eoip.synthetic.events.catalogue import EventScope, EventSeverity, EventType
from eoip.synthetic.events.scheduler import SyntheticEvent

EVIDENCE_TYPE = "REPRESENTATIVE_SYNTHETIC"


@dataclass(frozen=True, slots=True)
class TemporalSplit:
    """Chronological train/validation/test population with explicit boundaries."""

    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame
    train_end: pd.Timestamp
    validation_end: pd.Timestamp


def chronological_split(
    frame: pd.DataFrame,
    *,
    timestamp_column: str,
    train_fraction: float = 0.60,
    validation_fraction: float = 0.20,
) -> TemporalSplit:
    """Split unique timestamps chronologically without placing a time in two sets."""
    if frame.empty:
        raise ValueError("Cannot split an empty frame.")
    if timestamp_column not in frame:
        raise ValueError(f"Missing timestamp column: {timestamp_column}")
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("Split fractions must be between zero and one.")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("Train and validation fractions must sum below one.")

    ordered = frame.copy(deep=True)
    ordered[timestamp_column] = pd.to_datetime(
        ordered[timestamp_column], utc=True, errors="raise"
    )
    ordered = ordered.sort_values(timestamp_column, kind="stable").reset_index(
        drop=True
    )
    timestamps = pd.Index(ordered[timestamp_column].drop_duplicates())
    if len(timestamps) < 3:
        raise ValueError("At least three unique timestamps are required.")
    train_index = max(1, math.floor(len(timestamps) * train_fraction))
    validation_index = max(
        train_index + 1,
        math.floor(len(timestamps) * (train_fraction + validation_fraction)),
    )
    validation_index = min(validation_index, len(timestamps) - 1)
    train_end = pd.Timestamp(timestamps[train_index - 1])
    validation_end = pd.Timestamp(timestamps[validation_index - 1])
    train = ordered.loc[ordered[timestamp_column] <= train_end].copy()
    validation = ordered.loc[
        (ordered[timestamp_column] > train_end)
        & (ordered[timestamp_column] <= validation_end)
    ].copy()
    test = ordered.loc[ordered[timestamp_column] > validation_end].copy()
    return TemporalSplit(train, validation, test, train_end, validation_end)


def reconstruct_events(frame: pd.DataFrame) -> tuple[SyntheticEvent, ...]:
    """Reconstruct independently scheduled events from generator truth records."""
    events: list[SyntheticEvent] = []
    for record in frame.to_dict(orient="records"):
        events.append(
            SyntheticEvent(
                ground_truth_event_id=str(record["ground_truth_event_id"]),
                event_type=EventType(str(record["event_type"])),
                event_scope=EventScope(str(record["event_scope"])),
                plant_id=str(record["plant_id"]),
                asset_type=str(record["asset_type"]),
                asset_id=str(record["asset_id"]),
                parent_event_id=_optional_string(record.get("parent_event_id")),
                start_at_utc=pd.Timestamp(record["start_at_utc"]).to_pydatetime(),
                end_at_utc=pd.Timestamp(record["end_at_utc"]).to_pydatetime(),
                severity=EventSeverity(str(record["severity"])),
                severity_score=float(record["severity_score"]),
                power_modifier_ratio=_optional_float(
                    record.get("power_modifier_ratio")
                ),
                measurement_channel=_optional_string(record.get("measurement_channel")),
                measurement_bias=_optional_float(record.get("measurement_bias")),
                is_planned=bool(record["is_planned"]),
                cause_code=str(record["cause_code"]),
                parameters_json=str(record["parameters_json"]),
                expected_alarm_code=_optional_string(record.get("expected_alarm_code")),
                expected_incident=bool(record["expected_incident"]),
                expected_work_order=bool(record["expected_work_order"]),
                generation_run_id=str(record["generation_run_id"]),
                schema_version=str(record["schema_version"]),
            )
        )
    return tuple(events)


def calculate_data_quality(
    frame: pd.DataFrame,
    *,
    timestamp_column: str,
    asset_column: str,
    interval_minutes: int,
    quality_column: str = "quality_flag",
    numeric_ranges: dict[str, tuple[float, float]] | None = None,
) -> dict[str, Any]:
    """Measure slot completeness, record duplicates, nulls, and sensor validity."""
    if frame.empty:
        raise ValueError("Data-quality evaluation requires observations.")
    required = {timestamp_column, asset_column}
    missing = required - set(frame)
    if missing:
        raise ValueError(f"Missing data-quality columns: {sorted(missing)}")
    evaluated = frame.copy(deep=True)
    evaluated[timestamp_column] = pd.to_datetime(
        evaluated[timestamp_column], utc=True, errors="raise"
    )
    asset_count = int(evaluated[asset_column].nunique())
    interval_count = (
        int(
            (
                evaluated[timestamp_column].max() - evaluated[timestamp_column].min()
            ).total_seconds()
            // (interval_minutes * 60)
        )
        + 1
    )
    expected_slots = asset_count * interval_count
    observed_slots = int(
        evaluated.drop_duplicates([asset_column, timestamp_column]).shape[0]
    )
    duplicate_count = int(evaluated.duplicated([asset_column, timestamp_column]).sum())
    missing_records = max(expected_slots - observed_slots, 0)
    relevant_columns = [
        column
        for column in evaluated.columns
        if column not in {timestamp_column, asset_column}
    ]
    null_cells = int(evaluated[relevant_columns].isna().sum().sum())
    total_cells = len(evaluated) * len(relevant_columns)

    valid_values = 0
    invalid_values = 0
    for column, (minimum, maximum) in (numeric_ranges or {}).items():
        if column not in evaluated:
            continue
        values = pd.to_numeric(evaluated[column], errors="coerce")
        valid = values.notna() & np.isfinite(values) & values.between(minimum, maximum)
        valid_values += int(valid.sum())
        invalid_values += int((~valid).sum())
    sensor_total = valid_values + invalid_values
    quality_valid = None
    if quality_column in evaluated:
        quality_valid = float(
            evaluated[quality_column].astype(str).str.lower().eq("valid").mean() * 100
        )
    return {
        "asset_count": asset_count,
        "expected_slots": expected_slots,
        "observed_unique_slots": observed_slots,
        "missing_record_count": missing_records,
        "telemetry_completeness_percent": observed_slots / expected_slots * 100,
        "duplicate_record_count": duplicate_count,
        "duplicate_record_percent": duplicate_count / len(evaluated) * 100,
        "null_cell_count": null_cells,
        "null_cell_percent": (null_cells / total_cells * 100) if total_cells else 0.0,
        "sensor_values_evaluated": sensor_total,
        "sensor_valid_values": valid_values,
        "sensor_invalid_values": invalid_values,
        "sensor_validity_percent": (
            (valid_values / sensor_total * 100) if sensor_total else None
        ),
        "declared_valid_quality_percent": quality_valid,
    }


def future_failure_labels(
    observations: pd.DataFrame,
    failures: pd.DataFrame,
    *,
    timestamp_column: str,
    equipment_column: str,
    failure_timestamp_column: str,
    horizon: timedelta,
) -> pd.Series:
    """Return labels based strictly on failures after each observation."""
    from eoip.maintenance.failure_windows import label_failure_windows

    labeled = label_failure_windows(
        observations,
        failures,
        timestamp_column=timestamp_column,
        equipment_id_column=equipment_column,
        failure_timestamp_column=failure_timestamp_column,
        prediction_window=horizon,
        target_column="future_failure",
    )
    return labeled["future_failure"]


def evidence_metadata(*, generated_at: datetime | None = None) -> dict[str, str]:
    """Return mandatory evidence classification metadata."""
    timestamp = generated_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware.")
    return {
        "evidence_type": EVIDENCE_TYPE,
        "generated_at": timestamp.isoformat(),
        "production_evidence": "false",
    }


def _optional_string(value: object) -> str | None:
    return None if value is None or pd.isna(value) else str(value)


def _optional_float(value: object) -> float | None:
    return None if value is None or pd.isna(value) else float(value)


__all__ = [
    "EVIDENCE_TYPE",
    "TemporalSplit",
    "calculate_data_quality",
    "chronological_split",
    "evidence_metadata",
    "future_failure_labels",
    "reconstruct_events",
]
