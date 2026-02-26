"""Tests for health and basic endpoints."""


def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["api_key_configured"] is True
    assert data["cases"] == 3  # seeded demo cases
    assert "active_sessions" in data
    assert "timestamp" in data
    assert "model" in data
    assert "auth_enabled" in data


def test_ui_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_security_headers(client):
    resp = client.get("/api/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["X-XSS-Protection"] == "1; mode=block"
    assert "X-Request-ID" in resp.headers


def test_request_id_present(client):
    resp = client.get("/api/health")
    request_id = resp.headers.get("X-Request-ID")
    assert request_id is not None
    assert len(request_id) == 8
