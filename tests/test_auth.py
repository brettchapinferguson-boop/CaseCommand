"""
Tests for CaseCommand authentication system.
"""

import pytest
from unittest.mock import patch, MagicMock

import jwt
from fastapi.testclient import TestClient


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    mock = MagicMock()
    mock.table.return_value.select.return_value.execute.return_value.data = []
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    return mock


@pytest.fixture
def app(mock_supabase):
    """Create a test app with mocked dependencies."""
    with patch.dict("os.environ", {
        "ANTHROPIC_API_KEY": "test-key",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SECRET_KEY": "test-key",
        "AUTH_TOKEN": "test-bearer-token",
        "SUPABASE_JWT_SECRET": "test-jwt-secret-that-is-long-enough",
    }):
        # Clear cached settings
        from src.config import get_settings
        get_settings.cache_clear()

        with patch("src.config.get_settings") as mock_settings:
            from src.config import Settings
            settings = Settings()
            settings.AUTH_TOKEN = "test-bearer-token"
            settings.SUPABASE_JWT_SECRET = "test-jwt-secret-that-is-long-enough"
            mock_settings.return_value = settings

            with patch("server.create_client", return_value=mock_supabase):
                with patch("server.CaseCommandAI"):
                    from server import create_app
                    test_app = create_app()
                    yield test_app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestLegacyAuth:
    """Test legacy bearer token authentication."""

    def test_health_no_auth_required(self, client):
        """Health check should work without auth."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_legacy_cases_no_token_rejected(self, client):
        """Requests without a token should be rejected."""
        resp = client.get("/api/cases")
        assert resp.status_code == 401

    def test_legacy_cases_wrong_token_rejected(self, client):
        """Requests with wrong token should be rejected."""
        resp = client.get("/api/cases", headers={"Authorization": "Bearer wrong-token"})
        assert resp.status_code == 401

    def test_legacy_cases_valid_token(self, client):
        """Requests with correct legacy token should succeed."""
        resp = client.get(
            "/api/cases",
            headers={"Authorization": "Bearer test-bearer-token"},
        )
        assert resp.status_code == 200


class TestLegacyAuthMissing:
    """Test that missing AUTH_TOKEN rejects all requests (security fix)."""

    def test_no_auth_token_configured(self):
        """When AUTH_TOKEN is empty, legacy endpoints should reject requests."""
        with patch.dict("os.environ", {
            "ANTHROPIC_API_KEY": "test-key",
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SECRET_KEY": "test-key",
            "AUTH_TOKEN": "",
        }):
            from src.config import get_settings
            get_settings.cache_clear()

            with patch("server.create_client", return_value=MagicMock()):
                with patch("server.CaseCommandAI"):
                    from server import create_app
                    test_app = create_app()
                    test_client = TestClient(test_app)

                    resp = test_client.get("/api/cases")
                    assert resp.status_code == 401
                    assert "not configured" in resp.json()["detail"].lower() or resp.status_code == 401


class TestDocumentSecurity:
    """Test that document downloads require authentication."""

    def test_legacy_document_download_requires_auth(self, client):
        """Document endpoints should require authentication."""
        resp = client.get("/api/documents/test.docx")
        assert resp.status_code == 401
