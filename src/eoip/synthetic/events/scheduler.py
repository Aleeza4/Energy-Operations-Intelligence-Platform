"""
Deterministic synthetic event scheduler for EOIP Phase 2.

This module schedules event instances from the canonical event catalogue while
preserving topology scope, UTC time-grid alignment, seasonal/daylight rules,
minimum separation, overlap constraints, and deterministic identifier order.

The scheduler performs no file I/O and does not apply physical effects. It
returns immutable SyntheticEvent objects and provides a DataFrame conversion
helper for the ground-truth event dataset.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import numpy as np
import pandas as pd

from eoip.synthetic.events.catalogue import (
    DEFAULT_EVENT_CATALOGUE,
    EventCatalogue,
    EventDefinition,
    EventScope,
    EventSeverity,
    EventType,
)


class _RandomContextProtocol(Protocol):
    """Minimal random-context interface required by the scheduler."""

    def generator(
        self,
        name: str,
        entity_id: str | None = None,
    ) -> np.random.Generator:
        """Return a deterministic named NumPy random generator."""


@dataclass(frozen=True, slots=True)
class EventSchedulerConfig:
    """Configuration for deterministic event scheduling."""

    random_seed: int = 20250201
    interval_minutes: int = 15
    rate_multiplier: float = 1.0
    maximum_events_per_definition: int = 100_000
    align_to_grid: bool = True
    enforce_minimum_separation: bool = True
    enforce_overlap_rules: bool = True
    schema_version: str = "1.0.0"

    def __post_init__(self) -> None:
        """Validate scheduler configuration."""
        normalized_schema_version = self.schema_version.strip()
        object.__setattr__(
            self,
            "schema_version",
            normalized_schema_version,
        )

        if isinstance(self.random_seed, bool) or not isinstance(
            self.random_seed,
            int,
        ):
            raise TypeError("random_seed must be an integer.")

        if self.random_seed < 0:
            raise ValueError("random_seed must be non-negative.")

        if isinstance(self.interval_minutes, bool) or not isinstance(
            self.interval_minutes,
            int,
        ):
            raise TypeError("interval_minutes must be an integer.")

        if self.interval_minutes <= 0:
            raise ValueError("interval_minutes must be greater than zero.")

        if 1_440 % self.interval_minutes != 0:
            raise ValueError("interval_minutes must divide evenly into 1440.")

        if isinstance(self.rate_multiplier, bool) or not isinstance(
            self.rate_multiplier,
            (int, float),
        ):
            raise TypeError("rate_multiplier must be numeric.")

        if not math.isfinite(self.rate_multiplier):
            raise ValueError("rate_multiplier must be finite.")

        if self.rate_multiplier < 0:
            raise ValueError("rate_multiplier must be non-negative.")

        if isinstance(self.maximum_events_per_definition, bool) or not isinstance(
            self.maximum_events_per_definition, int
        ):
            raise TypeError("maximum_events_per_definition must be an integer.")

        if self.maximum_events_per_definition <= 0:
            raise ValueError("maximum_events_per_definition must be greater than zero.")

        for field_name in (
            "align_to_grid",
            "enforce_minimum_separation",
            "enforce_overlap_rules",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be a boolean.")

        if not normalized_schema_version:
            raise ValueError("schema_version cannot be empty.")


@dataclass(frozen=True, slots=True)
class EligibleAsset:
    """Normalized schedulable asset reference."""

    scope: EventScope
    plant_id: str
    asset_type: str
    asset_id: str

    def __post_init__(self) -> None:
        """Normalize and validate the asset reference."""
        normalized_plant_id = self.plant_id.strip().upper()
        normalized_asset_type = self.asset_type.strip().lower()
        normalized_asset_id = self.asset_id.strip().upper()

        object.__setattr__(self, "plant_id", normalized_plant_id)
        object.__setattr__(
            self,
            "asset_type",
            normalized_asset_type,
        )
        object.__setattr__(self, "asset_id", normalized_asset_id)

        if not isinstance(self.scope, EventScope):
            raise TypeError("scope must be an EventScope value.")

        if not normalized_plant_id:
            raise ValueError("plant_id cannot be empty.")

        if not normalized_asset_type:
            raise ValueError("asset_type cannot be empty.")

        if not normalized_asset_id:
            raise ValueError("asset_id cannot be empty.")


@dataclass(frozen=True, slots=True)
class SyntheticEvent:
    """Immutable scheduled ground-truth event."""

    ground_truth_event_id: str
    event_type: EventType
    event_scope: EventScope
    plant_id: str
    asset_type: str
    asset_id: str
    parent_event_id: str | None
    start_at_utc: datetime
    end_at_utc: datetime
    severity: EventSeverity
    severity_score: float
    power_modifier_ratio: float | None
    measurement_channel: str | None
    measurement_bias: float | None
    is_planned: bool
    cause_code: str
    parameters_json: str
    expected_alarm_code: str | None
    expected_incident: bool
    expected_work_order: bool
    generation_run_id: str
    schema_version: str

    def __post_init__(self) -> None:
        """Validate scheduled event invariants."""
        if self.start_at_utc.tzinfo is None:
            raise ValueError("start_at_utc must be timezone-aware.")

        if self.end_at_utc.tzinfo is None:
            raise ValueError("end_at_utc must be timezone-aware.")

        if self.end_at_utc <= self.start_at_utc:
            raise ValueError("end_at_utc must occur after start_at_utc.")

        if not isinstance(self.event_type, EventType):
            raise TypeError("event_type must be an EventType value.")

        if not isinstance(self.event_scope, EventScope):
            raise TypeError("event_scope must be an EventScope value.")

        if not isinstance(self.severity, EventSeverity):
            raise TypeError("severity must be an EventSeverity value.")

        if not 0.0 <= self.severity_score <= 1.0:
            raise ValueError("severity_score must be between zero and one.")

    @property
    def duration_minutes(self) -> float:
        """Return exact event duration in minutes."""
        return (self.end_at_utc - self.start_at_utc).total_seconds() / 60.0

    def to_record(self) -> dict[str, object]:
        """Return a serialization-ready event record."""
        record = asdict(self)
        record["event_type"] = self.event_type.value
        record["event_scope"] = self.event_scope.value
        record["severity"] = self.severity.value
        record["start_at_utc"] = self.start_at_utc
        record["end_at_utc"] = self.end_at_utc
        return record


class EventConflictResolver:
    """Resolve event overlaps and minimum-separation conflicts."""

    def __init__(self, catalogue: EventCatalogue) -> None:
        """Create a conflict resolver."""
        self._catalogue = catalogue

    def resolve(
        self,
        events: Iterable[SyntheticEvent],
        *,
        enforce_minimum_separation: bool,
        enforce_overlap_rules: bool,
    ) -> tuple[SyntheticEvent, ...]:
        """Return events accepted in stable priority order."""
        ordered = sorted(
            events,
            key=_event_sort_key,
        )
        accepted: list[SyntheticEvent] = []

        for candidate in ordered:
            if self._conflicts(
                candidate,
                accepted,
                enforce_minimum_separation=enforce_minimum_separation,
                enforce_overlap_rules=enforce_overlap_rules,
            ):
                continue

            accepted.append(candidate)

        return tuple(accepted)

    def _conflicts(
        self,
        candidate: SyntheticEvent,
        accepted: Sequence[SyntheticEvent],
        *,
        enforce_minimum_separation: bool,
        enforce_overlap_rules: bool,
    ) -> bool:
        """Return whether a candidate conflicts with accepted events."""
        candidate_definition = self._catalogue.get(candidate.event_type)

        for existing in accepted:
            if not _shares_affected_scope(candidate, existing):
                continue

            existing_definition = self._catalogue.get(existing.event_type)

            if (
                enforce_overlap_rules
                and _intervals_overlap(candidate, existing)
                and not _overlap_allowed(
                    candidate_definition,
                    existing_definition,
                )
            ):
                return True

            if enforce_minimum_separation:
                required_gap = max(
                    candidate_definition.minimum_separation_minutes,
                    existing_definition.minimum_separation_minutes,
                )
                if _event_gap_minutes(candidate, existing) < required_gap:
                    return True

        return False


class EventScheduler:
    """Schedule catalogue events over a normalized portfolio and time grid."""

    def __init__(
        self,
        config: EventSchedulerConfig | None = None,
        catalogue: EventCatalogue = DEFAULT_EVENT_CATALOGUE,
        random_context: _RandomContextProtocol | None = None,
    ) -> None:
        """Create a deterministic scheduler."""
        self.config = config or EventSchedulerConfig()
        self.catalogue = catalogue
        self.random_context = random_context
        self.conflict_resolver = EventConflictResolver(catalogue)

    def schedule(
        self,
        portfolio: Any,
        time_grid: Iterable[Any],
        *,
        generation_run_id: str = "RUN-UNPUBLISHED",
    ) -> tuple[SyntheticEvent, ...]:
        """Schedule, resolve, sort, and identify synthetic events."""
        timestamps = _normalize_time_grid(
            time_grid,
            interval_minutes=self.config.interval_minutes,
        )
        assets = _normalize_portfolio(portfolio)

        if not timestamps:
            raise ValueError("time_grid must contain at least one timestamp.")

        if not assets:
            raise ValueError("portfolio must contain at least one eligible asset.")

        if not generation_run_id.strip():
            raise ValueError("generation_run_id cannot be empty.")

        start = timestamps[0]
        end = timestamps[-1] + timedelta(minutes=self.config.interval_minutes)
        years = (end - start).total_seconds() / (365.25 * 24.0 * 3_600.0)

        candidates: list[SyntheticEvent] = []

        for definition in self.catalogue:
            eligible_assets = tuple(
                asset for asset in assets if asset.scope in definition.eligible_scopes
            )

            if not eligible_assets:
                continue

            definition_rng = self._generator(
                stream_name="events",
                entity_id=definition.event_type.value,
            )
            expected_count = (
                definition.annual_rate_per_eligible_asset
                * len(eligible_assets)
                * years
                * self.config.rate_multiplier
            )
            event_count = min(
                int(definition_rng.poisson(expected_count)),
                self.config.maximum_events_per_definition,
            )

            for ordinal in range(event_count):
                asset = eligible_assets[
                    int(definition_rng.integers(0, len(eligible_assets)))
                ]
                event = _schedule_candidate(
                    definition=definition,
                    asset=asset,
                    timestamps=timestamps,
                    rng=definition_rng,
                    interval_minutes=self.config.interval_minutes,
                    align_to_grid=self.config.align_to_grid,
                    generation_run_id=generation_run_id,
                    provisional_ordinal=ordinal + 1,
                    schema_version=self.config.schema_version,
                )
                if event is not None:
                    candidates.append(event)

        resolved = self.conflict_resolver.resolve(
            candidates,
            enforce_minimum_separation=(self.config.enforce_minimum_separation),
            enforce_overlap_rules=self.config.enforce_overlap_rules,
        )

        return _assign_stable_event_ids(resolved)

    def _generator(
        self,
        *,
        stream_name: str,
        entity_id: str,
    ) -> np.random.Generator:
        """Return a deterministic named generator."""
        if self.random_context is not None:
            return self.random_context.generator(
                stream_name,
                entity_id=entity_id,
            )

        entropy = _stable_entropy(
            self.config.random_seed,
            stream_name,
            entity_id,
        )
        return np.random.default_rng(entropy)


def schedule_events(
    portfolio: Any,
    time_grid: Iterable[Any],
    config: EventSchedulerConfig | None = None,
    random_context: _RandomContextProtocol | None = None,
    *,
    catalogue: EventCatalogue = DEFAULT_EVENT_CATALOGUE,
    generation_run_id: str = "RUN-UNPUBLISHED",
) -> tuple[SyntheticEvent, ...]:
    """Public functional adapter for EventScheduler."""
    return EventScheduler(
        config=config,
        catalogue=catalogue,
        random_context=random_context,
    ).schedule(
        portfolio,
        time_grid,
        generation_run_id=generation_run_id,
    )


def resolve_event_conflicts(
    events: Iterable[SyntheticEvent],
    *,
    catalogue: EventCatalogue = DEFAULT_EVENT_CATALOGUE,
    enforce_minimum_separation: bool = True,
    enforce_overlap_rules: bool = True,
) -> tuple[SyntheticEvent, ...]:
    """Resolve conflicts for an existing event collection."""
    return EventConflictResolver(catalogue).resolve(
        events,
        enforce_minimum_separation=enforce_minimum_separation,
        enforce_overlap_rules=enforce_overlap_rules,
    )


def events_to_frame(
    events: Iterable[SyntheticEvent],
) -> pd.DataFrame:
    """Convert scheduled events to the ground-truth event DataFrame."""
    records = [event.to_record() for event in events]
    frame = pd.DataFrame.from_records(
        records,
        columns=_output_columns(),
    )

    if frame.empty:
        return frame

    return frame.sort_values(
        [
            "start_at_utc",
            "event_scope",
            "asset_id",
            "event_type",
        ],
        kind="stable",
    ).reset_index(drop=True)


def _schedule_candidate(
    *,
    definition: EventDefinition,
    asset: EligibleAsset,
    timestamps: tuple[datetime, ...],
    rng: np.random.Generator,
    interval_minutes: int,
    align_to_grid: bool,
    generation_run_id: str,
    provisional_ordinal: int,
    schema_version: str,
) -> SyntheticEvent | None:
    """Schedule one candidate event for a selected asset."""
    eligible_timestamps = tuple(
        timestamp
        for timestamp in timestamps
        if _timestamp_allowed(timestamp, definition)
    )

    if not eligible_timestamps:
        return None

    start = eligible_timestamps[int(rng.integers(0, len(eligible_timestamps)))]
    duration_minutes = _sample_duration_minutes(
        definition,
        rng,
        interval_minutes=interval_minutes,
        align_to_grid=align_to_grid,
    )
    end = start + timedelta(minutes=duration_minutes)

    maximum_end = timestamps[-1] + timedelta(minutes=interval_minutes)
    if end > maximum_end:
        end = maximum_end

    if end <= start:
        return None

    severity = _sample_severity(definition, rng)
    severity_score = _severity_score(severity, rng)
    power_modifier = _sample_power_modifier(definition, rng)
    measurement_channel = _sample_measurement_channel(
        definition,
        rng,
    )
    measurement_bias = _sample_measurement_bias(
        definition,
        measurement_channel,
        rng,
    )
    expected_alarm_code = (
        definition.alarm_codes[int(rng.integers(0, len(definition.alarm_codes)))]
        if definition.alarm_codes
        else None
    )
    expected_incident = float(rng.random()) < definition.incident_probability
    expected_work_order = float(rng.random()) < definition.work_order_probability

    parameters = {
        "catalogue_event_type": definition.event_type.value,
        "provisional_ordinal": provisional_ordinal,
        "duration_minutes": duration_minutes,
        "recovery_behavior": definition.recovery_behavior.value,
    }

    return SyntheticEvent(
        ground_truth_event_id="GTE-PENDING",
        event_type=definition.event_type,
        event_scope=asset.scope,
        plant_id=asset.plant_id,
        asset_type=asset.asset_type,
        asset_id=asset.asset_id,
        parent_event_id=None,
        start_at_utc=start,
        end_at_utc=end,
        severity=severity,
        severity_score=severity_score,
        power_modifier_ratio=power_modifier,
        measurement_channel=measurement_channel,
        measurement_bias=measurement_bias,
        is_planned=definition.planned,
        cause_code=definition.event_type.value.upper(),
        parameters_json=json.dumps(
            parameters,
            sort_keys=True,
            separators=(",", ":"),
        ),
        expected_alarm_code=expected_alarm_code,
        expected_incident=expected_incident,
        expected_work_order=expected_work_order,
        generation_run_id=generation_run_id.strip(),
        schema_version=schema_version,
    )


def _normalize_time_grid(
    time_grid: Iterable[Any],
    *,
    interval_minutes: int,
) -> tuple[datetime, ...]:
    """Normalize and validate a UTC-aware time grid."""
    timestamps = tuple(pd.Timestamp(value).to_pydatetime() for value in time_grid)

    if not timestamps:
        return ()

    if any(timestamp.tzinfo is None for timestamp in timestamps):
        raise ValueError("time_grid timestamps must be timezone-aware.")

    normalized = tuple(timestamp.astimezone(UTC) for timestamp in timestamps)

    if normalized != tuple(sorted(normalized)):
        raise ValueError("time_grid must be sorted.")

    if len(normalized) != len(set(normalized)):
        raise ValueError("time_grid must contain unique timestamps.")

    expected_delta = timedelta(minutes=interval_minutes)
    if any(
        later - earlier != expected_delta
        for earlier, later in zip(
            normalized,
            normalized[1:],
            strict=False,
        )
    ):
        raise ValueError("time_grid must use a constant configured interval.")

    return normalized


def _normalize_portfolio(portfolio: Any) -> tuple[EligibleAsset, ...]:
    """Normalize supported portfolio representations."""
    assets: list[EligibleAsset] = []

    if isinstance(portfolio, Mapping):
        for scope_name, values in portfolio.items():
            scope = EventScope(str(scope_name))
            assets.extend(_normalize_scope_values(scope, values))
    elif isinstance(portfolio, pd.DataFrame):
        required = {"scope", "plant_id", "asset_type", "asset_id"}
        missing = required.difference(portfolio.columns)
        if missing:
            raise ValueError(
                "portfolio DataFrame is missing columns: " f"{sorted(missing)}."
            )

        for row in portfolio.to_dict(orient="records"):
            assets.append(
                EligibleAsset(
                    scope=EventScope(str(row["scope"])),
                    plant_id=str(row["plant_id"]),
                    asset_type=str(row["asset_type"]),
                    asset_id=str(row["asset_id"]),
                )
            )
    else:
        for item in portfolio:
            if isinstance(item, EligibleAsset):
                assets.append(item)
                continue

            assets.append(
                EligibleAsset(
                    scope=EventScope(item.scope),
                    plant_id=item.plant_id,
                    asset_type=item.asset_type,
                    asset_id=item.asset_id,
                )
            )

    unique: dict[
        tuple[EventScope, str, str],
        EligibleAsset,
    ] = {}

    for asset in assets:
        key = (asset.scope, asset.plant_id, asset.asset_id)
        if key in unique:
            raise ValueError(f"Duplicate eligible asset '{asset.asset_id}'.")
        unique[key] = asset

    return tuple(
        sorted(
            unique.values(),
            key=lambda item: (
                item.scope.value,
                item.plant_id,
                item.asset_id,
            ),
        )
    )


def _normalize_scope_values(
    scope: EventScope,
    values: Any,
) -> list[EligibleAsset]:
    """Normalize one mapping scope collection."""
    normalized: list[EligibleAsset] = []

    for item in values:
        if isinstance(item, Mapping):
            plant_id = str(item["plant_id"])
            asset_type = str(item.get("asset_type", scope.value))
            asset_id = str(item["asset_id"])
        else:
            plant_id = str(item.plant_id)
            asset_type = str(getattr(item, "asset_type", scope.value))
            asset_id = str(item.asset_id)

        normalized.append(
            EligibleAsset(
                scope=scope,
                plant_id=plant_id,
                asset_type=asset_type,
                asset_id=asset_id,
            )
        )

    return normalized


def _timestamp_allowed(
    timestamp: datetime,
    definition: EventDefinition,
) -> bool:
    """Return whether a timestamp satisfies event restrictions."""
    if definition.seasonal_months and timestamp.month not in definition.seasonal_months:
        return False

    daylight = 6 <= timestamp.hour < 18

    return not (
        (definition.requires_daylight and not daylight)
        or (definition.excludes_daylight and daylight)
    )


def _sample_duration_minutes(
    definition: EventDefinition,
    rng: np.random.Generator,
    *,
    interval_minutes: int,
    align_to_grid: bool,
) -> int:
    """Sample a bounded triangular duration."""
    duration = definition.duration
    sampled = float(
        rng.triangular(
            duration.minimum_minutes,
            duration.typical_minutes,
            duration.maximum_minutes,
        )
    )

    if align_to_grid:
        intervals = max(
            1,
            int(round(sampled / interval_minutes)),
        )
        return intervals * interval_minutes

    return max(1, int(round(sampled)))


def _sample_severity(
    definition: EventDefinition,
    rng: np.random.Generator,
) -> EventSeverity:
    """Sample severity from normalized catalogue weights."""
    weights = definition.normalized_severity_weights
    severities = tuple(weights)
    probabilities = tuple(weights[severity] for severity in severities)
    index = int(
        rng.choice(
            len(severities),
            p=probabilities,
        )
    )
    return severities[index]


def _severity_score(
    severity: EventSeverity,
    rng: np.random.Generator,
) -> float:
    """Return a bounded continuous severity score."""
    bounds = {
        EventSeverity.LOW: (0.05, 0.25),
        EventSeverity.MODERATE: (0.25, 0.55),
        EventSeverity.HIGH: (0.55, 0.80),
        EventSeverity.CRITICAL: (0.80, 1.00),
    }
    lower, upper = bounds[severity]
    return round(float(rng.uniform(lower, upper)), 6)


def _sample_power_modifier(
    definition: EventDefinition,
    rng: np.random.Generator,
) -> float | None:
    """Sample an optional physical power modifier."""
    minimum = definition.minimum_power_modifier_ratio
    maximum = definition.maximum_power_modifier_ratio

    if minimum is None or maximum is None:
        return None

    if minimum == maximum:
        return minimum

    return round(float(rng.uniform(minimum, maximum)), 6)


def _sample_measurement_channel(
    definition: EventDefinition,
    rng: np.random.Generator,
) -> str | None:
    """Select an optional affected measurement channel."""
    if not definition.measurement_channels:
        return None

    return definition.measurement_channels[
        int(rng.integers(0, len(definition.measurement_channels)))
    ]


def _sample_measurement_bias(
    definition: EventDefinition,
    channel: str | None,
    rng: np.random.Generator,
) -> float | None:
    """Return a measurement bias for drift-like events."""
    if channel is None:
        return None

    if definition.event_type is EventType.SENSOR_DRIFT:
        return round(float(rng.uniform(-0.20, 0.20)), 6)

    if definition.event_type is EventType.SENSOR_STUCK:
        return 0.0

    return None


def _assign_stable_event_ids(
    events: Iterable[SyntheticEvent],
) -> tuple[SyntheticEvent, ...]:
    """Assign deterministic IDs after stable event sorting."""
    ordered = sorted(events, key=_event_sort_key)
    counters: dict[int, int] = {}
    assigned: list[SyntheticEvent] = []

    for event in ordered:
        year = event.start_at_utc.year
        counters[year] = counters.get(year, 0) + 1
        event_id = f"GTE-{year:04d}-{counters[year]:08d}"

        assigned.append(
            SyntheticEvent(
                **{
                    **asdict(event),
                    "ground_truth_event_id": event_id,
                    "event_type": event.event_type,
                    "event_scope": event.event_scope,
                    "severity": event.severity,
                }
            )
        )

    return tuple(assigned)


def _event_sort_key(
    event: SyntheticEvent,
) -> tuple[datetime, int, str, str]:
    """Return canonical stable event sort key."""
    scope_rank = {
        EventScope.PORTFOLIO: 0,
        EventScope.PLANT: 1,
        EventScope.FEEDER: 2,
        EventScope.TRANSFORMER: 3,
        EventScope.INVERTER: 4,
        EventScope.SENSOR: 5,
    }
    return (
        event.start_at_utc,
        scope_rank[event.event_scope],
        event.asset_id,
        event.event_type.value,
    )


def _intervals_overlap(
    left: SyntheticEvent,
    right: SyntheticEvent,
) -> bool:
    """Return whether two event intervals overlap."""
    return left.start_at_utc < right.end_at_utc and right.start_at_utc < left.end_at_utc


def _overlap_allowed(
    left: EventDefinition,
    right: EventDefinition,
) -> bool:
    """Return whether two definitions explicitly allow overlap."""
    return (
        right.event_type in left.allowed_overlap_types
        or left.event_type in right.allowed_overlap_types
    )


def _event_gap_minutes(
    left: SyntheticEvent,
    right: SyntheticEvent,
) -> float:
    """Return non-negative gap between two event intervals."""
    if _intervals_overlap(left, right):
        return 0.0

    if left.end_at_utc <= right.start_at_utc:
        delta = right.start_at_utc - left.end_at_utc
    else:
        delta = left.start_at_utc - right.end_at_utc

    return delta.total_seconds() / 60.0


def _shares_affected_scope(
    left: SyntheticEvent,
    right: SyntheticEvent,
) -> bool:
    """Return whether events affect the same operational hierarchy."""
    if left.event_scope is EventScope.PORTFOLIO:
        return True

    if right.event_scope is EventScope.PORTFOLIO:
        return True

    if left.plant_id != right.plant_id:
        return False

    if left.event_scope is EventScope.PLANT or right.event_scope is EventScope.PLANT:
        return True

    return left.asset_id == right.asset_id


def _stable_entropy(
    seed: int,
    stream_name: str,
    entity_id: str,
) -> int:
    """Return stable entropy without Python's randomized hash."""
    payload = f"{seed}|{stream_name}|{entity_id}".encode()
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _output_columns() -> tuple[str, ...]:
    """Return stable ground-truth event output columns."""
    return (
        "ground_truth_event_id",
        "event_type",
        "event_scope",
        "plant_id",
        "asset_type",
        "asset_id",
        "parent_event_id",
        "start_at_utc",
        "end_at_utc",
        "severity",
        "severity_score",
        "power_modifier_ratio",
        "measurement_channel",
        "measurement_bias",
        "is_planned",
        "cause_code",
        "parameters_json",
        "expected_alarm_code",
        "expected_incident",
        "expected_work_order",
        "generation_run_id",
        "schema_version",
    )


__all__ = [
    "EligibleAsset",
    "EventConflictResolver",
    "EventScheduler",
    "EventSchedulerConfig",
    "SyntheticEvent",
    "events_to_frame",
    "resolve_event_conflicts",
    "schedule_events",
]
