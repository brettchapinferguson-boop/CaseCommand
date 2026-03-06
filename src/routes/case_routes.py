"""
CaseCommand — Case Management Routes

CRUD operations for cases, scoped to the user's organization.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from src.models.requests import CaseCreate
from src.auth.jwt import CurrentUser

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


@router.get("")
def list_cases(user: CurrentUser, request: Request):
    """List all cases for the user's organization."""
    db = request.app.state.supabase

    query = db.table("cases").select("*")
    if user.org_id:
        query = query.eq("org_id", user.org_id)
    else:
        query = query.eq("user_id", user.user_id)

    result = query.order("created_at", desc=True).execute()
    return result.data


@router.get("/{case_id}")
def get_case(case_id: str, user: CurrentUser, request: Request):
    """Get a single case by ID, scoped to the user's org."""
    db = request.app.state.supabase

    query = db.table("cases").select("*").eq("id", case_id)
    if user.org_id:
        query = query.eq("org_id", user.org_id)

    result = query.execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Case not found")
    return result.data[0]


@router.post("", status_code=201)
def create_case(case: CaseCreate, user: CurrentUser, request: Request):
    """Create a new case in the user's organization."""
    db = request.app.state.supabase

    data = {
        "case_name": case.name,
        "case_type": case.type,
        "client_name": case.client,
        "opposing_party": case.opposing,
        "user_id": user.user_id,
    }
    if user.org_id:
        data["org_id"] = user.org_id

    result = db.table("cases").insert(data).execute()
    return result.data[0]


@router.patch("/{case_id}")
def update_case(case_id: str, updates: dict, user: CurrentUser, request: Request):
    """Update a case. Only allows updating specific fields."""
    db = request.app.state.supabase

    allowed_fields = {
        "case_name", "case_type", "client_name", "opposing_party",
        "case_number", "status", "notes",
    }
    update_data = {k: v for k, v in updates.items() if k in allowed_fields}

    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    query = db.table("cases").update(update_data).eq("id", case_id)
    if user.org_id:
        query = query.eq("org_id", user.org_id)

    result = query.execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Case not found")
    return result.data[0]


@router.delete("/{case_id}")
def delete_case(case_id: str, user: CurrentUser, request: Request):
    """Soft-delete a case by setting status to 'archived'."""
    db = request.app.state.supabase

    query = (
        db.table("cases")
        .update({"status": "archived"})
        .eq("id", case_id)
    )
    if user.org_id:
        query = query.eq("org_id", user.org_id)

    result = query.execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"status": "archived", "id": case_id}
