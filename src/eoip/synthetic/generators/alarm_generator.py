"""
Alarm generator for EOIP synthetic data generation.

This module derives deterministic, validated Alarm domain objects from
synthetic SCADA observations. Alarms are created from equipment faults,
maintenance states, derating conditions, and prolonged grid stoppages rather
than being generated as unrelated random records.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import timedelta
from typing import Final

from eoip.synthetic.generators.equipment_generator import (
    EquipmentGeneratorConfig,
)
from eoip.synthetic.generators.plant_generator import (
    PlantGeneratorConfig,
)
from eoip.synthetic.generators.scada_generator import (
    SCADAGeneratorConfig,
    generate_scada,
)
from eoip.synthetic.generators.weather_generator import (
    WeatherGeneratorConfig,
)
from eoip.synthetic.models.alarm import (
    Alarm,
    AlarmCategory,
    AlarmSeverity,
    AlarmStatus,
)
from eoip.synthetic.models.scada import (
    SCADAObservation,
    SCADAOperatingState,
)

_DEFAULT_RANDOM_SEED: Final[int] = 42
_DEFAULT_ACKNOWLEDGEMENT_MINUTES: Final[int] = 5
_DEFAULT_CLEARANCE_MINUTES: Final[int] = 30


@dataclass(frozen=True, slots=True)
class AlarmGeneratorConfig:
    """Configuration for deterministic alarm generation."""

    random_seed: int = _DEFAULT_RANDOM_SEED
    acknowledgement_probability: float = 0.85
    clearance_probability: float = 0.80
    minimum_acknowledgement_minutes: int = 1
    maximum_acknowledgement_minutes: int = 15
    minimum_clearance_minutes: int = 5
    maximum_clearance_minutes: int = 120
    generate_derating_alarms: bool = True
    generate_maintenance_alarms: bool = True
    generate_grid_alarms: bool = True
    is_synthetic_ground_truth: bool = True

    def __post_init__(self) -> None:
        """Validate alarm-generator configuration."""
        if isinstance(self.random_seed, bool) or not isinstance(
            self.random_seed,
            int,
        ):
            raise TypeError("random_seed must be an integer.")

        self._validate_probability(
            field_name="acknowledgement_probability",
            value=self.acknowledgement_probability,
        )
        self._validate_probability(
            field_name="clearance_probability",
            value=self.clearance_probability,
        )

        integer_fields = (
            "minimum_acknowledgement_minutes",
            "maximum_acknowledgement_minutes",
            "minimum_clearance_minutes",
            "maximum_clearance_minutes",
        )

        for field_name in integer_fields:
            value = getattr(self, field_name)

            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer.")

            if value < 0:
                raise ValueError(f"{field_name} must be greater than or equal to zero.")

        if self.maximum_acknowledgement_minutes < self.minimum_acknowledgement_minutes:
            raise ValueError(
                "maximum_acknowledgement_minutes must be greater than or "
                "equal to minimum_acknowledgement_minutes."
            )

        if self.maximum_clearance_minutes < self.minimum_clearance_minutes:
            raise ValueError(
                "maximum_clearance_minutes must be greater than or equal to "
                "minimum_clearance_minutes."
            )

        boolean_fields = (
            "generate_derating_alarms",
            "generate_maintenance_alarms",
            "generate_grid_alarms",
            "is_synthetic_ground_truth",
        )

        for field_name in boolean_fields:
            value = getattr(self, field_name)
            if not isinstance(value, bool):
                raise TypeError(f"{field_name} must be a boolean.")

    @staticmethod
    def _validate_probability(
        *,
        field_name: str,
        value: float,
    ) -> None:
        """Validate a probability between zero and one."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{field_name} must be numeric.")

        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{field_name} must be between 0.0 and 1.0.")


@dataclass(frozen=True, slots=True)
class _AlarmDefinition:
    """Internal immutable mapping from SCADA state to alarm metadata."""

    alarm_code: str
    alarm_name: str
    category: AlarmCategory
    severity: AlarmSeverity
    message: str


