"""
CaseCommand — Discovery Routes

Generate, manage, and analyze discovery sets.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.auth.jwt import CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])


class GenerateDiscoveryRequest(BaseModel):
    case_id: str
    set_type: str  # form_interrogatories, special_interrogatories, rfp, rfa, deposition_notice, subpoena_duces_tecum
    direction: str = "propounding"
    target_elements: list[str] = []
    additional_context: str = ""


class AnalyzeResponsesRequest(BaseModel):
    set_id: str
    responses: list[dict]  # [{item_number, request_text, response_text}]


class InjectInfoRequest(BaseModel):
    case_id: str
    new_facts: list[str]


@router.post("/generate", status_code=201)
async def generate_discovery(
    req: GenerateDiscoveryRequest,
    user: CurrentUser,
    request: Request,
):
    """Generate a discovery set for a case."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    from src.discovery.generator import DiscoveryGenerator
    gen = DiscoveryGenerator(supabase_client=db)

    result = await gen.generate_discovery_set(
        case_id=req.case_id,
        org_id=user.org_id,
        set_type=req.set_type,
        direction=req.direction,
        target_elements=req.target_elements,
        additional_context=req.additional_context,
    )

    return result


@router.post("/offensive-package", status_code=201)
async def generate_offensive_package(
    case_id: str,
    user: CurrentUser,
    request: Request,
):
    """Generate the complete offensive discovery package (FI, SI, RFP, RFA)."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    from src.discovery.generator import DiscoveryGenerator
    gen = DiscoveryGenerator(supabase_client=db)

    result = await gen.generate_offensive_package(case_id=case_id, org_id=user.org_id)
    return result


@router.post("/analyze-responses")
async def analyze_responses(
    req: AnalyzeResponsesRequest,
    user: CurrentUser,
    request: Request,
):
    """Analyze discovery responses from opposing party."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    from src.discovery.generator import DiscoveryGenerator
    gen = DiscoveryGenerator(supabase_client=db)

    result = await gen.analyze_responses(set_id=req.set_id, responses=req.responses)
    return result


@router.post("/inject")
async def inject_new_information(
    req: InjectInfoRequest,
    user: CurrentUser,
    request: Request,
):
    """Inject new information and auto-generate supplemental discovery if warranted."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    from src.discovery.generator import DiscoveryGenerator
    gen = DiscoveryGenerator(supabase_client=db)

    result = await gen.inject_new_information(
        case_id=req.case_id,
        org_id=user.org_id,
        new_facts=req.new_facts,
    )
    return result


@router.get("/sets/{case_id}")
def list_discovery_sets(
    case_id: str,
    user: CurrentUser,
    request: Request,
):
    """List all discovery sets for a case."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase
    result = (
        db.table("discovery_sets")
        .select("*")
        .eq("case_id", case_id)
        .eq("org_id", user.org_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


@router.get("/items/{set_id}")
def list_discovery_items(
    set_id: str,
    user: CurrentUser,
    request: Request,
):
    """List all items in a discovery set."""
    db = request.app.state.supabase
    result = (
        db.table("discovery_items")
        .select("*")
        .eq("set_id", set_id)
        .order("item_number")
        .execute()
    )
    return result.data or []
