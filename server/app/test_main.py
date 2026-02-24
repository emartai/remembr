"""
Test file to verify the FastAPI application setup.

Run with: pytest server/app/test_main.py
"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert "environment" in data
    assert data["version"] == "0.1.0"


def test_request_id_header(client):
    """Test that X-Request-ID header is added to responses."""
    response = client.get("/api/v1/health")

    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) == 36  # UUID length


def test_404_error_format(client):
    """Test that 404 errors follow the error format."""
    response = client.get("/api/v1/nonexistent")

    assert response.status_code == 404
    data = response.json()

    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
    assert "request_id" in data["error"]
