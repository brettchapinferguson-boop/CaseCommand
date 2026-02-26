"""Tests for authentication."""


def test_auth_disabled_allows_all(client):
    """When AUTH_TOKEN is not set, all requests pass through."""
    resp = client.get("/api/cases")
    assert resp.status_code == 200


def test_auth_enabled_rejects_no_token(auth_client):
    """When auth is enabled, requests without token are rejected."""
    resp = auth_client.get("/api/cases")
    assert resp.status_code == 401


def test_auth_enabled_rejects_bad_token(auth_client):
    """When auth is enabled, requests with wrong token are rejected."""
    resp = auth_client.get(
        "/api/cases",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 401


def test_auth_enabled_accepts_valid_token(auth_client, auth_headers):
    """When auth is enabled, requests with correct token pass."""
    resp = auth_client.get("/api/cases", headers=auth_headers)
    assert resp.status_code == 200


def test_auth_enabled_on_post(auth_client, auth_headers, mock_claude_success):
    """Auth works on POST endpoints too."""
    # Without auth
    resp = auth_client.post("/api/chat", json={"message": "test"})
    assert resp.status_code == 401

    # With auth
    resp = auth_client.post(
        "/api/chat",
        json={"message": "test"},
        headers=auth_headers,
    )
    assert resp.status_code == 200


def test_auth_enabled_on_crud(auth_client, auth_headers):
    """Auth works on CRUD endpoints."""
    # Create without auth
    resp = auth_client.post("/api/cases", json={
        "name": "Test", "type": "Test", "client": "Test", "opposing": "Test",
    })
    assert resp.status_code == 401

    # Create with auth
    resp = auth_client.post(
        "/api/cases",
        json={"name": "Test", "type": "Test", "client": "Test", "opposing": "Test"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    case_id = resp.json()["id"]

    # Update without auth
    resp = auth_client.put(f"/api/cases/{case_id}", json={"specials": 999})
    assert resp.status_code == 401

    # Delete without auth
    resp = auth_client.delete(f"/api/cases/{case_id}")
    assert resp.status_code == 401

    # Delete with auth
    resp = auth_client.delete(f"/api/cases/{case_id}", headers=auth_headers)
    assert resp.status_code == 200


def test_health_always_public(auth_client):
    """Health endpoint is always accessible regardless of auth."""
    resp = auth_client.get("/api/health")
    assert resp.status_code == 200


def test_auth_malformed_header(auth_client):
    """Malformed auth headers are rejected."""
    resp = auth_client.get(
        "/api/cases",
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert resp.status_code == 401

    resp = auth_client.get(
        "/api/cases",
        headers={"Authorization": "token-without-bearer-prefix"},
    )
    assert resp.status_code == 401
