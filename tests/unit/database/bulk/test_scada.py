"""Unit tests for the EOIP SCADA bulk loader."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from eoip.database.bulk.scada import SCADABulkLoader


def _session() -> Session:
    """Return a mocked SQLAlchemy session."""
    return MagicMock(spec=Session)


def _record() -> dict[str, object]:
    """Return a valid SCADA observation record."""
    return {
        "plant_id": "PLANT001",
        "equipment_id": "INV000001",
        "timestamp": datetime(2026, 8, 14, 10, 0, tzinfo=UTC),
        "active_power_kw": 500.0,
        "interval_energy_kwh": 125.0,
        "dc_voltage_v": 800.0,
        "dc_current_a": 625.0,
        "ac_voltage_v": 400.0,
        "ac_current_a": 720.0,
        "frequency_hz": 50.0,
        "power_factor": 0.98,
        "equipment_available": True,
        "grid_available": True,
        "operating_state": "normal",
        "quality": "valid",
    }


class TestSCADABulkLoaderConstruction:
    """Tests for SCADA bulk-loader construction."""

    def test_constructs_loader(self) -> None:
        session = _session()

        loader = SCADABulkLoader(session)

        assert loader.loader is not None


class TestSCADABulkLoaderValidation:
    """Tests for SCADA record validation."""

    def test_valid_record_passes_validation(self) -> None:
        record = _record()

        SCADABulkLoader._validate_record(record)

    def test_missing_required_column_raises(self) -> None:
        record = _record()
        del record["equipment_id"]

        with pytest.raises(
            ValueError,
            match="SCADA record is missing required columns",
        ):
            SCADABulkLoader._validate_record(record)

    def test_invalid_timestamp_type_raises(self) -> None:
        record = _record()
        record["timestamp"] = "2026-08-14T10:00:00Z"

        with pytest.raises(
            TypeError,
            match="SCADA timestamp must be a datetime instance",
        ):
            SCADABulkLoader._validate_record(record)


class TestSCADABulkLoaderLoad:
    """Tests for SCADA bulk loading."""

    def test_empty_records_returns_zero(self) -> None:
        loader = SCADABulkLoader(_session())
        loader.loader.insert_orm_records = MagicMock()

        result = loader.load([])

        assert result == 0
        loader.loader.insert_orm_records.assert_not_called()

    def test_load_calls_bulk_loader(self) -> None:
        loader = SCADABulkLoader(_session())
        loader.loader.insert_orm_records = MagicMock(return_value=1)

        record = _record()

        result = loader.load([record])

        assert result == 1
        loader.loader.insert_orm_records.assert_called_once()

    def test_load_multiple_records(self) -> None:
        loader = SCADABulkLoader(_session())
        loader.loader.insert_orm_records = MagicMock(return_value=2)

        first = _record()
        second = _record()
        second["timestamp"] = datetime(
            2026,
            8,
            14,
            10,
            15,
            tzinfo=UTC,
        )

        result = loader.load([first, second])

        assert result == 2

        loader.loader.insert_orm_records.assert_called_once()

        _, records = loader.loader.insert_orm_records.call_args.args

        assert len(records) == 2

    def test_load_validates_before_insert(self) -> None:
        loader = SCADABulkLoader(_session())
        loader.loader.insert_orm_records = MagicMock()

        record = _record()
        del record["plant_id"]

        with pytest.raises(
            ValueError,
            match="SCADA record is missing required columns",
        ):
            loader.load([record])

        loader.loader.insert_orm_records.assert_not_called()
