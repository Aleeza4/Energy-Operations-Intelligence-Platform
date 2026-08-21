"""End-to-end HTTP boundary tests for Phase 11 routes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from eoip.api.schemas import Role


def test_health_is_public(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_protected_route_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/plants")

    assert response.status_code == 401


def test_valid_login_and_current_user(client: TestClient, token_headers) -> None:
    response = client.get("/api/v1/auth/me", headers=token_headers(Role.VIEWER))

    assert response.status_code == 200
    assert response.json() == {"username": "viewer", "role": "viewer"}


def test_bad_credentials_are_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "viewer", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_invalid_token_is_rejected(client: TestClient) -> None:
    response = client.get(
        "/api/v1/plants",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_viewer_forbidden_from_admin(client: TestClient, token_headers) -> None:
    response = client.get(
        "/api/v1/admin/status",
        headers=token_headers(Role.VIEWER),
    )

    assert response.status_code == 403


def test_admin_allowed_on_admin_route(client: TestClient, token_headers) -> None:
    response = client.get(
        "/api/v1/admin/status",
        headers=token_headers(Role.ADMIN),
    )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_plant_list_filter_detail_and_not_found(
    client: TestClient,
    token_headers,
) -> None:
    headers = token_headers()
    response = client.get(
        "/api/v1/plants?status=operational&limit=1&offset=0",
        headers=headers,
    )
    detail = client.get("/api/v1/plants/PLANT001", headers=headers)
    missing = client.get("/api/v1/plants/PLANT999", headers=headers)

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert detail.json()["plant_name"] == "Solar Plant A"
    assert missing.status_code == 404


def test_equipment_list_filter_detail_and_not_found(
    client: TestClient,
    token_headers,
) -> None:
    headers = token_headers()
    response = client.get(
        "/api/v1/equipment?plant_id=PLANT001",
        headers=headers,
    )
    detail = client.get("/api/v1/equipment/INV000001", headers=headers)
    missing = client.get("/api/v1/equipment/INV999999", headers=headers)

    assert response.json()["total"] == 1
    assert detail.json()["equipment_type"] == "string_inverter"
    assert missing.status_code == 404


def test_scada_range_filters_and_bounds(client: TestClient, token_headers) -> None:
    headers = token_headers()
    response = client.get(
        "/api/v1/scada?plant_id=PLANT001&equipment_id=INV000001"
        "&start_time=2026-08-21T00:00:00Z&end_time=2026-08-22T00:00:00Z",
        headers=headers,
    )
    reversed_range = client.get(
        "/api/v1/scada?start_time=2026-08-22T00:00:00Z"
        "&end_time=2026-08-21T00:00:00Z",
        headers=headers,
    )
    oversized = client.get("/api/v1/scada?limit=1001", headers=headers)

    assert response.status_code == 200
    assert response.json()["items"][0]["timestamp"].endswith("Z")
    assert reversed_range.status_code == 422
    assert oversized.status_code == 422


def test_alarm_routes_and_filters(client: TestClient, token_headers) -> None:
    headers = token_headers()
    response = client.get("/api/v1/alarms?severity=high", headers=headers)
    detail = client.get("/api/v1/alarms/ALARM001", headers=headers)
    missing = client.get("/api/v1/alarms/ALARM999", headers=headers)

    assert response.json()["total"] == 1
    assert detail.json()["status"] == "active"
    assert missing.status_code == 404


def test_incident_routes_and_filters(client: TestClient, token_headers) -> None:
    headers = token_headers()
    response = client.get("/api/v1/incidents?status=open", headers=headers)
    detail = client.get("/api/v1/incidents/INC000001", headers=headers)
    missing = client.get("/api/v1/incidents/INC999999", headers=headers)

    assert response.json()["total"] == 1
    assert detail.json()["linked_alarm_id"] == "ALARM001"
    assert missing.status_code == 404


def test_analytics_summary_and_metric_validation(
    client: TestClient,
    token_headers,
) -> None:
    headers = token_headers()
    response = client.get(
        "/api/v1/analytics/summary?plant_id=PLANT001&metrics=scada_hourly",
        headers=headers,
    )
    invalid = client.get(
        "/api/v1/analytics/summary?metrics=unknown",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["plant_operations"] == []
    assert response.json()["scada_hourly"]
    assert invalid.status_code == 422


def test_forecast_routes_and_horizon_validation(
    client: TestClient,
    token_headers,
) -> None:
    headers = token_headers()
    response = client.get("/api/v1/forecasts?horizon=7", headers=headers)
    detail = client.get("/api/v1/forecasts/FORECAST001", headers=headers)
    invalid = client.get("/api/v1/forecasts?horizon=0", headers=headers)

    assert response.json()["total"] == 1
    assert detail.json()["model_name"] == "seasonal_naive"
    assert invalid.status_code == 422


def test_anomaly_routes_filters_evaluation_and_detail(
    client: TestClient,
    token_headers,
) -> None:
    headers = token_headers()
    response = client.get(
        "/api/v1/anomalies?method=isolation_forest",
        headers=headers,
    )
    evaluation = client.get("/api/v1/anomalies/evaluation", headers=headers)
    detail = client.get("/api/v1/anomalies/ANOMALY001", headers=headers)

    assert response.json()["total"] == 1
    assert evaluation.json()[0]["detected_count"] == 1
    assert detail.json()["score"] == 0.91


def test_recommendation_routes_and_financial_filters(
    client: TestClient,
    token_headers,
) -> None:
    headers = token_headers()
    response = client.get(
        "/api/v1/recommendations?recommendation_type=maintenance"
        "&minimum_priority=0.8&economically_justified=true",
        headers=headers,
    )
    detail = client.get("/api/v1/recommendations/REC000001", headers=headers)

    assert response.json()["total"] == 1
    assert detail.json()["net_financial_impact"] == 9000.0


def test_openapi_and_documentation_routes(client: TestClient) -> None:
    openapi = client.get("/openapi.json")
    docs = client.get("/docs")

    assert openapi.status_code == 200
    assert docs.status_code == 200
    schema = openapi.json()
    assert "/api/v1/health" in schema["paths"]
    assert "OAuth2PasswordBearer" in schema["components"]["securitySchemes"]


def test_internal_exception_does_not_leak_details(
    client: TestClient,
    token_headers,
) -> None:
    from eoip.api.app import app
    from eoip.api.dependencies import get_data_provider

    class BrokenProvider:
        def list_plants(self, **kwargs):
            del kwargs
            raise RuntimeError("secret database URL")

    app.dependency_overrides[get_data_provider] = BrokenProvider
    response = client.get("/api/v1/plants", headers=token_headers())

    assert response.status_code == 500
    assert "secret database URL" not in response.text
