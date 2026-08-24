"""Unit tests for EOIP analytics SQL queries."""

from __future__ import annotations

from sqlalchemy.sql.elements import TextClause

from eoip.database.analytics.queries import (
    open_alarm_summary_query,
    open_incident_summary_query,
    plant_operational_summary_query,
    scada_hourly_summary_query,
    weather_hourly_summary_query,
    work_order_status_summary_query,
)


def _sql(query: TextClause) -> str:
    """Return normalized SQL text for assertions."""
    return " ".join(str(query).split())


class TestPlantOperationalSummaryQuery:
    """Tests for plant operational summary SQL."""

    def test_returns_text_clause(self) -> None:
        query = plant_operational_summary_query()

        assert isinstance(query, TextClause)

    def test_contains_expected_equipment_aggregation(self) -> None:
        sql = _sql(plant_operational_summary_query())

        assert "FROM equipment" in sql
        assert "GROUP BY plant_id" in sql
        assert "equipment_count" in sql
        assert "operational_equipment_count" in sql
        assert "non_operational_equipment_count" in sql


class TestScadaHourlySummaryQuery:
    """Tests for SCADA hourly analytics SQL."""

    def test_returns_text_clause(self) -> None:
        query = scada_hourly_summary_query()

        assert isinstance(query, TextClause)

    def test_uses_scada_hourly_continuous_aggregate(self) -> None:
        sql = _sql(scada_hourly_summary_query())

        assert "FROM scada_hourly" in sql
        assert "avg_active_power_kw" in sql
        assert "max_active_power_kw" in sql
        assert "min_active_power_kw" in sql
        assert "total_energy_kwh" in sql

    def test_contains_expected_filters(self) -> None:
        sql = _sql(scada_hourly_summary_query())

        assert ":plant_id" in sql
        assert ":equipment_id" in sql
        assert ":start_at" in sql
        assert ":end_at" in sql


class TestWeatherHourlySummaryQuery:
    """Tests for weather hourly analytics SQL."""

    def test_returns_text_clause(self) -> None:
        query = weather_hourly_summary_query()

        assert isinstance(query, TextClause)

    def test_uses_weather_hourly_continuous_aggregate(self) -> None:
        sql = _sql(weather_hourly_summary_query())

        assert "FROM weather_hourly" in sql
        assert "avg_ghi_wm2" in sql
        assert "max_ghi_wm2" in sql
        assert "avg_ambient_temperature_c" in sql
        assert "avg_module_temperature_c" in sql

    def test_contains_expected_filters(self) -> None:
        sql = _sql(weather_hourly_summary_query())

        assert ":plant_id" in sql
        assert ":weather_station_id" in sql
        assert ":start_at" in sql
        assert ":end_at" in sql


class TestOpenAlarmSummaryQuery:
    """Tests for open-alarm analytics SQL."""

    def test_returns_text_clause(self) -> None:
        query = open_alarm_summary_query()

        assert isinstance(query, TextClause)

    def test_counts_uncleared_alarms_by_plant_and_severity(self) -> None:
        sql = _sql(open_alarm_summary_query())

        assert "FROM alarms" in sql
        assert "cleared_at IS NULL" in sql
        assert "GROUP BY plant_id, severity" in sql
        assert "alarm_count" in sql


class TestOpenIncidentSummaryQuery:
    """Tests for unresolved incident analytics SQL."""

    def test_returns_text_clause(self) -> None:
        query = open_incident_summary_query()

        assert isinstance(query, TextClause)

    def test_counts_unresolved_incidents_by_plant_and_severity(
        self,
    ) -> None:
        sql = _sql(open_incident_summary_query())

        assert "FROM incidents" in sql
        assert "resolved_at IS NULL" in sql
        assert "GROUP BY plant_id, severity" in sql
        assert "incident_count" in sql


class TestWorkOrderStatusSummaryQuery:
    """Tests for work-order status analytics SQL."""

    def test_returns_text_clause(self) -> None:
        query = work_order_status_summary_query()

        assert isinstance(query, TextClause)

    def test_contains_expected_work_order_aggregations(self) -> None:
        sql = _sql(work_order_status_summary_query())

        assert "FROM work_orders" in sql
        assert "GROUP BY plant_id, status" in sql
        assert "work_order_count" in sql
        assert "total_actual_cost" in sql
        assert "total_actual_labor_hours" in sql
