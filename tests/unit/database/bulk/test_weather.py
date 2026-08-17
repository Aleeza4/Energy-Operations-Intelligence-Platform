"""Unit tests for the EOIP weather bulk loader."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from eoip.database.bulk.weather import WeatherBulkLoader


def _session() -> Session:
    """Return a mocked SQLAlchemy session."""
    return MagicMock(spec=Session)


def _record() -> dict[str, object]:
    """Return a valid weather observation record."""
    return {
        "plant_id": "PLANT001",
        "weather_station_id": "WS0001",
        "timestamp": datetime(2026, 8, 14, 10, 0, tzinfo=UTC),
        "ghi_wm2": 750.0,
        "dni_wm2": 620.0,
        "dhi_wm2": 130.0,
        "ambient_temperature_c": 29.5,
        "module_temperature_c": 45.0,
        "wind_speed_ms": 3.75,
        "relative_humidity_pct": 43.5,
        "quality": "valid",
    }


class TestWeatherBulkLoaderConstruction:
    """Tests for weather bulk-loader construction."""

    def test_constructs_loader(self) -> None:
        loader = WeatherBulkLoader(_session())

        assert loader.loader is not None


class TestWeatherBulkLoaderValidation:
    """Tests for weather record validation."""

    def test_valid_record_passes_validation(self) -> None:
        record = _record()

        WeatherBulkLoader._validate_record(record)

    def test_missing_required_column_raises(self) -> None:
        record = _record()
        del record["weather_station_id"]

        with pytest.raises(
            ValueError,
            match="Weather record is missing required columns",
        ):
            WeatherBulkLoader._validate_record(record)

    def test_invalid_timestamp_type_raises(self) -> None:
        record = _record()
        record["timestamp"] = "2026-08-14T10:00:00Z"

        with pytest.raises(
            TypeError,
            match="Weather timestamp must be a datetime instance",
        ):
            WeatherBulkLoader._validate_record(record)


class TestWeatherBulkLoaderLoad:
    """Tests for weather bulk loading."""

    def test_empty_records_returns_zero(self) -> None:
        loader = WeatherBulkLoader(_session())
        loader.loader.insert_orm_records = MagicMock()

        result = loader.load([])

        assert result == 0
        loader.loader.insert_orm_records.assert_not_called()

    def test_load_calls_bulk_loader(self) -> None:
        loader = WeatherBulkLoader(_session())
        loader.loader.insert_orm_records = MagicMock(return_value=1)

        result = loader.load([_record()])

        assert result == 1
        loader.loader.insert_orm_records.assert_called_once()

    def test_load_multiple_records(self) -> None:
        loader = WeatherBulkLoader(_session())
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
        loader = WeatherBulkLoader(_session())
        loader.loader.insert_orm_records = MagicMock()

        record = _record()
        del record["plant_id"]

        with pytest.raises(
            ValueError,
            match="Weather record is missing required columns",
        ):
            loader.load([record])

        loader.loader.insert_orm_records.assert_not_called()