_ALARM_DEFINITIONS: Final[dict[SCADAOperatingState, _AlarmDefinition]] = {
    SCADAOperatingState.FAULT: _AlarmDefinition(
        alarm_code="EQUIPMENT_FAULT",
        alarm_name="Equipment Fault",
        category=AlarmCategory.EQUIPMENT,
        severity=AlarmSeverity.CRITICAL,
        message="Equipment entered a forced-fault operating state.",
    ),
    SCADAOperatingState.DERATED: _AlarmDefinition(
        alarm_code="PERFORMANCE_DERATING",
        alarm_name="Performance Derating",
        category=AlarmCategory.PERFORMANCE,
        severity=AlarmSeverity.WARNING,
        message="Equipment output is below its expected operating level.",
    ),
    SCADAOperatingState.MAINTENANCE: _AlarmDefinition(
        alarm_code="PLANNED_MAINTENANCE",
        alarm_name="Planned Maintenance",
        category=AlarmCategory.EQUIPMENT,
        severity=AlarmSeverity.INFORMATIONAL,
        message="Equipment is unavailable due to planned maintenance.",
    ),
    SCADAOperatingState.STOPPED: _AlarmDefinition(
        alarm_code="GRID_UNAVAILABLE",
        alarm_name="Grid Unavailable",
        category=AlarmCategory.GRID,
        severity=AlarmSeverity.MAJOR,
        message="Generation stopped because the grid is unavailable.",
    ),
}


def generate_alarms(
    config: AlarmGeneratorConfig | None = None,
    *,
    scada_config: SCADAGeneratorConfig | None = None,
    plant_config: PlantGeneratorConfig | None = None,
    equipment_config: EquipmentGeneratorConfig | None = None,
    weather_config: WeatherGeneratorConfig | None = None,
) -> tuple[Alarm, ...]:
    """
    Generate deterministic alarms from synthetic SCADA observations.

    Consecutive observations with the same alarm-producing operating state are
    merged into one alarm event for each equipment asset.
    """
    resolved_config = config or AlarmGeneratorConfig()
    observations = generate_scada(
        scada_config,
        plant_config=plant_config,
        equipment_config=equipment_config,
        weather_config=weather_config,
    )

    grouped = _group_by_equipment(observations)
    alarms: list[Alarm] = []
    alarm_counter = 1

    for equipment_index, equipment_id in enumerate(
        sorted(grouped),
        start=1,
    ):
        rng = random.Random(
            _equipment_seed(
                base_seed=resolved_config.random_seed,
                equipment_index=equipment_index,
            )
        )
        events = _extract_alarm_events(
            observations=grouped[equipment_id],
            config=resolved_config,
        )

        for event in events:
            alarm = _build_alarm(
                alarm_id=f"ALM-{alarm_counter:07d}",
                event=event,
                config=resolved_config,
                rng=rng,
            )
            alarms.append(alarm)
            alarm_counter += 1

    return tuple(alarms)


def generate_alarm_records(
    config: AlarmGeneratorConfig | None = None,
    *,
    scada_config: SCADAGeneratorConfig | None = None,
    plant_config: PlantGeneratorConfig | None = None,
    equipment_config: EquipmentGeneratorConfig | None = None,
    weather_config: WeatherGeneratorConfig | None = None,
) -> tuple[dict[str, object], ...]:
    """Generate serialization-ready alarm records."""
    return tuple(
        alarm.to_record()
        for alarm in generate_alarms(
            config,
            scada_config=scada_config,
            plant_config=plant_config,
            equipment_config=equipment_config,
            weather_config=weather_config,
        )
    )


@dataclass(frozen=True, slots=True)
class _AlarmEvent:
    """Internal merged alarm event derived from SCADA observations."""

    plant_id: str
    equipment_id: str
    state: SCADAOperatingState
    raised_at: object
    ended_at: object | None


def _group_by_equipment(
    observations: tuple[SCADAObservation, ...],
) -> dict[str, tuple[SCADAObservation, ...]]:
    """Group and chronologically sort SCADA observations by equipment."""
    grouped_lists: dict[str, list[SCADAObservation]] = {}

    for observation in observations:
        grouped_lists.setdefault(
            observation.equipment_id,
            [],
        ).append(observation)

    return {
        equipment_id: tuple(
            sorted(
                equipment_observations,
                key=lambda item: item.timestamp,
            )
        )
        for equipment_id, equipment_observations in grouped_lists.items()
    }


