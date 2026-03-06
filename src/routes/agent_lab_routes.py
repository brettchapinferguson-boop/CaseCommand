"""
CaseCommand — Agent Lab Routes

Admin endpoints for reviewing nightly agent outputs.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from src.models.requests import AgentOutputUpdate
from src.auth.jwt import CurrentUser

router = APIRouter(prefix="/api/v1/agent-outputs", tags=["agent-lab"])


@router.get("")
def list_agent_outputs(
    status: str | None = None,
    agent: str | None = None,
    limit: int = 50,
    user: CurrentUser = None,
    request: Request = None,
):
    """List agent outputs, optionally filtered by status or agent name."""
    db = request.app.state.supabase
    query = db.table("agent_outputs").select("*").order("created_at", desc=True).limit(limit)
    if status:
        query = query.eq("status", status)
    if agent:
        query = query.eq("agent_name", agent)
    result = query.execute()
    return result.data


@router.get("/summary")
def agent_outputs_summary(user: CurrentUser, request: Request):
    """Get summary stats for the Agent Lab dashboard."""
    db = request.app.state.supabase
    all_outputs = (
        db.table("agent_outputs")
        .select("id,agent_name,status,priority,run_id,created_at")
        .order("created_at", desc=True)
        .execute()
    )
    data = all_outputs.data or []

    pending = [r for r in data if r["status"] == "pending"]
    applied = [r for r in data if r["status"] == "applied"]
    dismissed = [r for r in data if r["status"] == "dismissed"]

    agents = {}
    for r in data:
        name = r["agent_name"]
        if name not in agents:
            agents[name] = {"total": 0, "pending": 0, "applied": 0}
        agents[name]["total"] += 1
        if r["status"] == "pending":
            agents[name]["pending"] += 1
        elif r["status"] == "applied":
            agents[name]["applied"] += 1

    run_ids = list({r["run_id"] for r in data if r.get("run_id")})
    latest_run = run_ids[0] if run_ids else None

    return {
        "total": len(data),
        "pending": len(pending),
        "applied": len(applied),
        "dismissed": len(dismissed),
        "agents": agents,
        "latest_run_id": latest_run,
    }


@router.patch("/{output_id}")
def update_agent_output(output_id: str, update: AgentOutputUpdate, user: CurrentUser, request: Request):
    """Mark an agent output as applied or dismissed."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    db = request.app.state.supabase
    update_data = {"status": update.status}
    if update.status == "applied":
        update_data["applied_at"] = datetime.now(timezone.utc).isoformat()
        update_data["applied_by"] = user.email or user.user_id

    result = db.table("agent_outputs").update(update_data).eq("id", output_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Agent output not found")
    return result.data[0]
