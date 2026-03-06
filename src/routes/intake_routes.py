"""
CaseCommand — Intake Routes

Client intake submission, AI analysis, scorecard viewing, and case creation.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.auth.jwt import CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/intake", tags=["intake"])


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class IntakeSubmission(BaseModel):
    """Client intake form submission."""
    client_first_name: str
    client_last_name: str
    client_email: str | None = None
    client_phone: str | None = None
    client_address: str | None = None

    # Employment details
    employer_name: str | None = None
    employer_address: str | None = None
    job_title: str | None = None
    hire_date: str | None = None
    termination_date: str | None = None
    employment_status: str | None = None
    annual_salary: float | None = None
    supervisor_name: str | None = None

    # Incident
    incident_date: str | None = None
    incident_description: str | None = None
    protected_class: list[str] = []
    adverse_actions: list[str] = []
    witnesses: list[dict] = []
    prior_complaints: list[dict] = []

    # Administrative exhaustion
    dfeh_filed: bool = False
    dfeh_filing_date: str | None = None
    dfeh_case_number: str | None = None
    right_to_sue: bool = False
    right_to_sue_date: str | None = None

    # Conversation transcript (from voice intake)
    transcript: str | None = None
    source_channel: str = "web"


class GreenlightRequest(BaseModel):
    """Request to accept an intake and create a case."""
    pass  # No additional fields needed — intake_id is in URL


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/submit", status_code=201)
async def submit_intake(
    submission: IntakeSubmission,
    user: CurrentUser,
    request: Request,
):
    """
    Submit a client intake for AI analysis.
    Returns a full viability scorecard with prima facie element analysis.
    """
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    from src.intake.engine import IntakeAnalyzer
    analyzer = IntakeAnalyzer(supabase_client=db)

    intake_data = submission.model_dump()

    # Run AI analysis
    analysis = await analyzer.analyze_intake(intake_data)

    # Save to database
    save_result = await analyzer.save_intake(
        intake_data=intake_data,
        analysis=analysis,
        org_id=user.org_id,
        user_id=user.user_id,
    )

    return {
        "intake_id": save_result.get("intake_id"),
        "status": "screening",
        "analysis": analysis,
    }


@router.get("")
def list_intakes(
    user: CurrentUser,
    request: Request,
    status: str | None = None,
):
    """List all intakes for the organization."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase
    query = (
        db.table("client_intakes")
        .select("id, client_first_name, client_last_name, employer_name, overall_score, recommended_action, status, case_id, created_at")
        .eq("org_id", user.org_id)
        .order("created_at", desc=True)
    )
    if status:
        query = query.eq("status", status)

    result = query.execute()
    return result.data or []


@router.get("/{intake_id}")
def get_intake(intake_id: str, user: CurrentUser, request: Request):
    """Get full intake details with causes of action scorecards."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    # Get intake
    intake = db.table("client_intakes").select("*").eq("id", intake_id).eq("org_id", user.org_id).execute()
    if not intake.data:
        raise HTTPException(status_code=404, detail="Intake not found")

    # Get causes of action
    coa = db.table("intake_causes_of_action").select("*").eq("intake_id", intake_id).execute()

    return {
        "intake": intake.data[0],
        "causes_of_action": coa.data or [],
    }


@router.post("/{intake_id}/greenlight", status_code=201)
async def greenlight_intake(
    intake_id: str,
    user: CurrentUser,
    request: Request,
):
    """
    Accept an intake and create a case file.
    Seeds the case with facts, generates complaint, and drafts discovery.
    """
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    from src.intake.engine import IntakeAnalyzer
    analyzer = IntakeAnalyzer(supabase_client=db)

    result = await analyzer.greenlight_intake(
        intake_id=intake_id,
        org_id=user.org_id,
        user_id=user.user_id,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # Auto-generate complaint
    from src.motions.engine import MotionEngine
    motion_engine = MotionEngine(supabase_client=db)
    complaint = await motion_engine.generate_complaint(
        case_id=result["case_id"],
        org_id=user.org_id,
    )

    # Auto-generate offensive discovery package
    from src.discovery.generator import DiscoveryGenerator
    discovery_gen = DiscoveryGenerator(supabase_client=db)
    discovery = await discovery_gen.generate_offensive_package(
        case_id=result["case_id"],
        org_id=user.org_id,
    )

    # Auto-compute deadlines from complaint filing
    from src.calendar.engine import CalendarEngine
    cal = CalendarEngine(supabase_client=db)
    deadlines = cal.compute_deadlines(
        trigger_event="complaint_filed",
        event_date=__import__("datetime").date.today(),
        case_id=result["case_id"],
        org_id=user.org_id,
    )

    return {
        "case_id": result["case_id"],
        "case_name": result["case_name"],
        "complaint_generated": bool(complaint.get("motion_id")),
        "discovery_sets_generated": discovery.get("sets_generated", 0),
        "deadlines_created": len(deadlines),
        "message": "Case created. Complaint drafted. Discovery ready. Deadlines calendared.",
    }


@router.post("/{intake_id}/decline")
def decline_intake(
    intake_id: str,
    user: CurrentUser,
    request: Request,
    reason: str = "",
):
    """Decline an intake."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase
    result = db.table("client_intakes").update({
        "status": "declined",
        "reviewed_by": user.user_id,
        "decline_reason": reason,
    }).eq("id", intake_id).eq("org_id", user.org_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Intake not found")

    return {"status": "declined", "intake_id": intake_id}
