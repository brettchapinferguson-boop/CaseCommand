"""
CaseCommand — Document Routes

Serve and manage generated legal documents.
Authentication required for all downloads.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from src.auth.jwt import CurrentUser
from src.storage.documents import DocumentStore

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.get("/{filename}")
def download_document(filename: str, user: CurrentUser, request: Request):
    """
    Download a generated document.

    Requires authentication. Prevents path traversal.
    """
    doc_store: DocumentStore = request.app.state.doc_store

    # Prevent path traversal
    safe_filename = Path(filename).name
    if safe_filename != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Try org-scoped path first, then global
    from src.storage.documents import LOCAL_DIR

    if user.org_id:
        filepath = LOCAL_DIR / user.org_id / safe_filename
        if filepath.exists() and filepath.is_file():
            return FileResponse(
                str(filepath),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                filename=safe_filename,
            )

    # Fallback to global dir
    filepath = LOCAL_DIR / safe_filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="Document not found")

    return FileResponse(
        str(filepath),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=safe_filename,
    )


@router.get("")
def list_documents(user: CurrentUser, request: Request):
    """List documents for the user's organization."""
    from src.storage.documents import LOCAL_DIR

    docs = []
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
                    })

    return docs
