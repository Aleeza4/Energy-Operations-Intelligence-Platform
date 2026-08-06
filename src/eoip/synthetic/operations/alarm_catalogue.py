"""
Stable alarm catalogue for EOIP synthetic operational lifecycles.

This module defines immutable alarm reference data used by the Phase 2
operations layer. Alarm codes are stable public reference values and must not
be changed casually because events, alarms, incidents, tests, and downstream
analytics link through them.

The catalogue owns definitions only. It does not generate alarm lifecycles,
sample acknowledgement times, read SCADA frames, or create incidents.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from eoip.synthetic.events.catalogue import EventScope, EventType
from eoip.synthetic.models.alarm import AlarmCategory, AlarmSeverity


class AlarmClearBehavior(StrEnum):
    """Supported alarm-clear lifecycle behaviors."""

    AUTO_CLEAR = "auto_clear"
    CLEAR_WITH_EVENT = "clear_with_event"
    MANUAL_CLEAR = "manual_clear"
    LATCHED = "latched"
    NO_CLEAR = "no_clear"


@dataclass(frozen=True, slots=True)
class AlarmDefinition:
    """Immutable reference definition for one alarm code."""

    code: str
    name: str
    category: AlarmCategory
    default_severity: AlarmSeverity
    scope: EventScope
    trigger: str
    clear_behavior: AlarmClearBehavior
    trigger_delay_minutes: int = 0
    clear_delay_minutes: int = 0
    suppression_rules: tuple[str, ...] = ()
    source_event_types: tuple[EventType, ...] = ()
    incident_eligible: bool = True
    nuisance_eligible: bool = False
    message_template: str | None = None

    def __post_init__(self) -> None:
        """Normalize and validate an alarm definition."""
        normalized_code = self.code.strip().upper()
        normalized_name = self.name.strip()
        normalized_trigger = self.trigger.strip()
        normalized_rules = tuple(
            rule.strip().lower() for rule in self.suppression_rules
        )
        normalized_message = (
            None if self.message_template is None else self.message_template.strip()
        )

        object.__setattr__(self, "code", normalized_code)
        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "trigger", normalized_trigger)
        object.__setattr__(self, "suppression_rules", normalized_rules)
        object.__setattr__(self, "message_template", normalized_message)

        if not normalized_code:
            raise ValueError("code cannot be empty.")
        if len(normalized_code) > 50:
            raise ValueError("code cannot exceed 50 characters.")

        valid_characters = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        if any(character not in valid_characters for character in normalized_code):
            raise ValueError(
                "code may contain only uppercase letters, digits, hyphens, and "
                "underscores."
            )

        if not normalized_name:
            raise ValueError("name cannot be empty.")
        if len(normalized_name) > 150:
            raise ValueError("name cannot exceed 150 characters.")
        if not isinstance(self.category, AlarmCategory):
            raise TypeError("category must be an AlarmCategory value.")
        if not isinstance(self.default_severity, AlarmSeverity):
            raise TypeError("default_severity must be an AlarmSeverity value.")
        if not isinstance(self.scope, EventScope):
            raise TypeError("scope must be an EventScope value.")
        if not normalized_trigger:
            raise ValueError("trigger cannot be empty.")
        if not isinstance(self.clear_behavior, AlarmClearBehavior):
            raise TypeError("clear_behavior must be an AlarmClearBehavior value.")

        for field_name in ("trigger_delay_minutes", "clear_delay_minutes"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer.")
            if value < 0:
                raise ValueError(f"{field_name} must be non-negative.")

        if len(normalized_rules) != len(set(normalized_rules)):
            raise ValueError("suppression_rules must not contain duplicates.")
        if any(not rule for rule in normalized_rules):
            raise ValueError("suppression_rules must not contain blank values.")
        if len(self.source_event_types) != len(set(self.source_event_types)):
            raise ValueError("source_event_types must not contain duplicates.")
        if not all(isinstance(item, EventType) for item in self.source_event_types):
            raise TypeError("source_event_types must contain EventType values.")

        for field_name in ("incident_eligible", "nuisance_eligible"):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be a boolean.")

        if normalized_message == "":
            raise ValueError("message_template cannot be blank when supplied.")

    def to_record(self) -> dict[str, object]:
        """Return a serialization-ready alarm-definition record."""
        record = asdict(self)
        record["category"] = self.category.value
        record["default_severity"] = self.default_severity.value
        record["scope"] = self.scope.value
        record["clear_behavior"] = self.clear_behavior.value
        record["source_event_types"] = tuple(
            event_type.value for event_type in self.source_event_types
        )
        return record


_ALARM_DEFINITIONS: Final[tuple[AlarmDefinition, ...]] = (
    AlarmDefinition(
        code="GRID-LOSS-001",
        name="Grid Connection Lost",
        category=AlarmCategory.GRID,
        default_severity=AlarmSeverity.CRITICAL,
        scope=EventScope.PLANT,
        trigger=(
            "Grid-connected status becomes false while generation " "potential exists."
        ),
        clear_behavior=AlarmClearBehavior.CLEAR_WITH_EVENT,
        clear_delay_minutes=5,
        suppression_rules=("planned_grid_isolation",),
        source_event_types=(EventType.GRID_OUTAGE,),
        message_template="Grid connection is unavailable for {plant_id}.",
    ),
    AlarmDefinition(
        code="GRID-CURTAIL-001",
        name="Grid Export Curtailment Active",
        category=AlarmCategory.GRID,
        default_severity=AlarmSeverity.MAJOR,
        scope=EventScope.PLANT,
        trigger="Active grid export limit is below available plant generation.",
        clear_behavior=AlarmClearBehavior.CLEAR_WITH_EVENT,
        trigger_delay_minutes=15,
        suppression_rules=("nighttime_zero_export",),
        source_event_types=(EventType.GRID_CURTAILMENT,),
        message_template="Grid curtailment is limiting export at {plant_id}.",
    ),
    AlarmDefinition(
        code="PLANT-TRIP-001",
        name="Plant Protection Trip",
        category=AlarmCategory.SAFETY,
        default_severity=AlarmSeverity.CRITICAL,
        scope=EventScope.PLANT,
        trigger=(
            "Plant-level protection or control trip forces all generation "
            "unavailable."
        ),
        clear_behavior=AlarmClearBehavior.MANUAL_CLEAR,
        clear_delay_minutes=15,
        suppression_rules=("planned_plant_maintenance",),
        source_event_types=(EventType.PLANT_TRIP,),
        message_template="Plant protection trip detected at {plant_id}.",
    ),
    AlarmDefinition(
        code="FDR-TRIP-001",
        name="Feeder Protection Trip",
        category=AlarmCategory.EQUIPMENT,
        default_severity=AlarmSeverity.CRITICAL,
        scope=EventScope.FEEDER,
        trigger="Feeder protection indicates a trip and descendants are unavailable.",
        clear_behavior=AlarmClearBehavior.MANUAL_CLEAR,
        clear_delay_minutes=10,
        suppression_rules=("planned_feeder_isolation",),
        source_event_types=(EventType.FEEDER_TRIP,),
        message_template="Feeder trip detected for {asset_id} at {plant_id}.",
    ),
    AlarmDefinition(
        code="TX-TRIP-001",
        name="Transformer Protection Trip",
        category=AlarmCategory.EQUIPMENT,
        default_severity=AlarmSeverity.CRITICAL,
        scope=EventScope.TRANSFORMER,
        trigger=(
            "Transformer protection indicates a trip and descendants are "
            "unavailable."
        ),
        clear_behavior=AlarmClearBehavior.MANUAL_CLEAR,
        clear_delay_minutes=15,
        suppression_rules=("planned_transformer_isolation",),
        source_event_types=(EventType.TRANSFORMER_TRIP,),
        message_template="Transformer trip detected for {asset_id} at {plant_id}.",
    ),
    AlarmDefinition(
        code="INV-TRIP-001",
        name="Inverter Trip",
        category=AlarmCategory.EQUIPMENT,
        default_severity=AlarmSeverity.MAJOR,
        scope=EventScope.INVERTER,
        trigger=(
            "Inverter enters fault or stopped state while generation "
            "potential exists."
        ),
        clear_behavior=AlarmClearBehavior.MANUAL_CLEAR,
        clear_delay_minutes=5,
        suppression_rules=("planned_inverter_maintenance", "upstream_outage_active"),
        source_event_types=(EventType.INVERTER_TRIP,),
        message_template="Inverter trip detected for {asset_id} at {plant_id}.",
    ),
    AlarmDefinition(
        code="INV-DERATE-001",
        name="Inverter Output Derating",
        category=AlarmCategory.PERFORMANCE,
        default_severity=AlarmSeverity.WARNING,
        scope=EventScope.INVERTER,
        trigger="Inverter output remains materially below expected output.",
        clear_behavior=AlarmClearBehavior.AUTO_CLEAR,
        trigger_delay_minutes=30,
        clear_delay_minutes=30,
        suppression_rules=(
            "low_irradiance",
            "upstream_outage_active",
            "active_curtailment",
        ),
        source_event_types=(EventType.INVERTER_DERATING,),
        nuisance_eligible=True,
        message_template="Inverter {asset_id} is operating below expected output.",
    ),
    AlarmDefinition(
        code="INV-TEMP-001",
        name="Inverter High Temperature",
        category=AlarmCategory.ENVIRONMENTAL,
        default_severity=AlarmSeverity.MAJOR,
        scope=EventScope.INVERTER,
        trigger="Inverter temperature exceeds its configured thermal threshold.",
        clear_behavior=AlarmClearBehavior.AUTO_CLEAR,
        trigger_delay_minutes=15,
        clear_delay_minutes=30,
        suppression_rules=("invalid_temperature_sensor",),
        source_event_types=(EventType.THERMAL_DERATING,),
        message_template="High inverter temperature detected for {asset_id}.",
    ),
    AlarmDefinition(
        code="INV-MPPT-001",
        name="MPPT Tracking Fault",
        category=AlarmCategory.EQUIPMENT,
        default_severity=AlarmSeverity.MAJOR,
        scope=EventScope.INVERTER,
        trigger="DC behavior indicates unstable or ineffective MPPT tracking.",
        clear_behavior=AlarmClearBehavior.MANUAL_CLEAR,
        trigger_delay_minutes=15,
        clear_delay_minutes=15,
        suppression_rules=("low_irradiance", "planned_inverter_maintenance"),
        source_event_types=(EventType.MPPT_FAULT,),
        message_template="MPPT fault detected for inverter {asset_id}.",
    ),
    AlarmDefinition(
        code="INV-DC-LOSS-001",
        name="DC String Production Loss",
        category=AlarmCategory.PERFORMANCE,
        default_severity=AlarmSeverity.WARNING,
        scope=EventScope.INVERTER,
        trigger="DC current or power shows a persistent step reduction.",
        clear_behavior=AlarmClearBehavior.MANUAL_CLEAR,
        trigger_delay_minutes=60,
        clear_delay_minutes=30,
        suppression_rules=(
            "low_irradiance",
            "active_curtailment",
            "upstream_outage_active",
        ),
        source_event_types=(EventType.DC_STRING_LOSS,),
        nuisance_eligible=True,
        message_template="Possible DC string loss detected for inverter {asset_id}.",
    ),
    AlarmDefinition(
        code="DATA-DRIFT-001",
        name="Sensor Measurement Drift",
        category=AlarmCategory.COMMUNICATION,
        default_severity=AlarmSeverity.WARNING,
        scope=EventScope.SENSOR,
        trigger="Sensor value develops persistent bias versus expected behavior.",
        clear_behavior=AlarmClearBehavior.MANUAL_CLEAR,
        trigger_delay_minutes=60,
        suppression_rules=("sensor_out_of_service",),
        source_event_types=(EventType.SENSOR_DRIFT,),
        nuisance_eligible=True,
        message_template="Measurement drift detected for sensor {asset_id}.",
    ),
    AlarmDefinition(
        code="DATA-STUCK-001",
        name="Sensor Value Stuck",
        category=AlarmCategory.COMMUNICATION,
        default_severity=AlarmSeverity.WARNING,
        scope=EventScope.SENSOR,
        trigger="Sensor repeats an unchanged value beyond the configured duration.",
        clear_behavior=AlarmClearBehavior.AUTO_CLEAR,
        trigger_delay_minutes=30,
        clear_delay_minutes=15,
        suppression_rules=("sensor_out_of_service",),
        source_event_types=(EventType.SENSOR_STUCK,),
        nuisance_eligible=True,
        message_template="Stuck measurement detected for sensor {asset_id}.",
    ),
    AlarmDefinition(
        code="COMMS-LOSS-001",
        name="Telemetry Communication Loss",
        category=AlarmCategory.COMMUNICATION,
        default_severity=AlarmSeverity.MAJOR,
        scope=EventScope.SENSOR,
        trigger="Expected telemetry is missing beyond the communication threshold.",
        clear_behavior=AlarmClearBehavior.AUTO_CLEAR,
        trigger_delay_minutes=15,
        clear_delay_minutes=15,
        suppression_rules=("planned_communications_maintenance",),
        source_event_types=(EventType.TELEMETRY_GAP,),
        message_template="Telemetry communication loss detected for {asset_id}.",
    ),
    AlarmDefinition(
        code="MTR-RESET-001",
        name="Revenue Meter Register Reset",
        category=AlarmCategory.COMMUNICATION,
        default_severity=AlarmSeverity.MAJOR,
        scope=EventScope.SENSOR,
        trigger="Cumulative export register decreases outside an approved condition.",
        clear_behavior=AlarmClearBehavior.LATCHED,
        suppression_rules=("approved_meter_replacement",),
        source_event_types=(EventType.METER_RESET,),
        message_template="Revenue meter register reset detected for {asset_id}.",
    ),
    AlarmDefinition(
        code="MAINT-OUTAGE-001",
        name="Planned Maintenance Outage",
        category=AlarmCategory.EQUIPMENT,
        default_severity=AlarmSeverity.INFORMATIONAL,
        scope=EventScope.INVERTER,
        trigger="Asset enters an approved planned-maintenance state.",
        clear_behavior=AlarmClearBehavior.CLEAR_WITH_EVENT,
        suppression_rules=("suppress_failure_alarms",),
        source_event_types=(EventType.MAINTENANCE_OUTAGE,),
        incident_eligible=False,
        message_template="Planned maintenance is active for {asset_id}.",
    ),
    AlarmDefinition(
        code="ENV-TEMP-001",
        name="High Ambient Temperature Stress",
        category=AlarmCategory.ENVIRONMENTAL,
        default_severity=AlarmSeverity.WARNING,
        scope=EventScope.PLANT,
        trigger="Ambient or cell temperature exceeds the configured stress threshold.",
        clear_behavior=AlarmClearBehavior.AUTO_CLEAR,
        trigger_delay_minutes=30,
        clear_delay_minutes=30,
        suppression_rules=("invalid_weather_station_data",),
        source_event_types=(EventType.HIGH_TEMPERATURE_STRESS,),
        nuisance_eligible=True,
        message_template="High temperature stress is active at {plant_id}.",
    ),
    AlarmDefinition(
        code="ENV-STORM-001",
        name="Severe Weather Event",
        category=AlarmCategory.ENVIRONMENTAL,
        default_severity=AlarmSeverity.MAJOR,
        scope=EventScope.PLANT,
        trigger="Weather indicates materially elevated wind, rain, or irradiance loss.",
        clear_behavior=AlarmClearBehavior.CLEAR_WITH_EVENT,
        trigger_delay_minutes=15,
        clear_delay_minutes=30,
        suppression_rules=("invalid_weather_station_data",),
        source_event_types=(EventType.STORM_EVENT,),
        message_template="Severe weather conditions detected at {plant_id}.",
    ),
)


class AlarmCatalogue:
    """Immutable lookup and filtering interface for alarm definitions."""

    def __init__(
        self,
        definitions: Iterable[AlarmDefinition] = _ALARM_DEFINITIONS,
    ) -> None:
        """Build and validate an alarm catalogue."""
        ordered = tuple(definitions)
        if not ordered:
            raise ValueError("AlarmCatalogue requires at least one definition.")

        codes = tuple(definition.code for definition in ordered)
        if len(codes) != len(set(codes)):
            raise ValueError("AlarmCatalogue contains duplicate alarm codes.")

        self._definitions = tuple(sorted(ordered, key=lambda item: item.code))
        self._by_code = MappingProxyType(
            {definition.code: definition for definition in self._definitions}
        )

    def __len__(self) -> int:
        """Return the number of alarm definitions."""
        return len(self._definitions)

    def __iter__(self):
        """Iterate through definitions in stable code order."""
        return iter(self._definitions)

    def get(self, code: str) -> AlarmDefinition:
        """Return one alarm definition by stable code."""
        normalized_code = code.strip().upper()
        if not normalized_code:
            raise ValueError("code cannot be empty.")
        try:
            return self._by_code[normalized_code]
        except KeyError as error:
            raise KeyError(f"Unknown alarm code '{normalized_code}'.") from error

    def find(self, code: str) -> AlarmDefinition | None:
        """Return a definition when present, otherwise None."""
        normalized_code = code.strip().upper()
        if not normalized_code:
            raise ValueError("code cannot be empty.")
        return self._by_code.get(normalized_code)

    def by_category(self, category: AlarmCategory) -> tuple[AlarmDefinition, ...]:
        """Return definitions matching an alarm category."""
        if not isinstance(category, AlarmCategory):
            raise TypeError("category must be an AlarmCategory value.")
        return tuple(item for item in self._definitions if item.category is category)

    def by_severity(self, severity: AlarmSeverity) -> tuple[AlarmDefinition, ...]:
        """Return definitions matching a default severity."""
        if not isinstance(severity, AlarmSeverity):
            raise TypeError("severity must be an AlarmSeverity value.")
        return tuple(
            item for item in self._definitions if item.default_severity is severity
        )

    def by_scope(self, scope: EventScope) -> tuple[AlarmDefinition, ...]:
        """Return definitions matching an operational scope."""
        if not isinstance(scope, EventScope):
            raise TypeError("scope must be an EventScope value.")
        return tuple(item for item in self._definitions if item.scope is scope)

    def for_event_type(self, event_type: EventType) -> tuple[AlarmDefinition, ...]:
        """Return definitions mapped to an event type."""
        if not isinstance(event_type, EventType):
            raise TypeError("event_type must be an EventType value.")
        return tuple(
            item for item in self._definitions if event_type in item.source_event_types
        )

    def incident_eligible(self) -> tuple[AlarmDefinition, ...]:
        """Return definitions eligible for incident creation."""
        return tuple(item for item in self._definitions if item.incident_eligible)

    def nuisance_eligible(self) -> tuple[AlarmDefinition, ...]:
        """Return definitions eligible for bounded nuisance alarms."""
        return tuple(item for item in self._definitions if item.nuisance_eligible)

    @property
    def codes(self) -> tuple[str, ...]:
        """Return all stable alarm codes in deterministic order."""
        return tuple(self._by_code)

    @property
    def mapping(self) -> Mapping[str, AlarmDefinition]:
        """Return the immutable code-to-definition mapping."""
        return self._by_code

    def to_records(self) -> tuple[dict[str, object], ...]:
        """Return all definitions as serialization-ready records."""
        return tuple(item.to_record() for item in self._definitions)


DEFAULT_ALARM_CATALOGUE: Final[AlarmCatalogue] = AlarmCatalogue()


def get_alarm_definition(code: str) -> AlarmDefinition:
    """Return an alarm definition from the default catalogue."""
    return DEFAULT_ALARM_CATALOGUE.get(code)


def find_alarm_definition(code: str) -> AlarmDefinition | None:
    """Return an alarm definition when the code is known."""
    return DEFAULT_ALARM_CATALOGUE.find(code)


def list_alarm_definitions() -> tuple[AlarmDefinition, ...]:
    """Return all default alarm definitions."""
    return tuple(DEFAULT_ALARM_CATALOGUE)


__all__ = [
    "DEFAULT_ALARM_CATALOGUE",
    "AlarmCatalogue",
    "AlarmClearBehavior",
    "AlarmDefinition",
    "find_alarm_definition",
    "get_alarm_definition",
    "list_alarm_definitions",
]
