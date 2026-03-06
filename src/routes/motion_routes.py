"""
CaseCommand — Motion & Pleading Routes

Draft, manage, and get oversight analysis for motions and pleadings.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.auth.jwt import CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/motions", tags=["motions"])


class DraftMotionRequest(BaseModel):
    case_id: str
    motion_type: str
    filing_party: str = "plaintiff"
    additional_context: str = ""
    target_issues: list[str] = []


class GenerateComplaintRequest(BaseModel):
    case_id: str


@router.post("/draft", status_code=201)
async def draft_motion(
    req: DraftMotionRequest,
    user: CurrentUser,
    request: Request,
):
    """Draft a motion or pleading."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    from src.motions.engine import MotionEngine
    engine = MotionEngine(supabase_client=db)

    result = await engine.draft_motion(
        case_id=req.case_id,
        org_id=user.org_id,
        motion_type=req.motion_type,
        filing_party=req.filing_party,
        additional_context=req.additional_context,
        target_issues=req.target_issues,
    )
    return result


@router.post("/complaint", status_code=201)
async def generate_complaint(
    req: GenerateComplaintRequest,
    user: CurrentUser,
    request: Request,
):
    """Generate a complaint from intake/case data."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    from src.motions.engine import MotionEngine
    engine = MotionEngine(supabase_client=db)

    result = await engine.generate_complaint(case_id=req.case_id, org_id=user.org_id)
    return result


@router.post("/oversight/{case_id}")
async def oversight_analysis(
    case_id: str,
    user: CurrentUser,
    request: Request,
):
    """Run the oversight agent to identify motion opportunities and risks."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    from src.motions.engine import MotionEngine
    engine = MotionEngine(supabase_client=db)

    result = await engine.oversight_analysis(case_id=case_id, org_id=user.org_id)
    return result


@router.get("/{case_id}")
def list_motions(
    case_id: str,
    user: CurrentUser,
    request: Request,
):
    """List all motions for a case."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase
    result = (
        db.table("motions")
        .select("*")
        .eq("case_id", case_id)
        .eq("org_id", user.org_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


@router.get("/detail/{motion_id}")
def get_motion(
    motion_id: str,
    user: CurrentUser,
    request: Request,
):
    """Get full motion details."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase
    result = (
        db.table("motions")
        .select("*")
        .eq("id", motion_id)
        .eq("org_id", user.org_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Motion not found")
    return result.data[0]
