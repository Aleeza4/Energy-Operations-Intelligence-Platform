"""Execution service for EOIP SQL analytics queries."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from eoip.database.analytics.queries import (
    open_alarm_summary_query,
    open_incident_summary_query,
    plant_operational_summary_query,
    scada_hourly_summary_query,
    weather_hourly_summary_query,
    work_order_status_summary_query,
)


class AnalyticsService:
    """Execute reusable EOIP analytics queries."""

    def __init__(self, session: Session) -> None:
        """Initialize analytics service."""
        self.session = session

    def plant_operational_summary(self) -> list[dict[str, object]]:
        """Return plant-level operational equipment summary."""
        result = self.session.execute(plant_operational_summary_query())

        return [dict(row._mapping) for row in result]

    def scada_hourly_summary(
        self,
        *,
        plant_id: str | None = None,
        equipment_id: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[dict[str, object]]:
        """Return filtered hourly SCADA analytics."""
        result = self.session.execute(
            scada_hourly_summary_query(),
            {
                "plant_id": plant_id,
                "equipment_id": equipment_id,
                "start_at": start_at,
                "end_at": end_at,
            },
        )

        return [dict(row._mapping) for row in result]

    def weather_hourly_summary(
        self,
        *,
        plant_id: str | None = None,
        weather_station_id: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[dict[str, object]]:
        """Return filtered hourly weather analytics."""
        result = self.session.execute(
            weather_hourly_summary_query(),
            {
                "plant_id": plant_id,
                "weather_station_id": weather_station_id,
                "start_at": start_at,
                "end_at": end_at,
            },
        )

        return [dict(row._mapping) for row in result]

    def open_alarm_summary(self) -> list[dict[str, object]]:
        """Return open-alarm counts by plant and severity."""
        result = self.session.execute(open_alarm_summary_query())

        return [dict(row._mapping) for row in result]

    def open_incident_summary(self) -> list[dict[str, object]]:
        """Return unresolved incident counts by plant and severity."""
        result = self.session.execute(open_incident_summary_query())

        return [dict(row._mapping) for row in result]

    def work_order_status_summary(self) -> list[dict[str, object]]:
        """Return work-order status and cost/labor analytics."""
        result = self.session.execute(work_order_status_summary_query())

        return [dict(row._mapping) for row in result]
