"""EOIP database analytics package."""

from eoip.database.analytics.queries import (
    open_alarm_summary_query,
    open_incident_summary_query,
    plant_operational_summary_query,
    scada_hourly_summary_query,
    weather_hourly_summary_query,
    work_order_status_summary_query,
)
from eoip.database.analytics.service import AnalyticsService

__all__ = [
    "AnalyticsService",
    "open_alarm_summary_query",
    "open_incident_summary_query",
    "plant_operational_summary_query",
    "scada_hourly_summary_query",
    "weather_hourly_summary_query",
    "work_order_status_summary_query",
]
