"""
Unit tests for the EOIP Phase 2 synthetic event catalogue.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from eoip.synthetic.events.catalogue import (
    DEFAULT_EVENT_CATALOGUE,
    DurationDistribution,
    EventCatalogue,
    EventDefinition,
    EventScope,
    EventSeverity,
    EventType,
    RecoveryBehavior,
    SeverityWeight,
    get_event_definition,
    list_event_definitions,
)


def _definition(**overrides: Any) -> EventDefinition:
    data: dict[str, Any] = {
        "event_type": EventType.INVERTER_TRIP,
        "display_name": "Inverter Trip",
        "description": "One inverter stops producing.",
        "eligible_scopes": (EventScope.INVERTER,),
        "annual_rate_per_eligible_asset": 1.0,
        "duration": DurationDistribution(15, 60, 120),
        "severity_distribution": (
            SeverityWeight(EventSeverity.MODERATE, 0.7),
            SeverityWeight(EventSeverity.HIGH, 0.3),
        ),
        "minimum_power_modifier_ratio": 0.0,
        "maximum_power_modifier_ratio": 0.0,
        "measurement_channels": (),
        "alarm_codes": ("INV-TRIP-001",),
        "incident_probability": 0.8,
        "work_order_probability": 0.5,
        "requires_daylight": False,
        "excludes_daylight": False,
        "planned": False,
        "recovery_behavior": RecoveryBehavior.MANUAL_RESET,
        "minimum_separation_minutes": 60,
        "seasonal_months": (),
        "allowed_overlap_types": (),
    }
    data.update(overrides)
    return EventDefinition(**data)


def test_default_catalogue_contains_every_event_type() -> None:
    definitions = tuple(DEFAULT_EVENT_CATALOGUE)

    assert len(definitions) == len(EventType)
    assert {item.event_type for item in definitions} == set(EventType)


def test_default_catalogue_is_sorted() -> None:
    values = [item.event_type.value for item in DEFAULT_EVENT_CATALOGUE]

    assert values == sorted(values)


@pytest.mark.parametrize("event_type", list(EventType))
def test_get_accepts_enum_and_string(event_type: EventType) -> None:
    assert DEFAULT_EVENT_CATALOGUE.get(event_type).event_type is event_type
    assert DEFAULT_EVENT_CATALOGUE.get(event_type.value).event_type is event_type


def test_public_helpers_use_default_catalogue() -> None:
    assert get_event_definition(EventType.GRID_OUTAGE) is (
        DEFAULT_EVENT_CATALOGUE.get(EventType.GRID_OUTAGE)
    )
    assert list_event_definitions() == tuple(DEFAULT_EVENT_CATALOGUE)


def test_definition_normalizes_text() -> None:
    definition = _definition(
        display_name=" Inverter Trip ",
        description=" One inverter stops producing. ",
        measurement_channels=(" AC_POWER_KW ",),
        alarm_codes=(" inv-trip-001 ",),
    )

    assert definition.display_name == "Inverter Trip"
    assert definition.description == "One inverter stops producing."
    assert definition.measurement_channels == ("ac_power_kw",)
    assert definition.alarm_codes == ("INV-TRIP-001",)


def test_definition_is_immutable() -> None:
    definition = _definition()

    with pytest.raises(FrozenInstanceError):
        definition.display_name = "Changed"  # type: ignore[misc]


def test_duration_distribution_is_immutable() -> None:
    duration = DurationDistribution(15, 60, 120)

    with pytest.raises(FrozenInstanceError):
        duration.minimum_minutes = 30  # type: ignore[misc]


@pytest.mark.parametrize(
    ("minimum", "typical", "maximum"),
    [(1, 1, 1), (15, 60, 120), (60, 60, 240)],
)
def test_duration_distribution_accepts_ordered_values(
    minimum: int,
    typical: int,
    maximum: int,
) -> None:
    duration = DurationDistribution(minimum, typical, maximum)

    assert duration.minimum_minutes == minimum
    assert duration.typical_minutes == typical
    assert duration.maximum_minutes == maximum


@pytest.mark.parametrize(
    ("minimum", "typical", "maximum"),
    [(60, 15, 120), (15, 120, 60), (120, 60, 15)],
)
def test_duration_distribution_rejects_bad_order(
    minimum: int,
    typical: int,
    maximum: int,
) -> None:
    with pytest.raises(ValueError, match="minimum <= typical <= maximum"):
        DurationDistribution(minimum, typical, maximum)


@pytest.mark.parametrize("value", [0, -1])
def test_duration_distribution_rejects_non_positive(value: int) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        DurationDistribution(value, 60, 120)


@pytest.mark.parametrize("value", [True, 1.5, "15", None])
def test_duration_distribution_requires_integers(value: object) -> None:
    with pytest.raises(TypeError, match="must be integers"):
        DurationDistribution(value, 60, 120)  # type: ignore[arg-type]


def test_severity_weight_accepts_positive_value() -> None:
    weight = SeverityWeight(EventSeverity.HIGH, 2.0)

    assert weight.severity is EventSeverity.HIGH
    assert weight.weight == 2.0


@pytest.mark.parametrize("value", [0.0, -1.0])
def test_severity_weight_rejects_non_positive(value: float) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        SeverityWeight(EventSeverity.HIGH, value)


@pytest.mark.parametrize("value", [True, "1", None])
def test_severity_weight_requires_numeric(value: object) -> None:
    with pytest.raises(TypeError, match="weight must be numeric"):
        SeverityWeight(
            EventSeverity.HIGH,
            value,  # type: ignore[arg-type]
        )


def test_normalized_severity_weights_sum_to_one() -> None:
    definition = _definition(
        severity_distribution=(
            SeverityWeight(EventSeverity.LOW, 1.0),
            SeverityWeight(EventSeverity.MODERATE, 2.0),
            SeverityWeight(EventSeverity.HIGH, 1.0),
        )
    )

    weights = definition.normalized_severity_weights

    assert sum(weights.values()) == pytest.approx(1.0)
    assert weights[EventSeverity.MODERATE] == pytest.approx(0.5)


def test_normalized_weights_are_read_only() -> None:
    weights = _definition().normalized_severity_weights

    with pytest.raises(TypeError):
        weights[EventSeverity.LOW] = 1.0  # type: ignore[index]


def test_derived_effect_properties() -> None:
    physical = _definition()
    measurement = _definition(
        minimum_power_modifier_ratio=None,
        maximum_power_modifier_ratio=None,
        measurement_channels=("ac_power_kw",),
    )

    assert physical.creates_physical_power_effect is True
    assert physical.creates_measurement_effect is False
    assert measurement.creates_physical_power_effect is False
    assert measurement.creates_measurement_effect is True


def test_to_record_serializes_enums() -> None:
    record = _definition(allowed_overlap_types=(EventType.STORM_EVENT,)).to_record()

    assert record["event_type"] == "inverter_trip"
    assert record["eligible_scopes"] == ("inverter",)
    assert record["recovery_behavior"] == "manual_reset"
    assert record["allowed_overlap_types"] == ("storm_event",)


@pytest.mark.parametrize("scope", list(EventScope))
def test_by_scope_returns_matching_definitions(scope: EventScope) -> None:
    definitions = DEFAULT_EVENT_CATALOGUE.by_scope(scope)

    assert all(scope in item.eligible_scopes for item in definitions)


def test_by_scope_requires_enum() -> None:
    with pytest.raises(TypeError, match="EventScope"):
        DEFAULT_EVENT_CATALOGUE.by_scope("plant")  # type: ignore[arg-type]


def test_planned_and_unplanned_filters() -> None:
    planned = DEFAULT_EVENT_CATALOGUE.planned()
    unplanned = DEFAULT_EVENT_CATALOGUE.unplanned()

    assert all(item.planned for item in planned)
    assert all(item.planned is False for item in unplanned)
    assert len(planned) + len(unplanned) == len(DEFAULT_EVENT_CATALOGUE)
    assert {item.event_type for item in planned} == {
        EventType.CLEANING_RECOVERY,
        EventType.MAINTENANCE_OUTAGE,
    }


def test_alarm_code_filter() -> None:
    definitions = DEFAULT_EVENT_CATALOGUE.with_alarm_code(" inv-trip-001 ")

    assert len(definitions) == 1
    assert definitions[0].event_type is EventType.INVERTER_TRIP
    assert DEFAULT_EVENT_CATALOGUE.with_alarm_code("UNKNOWN") == ()


def test_alarm_code_filter_rejects_blank() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        DEFAULT_EVENT_CATALOGUE.with_alarm_code(" ")


def test_physical_and_measurement_filters() -> None:
    physical = DEFAULT_EVENT_CATALOGUE.physical_events()
    measurement = DEFAULT_EVENT_CATALOGUE.measurement_events()

    assert all(item.creates_physical_power_effect for item in physical)
    assert all(item.creates_measurement_effect for item in measurement)


def test_to_records_returns_serialized_catalogue() -> None:
    records = DEFAULT_EVENT_CATALOGUE.to_records()

    assert len(records) == len(DEFAULT_EVENT_CATALOGUE)
    assert {item["event_type"] for item in records} == {
        event_type.value for event_type in EventType
    }


def test_catalogue_rejects_empty_definitions() -> None:
    with pytest.raises(ValueError, match="at least one definition"):
        EventCatalogue(())


def test_catalogue_rejects_duplicate_event_types() -> None:
    definitions = list(DEFAULT_EVENT_CATALOGUE)

    with pytest.raises(ValueError, match="duplicate event types"):
        EventCatalogue(definitions + [definitions[0]])


def test_catalogue_rejects_missing_event_types() -> None:
    with pytest.raises(ValueError, match="missing definitions"):
        EventCatalogue(tuple(DEFAULT_EVENT_CATALOGUE)[:-1])


@pytest.mark.parametrize("field_name", ["display_name", "description"])
def test_definition_rejects_blank_text(field_name: str) -> None:
    with pytest.raises(ValueError, match=f"{field_name} cannot be empty"):
        _definition(**{field_name: " "})


def test_definition_rejects_empty_scopes() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        _definition(eligible_scopes=())


def test_definition_rejects_duplicate_scopes() -> None:
    with pytest.raises(ValueError, match="must not contain duplicates"):
        _definition(
            eligible_scopes=(
                EventScope.INVERTER,
                EventScope.INVERTER,
            )
        )


@pytest.mark.parametrize(
    "field_name",
    ["incident_probability", "work_order_probability"],
)
@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_definition_rejects_probability_bounds(
    field_name: str,
    value: float,
) -> None:
    with pytest.raises(ValueError, match="between zero and one"):
        _definition(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    ["incident_probability", "work_order_probability"],
)
@pytest.mark.parametrize("value", [True, "0.5", None])
def test_definition_rejects_probability_types(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(TypeError, match=f"{field_name} must be numeric"):
        _definition(**{field_name: value})


def test_definition_rejects_negative_annual_rate() -> None:
    with pytest.raises(ValueError, match="must be non-negative"):
        _definition(annual_rate_per_eligible_asset=-0.1)


def test_definition_rejects_empty_severity_distribution() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        _definition(severity_distribution=())


def test_definition_rejects_duplicate_severities() -> None:
    with pytest.raises(ValueError, match="must not repeat severities"):
        _definition(
            severity_distribution=(
                SeverityWeight(EventSeverity.HIGH, 1.0),
                SeverityWeight(EventSeverity.HIGH, 2.0),
            )
        )


def test_definition_requires_both_power_bounds() -> None:
    with pytest.raises(ValueError, match="must both be set"):
        _definition(
            minimum_power_modifier_ratio=0.5,
            maximum_power_modifier_ratio=None,
        )


@pytest.mark.parametrize(
    ("minimum", "maximum"),
    [(-0.1, 0.5), (0.0, 1.1), (0.8, 0.2)],
)
def test_definition_rejects_invalid_power_bounds(
    minimum: float,
    maximum: float,
) -> None:
    with pytest.raises(ValueError):
        _definition(
            minimum_power_modifier_ratio=minimum,
            maximum_power_modifier_ratio=maximum,
        )


def test_definition_rejects_conflicting_daylight_rules() -> None:
    with pytest.raises(ValueError, match="both require and exclude"):
        _definition(requires_daylight=True, excludes_daylight=True)


@pytest.mark.parametrize("value", [1, 0, "false", None])
def test_definition_requires_boolean_planned(value: object) -> None:
    with pytest.raises(TypeError, match="planned must be a boolean"):
        _definition(planned=value)  # type: ignore[arg-type]


def test_definition_requires_recovery_enum() -> None:
    with pytest.raises(TypeError, match="RecoveryBehavior"):
        _definition(recovery_behavior="instant")  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [True, 1.5, "60", None])
def test_definition_requires_integer_separation(value: object) -> None:
    with pytest.raises(TypeError, match="must be an integer"):
        _definition(minimum_separation_minutes=value)  # type: ignore[arg-type]


def test_definition_rejects_duplicate_measurement_channels() -> None:
    with pytest.raises(ValueError, match="must not contain duplicates"):
        _definition(measurement_channels=("ac_power_kw", " AC_POWER_KW "))


def test_definition_rejects_duplicate_alarm_codes() -> None:
    with pytest.raises(ValueError, match="must not contain duplicates"):
        _definition(alarm_codes=("INV-TRIP-001", " inv-trip-001 "))


def test_definition_rejects_invalid_seasonal_months() -> None:
    with pytest.raises(ValueError, match="between 1 and 12"):
        _definition(seasonal_months=(0,))

    with pytest.raises(ValueError, match="must not contain duplicates"):
        _definition(seasonal_months=(6, 6))


def test_grid_outage_definition_contract() -> None:
    definition = get_event_definition(EventType.GRID_OUTAGE)

    assert EventScope.PLANT in definition.eligible_scopes
    assert EventScope.PORTFOLIO in definition.eligible_scopes
    assert definition.minimum_power_modifier_ratio == 0.0
    assert definition.maximum_power_modifier_ratio == 0.0
    assert definition.incident_probability == 1.0
    assert "GRID-LOSS-001" in definition.alarm_codes


def test_telemetry_gap_is_measurement_only() -> None:
    definition = get_event_definition(EventType.TELEMETRY_GAP)

    assert definition.creates_measurement_effect is True
    assert definition.creates_physical_power_effect is False


def test_maintenance_outage_is_planned() -> None:
    definition = get_event_definition(EventType.MAINTENANCE_OUTAGE)

    assert definition.planned is True
    assert definition.work_order_probability == 1.0


def test_cleaning_recovery_overlaps_soiling() -> None:
    definition = get_event_definition(EventType.CLEANING_RECOVERY)

    assert EventType.SOILING_ACCUMULATION in (definition.allowed_overlap_types)
