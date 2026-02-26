import os
import pytest
from unittest.mock import AsyncMock, patch

# Set test environment before importing app
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key-for-testing"
os.environ["CLAUDE_MODEL"] = "claude-sonnet-4-5-20250514"

from fastapi.testclient import TestClient
from server import app, sessions, rate_limits


@pytest.fixture(autouse=True)
def clear_state():
    """Clear sessions and rate limits between tests."""
    sessions.clear()
    rate_limits.clear()
    yield
    sessions.clear()
    rate_limits.clear()


@pytest.fixture
def client():
    """Test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_claude_success():
    """Mock a successful Claude API response."""
    mock_response = {
        "success": True,
        "text": "This is a test response from Claude.",
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }
    with patch("server.call_claude", new_callable=AsyncMock, return_value=mock_response) as mock:
        yield mock


@pytest.fixture
def mock_claude_failure():
    """Mock a failed Claude API response."""
    mock_response = {
        "success": False,
        "text": "",
        "error": "AI service unavailable",
    }
    with patch("server.call_claude", new_callable=AsyncMock, return_value=mock_response) as mock:
        yield mock
