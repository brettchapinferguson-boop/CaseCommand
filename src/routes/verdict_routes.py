"""
CaseCommand — Verdict Library Routes

Search verdicts, valuate cases, add verdict entries.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

from src.auth.jwt import CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/verdicts", tags=["verdicts"])


class AddVerdictRequest(BaseModel):
    case_name: str
    case_number: str | None = None
    court: str | None = None
    county: str | None = None
    judge: str | None = None
    resolution_date: str | None = None
    case_type: str | None = None
    causes_of_action: list[str] = []
    resolution_type: str
    verdict_amount: float | None = None
    economic_damages: float | None = None
    non_economic_damages: float | None = None
    punitive_damages: float | None = None
    attorney_fees: float | None = None
    key_facts: str | None = None
    notable_rulings: str | None = None
    source_type: str = "manual_entry"


class ValuateRequest(BaseModel):
    case_id: str


@router.get("/search")
async def search_verdicts(
    request: Request,
    user: CurrentUser,
    case_type: str | None = None,
    county: str | None = None,
    resolution_type: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    limit: int = Query(default=20, ge=1, le=100),
):
    """Search the verdict/settlement library."""
    db = request.app.state.supabase

    from src.verdicts.scraper import VerdictLibrary
    lib = VerdictLibrary(supabase_client=db)

    results = await lib.search_verdicts(
        case_type=case_type,
        county=county,
        resolution_type=resolution_type,
        min_amount=min_amount,
        max_amount=max_amount,
        limit=limit,
    )
    return results


@router.post("/valuate")
async def valuate_case(
    req: ValuateRequest,
    user: CurrentUser,
    request: Request,
):
    """Generate a data-driven case valuation using comparable verdicts."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    from src.verdicts.scraper import VerdictLibrary
    lib = VerdictLibrary(supabase_client=db)

    result = await lib.valuate_case(case_id=req.case_id, org_id=user.org_id)
    return result


@router.post("/add", status_code=201)
async def add_verdict(
    req: AddVerdictRequest,
    user: CurrentUser,
    request: Request,
):
    """Add a verdict/settlement to the library."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    from src.verdicts.scraper import VerdictLibrary
    lib = VerdictLibrary(supabase_client=db)

    verdict_data = req.model_dump()
    verdict_data["org_id"] = user.org_id

    result = await lib.add_verdict(verdict_data)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/scrape")
async def trigger_scrape(
    user: CurrentUser,
    request: Request,
):
    """Trigger a verdict scraping job to update the library."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase

    from src.verdicts.scraper import VerdictLibrary
    lib = VerdictLibrary(supabase_client=db)

    result = await lib.scrape_public_records(org_id=user.org_id)
    return result
