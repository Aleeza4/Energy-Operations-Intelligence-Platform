"""Reusable SQL analytics queries for EOIP."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.sql.elements import TextClause


def plant_operational_summary_query() -> TextClause:
    """Return SQL for plant-level operational summary analytics."""
    return text("""
        SELECT
            plant_id,
            COUNT(*) AS equipment_count,
            COUNT(*) FILTER (
                WHERE status = 'operational'
            ) AS operational_equipment_count,
            COUNT(*) FILTER (
                WHERE status <> 'operational'
            ) AS non_operational_equipment_count
        FROM equipment
        GROUP BY plant_id
        ORDER BY plant_id
        """)


def scada_hourly_summary_query() -> TextClause:
    """Return SQL for hourly SCADA performance analytics."""
    return text("""
        SELECT
            bucket,
            plant_id,
            equipment_id,
            sample_count,
            avg_active_power_kw,
            max_active_power_kw,
            min_active_power_kw,
            total_energy_kwh
        FROM scada_hourly
        WHERE (:plant_id IS NULL OR plant_id = :plant_id)
          AND (:equipment_id IS NULL OR equipment_id = :equipment_id)
          AND (:start_at IS NULL OR bucket >= :start_at)
          AND (:end_at IS NULL OR bucket < :end_at)
        ORDER BY bucket, plant_id, equipment_id
        """)


def weather_hourly_summary_query() -> TextClause:
    """Return SQL for hourly weather analytics."""
    return text("""
        SELECT
            bucket,
            plant_id,
            weather_station_id,
            sample_count,
            avg_ghi_wm2,
            max_ghi_wm2,
            avg_ambient_temperature_c,
            avg_module_temperature_c,
            avg_wind_speed_ms,
            avg_relative_humidity_pct
        FROM weather_hourly
        WHERE (:plant_id IS NULL OR plant_id = :plant_id)
          AND (
                :weather_station_id IS NULL
                OR weather_station_id = :weather_station_id
              )
          AND (:start_at IS NULL OR bucket >= :start_at)
          AND (:end_at IS NULL OR bucket < :end_at)
        ORDER BY bucket, plant_id, weather_station_id
        """)


def open_alarm_summary_query() -> TextClause:
    """Return SQL for current open-alarm analytics."""
    return text("""
        SELECT
            plant_id,
            severity,
            COUNT(*) AS alarm_count
        FROM alarms
        WHERE cleared_at IS NULL
        GROUP BY plant_id, severity
        ORDER BY plant_id, severity
        """)


def open_incident_summary_query() -> TextClause:
    """Return SQL for unresolved incident analytics."""
    return text("""
        SELECT
            plant_id,
            severity,
            COUNT(*) AS incident_count
        FROM incidents
        WHERE resolved_at IS NULL
        GROUP BY plant_id, severity
        ORDER BY plant_id, severity
        """)


def work_order_status_summary_query() -> TextClause:
    """Return SQL for work-order status analytics."""
    return text("""
        SELECT
            plant_id,
            status,
            COUNT(*) AS work_order_count,
            COALESCE(SUM(actual_cost), 0) AS total_actual_cost,
            COALESCE(SUM(actual_labor_hours), 0) AS total_actual_labor_hours
        FROM work_orders
        GROUP BY plant_id, status
        ORDER BY plant_id, status
        """)
