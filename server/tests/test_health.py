"""Tests for health check endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


def test_health_check_success(client):
    """Test health check returns 200 OK."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200


def test_health_check_response_format(client):
    """Test health check response has correct format."""
    response = client.get("/api/v1/health")
    data = response.json()

    assert "status" in data
    assert "environment" in data
    assert "version" in data
    assert "redis_status" in data

    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert data["redis_status"] in [
        "healthy",
        "unhealthy",
        "not_initialized",
        "error",
        "unknown",
    ]


def test_health_check_environment(client):
    """Test health check returns environment."""
    response = client.get("/api/v1/health")
    data = response.json()

    assert data["environment"] in ["local", "staging", "production"]


def test_health_check_has_request_id(client):
    """Test health check response includes request ID header."""
    response = client.get("/api/v1/health")

    assert "X-Request-ID" in response.headers
    request_id = response.headers["X-Request-ID"]

    # UUID format check (36 characters with hyphens)
    assert len(request_id) == 36
    assert request_id.count("-") == 4
