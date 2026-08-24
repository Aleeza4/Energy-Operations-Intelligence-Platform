"""Bulk-loading helpers for EOIP weather observations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime

from sqlalchemy.orm import Session

from eoip.database.bulk.loader import BulkLoader
from eoip.database.models.weather import WeatherObservationORM

REQUIRED_WEATHER_COLUMNS = {
    "plant_id",
    "weather_station_id",
    "timestamp",
    "ghi_wm2",
    "dni_wm2",
    "dhi_wm2",
    "ambient_temperature_c",
    "module_temperature_c",
    "wind_speed_ms",
    "relative_humidity_pct",
    "quality",
}


class WeatherBulkLoader:
    """Bulk loader for weather observation records."""

    def __init__(
        self,
        session: Session,
        *,
        batch_size: int = 5000,
    ) -> None:
        """Initialize the weather bulk loader."""
        self.loader = BulkLoader(
            session,
            batch_size=batch_size,
        )

    @staticmethod
    def _validate_record(
        record: Mapping[str, object],
    ) -> None:
        """Validate required weather record fields."""
        missing_columns = REQUIRED_WEATHER_COLUMNS - set(record)

        if missing_columns:
            raise ValueError(
                "Weather record is missing required columns: "
                f"{sorted(missing_columns)}"
            )

        timestamp = record["timestamp"]

        if not isinstance(timestamp, datetime):
            raise TypeError("Weather timestamp must be a datetime instance")

    def load(
        self,
        records: Iterable[Mapping[str, object]],
    ) -> int:
        """Validate and bulk insert weather observations."""
        normalized_records: list[dict[str, object]] = []

        for record in records:
            self._validate_record(record)
            normalized_records.append(dict(record))

        if not normalized_records:
            return 0

        return self.loader.insert_orm_records(
            WeatherObservationORM,
            normalized_records,
        )
