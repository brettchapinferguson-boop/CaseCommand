"""Tests for chat and AI endpoints."""


def test_chat_success(client, mock_claude_success):
    resp = client.post("/api/chat", json={"message": "What are my cases?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "session_id" in data
    assert data["response"] == "This is a test response from Claude."


def test_chat_with_session_id(client, mock_claude_success):
    resp = client.post(
        "/api/chat",
        json={"message": "Hello", "session_id": "test-session-123"},
    )
    assert resp.status_code == 200
    assert resp.json()["session_id"] == "test-session-123"


def test_chat_with_case_context(client, mock_claude_success):
    resp = client.post(
        "/api/chat",
        json={"message": "Status update", "current_case_id": "c1"},
    )
    assert resp.status_code == 200
    # Verify the mock was called with case context in the system prompt
    call_args = mock_claude_success.call_args
    system_prompt = call_args[0][0]
    assert "Rodriguez v. Smith Trucking" in system_prompt


def test_chat_session_persistence(client, mock_claude_success):
    # First message
    resp1 = client.post(
        "/api/chat",
        json={"message": "First message", "session_id": "persist-test"},
    )
    assert resp1.status_code == 200

    # Second message in same session
    resp2 = client.post(
        "/api/chat",
        json={"message": "Second message", "session_id": "persist-test"},
    )
    assert resp2.status_code == 200

    # Both should use the same session
    assert resp1.json()["session_id"] == resp2.json()["session_id"]


def test_chat_failure(client, mock_claude_failure):
    resp = client.post("/api/chat", json={"message": "Hello"})
    assert resp.status_code == 502


def test_chat_empty_message(client):
    resp = client.post("/api/chat", json={"message": ""})
    assert resp.status_code == 422  # Validation error


def test_chat_message_too_long(client):
    resp = client.post("/api/chat", json={"message": "x" * 50001})
    assert resp.status_code == 422


def test_ai_endpoint_success(client, mock_claude_success):
    resp = client.post(
        "/api/ai",
        json={
            "system": "You are a helpful assistant.",
            "message": "Hello",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["text"] == "This is a test response from Claude."


def test_ai_endpoint_failure(client, mock_claude_failure):
    resp = client.post(
        "/api/ai",
        json={
            "system": "You are a helpful assistant.",
            "message": "Hello",
        },
    )
    assert resp.status_code == 502


def test_ai_endpoint_validation(client):
    # Missing required fields
    resp = client.post("/api/ai", json={"message": "Hello"})
    assert resp.status_code == 422

    # Empty system prompt
    resp = client.post("/api/ai", json={"system": "", "message": "Hello"})
    assert resp.status_code == 422


def test_ai_temperature_bounds(client):
    resp = client.post(
        "/api/ai",
        json={"system": "test", "message": "test", "temperature": 1.5},
    )
    assert resp.status_code == 422

    resp = client.post(
        "/api/ai",
        json={"system": "test", "message": "test", "temperature": -0.1},
    )
    assert resp.status_code == 422


def test_ai_max_tokens_bounds(client):
    resp = client.post(
        "/api/ai",
        json={"system": "test", "message": "test", "max_tokens": 0},
    )
    assert resp.status_code == 422

    resp = client.post(
        "/api/ai",
        json={"system": "test", "message": "test", "max_tokens": 99999},
    )
    assert resp.status_code == 422


def test_digest_success(client, mock_claude_success):
    resp = client.get("/api/digest")
    assert resp.status_code == 200
    data = resp.json()
    assert "digest" in data
    assert "generated_at" in data


def test_digest_failure(client, mock_claude_failure):
    resp = client.get("/api/digest")
    assert resp.status_code == 502
