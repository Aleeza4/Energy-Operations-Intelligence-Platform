"""
Canonical synthetic event catalogue for EOIP Phase 2.

This module owns immutable event definitions used by event scheduling,
effect application, alarm generation, incident generation, and work-order
generation. It follows the event catalogue contract in
PHASE_2_IMPLEMENTATION_PLAN.md and performs no random sampling, DataFrame
creation, file I/O, or event scheduling.

All event definitions are deterministic, validated, and exposed through a
stable lookup API.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final


class EventScope(StrEnum):
    """Supported synthetic event propagation scopes."""

    PORTFOLIO = "portfolio"
    PLANT = "plant"
    FEEDER = "feeder"
    TRANSFORMER = "transformer"
    INVERTER = "inverter"
    SENSOR = "sensor"


class EventType(StrEnum):
    """Canonical Phase 2 synthetic event types."""

    GRID_OUTAGE = "grid_outage"
    GRID_CURTAILMENT = "grid_curtailment"
    PLANT_TRIP = "plant_trip"
    FEEDER_TRIP = "feeder_trip"
    TRANSFORMER_TRIP = "transformer_trip"
    INVERTER_TRIP = "inverter_trip"
    INVERTER_DERATING = "inverter_derating"
    THERMAL_DERATING = "thermal_derating"
    MPPT_FAULT = "mppt_fault"
    DC_STRING_LOSS = "dc_string_loss"
    SOILING_ACCUMULATION = "soiling_accumulation"
    CLEANING_RECOVERY = "cleaning_recovery"
    SENSOR_DRIFT = "sensor_drift"
    SENSOR_STUCK = "sensor_stuck"
    TELEMETRY_GAP = "telemetry_gap"
    METER_RESET = "meter_reset"
    MAINTENANCE_OUTAGE = "maintenance_outage"
    HIGH_TEMPERATURE_STRESS = "high_temperature_stress"
    STORM_EVENT = "storm_event"


class EventSeverity(StrEnum):
    """Operational severity bands used by event definitions."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryBehavior(StrEnum):
    """Supported recovery behaviors after an event ends."""

    INSTANT = "instant"
    LINEAR_RAMP = "linear_ramp"
    EXPONENTIAL = "exponential"
    MANUAL_RESET = "manual_reset"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class DurationDistribution:
    """Bounded event-duration distribution in minutes."""

    minimum_minutes: int
    typical_minutes: int
    maximum_minutes: int

    def __post_init__(self) -> None:
        """Validate duration ordering and types."""
        values = (
            self.minimum_minutes,
            self.typical_minutes,
            self.maximum_minutes,
        )

        for value in values:
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError("Duration values must be integers.")

            if value <= 0:
                raise ValueError("Duration values must be greater than zero.")

        if not (self.minimum_minutes <= self.typical_minutes <= self.maximum_minutes):
            raise ValueError(
                "Duration values must satisfy minimum <= typical <= maximum."
            )


@dataclass(frozen=True, slots=True)
class SeverityWeight:
    """Probability weight for one event severity."""

    severity: EventSeverity
    weight: float

    def __post_init__(self) -> None:
        """Validate severity weight."""
        if not isinstance(self.severity, EventSeverity):
            raise TypeError("severity must be an EventSeverity value.")

        if isinstance(self.weight, bool) or not isinstance(
            self.weight,
            (int, float),
        ):
            raise TypeError("weight must be numeric.")

        if not math.isfinite(self.weight):
            raise ValueError("weight must be finite.")

        if self.weight <= 0:
            raise ValueError("weight must be greater than zero.")


