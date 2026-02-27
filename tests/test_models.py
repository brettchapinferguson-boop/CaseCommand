"""
Tests for Pydantic request/response models in server.py.
"""

import pytest
from pydantic import ValidationError


# Import models from server (env vars set in conftest.py)
def get_models():
    from server import CaseCreate, ChatRequest, DiscoveryRequest, SettlementRequest

    return CaseCreate, ChatRequest, DiscoveryRequest, SettlementRequest


class TestCaseCreate:
    def test_valid_case(self):
        CaseCreate, *_ = get_models()
        case = CaseCreate(name="Smith v. Jones", type="PI", client="Smith", opposing="Jones")
        assert case.name == "Smith v. Jones"
        assert case.type == "PI"
        assert case.client == "Smith"
        assert case.opposing == "Jones"

    def test_missing_name(self):
        CaseCreate, *_ = get_models()
        with pytest.raises(ValidationError):
            CaseCreate(type="PI", client="Smith", opposing="Jones")

    def test_missing_type(self):
        CaseCreate, *_ = get_models()
        with pytest.raises(ValidationError):
            CaseCreate(name="Smith v. Jones", client="Smith", opposing="Jones")

    def test_missing_client(self):
        CaseCreate, *_ = get_models()
        with pytest.raises(ValidationError):
            CaseCreate(name="Smith v. Jones", type="PI", opposing="Jones")

    def test_missing_opposing(self):
        CaseCreate, *_ = get_models()
        with pytest.raises(ValidationError):
            CaseCreate(name="Smith v. Jones", type="PI", client="Smith")

    def test_all_fields_required(self):
        CaseCreate, *_ = get_models()
        with pytest.raises(ValidationError):
            CaseCreate()


class TestChatRequest:
    def test_valid_message(self):
        _, ChatRequest, *_ = get_models()
        req = ChatRequest(message="What are my urgent deadlines?")
        assert req.message == "What are my urgent deadlines?"

    def test_empty_message_allowed(self):
        _, ChatRequest, *_ = get_models()
        req = ChatRequest(message="")
        assert req.message == ""

    def test_missing_message(self):
        _, ChatRequest, *_ = get_models()
        with pytest.raises(ValidationError):
            ChatRequest()


class TestDiscoveryRequest:
    def test_valid_request(self):
        _, _, DiscoveryRequest, _ = get_models()
        req = DiscoveryRequest(
            case_name="Smith v. Jones",
            discovery_type="interrogatories",
            requests_and_responses=[
                {"number": 1, "request": "State your name.", "response": "John Smith."}
            ],
        )
        assert req.case_name == "Smith v. Jones"
        assert req.discovery_type == "interrogatories"
        assert len(req.requests_and_responses) == 1

    def test_empty_responses_list(self):
        _, _, DiscoveryRequest, _ = get_models()
        req = DiscoveryRequest(
            case_name="Smith v. Jones",
            discovery_type="RFP",
            requests_and_responses=[],
        )
        assert req.requests_and_responses == []

    def test_missing_case_name(self):
        _, _, DiscoveryRequest, _ = get_models()
        with pytest.raises(ValidationError):
            DiscoveryRequest(discovery_type="interrogatories", requests_and_responses=[])


class TestSettlementRequest:
    def test_valid_request(self):
        _, _, _, SettlementRequest = get_models()
        req = SettlementRequest(
            case_name="Smith v. Jones",
            trigger_point="Post-Discovery",
            valuation_data={"low": 50000, "mid": 150000, "high": 300000},
            recommendation_data={"liability_strength": "strong"},
        )
        assert req.trigger_point == "Post-Discovery"
        assert req.valuation_data["mid"] == 150000

    def test_missing_trigger_point(self):
        _, _, _, SettlementRequest = get_models()
        with pytest.raises(ValidationError):
            SettlementRequest(
                case_name="Smith v. Jones",
                valuation_data={},
                recommendation_data={},
            )

    def test_empty_dicts_allowed(self):
        _, _, _, SettlementRequest = get_models()
        req = SettlementRequest(
            case_name="Smith v. Jones",
            trigger_point="Pre-Trial",
            valuation_data={},
            recommendation_data={},
        )
        assert req.valuation_data == {}
