"""
CaseCommand — File Upload Storage Service

Handles file uploads to Supabase Storage (bucket: case-files).
Validates file types and sizes, manages signed URLs for downloads.
"""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

logger = logging.getLogger(__name__)

BUCKET_NAME = "case-files"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

ALLOWED_EXTENSIONS = {
    "pdf", "docx", "doc", "txt", "png", "jpg", "jpeg", "tiff", "tif",
}

EXTENSION_CONTENT_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "txt": "text/plain",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "tiff": "image/tiff",
    "tif": "image/tiff",
}


class FileUploadService:
    """
    Manages file uploads and downloads via Supabase Storage.

    All files are stored in the 'case-files' bucket, organized by
    org_id and file_id: {org_id}/{file_id}/{filename}
    """

    def __init__(self, supabase_client=None):
        self.db = supabase_client
        self._bucket_verified = False

    def _ensure_bucket(self):
        """Create the storage bucket if it doesn't exist."""
        if self._bucket_verified or not self.db:
            return
        try:
            self.db.storage.get_bucket(BUCKET_NAME)
            self._bucket_verified = True
        except Exception:
            try:
                self.db.storage.create_bucket(
                    BUCKET_NAME,
                    options={"public": False, "file_size_limit": MAX_FILE_SIZE},
                )
                self._bucket_verified = True
            except Exception as e:
                logger.warning("Could not create storage bucket '%s': %s", BUCKET_NAME, e)

    @staticmethod
    def validate_file_type(filename: str) -> tuple[bool, str]:
        """
        Validate that the file extension is in the allowed set.

        Returns (is_valid, extension_or_error_message).
        """
        ext = Path(filename).suffix.lstrip(".").lower()
        if not ext:
            return False, "File has no extension"
        if ext not in ALLOWED_EXTENSIONS:
            return False, (
                f"File type '.{ext}' is not allowed. "
                f"Accepted types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )
        return True, ext

    @staticmethod
    def get_content_type(filename: str) -> str:
        """Return the MIME content type for a given filename."""
        ext = Path(filename).suffix.lstrip(".").lower()
        if ext in EXTENSION_CONTENT_TYPES:
            return EXTENSION_CONTENT_TYPES[ext]
        guessed, _ = mimetypes.guess_type(filename)
        return guessed or "application/octet-stream"

    def upload_file(
        self,
        file_bytes: bytes,
        org_id: str,
        file_id: str,
        filename: str,
    ) -> str | None:
        """
        Upload file bytes to Supabase Storage.

        Storage path: {org_id}/{file_id}/{filename}
        Returns the storage path on success, or None on failure.
        """
        if not self.db:
            logger.error("No Supabase client available for file upload")
            return None

        self._ensure_bucket()

        storage_path = f"{org_id}/{file_id}/{filename}"
        content_type = self.get_content_type(filename)

        try:
            self.db.storage.from_(BUCKET_NAME).upload(
                storage_path,
                file_bytes,
                file_options={"content-type": content_type},
            )
            logger.info("Uploaded file to storage: %s", storage_path)
            return storage_path
        except Exception as e:
            logger.error("File upload failed for %s: %s", storage_path, e)
            return None

    def delete_file(self, storage_path: str) -> bool:
        """
        Delete a file from Supabase Storage.

        Returns True on success, False on failure.
        """
        if not self.db:
            return False

        try:
            self.db.storage.from_(BUCKET_NAME).remove([storage_path])
            logger.info("Deleted file from storage: %s", storage_path)
            return True
        except Exception as e:
            logger.error("File deletion failed for %s: %s", storage_path, e)
            return False

    def get_signed_url(self, storage_path: str, expires_in: int = 3600) -> str | None:
        """
        Generate a temporary signed download URL.

        Returns the signed URL, or None on failure.
        """
        if not self.db:
            return None

        try:
            result = self.db.storage.from_(BUCKET_NAME).create_signed_url(
                storage_path, expires_in
            )
            return result.get("signedURL")
        except Exception as e:
            logger.error("Signed URL generation failed for %s: %s", storage_path, e)
            return None
