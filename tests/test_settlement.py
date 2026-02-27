"""
Tests for the POST /api/settlement endpoint (settlement narrative generation).
"""

import pytest
from unittest.mock import MagicMock, patch

from tests.conftest import SAMPLE_CASE, make_supabase_mock, AI_RESPONSE


SETTLEMENT_PAYLOAD = {
    "case_name": "Smith v. Johnson",
    "trigger_point": "Post-Discovery",
    "valuation_data": {"low": 50000, "mid": 150000, "high": 300000},
    "recommendation_data": {
        "liability_strength": "strong",
        "damages_proven": True,
        "trial_risk": "moderate",
    },
}


@pytest.fixture
def settlement_client(mock_ai):
    import server

    sb = make_supabase_mock(list_data=[SAMPLE_CASE])
    with patch.object(server, "supabase", sb), patch.object(
        server, "ai_client", mock_ai
    ), patch.object(server, "AUTH_TOKEN", ""):
        from fastapi.testclient import TestClient

        yield TestClient(server.app)


class TestSettlementEndpoint:
    def test_returns_200(self, settlement_client):
        resp = settlement_client.post("/api/settlement", json=SETTLEMENT_PAYLOAD)
        assert resp.status_code == 200

    def test_response_has_result_and_model(self, settlement_client):
        resp = settlement_client.post("/api/settlement", json=SETTLEMENT_PAYLOAD)
        data = resp.json()
        assert "result" in data
        assert "model" in data

    def test_result_contains_ai_text(self, settlement_client):
        resp = settlement_client.post("/api/settlement", json=SETTLEMENT_PAYLOAD)
        assert resp.json()["result"] == AI_RESPONSE["text"]

    def test_calls_generate_settlement_narrative(self, settlement_client, mock_ai):
        settlement_client.post("/api/settlement", json=SETTLEMENT_PAYLOAD)
        mock_ai.generate_settlement_narrative.assert_called_once_with(
            case_name="Smith v. Johnson",
            trigger_point="Post-Discovery",
            valuation_data={"low": 50000, "mid": 150000, "high": 300000},
            recommendation_data=SETTLEMENT_PAYLOAD["recommendation_data"],
        )

    def test_empty_recommendation_data(self, settlement_client):
        payload = {**SETTLEMENT_PAYLOAD, "recommendation_data": {}}
        resp = settlement_client.post("/api/settlement", json=payload)
        assert resp.status_code == 200

    def test_missing_trigger_point_returns_422(self, settlement_client):
        payload = {
            "case_name": "Smith v. Johnson",
            "valuation_data": {"low": 0, "mid": 0, "high": 0},
            "recommendation_data": {},
        }
        resp = settlement_client.post("/api/settlement", json=payload)
        assert resp.status_code == 422