def _extract_alarm_events(
    *,
    observations: tuple[SCADAObservation, ...],
    config: AlarmGeneratorConfig,
) -> tuple[_AlarmEvent, ...]:
    """Merge consecutive alarm-producing SCADA states into event windows."""
    events: list[_AlarmEvent] = []
    active_state: SCADAOperatingState | None = None
    active_start = None
    active_plant_id = ""
    active_equipment_id = ""

    for observation in observations:
        candidate_state = _alarm_state_for_observation(
            observation=observation,
            config=config,
        )

        if candidate_state == active_state:
            continue

        if active_state is not None and active_start is not None:
            events.append(
                _AlarmEvent(
                    plant_id=active_plant_id,
                    equipment_id=active_equipment_id,
                    state=active_state,
                    raised_at=active_start,
                    ended_at=observation.timestamp,
                )
            )

        if candidate_state is None:
            active_state = None
            active_start = None
            active_plant_id = ""
            active_equipment_id = ""
            continue

        active_state = candidate_state
        active_start = observation.timestamp
        active_plant_id = observation.plant_id
        active_equipment_id = observation.equipment_id

    if active_state is not None and active_start is not None:
        events.append(
            _AlarmEvent(
                plant_id=active_plant_id,
                equipment_id=active_equipment_id,
                state=active_state,
                raised_at=active_start,
                ended_at=None,
            )
        )

    return tuple(events)


def _alarm_state_for_observation(
    *,
    observation: SCADAObservation,
    config: AlarmGeneratorConfig,
) -> SCADAOperatingState | None:
    """Return an alarm-producing state or None."""
    state = observation.operating_state

    if state is SCADAOperatingState.FAULT:
        return state

    if state is SCADAOperatingState.DERATED and config.generate_derating_alarms:
        return state

    if state is SCADAOperatingState.MAINTENANCE and config.generate_maintenance_alarms:
        return state

    if (
        state is SCADAOperatingState.STOPPED
        and config.generate_grid_alarms
        and observation.grid_available is False
    ):
        return state

    return None


def _build_alarm(
    *,
    alarm_id: str,
    event: _AlarmEvent,
    config: AlarmGeneratorConfig,
    rng: random.Random,
) -> Alarm:
    """Build one validated Alarm from a merged SCADA event."""
    from datetime import datetime

    if not isinstance(event.raised_at, datetime):
        raise TypeError("event.raised_at must be a datetime value.")

    if event.ended_at is not None and not isinstance(
        event.ended_at,
        datetime,
    ):
        raise TypeError("event.ended_at must be a datetime value or None.")

    definition = _ALARM_DEFINITIONS[event.state]
    acknowledged_at = None
    cleared_at = None

    if rng.random() < config.acknowledgement_probability:
        acknowledgement_delay = rng.randint(
            config.minimum_acknowledgement_minutes,
            config.maximum_acknowledgement_minutes,
        )
        acknowledged_at = event.raised_at + timedelta(minutes=acknowledgement_delay)

    if event.ended_at is not None and rng.random() < config.clearance_probability:
        clearance_delay = rng.randint(
            config.minimum_clearance_minutes,
            config.maximum_clearance_minutes,
        )
        candidate_clearance = event.ended_at + timedelta(minutes=clearance_delay)

        if acknowledged_at is not None:
            candidate_clearance = max(
                candidate_clearance,
                acknowledged_at,
            )

        cleared_at = candidate_clearance

    status = _resolve_status(
        acknowledged_at=acknowledged_at,
        cleared_at=cleared_at,
    )

    return Alarm(
        alarm_id=alarm_id,
        plant_id=event.plant_id,
        equipment_id=event.equipment_id,
        alarm_code=definition.alarm_code,
        alarm_name=definition.alarm_name,
        category=definition.category,
        severity=definition.severity,
        raised_at=event.raised_at,
        status=status,
        acknowledged_at=acknowledged_at,
        cleared_at=cleared_at,
        message=definition.message,
        is_synthetic_ground_truth=config.is_synthetic_ground_truth,
    )


def _resolve_status(
    *,
    acknowledged_at: object | None,
    cleared_at: object | None,
) -> AlarmStatus:
    """Resolve lifecycle status from generated timestamps."""
    if cleared_at is not None:
        return AlarmStatus.CLEARED

    if acknowledged_at is not None:
        return AlarmStatus.ACKNOWLEDGED

    return AlarmStatus.ACTIVE


def _equipment_seed(*, base_seed: int, equipment_index: int) -> int:
    """Return a stable random seed for one equipment alarm stream."""
    return base_seed * 100_000 + equipment_index
