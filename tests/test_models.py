"""
Tests for Pydantic request/response models.
"""

import pytest
from pydantic import ValidationError

from src.models.requests import (
    ChatRequest,
    CaseCreate,
    SignupRequest,
    LoginRequest,
    FirmConfigUpdate,
    CreateCheckoutRequest,
)


class TestChatRequest:
    def test_valid_chat(self):
        req = ChatRequest(message="Hello Casey")
        assert req.message == "Hello Casey"
        assert req.session_id is None

    def test_chat_with_session(self):
        req = ChatRequest(message="Hello", session_id="abc-123")
        assert req.session_id == "abc-123"


class TestCaseCreate:
    def test_valid_case(self):
        case = CaseCreate(name="Smith v. Jones", type="PI", client="Smith", opposing="Jones")
        assert case.name == "Smith v. Jones"


class TestSignupRequest:
    def test_valid_signup(self):
        req = SignupRequest(
            email="brett@example.com",
            password="securepass123",
            firm_name="Law Office of Brett Ferguson",
            attorney_name="Brett Ferguson",
            bar_number="281519",
        )
        assert req.jurisdiction == "California"

    def test_short_password_rejected(self):
        with pytest.raises(ValidationError):
            SignupRequest(
                email="brett@example.com",
                password="short",
                firm_name="Test Firm",
                attorney_name="Test",
            )


class TestFirmConfigUpdate:
    def test_partial_update(self):
        update = FirmConfigUpdate(firm_name="New Firm Name")
        assert update.firm_name == "New Firm Name"
        assert update.attorney_name is None

    def test_empty_update(self):
        update = FirmConfigUpdate()
        data = {k: v for k, v in update.model_dump().items() if v is not None}
        assert len(data) == 0
