"""
Unit tests for the EOIP synthetic operations alarm catalogue.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from eoip.synthetic.events.catalogue import EventScope, EventType
from eoip.synthetic.models.alarm import AlarmCategory, AlarmSeverity
from eoip.synthetic.operations.alarm_catalogue import (
    DEFAULT_ALARM_CATALOGUE,
    AlarmCatalogue,
    AlarmClearBehavior,
    AlarmDefinition,
    find_alarm_definition,
    get_alarm_definition,
    list_alarm_definitions,
)


def _definition(**overrides: Any) -> AlarmDefinition:
    """Return a compact valid alarm definition for validation tests."""
    data: dict[str, Any] = {
        "code": "INV-TEST-001",
        "name": "Test Inverter Alarm",
        "category": AlarmCategory.EQUIPMENT,
        "default_severity": AlarmSeverity.MAJOR,
        "scope": EventScope.INVERTER,
        "trigger": "A test inverter alarm condition becomes active.",
        "clear_behavior": AlarmClearBehavior.AUTO_CLEAR,
        "trigger_delay_minutes": 15,
        "clear_delay_minutes": 15,
        "suppression_rules": ("planned_maintenance",),
        "source_event_types": (EventType.INVERTER_TRIP,),
        "incident_eligible": True,
        "nuisance_eligible": False,
        "message_template": "Test alarm for {asset_id}.",
    }
    data.update(overrides)
    return AlarmDefinition(**data)


def test_default_catalogue_contains_expected_number_of_definitions() -> None:
    assert len(DEFAULT_ALARM_CATALOGUE) == 17


def test_default_catalogue_codes_are_unique_and_sorted() -> None:
    codes = DEFAULT_ALARM_CATALOGUE.codes

    assert codes == tuple(sorted(codes))
    assert len(codes) == len(set(codes))


def test_default_catalogue_iteration_matches_codes() -> None:
    definitions = tuple(DEFAULT_ALARM_CATALOGUE)

    assert tuple(item.code for item in definitions) == DEFAULT_ALARM_CATALOGUE.codes


@pytest.mark.parametrize(
    "code",
    [
        "GRID-LOSS-001",
        "GRID-CURTAIL-001",
        "PLANT-TRIP-001",
        "FDR-TRIP-001",
        "TX-TRIP-001",
        "INV-TRIP-001",
        "INV-DERATE-001",
        "INV-TEMP-001",
        "INV-MPPT-001",
        "INV-DC-LOSS-001",
        "DATA-DRIFT-001",
        "DATA-STUCK-001",
        "COMMS-LOSS-001",
        "MTR-RESET-001",
        "MAINT-OUTAGE-001",
        "ENV-TEMP-001",
        "ENV-STORM-001",
    ],
)
def test_expected_alarm_codes_exist(code: str) -> None:
    assert DEFAULT_ALARM_CATALOGUE.get(code).code == code


def test_get_normalizes_code() -> None:
    definition = DEFAULT_ALARM_CATALOGUE.get(" inv-trip-001 ")

    assert definition.code == "INV-TRIP-001"


def test_get_rejects_blank_code() -> None:
    with pytest.raises(ValueError, match="code cannot be empty"):
        DEFAULT_ALARM_CATALOGUE.get(" ")


def test_get_rejects_unknown_code() -> None:
    with pytest.raises(KeyError, match="Unknown alarm code"):
        DEFAULT_ALARM_CATALOGUE.get("UNKNOWN-001")


def test_find_returns_definition_or_none() -> None:
    assert DEFAULT_ALARM_CATALOGUE.find("grid-loss-001").code == "GRID-LOSS-001"
    assert DEFAULT_ALARM_CATALOGUE.find("UNKNOWN-001") is None


def test_find_rejects_blank_code() -> None:
    with pytest.raises(ValueError, match="code cannot be empty"):
        DEFAULT_ALARM_CATALOGUE.find("")


def test_public_lookup_helpers_use_default_catalogue() -> None:
    assert get_alarm_definition("GRID-LOSS-001") is DEFAULT_ALARM_CATALOGUE.get(
        "GRID-LOSS-001"
    )
    assert find_alarm_definition("UNKNOWN-001") is None
    assert list_alarm_definitions() == tuple(DEFAULT_ALARM_CATALOGUE)


def test_definition_normalizes_text_fields() -> None:
    definition = _definition(
        code=" inv-test-001 ",
        name=" Test Inverter Alarm ",
        trigger=" Test trigger. ",
        suppression_rules=(" Planned_Maintenance ",),
        message_template=" Test alarm for {asset_id}. ",
    )

    assert definition.code == "INV-TEST-001"
    assert definition.name == "Test Inverter Alarm"
    assert definition.trigger == "Test trigger."
    assert definition.suppression_rules == ("planned_maintenance",)
    assert definition.message_template == "Test alarm for {asset_id}."


def test_definition_is_immutable() -> None:
    definition = _definition()

    with pytest.raises(FrozenInstanceError):
        definition.name = "Changed"  # type: ignore[misc]


def test_to_record_serializes_enums() -> None:
    record = _definition().to_record()

    assert record["category"] == AlarmCategory.EQUIPMENT.value
    assert record["default_severity"] == AlarmSeverity.MAJOR.value
    assert record["scope"] == EventScope.INVERTER.value
    assert record["clear_behavior"] == AlarmClearBehavior.AUTO_CLEAR.value
    assert record["source_event_types"] == (EventType.INVERTER_TRIP.value,)


@pytest.mark.parametrize("category", list(AlarmCategory))
def test_by_category_returns_matching_definitions(
    category: AlarmCategory,
) -> None:
    definitions = DEFAULT_ALARM_CATALOGUE.by_category(category)

    assert all(item.category is category for item in definitions)


def test_by_category_rejects_invalid_type() -> None:
    with pytest.raises(TypeError, match="AlarmCategory"):
        DEFAULT_ALARM_CATALOGUE.by_category("equipment")  # type: ignore[arg-type]


@pytest.mark.parametrize("severity", list(AlarmSeverity))
def test_by_severity_returns_matching_definitions(
    severity: AlarmSeverity,
) -> None:
    definitions = DEFAULT_ALARM_CATALOGUE.by_severity(severity)

    assert all(item.default_severity is severity for item in definitions)


def test_by_severity_rejects_invalid_type() -> None:
    with pytest.raises(TypeError, match="AlarmSeverity"):
        DEFAULT_ALARM_CATALOGUE.by_severity("major")  # type: ignore[arg-type]


@pytest.mark.parametrize("scope", list(EventScope))
def test_by_scope_returns_matching_definitions(scope: EventScope) -> None:
    definitions = DEFAULT_ALARM_CATALOGUE.by_scope(scope)

    assert all(item.scope is scope for item in definitions)


def test_by_scope_rejects_invalid_type() -> None:
    with pytest.raises(TypeError, match="EventScope"):
        DEFAULT_ALARM_CATALOGUE.by_scope("plant")  # type: ignore[arg-type]


@pytest.mark.parametrize("event_type", list(EventType))
def test_for_event_type_returns_only_mapped_definitions(
    event_type: EventType,
) -> None:
    definitions = DEFAULT_ALARM_CATALOGUE.for_event_type(event_type)

    assert all(
        event_type in definition.source_event_types for definition in definitions
    )


def test_for_event_type_rejects_invalid_type() -> None:
    with pytest.raises(TypeError, match="EventType"):
        DEFAULT_ALARM_CATALOGUE.for_event_type("grid_outage")  # type: ignore[arg-type]


def test_incident_eligible_filter() -> None:
    definitions = DEFAULT_ALARM_CATALOGUE.incident_eligible()

    assert definitions
    assert all(item.incident_eligible for item in definitions)
    assert "MAINT-OUTAGE-001" not in {item.code for item in definitions}


def test_nuisance_eligible_filter() -> None:
    definitions = DEFAULT_ALARM_CATALOGUE.nuisance_eligible()

    assert definitions
    assert all(item.nuisance_eligible for item in definitions)
    assert {
        "INV-DERATE-001",
        "INV-DC-LOSS-001",
        "DATA-DRIFT-001",
        "DATA-STUCK-001",
        "ENV-TEMP-001",
    }.issubset({item.code for item in definitions})


def test_mapping_is_read_only() -> None:
    with pytest.raises(TypeError):
        DEFAULT_ALARM_CATALOGUE.mapping["NEW-001"] = _definition()  # type: ignore[index]


def test_to_records_returns_serialized_definitions() -> None:
    records = DEFAULT_ALARM_CATALOGUE.to_records()

    assert len(records) == len(DEFAULT_ALARM_CATALOGUE)
    assert all(isinstance(record, dict) for record in records)
    assert {record["code"] for record in records} == set(DEFAULT_ALARM_CATALOGUE.codes)


def test_catalogue_rejects_empty_definitions() -> None:
    with pytest.raises(ValueError, match="at least one definition"):
        AlarmCatalogue(())


def test_catalogue_rejects_duplicate_codes() -> None:
    definition = _definition()

    with pytest.raises(ValueError, match="duplicate alarm codes"):
        AlarmCatalogue((definition, definition))


@pytest.mark.parametrize("value", ["", "   "])
def test_definition_rejects_blank_code(value: str) -> None:
    with pytest.raises(ValueError, match="code cannot be empty"):
        _definition(code=value)


def test_definition_rejects_code_longer_than_limit() -> None:
    with pytest.raises(ValueError, match="cannot exceed 50"):
        _definition(code="A" * 51)


@pytest.mark.parametrize("value", ["INV CODE", "INV@001", "INV/001"])
def test_definition_rejects_invalid_code_characters(value: str) -> None:
    with pytest.raises(ValueError, match="uppercase letters"):
        _definition(code=value)


@pytest.mark.parametrize("field_name", ["name", "trigger"])
def test_definition_rejects_blank_required_text(field_name: str) -> None:
    with pytest.raises(ValueError, match=f"{field_name} cannot be empty"):
        _definition(**{field_name: " "})


def test_definition_rejects_name_longer_than_limit() -> None:
    with pytest.raises(ValueError, match="cannot exceed 150"):
        _definition(name="A" * 151)


def test_definition_rejects_invalid_category() -> None:
    with pytest.raises(TypeError, match="AlarmCategory"):
        _definition(category="equipment")  # type: ignore[arg-type]


def test_definition_rejects_invalid_severity() -> None:
    with pytest.raises(TypeError, match="AlarmSeverity"):
        _definition(default_severity="major")  # type: ignore[arg-type]


def test_definition_rejects_invalid_scope() -> None:
    with pytest.raises(TypeError, match="EventScope"):
        _definition(scope="inverter")  # type: ignore[arg-type]


def test_definition_rejects_invalid_clear_behavior() -> None:
    with pytest.raises(TypeError, match="AlarmClearBehavior"):
        _definition(clear_behavior="auto_clear")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field_name",
    ["trigger_delay_minutes", "clear_delay_minutes"],
)
@pytest.mark.parametrize("value", [True, 1.5, "15", None])
def test_definition_rejects_non_integer_delays(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(TypeError, match=f"{field_name} must be an integer"):
        _definition(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    ["trigger_delay_minutes", "clear_delay_minutes"],
)
def test_definition_rejects_negative_delays(field_name: str) -> None:
    with pytest.raises(ValueError, match=f"{field_name} must be non-negative"):
        _definition(**{field_name: -1})


def test_definition_rejects_duplicate_suppression_rules() -> None:
    with pytest.raises(ValueError, match="must not contain duplicates"):
        _definition(
            suppression_rules=(
                "planned_maintenance",
                " Planned_Maintenance ",
            )
        )


def test_definition_rejects_blank_suppression_rule() -> None:
    with pytest.raises(ValueError, match="blank values"):
        _definition(suppression_rules=(" ",))


def test_definition_rejects_duplicate_event_types() -> None:
    with pytest.raises(ValueError, match="must not contain duplicates"):
        _definition(
            source_event_types=(
                EventType.INVERTER_TRIP,
                EventType.INVERTER_TRIP,
            )
        )


def test_definition_rejects_invalid_event_type() -> None:
    with pytest.raises(TypeError, match="EventType values"):
        _definition(source_event_types=("inverter_trip",))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field_name",
    ["incident_eligible", "nuisance_eligible"],
)
@pytest.mark.parametrize("value", [1, 0, "true", None])
def test_definition_rejects_non_boolean_flags(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(TypeError, match=f"{field_name} must be a boolean"):
        _definition(**{field_name: value})


def test_definition_rejects_blank_message_template() -> None:
    with pytest.raises(ValueError, match="cannot be blank"):
        _definition(message_template=" ")


def test_grid_outage_alarm_contract() -> None:
    definition = get_alarm_definition("GRID-LOSS-001")

    assert definition.category is AlarmCategory.GRID
    assert definition.default_severity is AlarmSeverity.CRITICAL
    assert definition.scope is EventScope.PLANT
    assert definition.clear_behavior is AlarmClearBehavior.CLEAR_WITH_EVENT
    assert definition.source_event_types == (EventType.GRID_OUTAGE,)


def test_planned_maintenance_alarm_is_not_incident_eligible() -> None:
    definition = get_alarm_definition("MAINT-OUTAGE-001")

    assert definition.default_severity is AlarmSeverity.INFORMATIONAL
    assert definition.incident_eligible is False


def test_meter_reset_alarm_is_latched() -> None:
    definition = get_alarm_definition("MTR-RESET-001")

    assert definition.clear_behavior is AlarmClearBehavior.LATCHED
    assert definition.source_event_types == (EventType.METER_RESET,)