@dataclass(frozen=True, slots=True)
class EventDefinition:
    """Immutable definition of one schedulable synthetic event type."""

    event_type: EventType
    display_name: str
    description: str
    eligible_scopes: tuple[EventScope, ...]
    annual_rate_per_eligible_asset: float
    duration: DurationDistribution
    severity_distribution: tuple[SeverityWeight, ...]
    minimum_power_modifier_ratio: float | None
    maximum_power_modifier_ratio: float | None
    measurement_channels: tuple[str, ...]
    alarm_codes: tuple[str, ...]
    incident_probability: float
    work_order_probability: float
    requires_daylight: bool = False
    excludes_daylight: bool = False
    planned: bool = False
    recovery_behavior: RecoveryBehavior = RecoveryBehavior.INSTANT
    minimum_separation_minutes: int = 0
    seasonal_months: tuple[int, ...] = ()
    allowed_overlap_types: tuple[EventType, ...] = ()

    def __post_init__(self) -> None:
        """Normalize and validate the complete event definition."""
        normalized_name = self.display_name.strip()
        normalized_description = self.description.strip()
        normalized_channels = tuple(
            channel.strip().lower() for channel in self.measurement_channels
        )
        normalized_alarm_codes = tuple(
            code.strip().upper() for code in self.alarm_codes
        )

        object.__setattr__(self, "display_name", normalized_name)
        object.__setattr__(
            self,
            "description",
            normalized_description,
        )
        object.__setattr__(
            self,
            "measurement_channels",
            normalized_channels,
        )
        object.__setattr__(
            self,
            "alarm_codes",
            normalized_alarm_codes,
        )

        if not isinstance(self.event_type, EventType):
            raise TypeError("event_type must be an EventType value.")

        if not normalized_name:
            raise ValueError("display_name cannot be empty.")

        if not normalized_description:
            raise ValueError("description cannot be empty.")

        if not self.eligible_scopes:
            raise ValueError("eligible_scopes must not be empty.")

        if len(self.eligible_scopes) != len(set(self.eligible_scopes)):
            raise ValueError("eligible_scopes must not contain duplicates.")

        if not all(isinstance(scope, EventScope) for scope in self.eligible_scopes):
            raise TypeError("eligible_scopes must contain only EventScope values.")

        self._validate_probability(
            field_name="incident_probability",
            value=self.incident_probability,
        )
        self._validate_probability(
            field_name="work_order_probability",
            value=self.work_order_probability,
        )

        if isinstance(self.annual_rate_per_eligible_asset, bool) or not isinstance(
            self.annual_rate_per_eligible_asset,
            (int, float),
        ):
            raise TypeError("annual_rate_per_eligible_asset must be numeric.")

        if not math.isfinite(self.annual_rate_per_eligible_asset):
            raise ValueError("annual_rate_per_eligible_asset must be finite.")

        if self.annual_rate_per_eligible_asset < 0:
            raise ValueError("annual_rate_per_eligible_asset must be non-negative.")

        if not self.severity_distribution:
            raise ValueError("severity_distribution must not be empty.")

        severities = tuple(item.severity for item in self.severity_distribution)
        if len(severities) != len(set(severities)):
            raise ValueError("severity_distribution must not repeat severities.")

        if sum(item.weight for item in self.severity_distribution) <= 0:
            raise ValueError("severity_distribution weights must sum above zero.")

        self._validate_power_modifier_bounds()

        if self.requires_daylight and self.excludes_daylight:
            raise ValueError("An event cannot both require and exclude daylight.")

        if not isinstance(self.planned, bool):
            raise TypeError("planned must be a boolean.")

        if not isinstance(self.recovery_behavior, RecoveryBehavior):
            raise TypeError("recovery_behavior must be a RecoveryBehavior value.")

        if isinstance(self.minimum_separation_minutes, bool) or not isinstance(
            self.minimum_separation_minutes, int
        ):
            raise TypeError("minimum_separation_minutes must be an integer.")

        if self.minimum_separation_minutes < 0:
            raise ValueError("minimum_separation_minutes must be non-negative.")

        if len(normalized_channels) != len(set(normalized_channels)):
            raise ValueError("measurement_channels must not contain duplicates.")

        if any(not channel for channel in normalized_channels):
            raise ValueError("measurement_channels must not contain blank values.")

        if len(normalized_alarm_codes) != len(set(normalized_alarm_codes)):
            raise ValueError("alarm_codes must not contain duplicates.")

        if any(not code for code in normalized_alarm_codes):
            raise ValueError("alarm_codes must not contain blank values.")

        if len(self.seasonal_months) != len(set(self.seasonal_months)):
            raise ValueError("seasonal_months must not contain duplicates.")

        if any(month < 1 or month > 12 for month in self.seasonal_months):
            raise ValueError("seasonal_months values must be between 1 and 12.")

        if not all(
            isinstance(event_type, EventType)
            for event_type in self.allowed_overlap_types
        ):
            raise TypeError("allowed_overlap_types must contain EventType values.")

    @staticmethod
    def _validate_probability(
        *,
        field_name: str,
        value: float,
    ) -> None:
        """Validate a finite probability between zero and one."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{field_name} must be numeric.")

        if not math.isfinite(value):
            raise ValueError(f"{field_name} must be finite.")

        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{field_name} must be between zero and one.")

    def _validate_power_modifier_bounds(self) -> None:
        """Validate optional power-modifier bounds."""
        minimum = self.minimum_power_modifier_ratio
        maximum = self.maximum_power_modifier_ratio

        if minimum is None and maximum is None:
            return

        if minimum is None or maximum is None:
            raise ValueError("Power modifier bounds must both be set or both be None.")

        for field_name, value in (
            ("minimum_power_modifier_ratio", minimum),
            ("maximum_power_modifier_ratio", maximum),
        ):
            if isinstance(value, bool) or not isinstance(
                value,
                (int, float),
            ):
                raise TypeError(f"{field_name} must be numeric.")

            if not math.isfinite(value):
                raise ValueError(f"{field_name} must be finite.")

            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between zero and one.")

        if maximum < minimum:
            raise ValueError(
                "maximum_power_modifier_ratio must be greater than or equal "
                "to minimum_power_modifier_ratio."
            )

    @property
    def normalized_severity_weights(
        self,
    ) -> Mapping[EventSeverity, float]:
        """Return normalized severity probabilities."""
        total = sum(item.weight for item in self.severity_distribution)
        return MappingProxyType(
            {item.severity: item.weight / total for item in self.severity_distribution}
        )

    @property
    def creates_physical_power_effect(self) -> bool:
        """Return whether the event changes physical power."""
        return self.minimum_power_modifier_ratio is not None

    @property
    def creates_measurement_effect(self) -> bool:
        """Return whether the event targets measurement channels."""
        return bool(self.measurement_channels)

    def to_record(self) -> dict[str, object]:
        """Return a serialization-ready event-definition record."""
        record = asdict(self)
        record["event_type"] = self.event_type.value
        record["eligible_scopes"] = tuple(scope.value for scope in self.eligible_scopes)
        record["severity_distribution"] = tuple(
            {
                "severity": item.severity.value,
                "weight": item.weight,
            }
            for item in self.severity_distribution
        )
        record["recovery_behavior"] = self.recovery_behavior.value
        record["allowed_overlap_types"] = tuple(
            event_type.value for event_type in self.allowed_overlap_types
        )
        return record


def _severity_distribution(
    *items: tuple[EventSeverity, float],
) -> tuple[SeverityWeight, ...]:
    """Build a validated immutable severity distribution."""
    return tuple(
        SeverityWeight(severity=severity, weight=weight) for severity, weight in items
    )


_EVENT_DEFINITIONS: Final[tuple[EventDefinition, ...]] = (
    EventDefinition(
        event_type=EventType.GRID_OUTAGE,
        display_name="Grid Outage",
        description=(
            "Plant or portfolio export is forced to zero because the "
            "interconnecting grid is unavailable."
        ),
        eligible_scopes=(EventScope.PLANT, EventScope.PORTFOLIO),
        annual_rate_per_eligible_asset=1.8,
        duration=DurationDistribution(15, 90, 720),
        severity_distribution=_severity_distribution(
            (EventSeverity.HIGH, 0.35),
            (EventSeverity.CRITICAL, 0.65),
        ),
        minimum_power_modifier_ratio=0.0,
        maximum_power_modifier_ratio=0.0,
        measurement_channels=(),
        alarm_codes=("GRID-LOSS-001",),
        incident_probability=1.0,
        work_order_probability=0.10,
        recovery_behavior=RecoveryBehavior.LINEAR_RAMP,
        minimum_separation_minutes=720,
        allowed_overlap_types=(EventType.STORM_EVENT,),
    ),
    EventDefinition(
        event_type=EventType.GRID_CURTAILMENT,
        display_name="Grid Curtailment",
        description=(
            "Plant export is capped below available production while "
            "underlying resource and inverter capability remain available."
        ),
        eligible_scopes=(EventScope.PLANT,),
        annual_rate_per_eligible_asset=6.0,
        duration=DurationDistribution(30, 180, 720),
        severity_distribution=_severity_distribution(
            (EventSeverity.MODERATE, 0.55),
            (EventSeverity.HIGH, 0.45),
        ),
        minimum_power_modifier_ratio=0.20,
        maximum_power_modifier_ratio=0.85,
        measurement_channels=(),
        alarm_codes=("GRID-CURTAIL-001",),
        incident_probability=0.75,
        work_order_probability=0.0,
        requires_daylight=True,
        recovery_behavior=RecoveryBehavior.INSTANT,
        minimum_separation_minutes=240,
    ),
    EventDefinition(
        event_type=EventType.PLANT_TRIP,
        display_name="Plant Trip",
        description=(
            "All generation assets in one plant become unavailable because "
            "of a plant-level protection or control trip."
        ),
        eligible_scopes=(EventScope.PLANT,),
        annual_rate_per_eligible_asset=0.8,
        duration=DurationDistribution(15, 120, 1_440),
        severity_distribution=_severity_distribution(
            (EventSeverity.HIGH, 0.30),
            (EventSeverity.CRITICAL, 0.70),
        ),
        minimum_power_modifier_ratio=0.0,
        maximum_power_modifier_ratio=0.0,
        measurement_channels=(),
        alarm_codes=("PLANT-TRIP-001",),
        incident_probability=1.0,
        work_order_probability=0.60,
        recovery_behavior=RecoveryBehavior.LINEAR_RAMP,
        minimum_separation_minutes=1_440,
    ),
    EventDefinition(
        event_type=EventType.FEEDER_TRIP,
        display_name="Feeder Trip",
        description=(
            "A feeder and every downstream transformer and inverter become "
            "unavailable."
        ),
        eligible_scopes=(EventScope.FEEDER,),
        annual_rate_per_eligible_asset=0.9,
        duration=DurationDistribution(15, 90, 720),
        severity_distribution=_severity_distribution(
            (EventSeverity.MODERATE, 0.20),
            (EventSeverity.HIGH, 0.70),
            (EventSeverity.CRITICAL, 0.10),
        ),
        minimum_power_modifier_ratio=0.0,
        maximum_power_modifier_ratio=0.0,
        measurement_channels=(),
        alarm_codes=("FDR-TRIP-001",),
        incident_probability=0.95,
        work_order_probability=0.55,
        recovery_behavior=RecoveryBehavior.MANUAL_RESET,
        minimum_separation_minutes=720,
    ),
    EventDefinition(
        event_type=EventType.TRANSFORMER_TRIP,
        display_name="Transformer Trip",
        description=("A transformer and its downstream inverters become unavailable."),
        eligible_scopes=(EventScope.TRANSFORMER,),
        annual_rate_per_eligible_asset=0.6,
        duration=DurationDistribution(30, 180, 1_440),
        severity_distribution=_severity_distribution(
            (EventSeverity.HIGH, 0.65),
            (EventSeverity.CRITICAL, 0.35),
        ),
        minimum_power_modifier_ratio=0.0,
        maximum_power_modifier_ratio=0.0,
        measurement_channels=(),
        alarm_codes=("TX-TRIP-001",),
        incident_probability=1.0,
        work_order_probability=0.80,
        recovery_behavior=RecoveryBehavior.MANUAL_RESET,
        minimum_separation_minutes=1_440,
    ),
    EventDefinition(
        event_type=EventType.INVERTER_TRIP,
        display_name="Inverter Trip",
        description=("One inverter stops producing until automatic or manual reset."),
        eligible_scopes=(EventScope.INVERTER,),
        annual_rate_per_eligible_asset=1.2,
        duration=DurationDistribution(15, 60, 720),
        severity_distribution=_severity_distribution(
            (EventSeverity.MODERATE, 0.35),
            (EventSeverity.HIGH, 0.60),
            (EventSeverity.CRITICAL, 0.05),
        ),
        minimum_power_modifier_ratio=0.0,
        maximum_power_modifier_ratio=0.0,
        measurement_channels=(),
        alarm_codes=("INV-TRIP-001",),
        incident_probability=0.80,
        work_order_probability=0.50,
        recovery_behavior=RecoveryBehavior.MANUAL_RESET,
        minimum_separation_minutes=360,
    ),
    EventDefinition(
        event_type=EventType.INVERTER_DERATING,
        display_name="Inverter Derating",
        description=("One inverter operates with a persistent partial power limit."),
        eligible_scopes=(EventScope.INVERTER,),
        annual_rate_per_eligible_asset=1.8,
        duration=DurationDistribution(30, 240, 1_440),
        severity_distribution=_severity_distribution(
            (EventSeverity.LOW, 0.20),
            (EventSeverity.MODERATE, 0.60),
            (EventSeverity.HIGH, 0.20),
        ),
        minimum_power_modifier_ratio=0.20,
        maximum_power_modifier_ratio=0.80,
        measurement_channels=(),
        alarm_codes=("INV-DERATE-001",),
        incident_probability=0.45,
        work_order_probability=0.30,
        requires_daylight=True,
        recovery_behavior=RecoveryBehavior.LINEAR_RAMP,
        minimum_separation_minutes=240,
    ),
    EventDefinition(
        event_type=EventType.THERMAL_DERATING,
        display_name="Thermal Derating",
        description=(
            "Inverter output is gradually reduced because equipment "
            "temperature exceeds the model-specific threshold."
        ),
        eligible_scopes=(EventScope.INVERTER,),
        annual_rate_per_eligible_asset=2.5,
        duration=DurationDistribution(30, 120, 480),
        severity_distribution=_severity_distribution(
            (EventSeverity.LOW, 0.30),
            (EventSeverity.MODERATE, 0.55),
            (EventSeverity.HIGH, 0.15),
        ),
        minimum_power_modifier_ratio=0.55,
        maximum_power_modifier_ratio=0.95,
        measurement_channels=("inverter_temperature_c",),
        alarm_codes=("INV-TEMP-001",),
        incident_probability=0.35,
        work_order_probability=0.20,
        requires_daylight=True,
        recovery_behavior=RecoveryBehavior.EXPONENTIAL,
        minimum_separation_minutes=180,
        seasonal_months=(4, 5, 6, 7, 8, 9),
        allowed_overlap_types=(EventType.HIGH_TEMPERATURE_STRESS,),
    ),
    EventDefinition(
        event_type=EventType.MPPT_FAULT,
        display_name="MPPT Fault",
        description=("Reduced DC capture and unstable current affect one inverter."),
        eligible_scopes=(EventScope.INVERTER,),
        annual_rate_per_eligible_asset=0.8,
        duration=DurationDistribution(30, 360, 2_880),
        severity_distribution=_severity_distribution(
            (EventSeverity.MODERATE, 0.65),
            (EventSeverity.HIGH, 0.35),
        ),
        minimum_power_modifier_ratio=0.45,
        maximum_power_modifier_ratio=0.85,
        measurement_channels=("dc_current_a", "dc_power_kw"),
        alarm_codes=("INV-MPPT-001",),
        incident_probability=0.70,
        work_order_probability=0.65,
        requires_daylight=True,
        recovery_behavior=RecoveryBehavior.MANUAL_RESET,
        minimum_separation_minutes=720,
    ),
    EventDefinition(
        event_type=EventType.DC_STRING_LOSS,
        display_name="DC String Loss",
        description=(
            "A stepwise reduction in available DC input affects one inverter."
        ),
        eligible_scopes=(EventScope.INVERTER,),
        annual_rate_per_eligible_asset=1.0,
        duration=DurationDistribution(60, 1_440, 10_080),
        severity_distribution=_severity_distribution(
            (EventSeverity.LOW, 0.55),
            (EventSeverity.MODERATE, 0.40),
            (EventSeverity.HIGH, 0.05),
        ),
        minimum_power_modifier_ratio=0.80,
        maximum_power_modifier_ratio=0.98,
        measurement_channels=("dc_current_a",),
        alarm_codes=("INV-DC-LOSS-001",),
        incident_probability=0.25,
        work_order_probability=0.45,
        requires_daylight=True,
        recovery_behavior=RecoveryBehavior.MANUAL_RESET,
        minimum_separation_minutes=1_440,
    ),
    EventDefinition(
        event_type=EventType.SOILING_ACCUMULATION,
        display_name="Soiling Accumulation",
        description=(
            "Gradual plant-level irradiance-to-power loss accumulates between "
            "rainfall or cleaning events."
        ),
        eligible_scopes=(EventScope.PLANT,),
        annual_rate_per_eligible_asset=3.0,
        duration=DurationDistribution(1_440, 10_080, 43_200),
        severity_distribution=_severity_distribution(
            (EventSeverity.LOW, 0.70),
            (EventSeverity.MODERATE, 0.30),
        ),
        minimum_power_modifier_ratio=0.82,
        maximum_power_modifier_ratio=0.99,
        measurement_channels=(),
        alarm_codes=(),
        incident_probability=0.05,
        work_order_probability=0.40,
        recovery_behavior=RecoveryBehavior.NONE,
        minimum_separation_minutes=2_880,
    ),
    EventDefinition(
        event_type=EventType.CLEANING_RECOVERY,
        display_name="Cleaning Recovery",
        description=(
            "Planned cleaning restores a portion of accumulated soiling loss."
        ),
        eligible_scopes=(EventScope.PLANT,),
        annual_rate_per_eligible_asset=4.0,
        duration=DurationDistribution(60, 240, 720),
        severity_distribution=_severity_distribution(
            (EventSeverity.LOW, 1.0),
        ),
        minimum_power_modifier_ratio=0.95,
        maximum_power_modifier_ratio=1.0,
        measurement_channels=(),
        alarm_codes=(),
        incident_probability=0.0,
        work_order_probability=1.0,
        planned=True,
        recovery_behavior=RecoveryBehavior.INSTANT,
        minimum_separation_minutes=2_880,
        allowed_overlap_types=(EventType.SOILING_ACCUMULATION,),
    ),
    EventDefinition(
        event_type=EventType.SENSOR_DRIFT,
        display_name="Sensor Drift",
        description=("One measurement channel develops a gradually increasing bias."),
        eligible_scopes=(EventScope.SENSOR,),
        annual_rate_per_eligible_asset=0.35,
        duration=DurationDistribution(720, 4_320, 20_160),
        severity_distribution=_severity_distribution(
            (EventSeverity.LOW, 0.65),
            (EventSeverity.MODERATE, 0.35),
        ),
        minimum_power_modifier_ratio=None,
        maximum_power_modifier_ratio=None,
        measurement_channels=(
            "ghi_w_m2",
            "ambient_temperature_c",
            "dc_current_a",
            "ac_power_kw",
        ),
        alarm_codes=("DATA-DRIFT-001",),
        incident_probability=0.15,
        work_order_probability=0.30,
        recovery_behavior=RecoveryBehavior.MANUAL_RESET,
        minimum_separation_minutes=2_880,
    ),
    EventDefinition(
        event_type=EventType.SENSOR_STUCK,
        display_name="Sensor Stuck",
        description=("One measurement channel repeats a constant value."),
        eligible_scopes=(EventScope.SENSOR,),
        annual_rate_per_eligible_asset=0.25,
        duration=DurationDistribution(60, 720, 4_320),
        severity_distribution=_severity_distribution(
            (EventSeverity.LOW, 0.40),
            (EventSeverity.MODERATE, 0.50),
            (EventSeverity.HIGH, 0.10),
        ),
        minimum_power_modifier_ratio=None,
        maximum_power_modifier_ratio=None,
        measurement_channels=(
            "ghi_w_m2",
            "ambient_temperature_c",
            "dc_voltage_v",
            "ac_power_kw",
        ),
        alarm_codes=("DATA-STUCK-001",),
        incident_probability=0.30,
        work_order_probability=0.35,
        recovery_behavior=RecoveryBehavior.MANUAL_RESET,
        minimum_separation_minutes=1_440,
    ),
    EventDefinition(
        event_type=EventType.TELEMETRY_GAP,
        display_name="Telemetry Gap",
        description=(
            "Rows or channel values are intentionally missing for one asset "
            "or sensor."
        ),
        eligible_scopes=(
            EventScope.SENSOR,
            EventScope.INVERTER,
            EventScope.PLANT,
        ),
        annual_rate_per_eligible_asset=0.45,
        duration=DurationDistribution(15, 120, 1_440),
        severity_distribution=_severity_distribution(
            (EventSeverity.LOW, 0.35),
            (EventSeverity.MODERATE, 0.50),
            (EventSeverity.HIGH, 0.15),
        ),
        minimum_power_modifier_ratio=None,
        maximum_power_modifier_ratio=None,
        measurement_channels=(
            "weather",
            "inverter_scada",
            "plant_scada",
        ),
        alarm_codes=("COMMS-LOSS-001",),
        incident_probability=0.40,
        work_order_probability=0.20,
        recovery_behavior=RecoveryBehavior.INSTANT,
        minimum_separation_minutes=720,
    ),
    EventDefinition(
        event_type=EventType.METER_RESET,
        display_name="Revenue Meter Reset",
        description=(
            "The cumulative settlement register experiences a labeled " "discontinuity."
        ),
        eligible_scopes=(EventScope.SENSOR,),
        annual_rate_per_eligible_asset=0.05,
        duration=DurationDistribution(15, 15, 60),
        severity_distribution=_severity_distribution(
            (EventSeverity.MODERATE, 0.60),
            (EventSeverity.HIGH, 0.40),
        ),
        minimum_power_modifier_ratio=None,
        maximum_power_modifier_ratio=None,
        measurement_channels=("cumulative_export_energy_mwh",),
        alarm_codes=("MTR-RESET-001",),
        incident_probability=0.90,
        work_order_probability=0.50,
        recovery_behavior=RecoveryBehavior.MANUAL_RESET,
        minimum_separation_minutes=10_080,
    ),
    EventDefinition(
        event_type=EventType.MAINTENANCE_OUTAGE,
        display_name="Maintenance Outage",
        description=(
            "A planned asset outage creates explicit unavailability and "
            "maintenance-state suppression behavior."
        ),
        eligible_scopes=(
            EventScope.PLANT,
            EventScope.FEEDER,
            EventScope.TRANSFORMER,
            EventScope.INVERTER,
        ),
        annual_rate_per_eligible_asset=0.6,
        duration=DurationDistribution(60, 360, 1_440),
        severity_distribution=_severity_distribution(
            (EventSeverity.LOW, 0.70),
            (EventSeverity.MODERATE, 0.30),
        ),
        minimum_power_modifier_ratio=0.0,
        maximum_power_modifier_ratio=0.0,
        measurement_channels=(),
        alarm_codes=("MAINT-OUTAGE-001",),
        incident_probability=0.10,
        work_order_probability=1.0,
        planned=True,
        recovery_behavior=RecoveryBehavior.LINEAR_RAMP,
        minimum_separation_minutes=720,
    ),
    EventDefinition(
        event_type=EventType.HIGH_TEMPERATURE_STRESS,
        display_name="High Temperature Stress",
        description=(
            "Plant-wide high-temperature conditions increase equipment risk "
            "and may trigger thermal derating."
        ),
        eligible_scopes=(EventScope.PLANT,),
        annual_rate_per_eligible_asset=4.0,
        duration=DurationDistribution(120, 480, 1_440),
        severity_distribution=_severity_distribution(
            (EventSeverity.LOW, 0.30),
            (EventSeverity.MODERATE, 0.50),
            (EventSeverity.HIGH, 0.20),
        ),
        minimum_power_modifier_ratio=0.80,
        maximum_power_modifier_ratio=1.0,
        measurement_channels=("cell_temperature_c",),
        alarm_codes=("ENV-TEMP-001",),
        incident_probability=0.20,
        work_order_probability=0.05,
        requires_daylight=True,
        recovery_behavior=RecoveryBehavior.EXPONENTIAL,
        minimum_separation_minutes=720,
        seasonal_months=(4, 5, 6, 7, 8, 9),
        allowed_overlap_types=(EventType.THERMAL_DERATING,),
    ),
    EventDefinition(
        event_type=EventType.STORM_EVENT,
        display_name="Storm Event",
        description=(
            "Regional storm conditions reduce irradiance, increase wind and "
            "rain, and may coincide with equipment or grid trips."
        ),
        eligible_scopes=(EventScope.PLANT, EventScope.PORTFOLIO),
        annual_rate_per_eligible_asset=2.0,
        duration=DurationDistribution(60, 360, 1_440),
        severity_distribution=_severity_distribution(
            (EventSeverity.MODERATE, 0.55),
            (EventSeverity.HIGH, 0.35),
            (EventSeverity.CRITICAL, 0.10),
        ),
        minimum_power_modifier_ratio=0.10,
        maximum_power_modifier_ratio=0.75,
        measurement_channels=(
            "ghi_w_m2",
            "wind_speed_m_s",
            "precipitation_mm",
        ),
        alarm_codes=("ENV-STORM-001",),
        incident_probability=0.35,
        work_order_probability=0.10,
        recovery_behavior=RecoveryBehavior.LINEAR_RAMP,
        minimum_separation_minutes=1_440,
        allowed_overlap_types=(
            EventType.GRID_OUTAGE,
            EventType.FEEDER_TRIP,
            EventType.TRANSFORMER_TRIP,
        ),
    ),
)


class EventCatalogue:
    """Immutable lookup and filtering interface for event definitions."""

    def __init__(
        self,
        definitions: Iterable[EventDefinition] = _EVENT_DEFINITIONS,
    ) -> None:
        """Build and validate a catalogue."""
        ordered = tuple(definitions)

        if not ordered:
            raise ValueError("EventCatalogue requires at least one definition.")

        event_types = tuple(definition.event_type for definition in ordered)
        if len(event_types) != len(set(event_types)):
            raise ValueError("EventCatalogue contains duplicate event types.")

        missing_types = set(EventType).difference(event_types)
        if missing_types:
            missing = ", ".join(
                sorted(event_type.value for event_type in missing_types)
            )
            raise ValueError(f"EventCatalogue is missing definitions for: {missing}.")

        self._definitions = tuple(
            sorted(
                ordered,
                key=lambda definition: definition.event_type.value,
            )
        )
        self._by_type = MappingProxyType(
            {definition.event_type: definition for definition in self._definitions}
        )

    def __len__(self) -> int:
        """Return the number of event definitions."""
        return len(self._definitions)

    def __iter__(self):
        """Iterate through definitions in deterministic order."""
        return iter(self._definitions)

    def get(self, event_type: EventType | str) -> EventDefinition:
        """Return one event definition by enum or serialized value."""
        resolved_type = (
            event_type if isinstance(event_type, EventType) else EventType(event_type)
        )
        return self._by_type[resolved_type]

    def by_scope(
        self,
        scope: EventScope,
    ) -> tuple[EventDefinition, ...]:
        """Return definitions eligible for a scope."""
        if not isinstance(scope, EventScope):
            raise TypeError("scope must be an EventScope value.")

        return tuple(
            definition
            for definition in self._definitions
            if scope in definition.eligible_scopes
        )

    def planned(self) -> tuple[EventDefinition, ...]:
        """Return all planned event definitions."""
        return tuple(
            definition for definition in self._definitions if definition.planned
        )

    def unplanned(self) -> tuple[EventDefinition, ...]:
        """Return all unplanned event definitions."""
        return tuple(
            definition for definition in self._definitions if not definition.planned
        )

    def with_alarm_code(
        self,
        alarm_code: str,
    ) -> tuple[EventDefinition, ...]:
        """Return definitions that may create an alarm code."""
        normalized_code = alarm_code.strip().upper()
        if not normalized_code:
            raise ValueError("alarm_code cannot be empty.")

        return tuple(
            definition
            for definition in self._definitions
            if normalized_code in definition.alarm_codes
        )

    def physical_events(self) -> tuple[EventDefinition, ...]:
        """Return definitions that modify physical power."""
        return tuple(
            definition
            for definition in self._definitions
            if definition.creates_physical_power_effect
        )

    def measurement_events(self) -> tuple[EventDefinition, ...]:
        """Return definitions that modify measurement channels."""
        return tuple(
            definition
            for definition in self._definitions
            if definition.creates_measurement_effect
        )

    def to_records(self) -> tuple[dict[str, object], ...]:
        """Return all definitions as serialization-ready records."""
        return tuple(definition.to_record() for definition in self._definitions)


DEFAULT_EVENT_CATALOGUE: Final[EventCatalogue] = EventCatalogue()


def get_event_definition(
    event_type: EventType | str,
) -> EventDefinition:
    """Return an event definition from the default catalogue."""
    return DEFAULT_EVENT_CATALOGUE.get(event_type)


def list_event_definitions() -> tuple[EventDefinition, ...]:
    """Return all default event definitions in stable order."""
    return tuple(DEFAULT_EVENT_CATALOGUE)


__all__ = [
    "DEFAULT_EVENT_CATALOGUE",
    "DurationDistribution",
    "EventCatalogue",
    "EventDefinition",
    "EventScope",
    "EventSeverity",
    "EventType",
    "RecoveryBehavior",
    "SeverityWeight",
    "get_event_definition",
    "list_event_definitions",
]
