"""
CaseCommand — Calendar & Deadline Routes

Deadline management, timeline viewing, and deadline computation.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

from src.auth.jwt import CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])


class ComputeDeadlinesRequest(BaseModel):
    trigger_event: str  # complaint_filed, answer_filed, discovery_served, trial_set
    event_date: str
    case_id: str
    trial_date: str | None = None
    service_method: str = "electronic"


@router.get("/deadlines")
def get_upcoming_deadlines(
    user: CurrentUser,
    request: Request,
    days_ahead: int = Query(default=30, ge=1, le=365),
    case_id: str | None = None,
):
    """Get upcoming deadlines across all cases or for a specific case."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    from src.calendar.engine import CalendarEngine
    cal = CalendarEngine(supabase_client=db)

    deadlines = cal.get_upcoming_deadlines(
        org_id=user.org_id,
        days_ahead=days_ahead,
        case_id=case_id,
    )
    return deadlines


@router.post("/compute", status_code=201)
def compute_deadlines(
    req: ComputeDeadlinesRequest,
    user: CurrentUser,
    request: Request,
):
    """Compute and save deadlines triggered by a case event."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    from src.calendar.engine import CalendarEngine
    cal = CalendarEngine(supabase_client=db)

    deadlines = cal.compute_deadlines(
        trigger_event=req.trigger_event,
        event_date=req.event_date,
        case_id=req.case_id,
        org_id=user.org_id,
        trial_date=req.trial_date,
        service_method=req.service_method,
    )
    return {"deadlines_created": len(deadlines), "deadlines": deadlines}


@router.get("/timeline/{case_id}")
def get_case_timeline(
    case_id: str,
    user: CurrentUser,
    request: Request,
):
    """Get the full chronological timeline for a case."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    from src.calendar.engine import CalendarEngine
    cal = CalendarEngine(supabase_client=db)

    timeline = cal.get_case_timeline(case_id=case_id)
    return timeline


@router.patch("/deadlines/{deadline_id}/complete")
def complete_deadline(
    deadline_id: str,
    user: CurrentUser,
    request: Request,
):
    """Mark a deadline as completed."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    from src.calendar.engine import CalendarEngine
    cal = CalendarEngine(supabase_client=db)

    result = cal.complete_deadline(deadline_id=deadline_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
