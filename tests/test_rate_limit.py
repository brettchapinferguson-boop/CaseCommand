"""Tests for rate limiting."""
from server import _check_rate_limit, rate_limits
import server


def test_rate_limit_allows_requests():
    assert _check_rate_limit("1.2.3.4") is True


def test_rate_limit_blocks_after_threshold():
    original = server.RATE_LIMIT_REQUESTS
    server.RATE_LIMIT_REQUESTS = 3
    try:
        rate_limits.clear()
        assert _check_rate_limit("10.0.0.1") is True
        assert _check_rate_limit("10.0.0.1") is True
        assert _check_rate_limit("10.0.0.1") is True
        assert _check_rate_limit("10.0.0.1") is False  # 4th request blocked
    finally:
        server.RATE_LIMIT_REQUESTS = original


def test_rate_limit_per_ip():
    rate_limits.clear()
    original = server.RATE_LIMIT_REQUESTS
    server.RATE_LIMIT_REQUESTS = 2
    try:
        assert _check_rate_limit("ip-a") is True
        assert _check_rate_limit("ip-a") is True
        assert _check_rate_limit("ip-a") is False

        # Different IP should still work
        assert _check_rate_limit("ip-b") is True
    finally:
        server.RATE_LIMIT_REQUESTS = original


def test_rate_limit_integration(client, mock_claude_success):
    """Test that rate limiting applies to AI endpoints via HTTP."""
    original = server.RATE_LIMIT_REQUESTS
    server.RATE_LIMIT_REQUESTS = 2
    rate_limits.clear()
    try:
        resp1 = client.post("/api/chat", json={"message": "test1"})
        assert resp1.status_code == 200

        resp2 = client.post("/api/chat", json={"message": "test2"})
        assert resp2.status_code == 200

        resp3 = client.post("/api/chat", json={"message": "test3"})
        assert resp3.status_code == 429
    finally:
        server.RATE_LIMIT_REQUESTS = original


def test_rate_limit_not_applied_to_non_ai(client):
    """Non-AI endpoints should not be rate limited."""
    original = server.RATE_LIMIT_REQUESTS
    server.RATE_LIMIT_REQUESTS = 1
    rate_limits.clear()
    try:
        # These should never be rate limited
        for _ in range(5):
            resp = client.get("/api/health")
            assert resp.status_code == 200

        for _ in range(5):
            resp = client.get("/api/cases")
            assert resp.status_code == 200
    finally:
        server.RATE_LIMIT_REQUESTS = original
