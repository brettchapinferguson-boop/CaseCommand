"""
FastAPI endpoint tests for server.py.
Supabase and AI clients are fully mocked via conftest fixtures.
"""

import pytest
from unittest.mock import MagicMock, patch

from tests.conftest import SAMPLE_CASE, SAMPLE_CASE_2, make_supabase_mock


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["model"] == "claude-sonnet-4-6"

    def test_health_no_auth_required_by_default(self, client):
        """With AUTH_TOKEN unset, health check needs no token."""
        resp = client.get("/api/health")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/cases
# ---------------------------------------------------------------------------


class TestListCases:
    def test_returns_list(self, client, mock_supabase):
        resp = client.get("/api/cases")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_returns_empty_list(self, client_empty):
        resp = client_empty.get("/api/cases")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_case_fields_present(self, client):
        resp = client.get("/api/cases")
        case = resp.json()[0]
        assert "case_name" in case
        assert "case_type" in case
        assert "status" in case


# ---------------------------------------------------------------------------
# GET /api/cases/{id}
# ---------------------------------------------------------------------------


class TestGetCase:
    def test_returns_case(self, mock_ai):
        """Single-case list returns the first item."""
        import server

        sb = make_supabase_mock(list_data=[SAMPLE_CASE])
        with patch.object(server, "supabase", sb), patch.object(
            server, "ai_client", mock_ai
        ), patch.object(server, "AUTH_TOKEN", ""):
            from fastapi.testclient import TestClient

            c = TestClient(server.app)
            resp = c.get(f"/api/cases/{SAMPLE_CASE['id']}")
        assert resp.status_code == 200
        assert resp.json()["case_name"] == "Smith v. Johnson"

    def test_not_found_returns_404(self, mock_ai):
        import server

        sb = make_supabase_mock(list_data=[])
        with patch.object(server, "supabase", sb), patch.object(
            server, "ai_client", mock_ai
        ), patch.object(server, "AUTH_TOKEN", ""):
            from fastapi.testclient import TestClient

            c = TestClient(server.app)
            resp = c.get("/api/cases/nonexistent-id")
        assert resp.status_code == 404

    def test_404_detail(self, mock_ai):
        import server

        sb = make_supabase_mock(list_data=[])
        with patch.object(server, "supabase", sb), patch.object(
            server, "ai_client", mock_ai
        ), patch.object(server, "AUTH_TOKEN", ""):
            from fastapi.testclient import TestClient

            c = TestClient(server.app)
            resp = c.get("/api/cases/bad-id")
        assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# POST /api/cases
# ---------------------------------------------------------------------------


class TestCreateCase:
    def test_creates_and_returns_case(self, mock_ai):
        import server

        new_case = {**SAMPLE_CASE, "case_name": "New Case", "case_type": "Contract"}
        sb = make_supabase_mock(insert_data=[new_case])
        with patch.object(server, "supabase", sb), patch.object(
            server, "ai_client", mock_ai
        ), patch.object(server, "AUTH_TOKEN", ""):
            from fastapi.testclient import TestClient

            c = TestClient(server.app)
            resp = c.post(
                "/api/cases",
                json={
                    "name": "New Case",
                    "type": "Contract",
                    "client": "Alice",
                    "opposing": "Bob",
                },
            )
        assert resp.status_code == 201
        assert resp.json()["case_name"] == "New Case"

    def test_missing_field_returns_422(self, client):
        resp = client.post("/api/cases", json={"name": "Test"})
        assert resp.status_code == 422

    def test_supabase_insert_called(self, mock_ai):
        import server

        sb = make_supabase_mock(insert_data=[SAMPLE_CASE])
        with patch.object(server, "supabase", sb), patch.object(
            server, "ai_client", mock_ai
        ), patch.object(server, "AUTH_TOKEN", ""):
            from fastapi.testclient import TestClient

            c = TestClient(server.app)
            c.post(
                "/api/cases",
                json={
                    "name": "Test v. Defendant",
                    "type": "PI",
                    "client": "Jane",
                    "opposing": "Corp",
                },
            )
        sb.table.assert_called_with("cases")
        sb.table().insert.assert_called_once()
        inserted = sb.table().insert.call_args[0][0]
        assert inserted["case_name"] == "Test v. Defendant"
        assert inserted["case_type"] == "PI"
        assert inserted["client_name"] == "Jane"
        assert inserted["opposing_party"] == "Corp"


# ---------------------------------------------------------------------------
# POST /api/chat
# ---------------------------------------------------------------------------


class TestChat:
    def test_chat_returns_reply(self, client):
        resp = client.post("/api/chat", json={"message": "What are my deadlines?"})
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data
        assert "model" in data

    def test_chat_calls_ai(self, client, mock_ai):
        client.post("/api/chat", json={"message": "Summarize my cases."})
        mock_ai._call_api.assert_called_once()

    def test_chat_passes_cases_as_context(self, client, mock_ai):
        client.post("/api/chat", json={"message": "Any urgent matters?"})
        call_args = mock_ai._call_api.call_args
        system_prompt = call_args[0][0]
        assert "Smith v. Johnson" in system_prompt

    def test_chat_with_no_cases(self, client_empty, mock_ai):
        resp = client_empty.post("/api/chat", json={"message": "Any cases?"})
        assert resp.status_code == 200
        system_prompt = mock_ai._call_api.call_args[0][0]
        assert "No active cases" in system_prompt

    def test_chat_missing_message_returns_422(self, client):
        resp = client.post("/api/chat", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/deadlines
# ---------------------------------------------------------------------------


class TestDeadlines:
    def test_returns_list(self, client):
        resp = client.get("/api/deadlines")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_queries_active_cases(self, client, mock_supabase):
        client.get("/api/deadlines")
        # Verify .eq("status", "active") was called
        mock_supabase.table().select().eq.assert_called_with("status", "active")

    def test_orders_by_created_at(self, client, mock_supabase):
        client.get("/api/deadlines")
        mock_supabase.table().select().eq().order.assert_called_with(
            "created_at", desc=False
        )

    def test_empty_returns_empty_list(self, client_empty):
        resp = client_empty.get("/api/deadlines")
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


class TestAuth:
    def test_no_token_returns_401_when_auth_enabled(self, client_with_auth):
        resp = client_with_auth.get("/api/cases")
        assert resp.status_code == 401

    def test_wrong_token_returns_401(self, client_with_auth):
        resp = client_with_auth.get(
            "/api/cases", headers={"Authorization": "Bearer wrong-token"}
        )
        assert resp.status_code == 401

    def test_correct_token_returns_200(self, client_with_auth):
        resp = client_with_auth.get(
            "/api/cases", headers={"Authorization": "Bearer test-token"}
        )
        assert resp.status_code == 200

    def test_auth_not_required_when_token_unset(self, client):
        """No Authorization header needed when AUTH_TOKEN is empty."""
        resp = client.get("/api/cases")
        assert resp.status_code == 200

    def test_chat_requires_auth(self, client_with_auth):
        resp = client_with_auth.post("/api/chat", json={"message": "Hello"})
        assert resp.status_code == 401
