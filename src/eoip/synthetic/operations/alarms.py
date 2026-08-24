"""
Event-driven operational alarm lifecycle generation for EOIP Phase 2.

This module converts scheduled synthetic events into deterministic operational
alarm lifecycles by using the stable definitions in ``alarm_catalogue.py`` and
the authoritative ``Alarm`` domain model.

It is intentionally separate from ``generators/alarm_generator.py``:

- ``generators/alarm_generator.py`` derives simple alarms from generated SCADA
  operating states.
- this module creates event-linked operational lifecycles with stable catalogue
  codes, trigger and clear delays, acknowledgement simulation, suppression,
  bounded nuisance alarms, and truth-event lineage.

The public output is a pandas DataFrame because downstream incident generation,
validation, ETL, and analytics require explicit lineage and operational fields
that are not part of the compact ``Alarm`` domain model.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import numpy as np
import pandas as pd

from eoip.synthetic.events.catalogue import (
    EventScope,
    EventSeverity,
)
from eoip.synthetic.events.scheduler import SyntheticEvent
from eoip.synthetic.models.alarm import (
    Alarm,
    AlarmSeverity,
    AlarmStatus,
)
from eoip.synthetic.operations.alarm_catalogue import (
    DEFAULT_ALARM_CATALOGUE,
    AlarmCatalogue,
    AlarmClearBehavior,
    AlarmDefinition,
)

_EQUIPMENT_ID_PATTERN = re.compile(r"^EQP-\d{5}$")


class _RandomContextProtocol(Protocol):
    """Minimal named-random-stream interface used by alarm generation."""

    def generator(
        self,
        name: str,
        entity_id: str | None = None,
    ) -> np.random.Generator:
        """Return a deterministic named NumPy generator."""


@dataclass(frozen=True, slots=True)
class AlarmOperationsConfig:
    """Configuration for event-linked alarm lifecycle generation."""

    random_seed: int = 20250201
    acknowledgement_probability: float = 0.90
    informational_acknowledgement_probability: float = 0.35
    warning_acknowledgement_probability: float = 0.75
    major_acknowledgement_probability: float = 0.95
    critical_acknowledgement_probability: float = 0.995
    minimum_acknowledgement_minutes: int = 1
    maximum_acknowledgement_minutes: int = 30
    manual_clear_extra_minutes: int = 15
    nuisance_alarm_probability: float = 0.02
    maximum_nuisance_alarms_per_event: int = 1
    generate_nuisance_alarms: bool = True
    allow_equipment_id_fallback: bool = True
    is_synthetic_ground_truth: bool = True
    schema_version: str = "1.0.0"

    def __post_init__(self) -> None:
        """Normalize and validate configuration values."""
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

        probability_fields = (
            "acknowledgement_probability",
            "informational_acknowledgement_probability",
            "warning_acknowledgement_probability",
            "major_acknowledgement_probability",
            "critical_acknowledgement_probability",
            "nuisance_alarm_probability",
        )
        for field_name in probability_fields:
            self._validate_probability(
                field_name=field_name,
                value=getattr(self, field_name),
            )

        integer_fields = (
            "minimum_acknowledgement_minutes",
            "maximum_acknowledgement_minutes",
            "manual_clear_extra_minutes",
            "maximum_nuisance_alarms_per_event",
        )
        for field_name in integer_fields:
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer.")
            if value < 0:
                raise ValueError(f"{field_name} must be non-negative.")

        if self.maximum_acknowledgement_minutes < self.minimum_acknowledgement_minutes:
            raise ValueError(
                "maximum_acknowledgement_minutes must be greater than or "
                "equal to minimum_acknowledgement_minutes."
            )

        boolean_fields = (
            "generate_nuisance_alarms",
            "allow_equipment_id_fallback",
            "is_synthetic_ground_truth",
        )
        for field_name in boolean_fields:
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be a boolean.")

        if not normalized_schema_version:
            raise ValueError("schema_version cannot be empty.")

    @staticmethod
    def _validate_probability(
        *,
        field_name: str,
        value: float,
    ) -> None:
        """Validate a finite probability in the inclusive interval [0, 1]."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{field_name} must be numeric.")

        if not math.isfinite(value):
            raise ValueError(f"{field_name} must be finite.")

        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{field_name} must be between 0.0 and 1.0.")


