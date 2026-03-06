"""
CaseCommand — Request/Response Pydantic Models

Centralized schemas for all API endpoints.
"""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    current_case_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    model: str
    document: dict | None = None
    session_id: str | None = None


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

class CaseCreate(BaseModel):
    name: str
    type: str
    client: str
    opposing: str


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------

class AIRequest(BaseModel):
    system: str
    message: str
    max_tokens: int = 4096
    temperature: float = 0.3


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

class DiscoveryRequest(BaseModel):
    case_name: str
    discovery_type: str
    requests_and_responses: list


# ---------------------------------------------------------------------------
# Settlement
# ---------------------------------------------------------------------------

class SettlementRequest(BaseModel):
    case_name: str
    trigger_point: str
    valuation_data: dict
    recommendation_data: dict


# ---------------------------------------------------------------------------
# Outline
# ---------------------------------------------------------------------------

class OutlineRequest(BaseModel):
    case_name: str
    witness_name: str
    witness_role: str = "witness"
    exam_type: str = "cross"
    case_theory: str = ""
    documents: list = []


# ---------------------------------------------------------------------------
# Agent Lab
# ---------------------------------------------------------------------------

class AgentOutputUpdate(BaseModel):
    status: str  # "applied" or "dismissed"


# ---------------------------------------------------------------------------
# Auth / Onboarding
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    firm_name: str
    attorney_name: str
    bar_number: str = ""
    jurisdiction: str = "California"


class LoginRequest(BaseModel):
    email: str
    password: str


class FirmConfigUpdate(BaseModel):
    firm_name: str | None = None
    attorney_name: str | None = None
    bar_number: str | None = None
    jurisdiction: str | None = None
    firm_address: str | None = None
    firm_phone: str | None = None
    court_formatting: str | None = None


# ---------------------------------------------------------------------------
# Billing
# ---------------------------------------------------------------------------

class CreateCheckoutRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str


class UsageResponse(BaseModel):
    org_id: str
    period: str
    ai_calls_used: int
    ai_calls_limit: int
    documents_generated: int
