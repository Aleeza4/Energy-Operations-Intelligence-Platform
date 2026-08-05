"""Synthetic event package exports."""

from .catalogue import (
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
