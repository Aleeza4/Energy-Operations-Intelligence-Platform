"""Deterministic API integration dependencies."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from eoip.api.app import app
from eoip.api.dependencies import get_data_provider
from eoip.api.schemas import Role
from eoip.api.security import AuthService, UserRecord, get_auth_service, hash_password


class FakeDataProvider:
    """Test implementation exercising the complete HTTP provider boundary."""

    def __init__(self) -> None:
        timestamp = datetime(2026, 8, 21, 10, tzinfo=UTC)
        self.plants = [
            {
                "plant_id": "PLANT001",
                "plant_name": "Solar Plant A",
                "region": "South",
                "latitude": 24.8,
                "longitude": 67.0,
                "dc_capacity_mw": 120.0,
                "ac_capacity_mw": 100.0,
                "commissioning_date": date(2020, 1, 1),
                "status": "operational",
                "timezone_name": "Asia/Karachi",
            },
            {
                "plant_id": "PLANT002",
                "plant_name": "Solar Plant B",
                "region": "North",
                "latitude": 31.5,
                "longitude": 74.3,
                "dc_capacity_mw": 90.0,
                "ac_capacity_mw": 75.0,
                "commissioning_date": date(2021, 1, 1),
                "status": "planned_outage",
                "timezone_name": "Asia/Karachi",
            },
        ]
        self.equipment = [
            {
                "equipment_id": "INV000001",
                "plant_id": "PLANT001",
                "equipment_name": "Inverter 1",
                "equipment_type": "string_inverter",
                "manufacturer": "EOIP",
                "model_number": "INV-X",
                "serial_number": "SERIAL-1",
                "commissioning_date": date(2020, 1, 1),
                "rated_power_kw": 1000.0,
                "parent_equipment_id": None,
                "status": "operational",
            }
        ]
        self.scada = [
            {
                "plant_id": "PLANT001",
                "equipment_id": "INV000001",
                "timestamp": timestamp,
                "active_power_kw": 800.0,
                "interval_energy_kwh": 200.0,
                "dc_voltage_v": 1000.0,
                "dc_current_a": 850.0,
                "ac_voltage_v": 400.0,
                "ac_current_a": 1200.0,
                "frequency_hz": 50.0,
                "power_factor": 0.99,
                "equipment_available": True,
                "grid_available": True,
                "operating_state": "normal",
                "quality": "valid",
            }
        ]
        self.alarms = [
            {
                "alarm_id": "ALARM001",
                "plant_id": "PLANT001",
                "equipment_id": "INV000001",
                "alarm_code": "INV-TEMP",
                "alarm_name": "High temperature",
                "category": "thermal",
                "severity": "high",
                "raised_at": timestamp,
                "status": "active",
                "acknowledged_at": None,
                "cleared_at": None,
                "message": "Temperature threshold exceeded.",
            }
        ]
        self.incidents = [
            {
                "incident_id": "INC000001",
                "plant_id": "PLANT001",
                "equipment_id": "INV000001",
                "incident_name": "Inverter derating",
                "category": "equipment_failure",
                "severity": "high",
                "occurred_at": timestamp,
                "status": "open",
                "detected_at": timestamp,
                "resolved_at": None,
                "description": "Derating under investigation.",
                "root_cause": None,
                "linked_alarm_id": "ALARM001",
            }
        ]
        self.forecasts = [
            {
                "forecast_id": "FORECAST001",
                "model_name": "seasonal_naive",
                "target_column": "energy_kwh",
                "generated_at": timestamp,
                "row_count": 1,
                "units": "kWh",
                "values": [{"timestamp": timestamp, "prediction": 250.0}],
            }
        ]
        self.anomalies = [
            {
                "anomaly_id": "ANOMALY001",
                "anomaly_run_id": "RUN000001",
                "timestamp": timestamp,
                "score": 0.91,
                "detector_name": "isolation_forest",
                "target_column": "active_power_kw",
                "generated_at": timestamp,
                "severity": "high",
                "status": "detected",
            }
        ]
        self.recommendations = [
            {
                "recommendation_id": "REC000001",
                "plant_id": "PLANT001",
                "equipment_id": "INV000001",
                "recommendation_type": "maintenance",
                "action": "Schedule inspection.",
                "rationale": "Elevated validated risk.",
                "priority_rank": 1,
                "priority_score": 0.9,
                "risk_score": 0.8,
                "recoverable_energy_kwh": 500.0,
                "expected_benefit": 12000.0,
                "net_financial_impact": 9000.0,
                "roi_percent": 180.0,
                "economically_justified": True,
            }
        ]

    @staticmethod
    def _page(
        items: list[dict[str, Any]], limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        return items[offset : offset + limit], len(items)

    def list_plants(self, *, status: str | None, limit: int, offset: int):
        items = [
            row for row in self.plants if status is None or row["status"] == status
        ]
        return self._page(items, limit, offset)

    def get_plant(self, plant_id: str):
        return next((row for row in self.plants if row["plant_id"] == plant_id), None)

    def list_equipment(self, *, plant_id, equipment_type, status, limit, offset):
        items = [
            row
            for row in self.equipment
            if (plant_id is None or row["plant_id"] == plant_id)
            and (equipment_type is None or row["equipment_type"] == equipment_type)
            and (status is None or row["status"] == status)
        ]
        return self._page(items, limit, offset)

    def get_equipment(self, equipment_id: str):
        return next(
            (row for row in self.equipment if row["equipment_id"] == equipment_id),
            None,
        )

    def list_scada(self, *, plant_id, equipment_id, limit, offset, **kwargs):
        items = [
            row
            for row in self.scada
            if (plant_id is None or row["plant_id"] == plant_id)
            and (equipment_id is None or row["equipment_id"] == equipment_id)
        ]
        return self._page(items, limit, offset)

    def list_alarms(
        self, *, plant_id, equipment_id, severity, status, limit, offset, **kwargs
    ):
        items = [
            row
            for row in self.alarms
            if (plant_id is None or row["plant_id"] == plant_id)
            and (equipment_id is None or row["equipment_id"] == equipment_id)
            and (severity is None or row["severity"] == severity)
            and (status is None or row["status"] == status)
        ]
        return self._page(items, limit, offset)

    def get_alarm(self, alarm_id: str):
        return next((row for row in self.alarms if row["alarm_id"] == alarm_id), None)

    def list_incidents(
        self, *, plant_id, equipment_id, severity, status, limit, offset, **kwargs
    ):
        items = [
            row
            for row in self.incidents
            if (plant_id is None or row["plant_id"] == plant_id)
            and (equipment_id is None or row["equipment_id"] == equipment_id)
            and (severity is None or row["severity"] == severity)
            and (status is None or row["status"] == status)
        ]
        return self._page(items, limit, offset)

    def get_incident(self, incident_id: str):
        return next(
            (row for row in self.incidents if row["incident_id"] == incident_id),
            None,
        )

    def analytics_summary(self, *, plant_id, start_time, end_time):
        del start_time, end_time
        return {
            "plant_operations": [
                {"plant_id": plant_id or "PLANT001", "equipment_count": 1}
            ],
            "scada_hourly": [
                {"plant_id": plant_id or "PLANT001", "total_energy_kwh": 200.0}
            ],
            "open_alarms": [{"plant_id": plant_id or "PLANT001", "alarm_count": 1}],
            "open_incidents": [
                {"plant_id": plant_id or "PLANT001", "incident_count": 1}
            ],
        }

    def list_forecasts(self, *, model_name, horizon, limit, offset):
        del horizon
        items = [
            row
            for row in self.forecasts
            if model_name is None or row["model_name"] == model_name
        ]
        return self._page(items, limit, offset)

    def get_forecast(self, forecast_id: str):
        return next(
            (row for row in self.forecasts if row["forecast_id"] == forecast_id),
            None,
        )

    def list_anomalies(self, *, method, limit, offset, **kwargs):
        items = [
            row
            for row in self.anomalies
            if method is None or row["detector_name"] == method
        ]
        return self._page(items, limit, offset)

    def get_anomaly(self, anomaly_id: str):
        return next(
            (row for row in self.anomalies if row["anomaly_id"] == anomaly_id),
            None,
        )

    def anomaly_evaluation(self):
        return [
            {
                "detector_name": "isolation_forest",
                "run_count": 1,
                "detected_count": 1,
                "note": "Stored integration fixture.",
            }
        ]

    def list_recommendations(
        self,
        *,
        plant_id,
        equipment_id,
        recommendation_type,
        minimum_priority,
        economically_justified,
        limit,
        offset,
    ):
        items = [
            row
            for row in self.recommendations
            if (plant_id is None or row["plant_id"] == plant_id)
            and (equipment_id is None or row["equipment_id"] == equipment_id)
            and (
                recommendation_type is None
                or row["recommendation_type"] == recommendation_type
            )
            and (minimum_priority is None or row["priority_score"] >= minimum_priority)
            and (
                economically_justified is None
                or row["economically_justified"] == economically_justified
            )
        ]
        return self._page(items, limit, offset)

    def get_recommendation(self, recommendation_id: str):
        return next(
            (
                row
                for row in self.recommendations
                if row["recommendation_id"] == recommendation_id
            ),
            None,
        )


@pytest.fixture
def auth_service() -> AuthService:
    users = tuple(
        UserRecord(
            username=role.value,
            password_hash=hash_password(
                f"{role.value}-password",
                salt=f"{role.value}-test-salt".encode(),
            ),
            role=role,
        )
        for role in Role
    )
    return AuthService(
        secret="integration-test-secret-at-least-32-characters",
        expiry_minutes=30,
        users=users,
    )


@pytest.fixture
def client(auth_service: AuthService) -> TestClient:
    app.dependency_overrides[get_data_provider] = FakeDataProvider
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def token_headers(client: TestClient):
    def headers(role: Role = Role.VIEWER) -> dict[str, str]:
        response = client.post(
            "/api/v1/auth/token",
            data={
                "username": role.value,
                "password": f"{role.value}-password",
            },
        )
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return headers