@dataclass(frozen=True, slots=True)
class AlarmSCADAContext:
    """
    Optional operational context used to resolve assets and suppression rules.

    ``equipment_id_by_asset`` maps event asset IDs such as feeder, transformer,
    inverter, sensor, or plant identifiers to authoritative ``EQP-00001`` style
    equipment IDs.

    ``default_equipment_id_by_plant`` supplies a representative plant-level
    equipment ID for plant and portfolio alarms.

    ``suppression_rules_by_event_id`` contains active rule names for each
    ground-truth event. A catalogue alarm is suppressed when any active rule
    intersects its configured suppression rules.

    ``observation_end_at`` caps lifecycle timestamps to the generated dataset
    window. Alarms that would clear after this boundary remain open.
    """

    equipment_id_by_asset: Mapping[str, str] | None = None
    default_equipment_id_by_plant: Mapping[str, str] | None = None
    suppression_rules_by_event_id: Mapping[str, tuple[str, ...]] | None = None
    observation_end_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate mappings and optional observation boundary."""
        equipment_mapping = dict(self.equipment_id_by_asset or {})
        plant_mapping = dict(self.default_equipment_id_by_plant or {})
        suppression_mapping = dict(self.suppression_rules_by_event_id or {})

        normalized_equipment_mapping = {
            str(asset_id).strip().upper(): _normalize_equipment_id(equipment_id)
            for asset_id, equipment_id in equipment_mapping.items()
        }
        normalized_plant_mapping = {
            str(plant_id).strip().upper(): _normalize_equipment_id(equipment_id)
            for plant_id, equipment_id in plant_mapping.items()
        }
        normalized_suppression_mapping = {
            str(event_id).strip().upper(): tuple(rule.strip().lower() for rule in rules)
            for event_id, rules in suppression_mapping.items()
        }

        if any(not asset_id for asset_id in normalized_equipment_mapping):
            raise ValueError("equipment_id_by_asset keys cannot be empty.")

        if any(not plant_id for plant_id in normalized_plant_mapping):
            raise ValueError("default_equipment_id_by_plant keys cannot be empty.")

        for event_id, rules in normalized_suppression_mapping.items():
            if not event_id:
                raise ValueError("suppression_rules_by_event_id keys cannot be empty.")
            if len(rules) != len(set(rules)):
                raise ValueError("suppression rules must not contain duplicates.")
            if any(not rule for rule in rules):
                raise ValueError("suppression rules must not contain blank values.")

        if self.observation_end_at is not None:
            _validate_aware_datetime(
                field_name="observation_end_at",
                value=self.observation_end_at,
            )

        object.__setattr__(
            self,
            "equipment_id_by_asset",
            normalized_equipment_mapping,
        )
        object.__setattr__(
            self,
            "default_equipment_id_by_plant",
            normalized_plant_mapping,
        )
        object.__setattr__(
            self,
            "suppression_rules_by_event_id",
            normalized_suppression_mapping,
        )


@dataclass(frozen=True, slots=True)
class AlarmGenerationSummary:
    """Aggregate result metadata for one alarm-generation run."""

    input_event_count: int
    generated_alarm_count: int
    suppressed_alarm_count: int
    nuisance_alarm_count: int

    def to_record(self) -> dict[str, int]:
        """Return a serialization-ready summary."""
        return {
            "input_event_count": self.input_event_count,
            "generated_alarm_count": self.generated_alarm_count,
            "suppressed_alarm_count": self.suppressed_alarm_count,
            "nuisance_alarm_count": self.nuisance_alarm_count,
        }


@dataclass(frozen=True, slots=True)
class AlarmGenerationResult:
    """Alarm DataFrame and summary metadata."""

    frame: pd.DataFrame
    summary: AlarmGenerationSummary


@dataclass(frozen=True, slots=True)
class _AlarmCandidate:
    """Internal event-to-alarm candidate before stable ID assignment."""

    event: SyntheticEvent
    definition: AlarmDefinition
    equipment_id: str
    raised_at: datetime
    acknowledged_at: datetime | None
    cleared_at: datetime | None
    status: AlarmStatus
    severity: AlarmSeverity
    message: str | None
    is_nuisance: bool


def generate_alarms(
    events: Iterable[SyntheticEvent],
    scada_context: AlarmSCADAContext | Mapping[str, Any] | None = None,
    config: AlarmOperationsConfig | None = None,
    random_context: _RandomContextProtocol | None = None,
    *,
    catalogue: AlarmCatalogue = DEFAULT_ALARM_CATALOGUE,
) -> pd.DataFrame:
    """
    Generate deterministic event-linked operational alarm lifecycles.

    The function:

    - maps event types or explicit expected alarm codes to stable catalogue
      definitions;
    - applies trigger and clear delays;
    - applies configured suppression rules;
    - simulates acknowledgement with severity-sensitive probabilities;
    - adds bounded nuisance alarms when enabled;
    - assigns stable ``ALM-0000001`` identifiers only after deterministic sort;
    - links each alarm to its ground-truth event ID.

    The returned DataFrame is sorted by raise time, plant, equipment, code, and
    alarm ID.
    """
    return generate_alarm_result(
        events,
        scada_context=scada_context,
        config=config,
        random_context=random_context,
        catalogue=catalogue,
    ).frame


def generate_alarm_result(
    events: Iterable[SyntheticEvent],
    scada_context: AlarmSCADAContext | Mapping[str, Any] | None = None,
    config: AlarmOperationsConfig | None = None,
    random_context: _RandomContextProtocol | None = None,
    *,
    catalogue: AlarmCatalogue = DEFAULT_ALARM_CATALOGUE,
) -> AlarmGenerationResult:
    """Generate alarms together with aggregate run metadata."""
    resolved_config = config or AlarmOperationsConfig()
    resolved_context = _normalize_scada_context(scada_context)
    ordered_events = tuple(sorted(events, key=_event_sort_key))

    candidates: list[_AlarmCandidate] = []
    suppressed_count = 0
    nuisance_count = 0

    for event in ordered_events:
        definitions = _definitions_for_event(
            event,
            catalogue=catalogue,
        )

        for definition in definitions:
            if _is_suppressed(
                event,
                definition,
                context=resolved_context,
            ):
                suppressed_count += 1
                continue

            equipment_id = _resolve_equipment_id(
                event,
                context=resolved_context,
                config=resolved_config,
            )
            rng = _generator(
                config=resolved_config,
                random_context=random_context,
                stream_name="operations.alarms",
                entity_id=(
                    f"{event.ground_truth_event_id}|" f"{definition.code}|primary"
                ),
            )
            candidate = _build_candidate(
                event=event,
                definition=definition,
                equipment_id=equipment_id,
                config=resolved_config,
                context=resolved_context,
                rng=rng,
                is_nuisance=False,
            )
            if candidate is not None:
                candidates.append(candidate)

            nuisance_candidates = _build_nuisance_candidates(
                event=event,
                definition=definition,
                equipment_id=equipment_id,
                config=resolved_config,
                context=resolved_context,
                random_context=random_context,
            )
            candidates.extend(nuisance_candidates)
            nuisance_count += len(nuisance_candidates)

    frame = _candidates_to_frame(
        candidates,
        config=resolved_config,
    )
    summary = AlarmGenerationSummary(
        input_event_count=len(ordered_events),
        generated_alarm_count=len(frame),
        suppressed_alarm_count=suppressed_count,
        nuisance_alarm_count=nuisance_count,
    )
    return AlarmGenerationResult(frame=frame, summary=summary)


def alarms_to_domain_models(
    alarms: pd.DataFrame,
) -> tuple[Alarm, ...]:
    """Convert an alarm DataFrame back to authoritative Alarm objects."""
    required_columns = {
        "alarm_id",
        "plant_id",
        "equipment_id",
        "alarm_code",
        "alarm_name",
        "category",
        "severity",
        "raised_at",
        "status",
        "acknowledged_at",
        "cleared_at",
        "message",
        "is_synthetic_ground_truth",
    }
    missing = required_columns.difference(alarms.columns)
    if missing:
        raise ValueError("alarms DataFrame is missing columns: " f"{sorted(missing)}.")

    models: list[Alarm] = []
    for row in alarms.to_dict(orient="records"):
        models.append(
            Alarm(
                alarm_id=str(row["alarm_id"]),
                plant_id=str(row["plant_id"]),
                equipment_id=str(row["equipment_id"]),
                alarm_code=str(row["alarm_code"]),
                alarm_name=str(row["alarm_name"]),
                category=_coerce_alarm_category(row["category"]),
                severity=_coerce_alarm_severity(row["severity"]),
                raised_at=_coerce_timestamp(
                    row["raised_at"],
                    field_name="raised_at",
                    allow_none=False,
                ),
                status=_coerce_alarm_status(row["status"]),
                acknowledged_at=_coerce_timestamp(
                    row["acknowledged_at"],
                    field_name="acknowledged_at",
                    allow_none=True,
                ),
                cleared_at=_coerce_timestamp(
                    row["cleared_at"],
                    field_name="cleared_at",
                    allow_none=True,
                ),
                message=(None if pd.isna(row["message"]) else str(row["message"])),
                is_synthetic_ground_truth=bool(row["is_synthetic_ground_truth"]),
            )
        )

    return tuple(models)


def _normalize_scada_context(
    value: AlarmSCADAContext | Mapping[str, Any] | None,
) -> AlarmSCADAContext:
    """Normalize supported SCADA context representations."""
    if value is None:
        return AlarmSCADAContext()

    if isinstance(value, AlarmSCADAContext):
        return value

    if isinstance(value, Mapping):
        return AlarmSCADAContext(
            equipment_id_by_asset=value.get("equipment_id_by_asset"),
            default_equipment_id_by_plant=value.get("default_equipment_id_by_plant"),
            suppression_rules_by_event_id=value.get("suppression_rules_by_event_id"),
            observation_end_at=value.get("observation_end_at"),
        )

    raise TypeError("scada_context must be an AlarmSCADAContext, mapping, or None.")


def _definitions_for_event(
    event: SyntheticEvent,
    *,
    catalogue: AlarmCatalogue,
) -> tuple[AlarmDefinition, ...]:
    """Resolve stable catalogue definitions for an event."""
    if event.expected_alarm_code is not None:
        definition = catalogue.find(event.expected_alarm_code)
        if definition is not None:
            return (definition,)

    return catalogue.for_event_type(event.event_type)


def _is_suppressed(
    event: SyntheticEvent,
    definition: AlarmDefinition,
    *,
    context: AlarmSCADAContext,
) -> bool:
    """Return whether active suppression rules suppress a definition."""
    active_rules = set(
        (context.suppression_rules_by_event_id or {}).get(
            event.ground_truth_event_id.upper(),
            (),
        )
    )
    configured_rules = set(definition.suppression_rules)
    return bool(active_rules.intersection(configured_rules))


def _resolve_equipment_id(
    event: SyntheticEvent,
    *,
    context: AlarmSCADAContext,
    config: AlarmOperationsConfig,
) -> str:
    """Resolve an authoritative Alarm-compatible equipment identifier."""
    asset_id = event.asset_id.strip().upper()
    plant_id = event.plant_id.strip().upper()

    if _EQUIPMENT_ID_PATTERN.fullmatch(asset_id):
        return asset_id

    mapped = (context.equipment_id_by_asset or {}).get(asset_id)
    if mapped is not None:
        return mapped

    plant_default = (context.default_equipment_id_by_plant or {}).get(plant_id)
    if plant_default is not None:
        return plant_default

    if not config.allow_equipment_id_fallback:
        raise ValueError(
            "Unable to resolve an EQP-formatted equipment ID for event "
            f"'{event.ground_truth_event_id}' targeting '{event.asset_id}'."
        )

    return _fallback_equipment_id(
        plant_id=plant_id,
        asset_id=asset_id,
        scope=event.event_scope,
    )


def _fallback_equipment_id(
    *,
    plant_id: str,
    asset_id: str,
    scope: EventScope,
) -> str:
    """Return a stable synthetic EQP identifier for unresolved scopes."""
    payload = f"{plant_id}|{scope.value}|{asset_id}".encode()
    digest = hashlib.sha256(payload).digest()
    numeric_value = int.from_bytes(
        digest[:8],
        "big",
        signed=False,
    )
    return f"EQP-{numeric_value % 99_999 + 1:05d}"


def _build_candidate(
    *,
    event: SyntheticEvent,
    definition: AlarmDefinition,
    equipment_id: str,
    config: AlarmOperationsConfig,
    context: AlarmSCADAContext,
    rng: np.random.Generator,
    is_nuisance: bool,
) -> _AlarmCandidate | None:
    """Build one validated lifecycle candidate."""
    trigger_delay = definition.trigger_delay_minutes
    if is_nuisance:
        trigger_delay += int(rng.integers(1, 16))

    raised_at = event.start_at_utc + timedelta(minutes=trigger_delay)

    if raised_at >= event.end_at_utc and not is_nuisance:
        return None

    cleared_at = _clear_timestamp(
        event=event,
        definition=definition,
        config=config,
        context=context,
        raised_at=raised_at,
        is_nuisance=is_nuisance,
    )
    severity = _resolve_severity(
        definition.default_severity,
        event.severity,
        is_nuisance=is_nuisance,
    )
    acknowledged_at = _acknowledgement_timestamp(
        raised_at=raised_at,
        cleared_at=cleared_at,
        severity=severity,
        config=config,
        rng=rng,
        is_nuisance=is_nuisance,
    )
    status = _status_for_timestamps(
        acknowledged_at=acknowledged_at,
        cleared_at=cleared_at,
    )
    message = _render_message(
        definition,
        event=event,
        equipment_id=equipment_id,
        is_nuisance=is_nuisance,
    )

    return _AlarmCandidate(
        event=event,
        definition=definition,
        equipment_id=equipment_id,
        raised_at=raised_at,
        acknowledged_at=acknowledged_at,
        cleared_at=cleared_at,
        status=status,
        severity=severity,
        message=message,
        is_nuisance=is_nuisance,
    )


def _build_nuisance_candidates(
    *,
    event: SyntheticEvent,
    definition: AlarmDefinition,
    equipment_id: str,
    config: AlarmOperationsConfig,
    context: AlarmSCADAContext,
    random_context: _RandomContextProtocol | None,
) -> tuple[_AlarmCandidate, ...]:
    """Generate bounded nuisance alarms for eligible definitions."""
    if (
        not config.generate_nuisance_alarms
        or not definition.nuisance_eligible
        or config.maximum_nuisance_alarms_per_event == 0
    ):
        return ()

    rng = _generator(
        config=config,
        random_context=random_context,
        stream_name="operations.alarms.nuisance",
        entity_id=(f"{event.ground_truth_event_id}|{definition.code}"),
    )
    count = int(
        rng.binomial(
            config.maximum_nuisance_alarms_per_event,
            config.nuisance_alarm_probability,
        )
    )

    candidates: list[_AlarmCandidate] = []
    for _ in range(count):
        candidate = _build_candidate(
            event=event,
            definition=definition,
            equipment_id=equipment_id,
            config=config,
            context=context,
            rng=rng,
            is_nuisance=True,
        )
        if candidate is not None:
            candidates.append(candidate)

    return tuple(candidates)


def _clear_timestamp(
    *,
    event: SyntheticEvent,
    definition: AlarmDefinition,
    config: AlarmOperationsConfig,
    context: AlarmSCADAContext,
    raised_at: datetime,
    is_nuisance: bool,
) -> datetime | None:
    """Return lifecycle-policy-compliant clearance time."""
    behavior = definition.clear_behavior

    if behavior in {
        AlarmClearBehavior.LATCHED,
        AlarmClearBehavior.NO_CLEAR,
    }:
        return None

    clear_delay = definition.clear_delay_minutes
    if behavior is AlarmClearBehavior.MANUAL_CLEAR:
        clear_delay += config.manual_clear_extra_minutes

    if is_nuisance:
        nuisance_duration = max(5, min(30, clear_delay or 15))
        candidate = raised_at + timedelta(minutes=nuisance_duration)
    else:
        candidate = event.end_at_utc + timedelta(minutes=clear_delay)

    observation_end = context.observation_end_at
    if observation_end is not None and candidate > observation_end:
        return None

    if candidate < raised_at:
        return raised_at

    return candidate


def _acknowledgement_timestamp(
    *,
    raised_at: datetime,
    cleared_at: datetime | None,
    severity: AlarmSeverity,
    config: AlarmOperationsConfig,
    rng: np.random.Generator,
    is_nuisance: bool,
) -> datetime | None:
    """Sample acknowledgement while preserving Alarm model ordering."""
    probability = _acknowledgement_probability(
        severity,
        config=config,
    )
    if is_nuisance:
        probability *= config.acknowledgement_probability

    if float(rng.random()) >= probability:
        return None

    delay = int(
        rng.integers(
            config.minimum_acknowledgement_minutes,
            config.maximum_acknowledgement_minutes + 1,
        )
    )
    candidate = raised_at + timedelta(minutes=delay)

    # The authoritative Alarm model requires acknowledgement not to occur after
    # clearance. The implementation-plan allowance for late acknowledgements is
    # therefore represented by omitting acknowledgement when the sampled time
    # would fall outside the closed lifecycle.
    if cleared_at is not None and candidate > cleared_at:
        return None

    return candidate


def _acknowledgement_probability(
    severity: AlarmSeverity,
    *,
    config: AlarmOperationsConfig,
) -> float:
    """Return severity-sensitive acknowledgement probability."""
    severity_probability = {
        AlarmSeverity.INFORMATIONAL: (config.informational_acknowledgement_probability),
        AlarmSeverity.WARNING: (config.warning_acknowledgement_probability),
        AlarmSeverity.MAJOR: (config.major_acknowledgement_probability),
        AlarmSeverity.CRITICAL: (config.critical_acknowledgement_probability),
    }[severity]
    return min(
        severity_probability * config.acknowledgement_probability,
        1.0,
    )


def _resolve_severity(
    default: AlarmSeverity,
    event_severity: EventSeverity,
    *,
    is_nuisance: bool,
) -> AlarmSeverity:
    """Resolve catalogue and event severity without reducing defaults."""
    if is_nuisance:
        return AlarmSeverity.WARNING

    event_mapping = {
        EventSeverity.LOW: AlarmSeverity.INFORMATIONAL,
        EventSeverity.MODERATE: AlarmSeverity.WARNING,
        EventSeverity.HIGH: AlarmSeverity.MAJOR,
        EventSeverity.CRITICAL: AlarmSeverity.CRITICAL,
    }
    rank = {
        AlarmSeverity.INFORMATIONAL: 0,
        AlarmSeverity.WARNING: 1,
        AlarmSeverity.MAJOR: 2,
        AlarmSeverity.CRITICAL: 3,
    }
    event_value = event_mapping[event_severity]
    return default if rank[default] >= rank[event_value] else event_value


def _status_for_timestamps(
    *,
    acknowledged_at: datetime | None,
    cleared_at: datetime | None,
) -> AlarmStatus:
    """Derive an Alarm lifecycle status from timestamps."""
    if cleared_at is not None:
        return AlarmStatus.CLEARED

    if acknowledged_at is not None:
        return AlarmStatus.ACKNOWLEDGED

    return AlarmStatus.ACTIVE


def _render_message(
    definition: AlarmDefinition,
    *,
    event: SyntheticEvent,
    equipment_id: str,
    is_nuisance: bool,
) -> str:
    """Render a bounded catalogue message."""
    template = definition.message_template or definition.name
    values = {
        "plant_id": event.plant_id,
        "asset_id": event.asset_id,
        "equipment_id": equipment_id,
        "event_type": event.event_type.value,
    }

    try:
        message = template.format_map(values)
    except (KeyError, ValueError):
        message = template

    if is_nuisance:
        message = f"Nuisance simulation: {message}"

    return message[:500]


def _candidates_to_frame(
    candidates: Iterable[_AlarmCandidate],
    *,
    config: AlarmOperationsConfig,
) -> pd.DataFrame:
    """Assign stable IDs, validate Alarm models, and build output."""
    ordered = tuple(sorted(candidates, key=_candidate_sort_key))
    records: list[dict[str, object]] = []

    for index, candidate in enumerate(ordered, start=1):
        alarm_id = f"ALM-{index:07d}"
        alarm = Alarm(
            alarm_id=alarm_id,
            plant_id=candidate.event.plant_id,
            equipment_id=candidate.equipment_id,
            alarm_code=candidate.definition.code,
            alarm_name=candidate.definition.name,
            category=candidate.definition.category,
            severity=candidate.severity,
            raised_at=candidate.raised_at,
            status=candidate.status,
            acknowledged_at=candidate.acknowledged_at,
            cleared_at=candidate.cleared_at,
            message=candidate.message,
            is_synthetic_ground_truth=(config.is_synthetic_ground_truth),
        )
        records.append(
            _alarm_record(
                alarm,
                candidate=candidate,
                schema_version=config.schema_version,
            )
        )

    frame = pd.DataFrame.from_records(
        records,
        columns=_output_columns(),
    )
    if frame.empty:
        return frame

    datetime_columns = (
        "raised_at",
        "acknowledged_at",
        "cleared_at",
        "event_start_at_utc",
        "event_end_at_utc",
    )
    for column in datetime_columns:
        frame[column] = pd.to_datetime(
            frame[column],
            utc=True,
            errors="coerce",
        )

    return frame.sort_values(
        [
            "raised_at",
            "plant_id",
            "equipment_id",
            "alarm_code",
            "alarm_id",
        ],
        kind="stable",
    ).reset_index(drop=True)


def _alarm_record(
    alarm: Alarm,
    *,
    candidate: _AlarmCandidate,
    schema_version: str,
) -> dict[str, object]:
    """Build one lineage-rich alarm output record."""
    return {
        "alarm_id": alarm.alarm_id,
        "plant_id": alarm.plant_id,
        "equipment_id": alarm.equipment_id,
        "source_asset_id": candidate.event.asset_id,
        "source_asset_type": candidate.event.asset_type,
        "event_scope": candidate.event.event_scope.value,
        "ground_truth_event_id": (candidate.event.ground_truth_event_id),
        "alarm_code": alarm.alarm_code,
        "alarm_name": alarm.alarm_name,
        "category": alarm.category.value,
        "severity": alarm.severity.value,
        "raised_at": alarm.raised_at,
        "status": alarm.status.value,
        "acknowledged_at": alarm.acknowledged_at,
        "cleared_at": alarm.cleared_at,
        "message": alarm.message,
        "is_open": alarm.is_open,
        "is_critical": alarm.is_critical,
        "acknowledgement_seconds": (alarm.acknowledgement_seconds),
        "resolution_seconds": alarm.resolution_seconds,
        "is_synthetic_ground_truth": (alarm.is_synthetic_ground_truth),
        "is_nuisance": candidate.is_nuisance,
        "incident_eligible": (candidate.definition.incident_eligible),
        "event_type": candidate.event.event_type.value,
        "event_start_at_utc": candidate.event.start_at_utc,
        "event_end_at_utc": candidate.event.end_at_utc,
        "generation_run_id": candidate.event.generation_run_id,
        "schema_version": schema_version,
    }


def _candidate_sort_key(
    candidate: _AlarmCandidate,
) -> tuple[datetime, str, str, str, bool]:
    """Return deterministic pre-ID alarm ordering."""
    return (
        candidate.raised_at,
        candidate.event.plant_id,
        candidate.equipment_id,
        candidate.definition.code,
        candidate.is_nuisance,
    )


def _event_sort_key(
    event: SyntheticEvent,
) -> tuple[datetime, str, str, str]:
    """Return deterministic event ordering."""
    return (
        event.start_at_utc,
        event.plant_id,
        event.asset_id,
        event.event_type.value,
    )


def _generator(
    *,
    config: AlarmOperationsConfig,
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


def _normalize_equipment_id(value: object) -> str:
    """Normalize and validate an EQP-formatted identifier."""
    normalized = str(value).strip().upper()
    if not _EQUIPMENT_ID_PATTERN.fullmatch(normalized):
        raise ValueError(
            f"Invalid equipment ID '{normalized}'. " "Use the format 'EQP-00001'."
        )
    return normalized


def _validate_aware_datetime(
    *,
    field_name: str,
    value: object,
) -> None:
    """Validate a timezone-aware datetime."""
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime value.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware.")


def _coerce_timestamp(
    value: object,
    *,
    field_name: str,
    allow_none: bool,
) -> datetime | None:
    """Coerce a DataFrame timestamp to an aware Python datetime."""
    if value is None or pd.isna(value):
        if allow_none:
            return None
        raise ValueError(f"{field_name} cannot be missing.")

    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware.")
    return timestamp.to_pydatetime().astimezone(UTC)


def _coerce_alarm_category(value: object):
    """Coerce a serialized category to the authoritative enum."""
    from eoip.synthetic.models.alarm import AlarmCategory

    return value if isinstance(value, AlarmCategory) else AlarmCategory(str(value))


def _coerce_alarm_severity(value: object) -> AlarmSeverity:
    """Coerce a serialized severity to AlarmSeverity."""
    return value if isinstance(value, AlarmSeverity) else AlarmSeverity(str(value))


def _coerce_alarm_status(value: object) -> AlarmStatus:
    """Coerce a serialized status to AlarmStatus."""
    return value if isinstance(value, AlarmStatus) else AlarmStatus(str(value))


def _output_columns() -> tuple[str, ...]:
    """Return the stable operational alarm output contract."""
    return (
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
    )


__all__ = [
    "AlarmGenerationResult",
    "AlarmGenerationSummary",
    "AlarmOperationsConfig",
    "AlarmSCADAContext",
    "alarms_to_domain_models",
    "generate_alarm_result",
    "generate_alarms",
]
