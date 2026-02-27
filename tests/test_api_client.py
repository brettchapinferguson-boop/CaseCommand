"""
Unit tests for CaseCommandAI in src/api_client.py.
All httpx calls are mocked — no live API calls.
"""

import os
import json
import pytest
from unittest.mock import MagicMock, patch

from src.api_client import CaseCommandAI


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_httpx_response(text="AI result", model="claude-sonnet-4-6"):
    response = MagicMock()
    response.json.return_value = {
        "content": [{"text": text}],
        "model": model,
        "usage": {"input_tokens": 50, "output_tokens": 100},
    }
    response.raise_for_status = MagicMock()
    return response


def patch_httpx(response):
    """Context manager that patches httpx.Client to return a given response."""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = response
    return patch("src.api_client.httpx.Client", return_value=mock_client)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ai():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"}):
        return CaseCommandAI()


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestInit:
    def test_missing_api_key_raises(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                CaseCommandAI()

    def test_headers_set(self, ai):
        assert "x-api-key" in ai._headers
        assert ai._headers["anthropic-version"] == "2023-06-01"
        assert ai._headers["content-type"] == "application/json"

    def test_model_constant(self, ai):
        assert ai.MODEL == "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# _call_api
# ---------------------------------------------------------------------------


class TestCallApi:
    def test_returns_text_model_usage(self, ai):
        resp = make_httpx_response(text="Hello world")
        with patch_httpx(resp):
            result = ai._call_api("system", "user message")
        assert result["text"] == "Hello world"
        assert result["model"] == "claude-sonnet-4-6"
        assert "usage" in result

    def test_posts_correct_payload(self, ai):
        resp = make_httpx_response()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = resp

        with patch("src.api_client.httpx.Client", return_value=mock_client):
            ai._call_api("sys prompt", "user msg", max_tokens=512)

        call_kwargs = mock_client.post.call_args
        payload = call_kwargs[1]["json"]
        assert payload["model"] == "claude-sonnet-4-6"
        assert payload["max_tokens"] == 512
        assert payload["system"] == "sys prompt"
        assert payload["messages"][0]["content"] == "user msg"

    def test_raises_on_http_error(self, ai):
        import httpx

        resp = MagicMock()
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=MagicMock()
        )
        with patch_httpx(resp):
            with pytest.raises(httpx.HTTPStatusError):
                ai._call_api("system", "message")


# ---------------------------------------------------------------------------
# analyze_discovery_responses
# ---------------------------------------------------------------------------


class TestAnalyzeDiscovery:
    def test_returns_analysis(self, ai):
        resp = make_httpx_response(text="Key findings: ...")
        items = [{"number": 1, "request": "State your name.", "response": "John."}]
        with patch_httpx(resp):
            result = ai.analyze_discovery_responses("Smith v. Jones", "interrogatories", items)
        assert result["text"] == "Key findings: ..."

    def test_includes_case_name_in_prompt(self, ai):
        resp = make_httpx_response()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = resp

        with patch("src.api_client.httpx.Client", return_value=mock_client):
            ai.analyze_discovery_responses(
                "Doe v. Corp",
                "RFP",
                [{"number": 1, "request": "Produce docs.", "response": "Objection."}],
            )

        payload = mock_client.post.call_args[1]["json"]
        assert "Doe v. Corp" in payload["messages"][0]["content"]

    def test_empty_items_list(self, ai):
        resp = make_httpx_response(text="No items to analyze.")
        with patch_httpx(resp):
            result = ai.analyze_discovery_responses("Case", "interrogatories", [])
        assert "text" in result

    def test_multiple_items_formatted(self, ai):
        resp = make_httpx_response()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = resp

        items = [
            {"number": 1, "request": "Q1", "response": "A1"},
            {"number": 2, "request": "Q2", "response": "A2"},
        ]
        with patch("src.api_client.httpx.Client", return_value=mock_client):
            ai.analyze_discovery_responses("Case", "interrogatories", items)

        payload = mock_client.post.call_args[1]["json"]
        content = payload["messages"][0]["content"]
        assert "Request 1" in content
        assert "Request 2" in content


# ---------------------------------------------------------------------------
# generate_examination_outline
# ---------------------------------------------------------------------------


class TestExaminationOutline:
    def test_returns_outline(self, ai):
        resp = make_httpx_response(text="I. Opening\nII. Liability")
        with patch_httpx(resp):
            result = ai.generate_examination_outline(
                "Smith v. Jones",
                "John Smith",
                "plaintiff",
                "direct",
                ["Medical records", "Police report"],
                "Defendant was negligent",
            )
        assert "Opening" in result["text"]

    def test_cross_exam_type_in_prompt(self, ai):
        resp = make_httpx_response()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = resp

        with patch("src.api_client.httpx.Client", return_value=mock_client):
            ai.generate_examination_outline(
                "Case", "Witness", "expert", "cross", [], "Theory"
            )

        payload = mock_client.post.call_args[1]["json"]
        assert "CROSS" in payload["messages"][0]["content"]

    def test_no_documents_handled(self, ai):
        resp = make_httpx_response(text="Outline here")
        with patch_httpx(resp):
            result = ai.generate_examination_outline(
                "Case", "Witness", "defendant", "direct", [], "Theory"
            )
        assert result["text"] == "Outline here"


# ---------------------------------------------------------------------------
# generate_settlement_narrative
# ---------------------------------------------------------------------------


class TestSettlementNarrative:
    def test_returns_narrative(self, ai):
        resp = make_httpx_response(text="Settlement recommendation: accept $150k")
        with patch_httpx(resp):
            result = ai.generate_settlement_narrative(
                "Smith v. Jones",
                "Post-Discovery",
                {"low": 50000, "mid": 150000, "high": 300000},
                {"liability_strength": "strong"},
            )
        assert "150k" in result["text"]

    def test_valuation_formatted(self, ai):
        resp = make_httpx_response()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = resp

        with patch("src.api_client.httpx.Client", return_value=mock_client):
            ai.generate_settlement_narrative(
                "Case", "Pre-Trial", {"low": 1000, "mid": 5000, "high": 10000}, {}
            )

        payload = mock_client.post.call_args[1]["json"]
        content = payload["messages"][0]["content"]
        assert "$1,000" in content
        assert "$5,000" in content
        assert "$10,000" in content
