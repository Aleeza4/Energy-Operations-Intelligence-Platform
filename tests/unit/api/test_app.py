"""Unit tests for FastAPI construction and OpenAPI metadata."""

from __future__ import annotations

from fastapi.testclient import TestClient

from eoip.api.app import app, create_app


def test_exported_app_registers_and_dispatches_versioned_routes() -> None:
    """Guard the exact ASGI object targeted by the documented Uvicorn command."""
    paths = set(app.openapi()["paths"])

    assert "/api/v1/health" in paths
    assert "/api/v1/auth/token" in paths
    assert "/api/v1/admin/status" in paths

    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_app_registers_versioned_routes() -> None:
    application = create_app()
    paths = set(application.openapi()["paths"])

    assert "/api/v1/health" in paths
    assert "/api/v1/plants" in paths
    assert "/api/v1/recommendations/{recommendation_id}" in paths


def test_openapi_has_oauth_and_expected_paths() -> None:
    schema = create_app().openapi()

    assert schema["info"]["title"] == "Energy Operations Intelligence Platform API"
    assert "OAuth2PasswordBearer" in schema["components"]["securitySchemes"]
    assert "/api/v1/scada" in schema["paths"]
    assert "/api/v1/admin/status" in schema["paths"]
