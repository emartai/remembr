"""Tests for middleware functionality."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


def test_request_id_middleware_adds_header(client):
    """Test that request ID is added to response headers."""
    response = client.get("/api/v1/health")
    
    assert "X-Request-ID" in response.headers


def test_request_id_is_unique(client):
    """Test that each request gets a unique request ID."""
    response1 = client.get("/api/v1/health")
    response2 = client.get("/api/v1/health")
    
    request_id1 = response1.headers["X-Request-ID"]
    request_id2 = response2.headers["X-Request-ID"]
    
    assert request_id1 != request_id2


def test_cors_headers_present(client):
    """Test that CORS headers are present."""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    
    assert "access-control-allow-origin" in response.headers
