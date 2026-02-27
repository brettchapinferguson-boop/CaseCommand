"""
Shared fixtures for CaseCommand test suite.
All Supabase and AI client calls are mocked — no live API calls needed.
"""

import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Set env vars before server is imported so module-level init succeeds
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key")


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_CASE = {
    "id": "11111111-1111-1111-1111-111111111111",
    "case_name": "Smith v. Johnson",
    "case_type": "PI",
    "client_name": "Alice Smith",
    "opposing_party": "Bob Johnson",
    "status": "active",
    "case_number": "2024-CV-001",
    "notes": None,
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T10:00:00Z",
    "user_id": None,
}

SAMPLE_CASE_2 = {
    "id": "22222222-2222-2222-2222-222222222222",
    "case_name": "Doe v. Corp",
    "case_type": "Contract",
    "client_name": "Jane Doe",
    "opposing_party": "Big Corp",
    "status": "active",
    "case_number": "2024-CV-002",
    "notes": None,
    "created_at": "2024-01-20T10:00:00Z",
    "updated_at": "2024-01-20T10:00:00Z",
    "user_id": None,
}

AI_RESPONSE = {
    "text": "Here is the AI analysis result.",
    "model": "claude-sonnet-4-6",
    "usage": {"input_tokens": 50, "output_tokens": 100},
}


# ---------------------------------------------------------------------------
# Supabase mock helpers
# ---------------------------------------------------------------------------


def _make_execute_result(data):
    result = MagicMock()
    result.data = data
    return result


def make_supabase_mock(
    list_data=None,
    single_data=None,
    insert_data=None,
):
    """
    Build a MagicMock Supabase client supporting method chaining:
      .table().select("*").execute()
      .table().select("*").eq(...).execute()
      .table().select("*").eq(...).order(...).execute()
      .table().insert(...).execute()
    """
    if list_data is None:
        list_data = []
    if insert_data is None:
        insert_data = [SAMPLE_CASE]

    mock = MagicMock()

    # --- query builder (returned by .select()) ---
    query = MagicMock()
    query.execute.return_value = _make_execute_result(list_data)
    query.eq.return_value = query          # chaining: .eq().eq(), .eq().order()
    query.order.return_value = query       # chaining

    # --- insert builder (returned by .insert()) ---
    insert_query = MagicMock()
    insert_query.execute.return_value = _make_execute_result(insert_data)

    # --- table mock ---
    table = MagicMock()
    table.select.return_value = query
    table.insert.return_value = insert_query

    mock.table.return_value = table
    return mock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_supabase():
    return make_supabase_mock(list_data=[SAMPLE_CASE, SAMPLE_CASE_2])


@pytest.fixture
def mock_supabase_empty():
    return make_supabase_mock(list_data=[])


@pytest.fixture
def mock_supabase_single():
    """Supabase mock that returns a single case for list queries."""
    return make_supabase_mock(list_data=[SAMPLE_CASE])


@pytest.fixture
def mock_ai():
    mock = MagicMock()
    mock._call_api.return_value = AI_RESPONSE.copy()
    mock.analyze_discovery_responses.return_value = AI_RESPONSE.copy()
    mock.generate_settlement_narrative.return_value = AI_RESPONSE.copy()
    mock.generate_examination_outline.return_value = AI_RESPONSE.copy()
    return mock


@pytest.fixture
def client(mock_supabase, mock_ai):
    """Test client with Supabase and AI mocked."""
    import server

    with patch.object(server, "supabase", mock_supabase), patch.object(
        server, "ai_client", mock_ai
    ), patch.object(server, "AUTH_TOKEN", ""):
        yield TestClient(server.app)


@pytest.fixture
def client_with_auth(mock_supabase, mock_ai):
    """Test client with AUTH_TOKEN='test-token' enabled."""
    import server

    with patch.object(server, "supabase", mock_supabase), patch.object(
        server, "ai_client", mock_ai
    ), patch.object(server, "AUTH_TOKEN", "test-token"):
        yield TestClient(server.app, raise_server_exceptions=True)


@pytest.fixture
def client_empty(mock_supabase_empty, mock_ai):
    """Test client backed by an empty Supabase (no cases)."""
    import server

    with patch.object(server, "supabase", mock_supabase_empty), patch.object(
        server, "ai_client", mock_ai
    ), patch.object(server, "AUTH_TOKEN", ""):
        yield TestClient(server.app)
