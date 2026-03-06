"""
CaseCommand — Document Routes

Serve and manage generated legal documents.
Authentication required for all downloads.

Documents are stored in Supabase Storage for persistence across deploys.
When a local file is missing (e.g., after redeploy), it is fetched from
storage transparently.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse

from src.auth.jwt import CurrentUser
from src.storage.documents import DocumentStore, LOCAL_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.get("/{filename}")
def download_document(filename: str, user: CurrentUser, request: Request):
    """
    Download a generated document.

    Lookup order:
    1. Local org-scoped directory (fast, works between requests)
    2. Supabase Storage via signed URL (survives redeployment)
    3. Local global directory (legacy / no-org fallback)
    """
    doc_store: DocumentStore = request.app.state.doc_store

    # Prevent path traversal
    safe_filename = Path(filename).name
    if safe_filename != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # 1. Try org-scoped local path
    if user.org_id:
        filepath = LOCAL_DIR / user.org_id / safe_filename
        if filepath.exists() and filepath.is_file():
            return FileResponse(str(filepath), media_type=DOCX_MEDIA_TYPE, filename=safe_filename)

    # 2. Try Supabase Storage (signed URL redirect)
    if user.org_id and doc_store.db:
        storage_path = f"{user.org_id}/{safe_filename}"
        signed_url = doc_store.get_signed_url(storage_path, expires_in=300)
        if signed_url:
            return RedirectResponse(url=signed_url, status_code=302)

    # 3. Fallback to global local dir (legacy)
    filepath = LOCAL_DIR / safe_filename
    if filepath.exists() and filepath.is_file():
        return FileResponse(str(filepath), media_type=DOCX_MEDIA_TYPE, filename=safe_filename)

    raise HTTPException(status_code=404, detail="Document not found")


@router.get("")
def list_documents(user: CurrentUser, request: Request):
    """
    List documents for the user's organization.

    Lists from both local filesystem and Supabase Storage.
    """
    doc_store: DocumentStore = request.app.state.doc_store
    docs = []

    # Local org-scoped documents
    if user.org_id:
        org_dir = LOCAL_DIR / user.org_id
        if org_dir.exists():
            for f in sorted(org_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                if f.suffix == ".docx":
                    docs.append({
                        "filename": f.name,
                        "url": f"/api/v1/documents/{f.name}",
                        "size": f.stat().st_size,
                        "created_at": f.stat().st_mtime,
                        "source": "local",
                    })

    # Supabase Storage documents (catch files that survived redeploy)
    if user.org_id and doc_store.db:
        local_names = {d["filename"] for d in docs}
        try:
            files = doc_store.db.storage.from_("documents").list(user.org_id)
            for f in (files or []):
                name = f.get("name", "")
                if name.endswith(".docx") and name not in local_names:
                    docs.append({
                        "filename": name,
                        "url": f"/api/v1/documents/{name}",
                        "size": f.get("metadata", {}).get("size", 0),
                        "created_at": f.get("created_at", ""),
                        "source": "storage",
                    })
        except Exception as e:
            logger.warning("Could not list storage documents: %s", e)

    return docs
