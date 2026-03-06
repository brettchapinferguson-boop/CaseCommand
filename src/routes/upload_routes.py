"""
CaseCommand — File Upload Routes

Endpoints for uploading, listing, downloading, and processing files.
All files are stored in Supabase Storage (bucket: case-files) and tracked
in the 'uploaded_files' table. Processing jobs are tracked in 'processing_jobs'.

Authentication required for all endpoints.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Query
from pydantic import BaseModel

from src.auth.jwt import CurrentUser, require_org
from src.storage.file_upload import (
    FileUploadService,
    MAX_FILE_SIZE,
    ALLOWED_EXTENSIONS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/files", tags=["files"])
jobs_router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class FileMetadata(BaseModel):
    id: str
    org_id: str
    filename: str
    file_type: str
    size: int
    storage_path: str
    case_id: str | None = None
    description: str | None = None
    status: str = "uploaded"
    created_at: str
    updated_at: str


class UploadResponse(BaseModel):
    file: FileMetadata
    message: str


class JobResponse(BaseModel):
    job_id: str
    file_id: str
    status: str
    created_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_upload_service(request: Request) -> FileUploadService:
    """Retrieve the FileUploadService from app state."""
    svc: FileUploadService | None = getattr(request.app.state, "file_upload_service", None)
    if svc is None:
        # Fallback: create from supabase client on app.state
        supabase = getattr(request.app.state, "supabase", None)
        svc = FileUploadService(supabase_client=supabase)
        request.app.state.file_upload_service = svc
    return svc


def _get_supabase(request: Request):
    """Retrieve the Supabase client from app state."""
    db = getattr(request.app.state, "supabase", None)
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return db


# ---------------------------------------------------------------------------
# 1. POST /api/v1/files/upload — Upload a file
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_file(
    request: Request,
    user: CurrentUser,
    file: UploadFile = File(...),
    case_id: str | None = Query(default=None),
    description: str | None = Query(default=None),
):
    """
    Upload a file (PDF, DOCX, DOC, TXT, PNG, JPG, TIFF).

    The file is stored in Supabase Storage under the user's org and tracked
    in the 'uploaded_files' table.
    """
    # Require org membership
    if not user.org_id:
        raise HTTPException(
            status_code=403,
            detail="No organization associated with this account. Complete onboarding first.",
        )

    # Validate file type
    is_valid, ext_or_error = FileUploadService.validate_file_type(file.filename or "")
    if not is_valid:
        raise HTTPException(status_code=400, detail=ext_or_error)
    file_ext = ext_or_error

    # Read file content and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum size of {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    file_id = uuid.uuid4().hex
    filename = file.filename or f"upload_{file_id}.{file_ext}"
    now = datetime.now(timezone.utc).isoformat()

    # Upload to Supabase Storage
    upload_service = _get_upload_service(request)
    storage_path = upload_service.upload_file(
        file_bytes=content,
        org_id=user.org_id,
        file_id=file_id,
        filename=filename,
    )
    if storage_path is None:
        raise HTTPException(status_code=500, detail="File upload to storage failed")

    # Insert record into uploaded_files table
    db = _get_supabase(request)
    record = {
        "id": file_id,
        "org_id": user.org_id,
        "uploaded_by": user.user_id,
        "filename": filename,
        "file_type": file_ext,
        "size": len(content),
        "storage_path": storage_path,
        "case_id": case_id,
        "description": description,
        "status": "uploaded",
        "created_at": now,
        "updated_at": now,
    }

    try:
        result = db.table("uploaded_files").insert(record).execute()
        if not result.data:
            raise Exception("Insert returned no data")
        saved = result.data[0]
    except Exception as e:
        # Best-effort cleanup: remove file from storage if DB insert fails
        logger.error("DB insert failed for uploaded file %s: %s", file_id, e)
        upload_service.delete_file(storage_path)
        raise HTTPException(status_code=500, detail="Failed to save file record")

    return UploadResponse(
        file=FileMetadata(
            id=saved["id"],
            org_id=saved["org_id"],
            filename=saved["filename"],
            file_type=saved["file_type"],
            size=saved["size"],
            storage_path=saved["storage_path"],
            case_id=saved.get("case_id"),
            description=saved.get("description"),
            status=saved["status"],
            created_at=saved["created_at"],
            updated_at=saved["updated_at"],
        ),
        message="File uploaded successfully",
    )


# ---------------------------------------------------------------------------
# 2. GET /api/v1/files — List uploaded files (org-scoped, paginated)
# ---------------------------------------------------------------------------

@router.get("")
def list_files(
    request: Request,
    user: CurrentUser,
    case_id: str | None = Query(default=None),
    file_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """
    List uploaded files for the authenticated user's organization.

    Supports optional filtering by case_id, file_type, and status.
    """
    if not user.org_id:
        raise HTTPException(
            status_code=403,
            detail="No organization associated with this account. Complete onboarding first.",
        )

    db = _get_supabase(request)
    query = (
        db.table("uploaded_files")
        .select("*")
        .eq("org_id", user.org_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )

    if case_id is not None:
        query = query.eq("case_id", case_id)
    if file_type is not None:
        query = query.eq("file_type", file_type)
    if status is not None:
        query = query.eq("status", status)

    try:
        result = query.execute()
    except Exception as e:
        logger.error("Failed to list files for org %s: %s", user.org_id, e)
        raise HTTPException(status_code=500, detail="Failed to list files")

    return {
        "files": result.data or [],
        "limit": limit,
        "offset": offset,
    }


# ---------------------------------------------------------------------------
# 3. GET /api/v1/files/{file_id} — Get file metadata
# ---------------------------------------------------------------------------

@router.get("/{file_id}")
def get_file(
    file_id: str,
    request: Request,
    user: CurrentUser,
):
    """Retrieve metadata for a single uploaded file."""
    if not user.org_id:
        raise HTTPException(
            status_code=403,
            detail="No organization associated with this account. Complete onboarding first.",
        )

    db = _get_supabase(request)

    try:
        result = (
            db.table("uploaded_files")
            .select("*")
            .eq("id", file_id)
            .eq("org_id", user.org_id)
            .execute()
        )
    except Exception as e:
        logger.error("Failed to fetch file %s: %s", file_id, e)
        raise HTTPException(status_code=500, detail="Failed to fetch file")

    if not result.data:
        raise HTTPException(status_code=404, detail="File not found")

    return result.data[0]


# ---------------------------------------------------------------------------
# 4. GET /api/v1/files/{file_id}/download — Signed download URL
# ---------------------------------------------------------------------------

@router.get("/{file_id}/download")
def download_file(
    file_id: str,
    request: Request,
    user: CurrentUser,
):
    """Generate a temporary signed download URL for the file."""
    if not user.org_id:
        raise HTTPException(
            status_code=403,
            detail="No organization associated with this account. Complete onboarding first.",
        )

    db = _get_supabase(request)

    try:
        result = (
            db.table("uploaded_files")
            .select("*")
            .eq("id", file_id)
            .eq("org_id", user.org_id)
            .execute()
        )
    except Exception as e:
        logger.error("Failed to fetch file %s for download: %s", file_id, e)
        raise HTTPException(status_code=500, detail="Failed to fetch file record")

    if not result.data:
        raise HTTPException(status_code=404, detail="File not found")

    file_record = result.data[0]
    upload_service = _get_upload_service(request)
    signed_url = upload_service.get_signed_url(
        file_record["storage_path"], expires_in=3600
    )

    if not signed_url:
        raise HTTPException(status_code=500, detail="Could not generate download URL")

    return {
        "file_id": file_id,
        "filename": file_record["filename"],
        "download_url": signed_url,
        "expires_in": 3600,
    }


# ---------------------------------------------------------------------------
# 5. DELETE /api/v1/files/{file_id} — Delete file and its chunks
# ---------------------------------------------------------------------------

@router.delete("/{file_id}")
def delete_file(
    file_id: str,
    request: Request,
    user: CurrentUser,
):
    """
    Delete a file from storage and the database.

    Also removes any associated chunks from the 'file_chunks' table.
    """
    if not user.org_id:
        raise HTTPException(
            status_code=403,
            detail="No organization associated with this account. Complete onboarding first.",
        )

    db = _get_supabase(request)

    # Fetch the file record (org-scoped)
    try:
        result = (
            db.table("uploaded_files")
            .select("*")
            .eq("id", file_id)
            .eq("org_id", user.org_id)
            .execute()
        )
    except Exception as e:
        logger.error("Failed to fetch file %s for deletion: %s", file_id, e)
        raise HTTPException(status_code=500, detail="Failed to fetch file record")

    if not result.data:
        raise HTTPException(status_code=404, detail="File not found")

    file_record = result.data[0]

    # Delete from Supabase Storage
    upload_service = _get_upload_service(request)
    upload_service.delete_file(file_record["storage_path"])

    # Delete associated chunks (best-effort)
    try:
        db.table("file_chunks").delete().eq("file_id", file_id).execute()
    except Exception as e:
        logger.warning("Failed to delete chunks for file %s: %s", file_id, e)

    # Delete the file record
    try:
        db.table("uploaded_files").delete().eq("id", file_id).execute()
    except Exception as e:
        logger.error("Failed to delete file record %s: %s", file_id, e)
        raise HTTPException(status_code=500, detail="Failed to delete file record")

    return {"message": "File deleted successfully", "file_id": file_id}


# ---------------------------------------------------------------------------
# 6. POST /api/v1/files/{file_id}/process — Trigger text extraction + embedding
# ---------------------------------------------------------------------------

@router.post("/{file_id}/process", response_model=JobResponse, status_code=202)
def process_file(
    file_id: str,
    request: Request,
    user: CurrentUser,
):
    """
    Trigger text extraction and embedding generation for a file.

    Creates a background processing job and returns the job ID for tracking.
    """
    if not user.org_id:
        raise HTTPException(
            status_code=403,
            detail="No organization associated with this account. Complete onboarding first.",
        )

    db = _get_supabase(request)

    # Verify the file exists and belongs to the org
    try:
        result = (
            db.table("uploaded_files")
            .select("*")
            .eq("id", file_id)
            .eq("org_id", user.org_id)
            .execute()
        )
    except Exception as e:
        logger.error("Failed to fetch file %s for processing: %s", file_id, e)
        raise HTTPException(status_code=500, detail="Failed to fetch file record")

    if not result.data:
        raise HTTPException(status_code=404, detail="File not found")

    file_record = result.data[0]

    # Don't allow re-processing if already completed
    if file_record.get("status") == "processed":
        raise HTTPException(status_code=409, detail="File has already been processed")

    job_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()

    # Create the processing job record
    job_record = {
        "id": job_id,
        "file_id": file_id,
        "org_id": user.org_id,
        "status": "queued",
        "created_by": user.user_id,
        "created_at": now,
        "updated_at": now,
    }

    try:
        job_result = db.table("processing_jobs").insert(job_record).execute()
        if not job_result.data:
            raise Exception("Insert returned no data")
    except Exception as e:
        logger.error("Failed to create processing job for file %s: %s", file_id, e)
        raise HTTPException(status_code=500, detail="Failed to create processing job")

    # Update file status to 'processing'
    try:
        db.table("uploaded_files").update(
            {"status": "processing", "updated_at": now}
        ).eq("id", file_id).execute()
    except Exception as e:
        logger.warning("Failed to update file status for %s: %s", file_id, e)

    return JobResponse(
        job_id=job_id,
        file_id=file_id,
        status="queued",
        created_at=now,
    )


# ---------------------------------------------------------------------------
# 7. GET /api/v1/jobs/{job_id} — Check job status
# ---------------------------------------------------------------------------

@jobs_router.get("/{job_id}")
def get_job_status(
    job_id: str,
    request: Request,
    user: CurrentUser,
):
    """Check the status of a processing job."""
    if not user.org_id:
        raise HTTPException(
            status_code=403,
            detail="No organization associated with this account. Complete onboarding first.",
        )

    db = _get_supabase(request)

    try:
        result = (
            db.table("processing_jobs")
            .select("*")
            .eq("id", job_id)
            .eq("org_id", user.org_id)
            .execute()
        )
    except Exception as e:
        logger.error("Failed to fetch job %s: %s", job_id, e)
        raise HTTPException(status_code=500, detail="Failed to fetch job status")

    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")

    return result.data[0]
