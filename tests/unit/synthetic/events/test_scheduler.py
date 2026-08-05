"""
Unit tests for EOIP synthetic event scheduler.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from eoip.synthetic.events.catalogue import EventScope, EventSeverity, EventType
from eoip.synthetic.events.scheduler import (
    EligibleAsset,
    EventScheduler,
    EventSchedulerConfig,
    SyntheticEvent,
    events_to_frame,
    schedule_events,
)


def _portfolio():
    return (
        EligibleAsset(EventScope.PLANT, "PLANT-001", "plant", "PLANT-001"),
        EligibleAsset(EventScope.INVERTER, "PLANT-001", "inverter", "EQP-00001"),
    )


def _grid():
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return tuple(start + timedelta(minutes=15 * i) for i in range(96))


def test_config_defaults():
    cfg = EventSchedulerConfig()
    assert cfg.interval_minutes == 15


def test_schedule_returns_tuple():
    events = EventScheduler().schedule(
        _portfolio(), _grid(), generation_run_id="RUN-001"
    )
    assert isinstance(events, tuple)


def test_functional_api():
    events = schedule_events(_portfolio(), _grid(), generation_run_id="RUN-001")
    assert isinstance(events, tuple)


def test_dataframe_conversion():
    frame = events_to_frame(
        schedule_events(_portfolio(), _grid(), generation_run_id="RUN-001")
    )
    assert isinstance(frame, pd.DataFrame)


def test_empty_dataframe():
    assert events_to_frame(()).empty


def test_duration_property():
    event = SyntheticEvent(
        "GTE-2026-00000001",
        EventType.GRID_OUTAGE,
        EventScope.PLANT,
        "PLANT-001",
        "plant",
        "PLANT-001",
        None,
        datetime(2026, 1, 1, tzinfo=UTC),
        datetime(2026, 1, 1, 1, tzinfo=UTC),
        EventSeverity.HIGH,
        0.5,
        0.0,
        None,
        None,
        False,
        "GRID",
        "{}",
        None,
        False,
        False,
        "RUN",
        "1.0.0",
    )
    assert event.duration_minutes == 60.0
