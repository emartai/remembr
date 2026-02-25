"""Tests for error handling."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


def test_404_error_format(client):
    """Test that 404 errors follow the standard error format."""
    response = client.get("/api/v1/nonexistent")

    assert response.status_code == 404
    data = response.json()

    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
    assert "request_id" in data["error"]

    # Error code format changed from HTTP_404 to NOT_FOUND
    assert data["error"]["code"] == "NOT_FOUND"


def test_404_includes_request_id(client):
    """Test that 404 errors include request ID."""
    response = client.get("/api/v1/nonexistent")
    data = response.json()

    assert "request_id" in data["error"]
    assert len(data["error"]["request_id"]) == 36  # UUID length


def test_error_has_request_id_header(client):
    """Test that error responses include X-Request-ID header."""
    response = client.get("/api/v1/nonexistent")

    assert "X-Request-ID" in response.headers

    # Request ID in header should match request ID in body
    header_id = response.headers["X-Request-ID"]
    body_id = response.json()["error"]["request_id"]

    assert header_id == body_id


def test_method_not_allowed_error(client):
    """Test that 405 errors follow the standard error format."""
    response = client.post("/api/v1/health")

    assert response.status_code == 405
    data = response.json()

    assert "error" in data
    # Error code for unmapped status codes is HTTP_{status_code}
    assert data["error"]["code"] == "HTTP_405"
