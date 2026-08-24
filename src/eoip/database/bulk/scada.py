"""Bulk-loading helpers for EOIP SCADA observations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime

from sqlalchemy.orm import Session

from eoip.database.bulk.loader import BulkLoader
from eoip.database.models.scada import SCADAObservationORM

REQUIRED_SCADA_COLUMNS = {
    "plant_id",
    "equipment_id",
    "timestamp",
    "active_power_kw",
    "interval_energy_kwh",
    "dc_voltage_v",
    "dc_current_a",
    "ac_voltage_v",
    "ac_current_a",
    "frequency_hz",
    "power_factor",
    "equipment_available",
    "grid_available",
    "operating_state",
    "quality",
}


class SCADABulkLoader:
    """Bulk loader for SCADA observation records."""

    def __init__(
        self,
        session: Session,
        *,
        batch_size: int = 5000,
    ) -> None:
        """Initialize the SCADA bulk loader."""
        self.loader = BulkLoader(
            session,
            batch_size=batch_size,
        )

    @staticmethod
    def _validate_record(
        record: Mapping[str, object],
    ) -> None:
        """Validate required SCADA record fields."""
        missing_columns = REQUIRED_SCADA_COLUMNS - set(record)

        if missing_columns:
            raise ValueError(
                "SCADA record is missing required columns: "
                f"{sorted(missing_columns)}"
            )

        timestamp = record["timestamp"]

        if not isinstance(timestamp, datetime):
            raise TypeError("SCADA timestamp must be a datetime instance")

    def load(
        self,
        records: Iterable[Mapping[str, object]],
    ) -> int:
        """Validate and bulk insert SCADA observations."""
        normalized_records: list[dict[str, object]] = []

        for record in records:
            self._validate_record(record)
            normalized_records.append(dict(record))

        if not normalized_records:
            return 0

        return self.loader.insert_orm_records(
            SCADAObservationORM,
            normalized_records,
        )
