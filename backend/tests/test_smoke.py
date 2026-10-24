from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_is_available_without_database_queries() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "1.0.0"}


def test_expected_api_routers_are_registered() -> None:
    paths = {route.path for route in app.routes if hasattr(route, "path")}

    assert "/api/v1/auth/register" in paths
    assert "/api/v1/employees" in paths
    assert "/api/v1/tasks" in paths
    assert "/api/v1/leaves" in paths
    assert "/api/v1/analytics" in paths
    assert "/api/v1/auth/me" in paths
    assert "/api/v1/auth/me/export" in paths
    assert "/api/v1/auth/sessions/{session_id}/revoke" in paths
    assert "/api/v1/auth/sessions/revoke-all" in paths


def test_api_responses_use_frontend_snake_case_field_names() -> None:
    api_routes = [
        route
        for route in app.routes
        if hasattr(route, "path") and route.path.startswith("/api/")
    ]

    assert api_routes
    assert all(getattr(route, "response_model_by_alias", False) is False for route in api_routes)
