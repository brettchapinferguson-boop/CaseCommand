import os
import tempfile
import pytest
from unittest.mock import AsyncMock, patch

# Set test environment before importing app
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key-for-testing"
os.environ["CLAUDE_MODEL"] = "claude-opus-4-8"
os.environ["PARALEGAL_INTERVAL"] = "0"  # disable background worker in tests
os.environ["DATABASE_PATH"] = tempfile.mktemp(suffix=".db")

from fastapi.testclient import TestClient
from server import app, sessions, rate_limits
import database as db


@pytest.fixture(autouse=True)
def clear_state():
    """Clear sessions and rate limits between tests."""
    sessions.clear()
    rate_limits.clear()
    yield
    sessions.clear()
    rate_limits.clear()


@pytest.fixture
def client(tmp_path):
    """Test client with a fresh database per test."""
    test_db = str(tmp_path / "test.db")
    db.DB_PATH = test_db
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_claude_success():
    """Mock a successful text-only Claude response (for /api/ai, /api/digest)."""
    mock_response = {
        "success": True,
        "text": "This is a test response from Claude.",
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }
    with patch("server.call_claude", new_callable=AsyncMock, return_value=mock_response) as mock:
        yield mock


@pytest.fixture
def mock_claude_failure():
    """Mock a failed text-only Claude response."""
    mock_response = {
        "success": False,
        "text": "",
        "error": "AI service unavailable",
    }
    with patch("server.call_claude", new_callable=AsyncMock, return_value=mock_response) as mock:
        yield mock


@pytest.fixture
def mock_agent_success():
    """Mock a successful agentic run (for /api/chat, /api/agent/draft)."""
    mock_response = {
        "success": True,
        "text": "This is a test response from Claude.",
        "actions": ["create_task(title=Follow up)"],
        "usage": {"input_tokens": 200, "output_tokens": 80},
        "error": None,
    }
    with patch("server.run_agent", new_callable=AsyncMock, return_value=mock_response) as mock:
        yield mock


@pytest.fixture
def mock_agent_failure():
    """Mock a failed agentic run."""
    mock_response = {
        "success": False,
        "text": "",
        "actions": [],
        "usage": {"input_tokens": 0, "output_tokens": 0},
        "error": "AI service unavailable",
    }
    with patch("server.run_agent", new_callable=AsyncMock, return_value=mock_response) as mock:
        yield mock


# ── Auth fixtures ─────────────────────────────────

@pytest.fixture
def auth_client(tmp_path):
    """Test client with auth enabled and fresh database."""
    import server
    test_db = str(tmp_path / "auth_test.db")
    db.DB_PATH = test_db
    original_token = server.AUTH_TOKEN
    original_enabled = server.AUTH_ENABLED
    server.AUTH_TOKEN = "test-secret-token"
    server.AUTH_ENABLED = True
    with TestClient(app) as c:
        yield c
    server.AUTH_TOKEN = original_token
    server.AUTH_ENABLED = original_enabled


@pytest.fixture
def auth_headers():
    """Valid auth headers."""
    return {"Authorization": "Bearer test-secret-token"}
