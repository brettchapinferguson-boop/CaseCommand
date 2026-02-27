"""
Tests for the POST /api/discovery endpoint (discovery analysis).
"""

import pytest
from unittest.mock import MagicMock, patch

from tests.conftest import SAMPLE_CASE, make_supabase_mock, AI_RESPONSE


DISCOVERY_PAYLOAD = {
    "case_name": "Smith v. Johnson",
    "discovery_type": "interrogatories",
    "requests_and_responses": [
        {"number": 1, "request": "State your full name.", "response": "John Smith."},
        {
            "number": 2,
            "request": "Describe the incident.",
            "response": "I don't recall.",
        },
    ],
}


@pytest.fixture
def discovery_client(mock_ai):
    import server

    sb = make_supabase_mock(list_data=[SAMPLE_CASE])
    with patch.object(server, "supabase", sb), patch.object(
        server, "ai_client", mock_ai
    ), patch.object(server, "AUTH_TOKEN", ""):
        from fastapi.testclient import TestClient

        yield TestClient(server.app)


class TestDiscoveryEndpoint:
    def test_returns_200(self, discovery_client):
        resp = discovery_client.post("/api/discovery", json=DISCOVERY_PAYLOAD)
        assert resp.status_code == 200

    def test_response_has_result_and_model(self, discovery_client):
        resp = discovery_client.post("/api/discovery", json=DISCOVERY_PAYLOAD)
        data = resp.json()
        assert "result" in data
        assert "model" in data

    def test_result_contains_ai_text(self, discovery_client):
        resp = discovery_client.post("/api/discovery", json=DISCOVERY_PAYLOAD)
        assert resp.json()["result"] == AI_RESPONSE["text"]

    def test_calls_analyze_discovery_responses(self, discovery_client, mock_ai):
        discovery_client.post("/api/discovery", json=DISCOVERY_PAYLOAD)
        mock_ai.analyze_discovery_responses.assert_called_once_with(
            case_name="Smith v. Johnson",
            discovery_type="interrogatories",
            requests_and_responses=DISCOVERY_PAYLOAD["requests_and_responses"],
        )

    def test_empty_responses_list(self, discovery_client):
        payload = {**DISCOVERY_PAYLOAD, "requests_and_responses": []}
        resp = discovery_client.post("/api/discovery", json=payload)
        assert resp.status_code == 200

    def test_missing_case_name_returns_422(self, discovery_client):
        payload = {
            "discovery_type": "interrogatories",
            "requests_and_responses": [],
        }
        resp = discovery_client.post("/api/discovery", json=payload)
        assert resp.status_code == 422
