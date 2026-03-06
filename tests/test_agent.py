"""
Tests for the agent engine.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.agent import _build_system_prompt, _execute_tool, SOUL


class TestBuildSystemPrompt:
    def test_default_prompt(self):
        """Without firm config, returns the base SOUL."""
        result = _build_system_prompt(None)
        assert result == SOUL

    def test_with_firm_config(self):
        """With firm config, appends firm identity section."""
        config = {
            "firm_name": "Test Law Group",
            "attorney_name": "Jane Doe",
            "bar_number": "123456",
            "jurisdiction": "New York",
        }
        result = _build_system_prompt(config)
        assert "Test Law Group" in result
        assert "Jane Doe" in result
        assert "123456" in result
        assert "New York" in result

    def test_firm_config_replaces_default_identity(self):
        """Firm config should replace hardcoded Brett Ferguson references."""
        config = {
            "firm_name": "Smith & Associates",
            "attorney_name": "John Smith",
            "bar_number": "999999",
        }
        result = _build_system_prompt(config)
        assert "Firm Identity" in result


class TestExecuteTool:
    @pytest.mark.asyncio
    async def test_generate_legal_document(self):
        result = await _execute_tool(
            "generate_legal_document",
            {"title": "Test Doc", "body": "Body"},
            {},
        )
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_lookup_case_no_db(self):
        result = await _execute_tool("lookup_case", {"query": "test"}, {})
        assert result["status"] == "error"
        assert "Database" in result["message"]

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        result = await _execute_tool("nonexistent_tool", {}, {})
        assert result["status"] == "error"
        assert "Unknown" in result["message"]

    @pytest.mark.asyncio
    async def test_lookup_case_with_org_scope(self):
        """Lookup should scope to org_id when provided."""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.execute.return_value.data = [
            {"case_name": "Smith v. Jones", "client_name": "Smith", "case_type": "PI"}
        ]
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value = mock_query

        result = await _execute_tool(
            "lookup_case",
            {"query": "smith"},
            {"supabase": mock_db, "org_id": "org-123"},
        )
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_create_case_includes_org_id(self):
        """Create case should include org_id when provided."""
        mock_db = MagicMock()
        mock_db.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "case-1", "case_name": "Test", "org_id": "org-123"}
        ]

        result = await _execute_tool(
            "create_case",
            {
                "case_name": "Test v. Case",
                "case_type": "PI",
                "client_name": "Test",
                "opposing_party": "Case",
            },
            {"supabase": mock_db, "org_id": "org-123", "user_id": "user-1"},
        )
        assert result["status"] == "success"
        # Verify org_id was passed to the insert
        call_args = mock_db.table.return_value.insert.call_args[0][0]
        assert call_args["org_id"] == "org-123"
