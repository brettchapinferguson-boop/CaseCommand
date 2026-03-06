"""
CaseCommand — Contract Review Routes

Review, analyze, and generate contracts (NDAs, protective orders, settlements, etc.).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.auth.jwt import CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/contracts", tags=["contracts"])


class ReviewContractRequest(BaseModel):
    contract_text: str
    contract_type: str  # nda, protective_order, settlement_agreement, employment_agreement
    case_id: str | None = None
    reviewing_for: str = "plaintiff"


class GenerateContractRequest(BaseModel):
    contract_type: str
    parameters: dict


@router.post("/review", status_code=201)
async def review_contract(
    req: ReviewContractRequest,
    user: CurrentUser,
    request: Request,
):
    """Review a contract and get AI analysis with risk flags and redline suggestions."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    from src.contracts.reviewer import ContractReviewer
    reviewer = ContractReviewer(supabase_client=db)

    result = await reviewer.review_contract(
        contract_text=req.contract_text,
        contract_type=req.contract_type,
        case_id=req.case_id,
        org_id=user.org_id,
        reviewing_for=req.reviewing_for,
    )
    return result


@router.post("/generate", status_code=201)
async def generate_contract(
    req: GenerateContractRequest,
    user: CurrentUser,
    request: Request,
):
    """Generate a new contract from parameters."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    from src.contracts.reviewer import ContractReviewer
    reviewer = ContractReviewer(supabase_client=db)

    result = await reviewer.generate_contract(
        contract_type=req.contract_type,
        parameters=req.parameters,
        org_id=user.org_id,
    )
    return result


@router.get("")
def list_reviews(
    user: CurrentUser,
    request: Request,
    case_id: str | None = None,
):
    """List contract reviews for the organization."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase
    query = (
        db.table("contract_reviews")
        .select("id, contract_type, title, overall_risk, recommendation, status, created_at")
        .eq("org_id", user.org_id)
        .order("created_at", desc=True)
    )
    if case_id:
        query = query.eq("case_id", case_id)

    result = query.execute()
    return result.data or []


@router.get("/{review_id}")
def get_review(
    review_id: str,
    user: CurrentUser,
    request: Request,
):
    """Get full contract review details."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase
    result = (
        db.table("contract_reviews")
        .select("*")
        .eq("id", review_id)
        .eq("org_id", user.org_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Review not found")
    return result.data[0]
