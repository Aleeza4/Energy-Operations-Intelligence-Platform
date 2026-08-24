"""Unit tests for the EOIP analytics service."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from eoip.database.analytics.service import AnalyticsService


def _mock_session() -> MagicMock:
    """Return a Session-compatible mock."""
    return MagicMock(spec=Session)


def _row(**values: object) -> SimpleNamespace:
    """Return a row-like object exposing SQLAlchemy-style mapping data."""
    return SimpleNamespace(_mapping=values)


class TestAnalyticsServiceConstruction:
    """Tests for analytics service construction."""

    def test_service_stores_session(self) -> None:
        session = _mock_session()

        service = AnalyticsService(session)

        assert service.session is session


class TestPlantOperationalSummary:
    """Tests for plant operational summary execution."""

    def test_returns_rows_as_dictionaries(self) -> None:
        session = _mock_session()
        session.execute.return_value = [
            _row(
                plant_id="PLANT001",
                equipment_count=10,
                operational_equipment_count=8,
                non_operational_equipment_count=2,
            )
        ]

        service = AnalyticsService(session)

        result = service.plant_operational_summary()

        assert result == [
            {
                "plant_id": "PLANT001",
                "equipment_count": 10,
                "operational_equipment_count": 8,
                "non_operational_equipment_count": 2,
            }
        ]

        session.execute.assert_called_once()


class TestScadaHourlySummary:
    """Tests for SCADA hourly analytics execution."""

    def test_returns_scada_rows(self) -> None:
        session = _mock_session()

        bucket = datetime(
            2026,
            8,
            14,
            10,
            0,
            tzinfo=UTC,
        )

        session.execute.return_value = [
            _row(
                bucket=bucket,
                plant_id="PLANT001",
                equipment_id="INV000001",
                sample_count=4,
                avg_active_power_kw=550.0,
                max_active_power_kw=700.0,
                min_active_power_kw=400.0,
                total_energy_kwh=550.0,
            )
        ]

        service = AnalyticsService(session)

        result = service.scada_hourly_summary(
            plant_id="PLANT001",
            equipment_id="INV000001",
            start_at=bucket,
            end_at=datetime(
                2026,
                8,
                14,
                11,
                0,
                tzinfo=UTC,
            ),
        )

        assert result[0]["plant_id"] == "PLANT001"
        assert result[0]["equipment_id"] == "INV000001"
        assert result[0]["sample_count"] == 4
        assert result[0]["avg_active_power_kw"] == 550.0

        session.execute.assert_called_once()

    def test_passes_expected_query_parameters(self) -> None:
        session = _mock_session()
        session.execute.return_value = []

        service = AnalyticsService(session)

        start_at = datetime(
            2026,
            8,
            1,
            tzinfo=UTC,
        )
        end_at = datetime(
            2026,
            8,
            2,
            tzinfo=UTC,
        )

        service.scada_hourly_summary(
            plant_id="PLANT001",
            equipment_id="INV000001",
            start_at=start_at,
            end_at=end_at,
        )

        _, parameters = session.execute.call_args.args

        assert parameters == {
            "plant_id": "PLANT001",
            "equipment_id": "INV000001",
            "start_at": start_at,
            "end_at": end_at,
        }


class TestWeatherHourlySummary:
    """Tests for weather hourly analytics execution."""

    def test_returns_weather_rows(self) -> None:
        session = _mock_session()

        bucket = datetime(
            2026,
            8,
            14,
            10,
            0,
            tzinfo=UTC,
        )

        session.execute.return_value = [
            _row(
                bucket=bucket,
                plant_id="PLANT001",
                weather_station_id="WS0001",
                sample_count=4,
                avg_ghi_wm2=750.0,
                max_ghi_wm2=900.0,
                avg_ambient_temperature_c=29.5,
                avg_module_temperature_c=45.0,
                avg_wind_speed_ms=3.75,
                avg_relative_humidity_pct=43.5,
            )
        ]

        service = AnalyticsService(session)

        result = service.weather_hourly_summary(
            plant_id="PLANT001",
            weather_station_id="WS0001",
        )

        assert result[0]["plant_id"] == "PLANT001"
        assert result[0]["weather_station_id"] == "WS0001"
        assert result[0]["avg_ghi_wm2"] == 750.0
        assert result[0]["max_ghi_wm2"] == 900.0

        session.execute.assert_called_once()

    def test_passes_expected_query_parameters(self) -> None:
        session = _mock_session()
        session.execute.return_value = []

        service = AnalyticsService(session)

        service.weather_hourly_summary(
            plant_id="PLANT001",
            weather_station_id="WS0001",
        )

        _, parameters = session.execute.call_args.args

        assert parameters == {
            "plant_id": "PLANT001",
            "weather_station_id": "WS0001",
            "start_at": None,
            "end_at": None,
        }


class TestOpenAlarmSummary:
    """Tests for open-alarm analytics execution."""

    def test_returns_alarm_summary_rows(self) -> None:
        session = _mock_session()
        session.execute.return_value = [
            _row(
                plant_id="PLANT001",
                severity="critical",
                alarm_count=3,
            )
        ]

        service = AnalyticsService(session)

        result = service.open_alarm_summary()

        assert result == [
            {
                "plant_id": "PLANT001",
                "severity": "critical",
                "alarm_count": 3,
            }
        ]

        session.execute.assert_called_once()


class TestOpenIncidentSummary:
    """Tests for incident analytics execution."""

    def test_returns_incident_summary_rows(self) -> None:
        session = _mock_session()
        session.execute.return_value = [
            _row(
                plant_id="PLANT001",
                severity="high",
                incident_count=2,
            )
        ]

        service = AnalyticsService(session)

        result = service.open_incident_summary()

        assert result == [
            {
                "plant_id": "PLANT001",
                "severity": "high",
                "incident_count": 2,
            }
        ]

        session.execute.assert_called_once()


class TestWorkOrderStatusSummary:
    """Tests for work-order analytics execution."""

    def test_returns_work_order_summary_rows(self) -> None:
        session = _mock_session()
        session.execute.return_value = [
            _row(
                plant_id="PLANT001",
                status="completed",
                work_order_count=5,
                total_actual_cost=10000.0,
                total_actual_labor_hours=20.0,
            )
        ]

        service = AnalyticsService(session)

        result = service.work_order_status_summary()

        assert result == [
            {
                "plant_id": "PLANT001",
                "status": "completed",
                "work_order_count": 5,
                "total_actual_cost": 10000.0,
                "total_actual_labor_hours": 20.0,
            }
        ]

        session.execute.assert_called_once()
