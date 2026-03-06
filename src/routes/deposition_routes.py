"""
CaseCommand — Deposition Routes

Depo prep, practice sessions, and transcript analysis.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.auth.jwt import CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/depositions", tags=["depositions"])


class PrepOutlineRequest(BaseModel):
    case_id: str
    deponent_name: str
    deponent_role: str
    depo_type: str = "taking"  # taking or defending
    areas_of_inquiry: list[str] = []


class PracticeRequest(BaseModel):
    prep_id: str
    deponent_answer: str
    question_area: str | None = None


class TranscriptAnalysisRequest(BaseModel):
    case_id: str
    prep_id: str
    transcript_text: str


@router.post("/prep", status_code=201)
async def generate_prep(
    req: PrepOutlineRequest,
    user: CurrentUser,
    request: Request,
):
    """Generate deposition preparation outline."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    from src.deposition.prep import DepositionPrep
    prep = DepositionPrep(supabase_client=db)

    result = await prep.generate_outline(
        case_id=req.case_id,
        org_id=user.org_id,
        deponent_name=req.deponent_name,
        deponent_role=req.deponent_role,
        depo_type=req.depo_type,
        areas_of_inquiry=req.areas_of_inquiry,
    )
    return result


@router.post("/practice")
async def practice_session(
    req: PracticeRequest,
    user: CurrentUser,
    request: Request,
):
    """Run a deposition practice session exchange."""
    db = request.app.state.supabase

    from src.deposition.prep import DepositionPrep
    prep = DepositionPrep(supabase_client=db)

    result = await prep.practice_session(
        prep_id=req.prep_id,
        deponent_answer=req.deponent_answer,
        question_area=req.question_area,
    )
    return result


@router.post("/analyze-transcript")
async def analyze_transcript(
    req: TranscriptAnalysisRequest,
    user: CurrentUser,
    request: Request,
):
    """Analyze a deposition transcript for admissions and impeachment material."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    from src.deposition.prep import DepositionPrep
    prep = DepositionPrep(supabase_client=db)

    result = await prep.analyze_transcript(
        case_id=req.case_id,
        org_id=user.org_id,
        prep_id=req.prep_id,
        transcript_text=req.transcript_text,
    )
    return result


@router.get("/{case_id}")
def list_deposition_preps(
    case_id: str,
    user: CurrentUser,
    request: Request,
):
    """List all deposition preps for a case."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase
    result = (
        db.table("deposition_preps")
        .select("id, deponent_name, deponent_role, deposition_date, status, created_at")
        .eq("case_id", case_id)
        .eq("org_id", user.org_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []
