"""
CaseCommand — Text Extraction

Extracts text from PDFs, Word documents, plain text files, and images.
Provides structured results with per-page content and metadata.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class PageContent:
    """Content extracted from a single page (or logical section)."""

    page_number: int
    text: str
    has_text: bool = True


@dataclass
class ExtractionResult:
    """Full result of a text extraction operation."""

    text: str                          # Full concatenated text
    pages: list[PageContent]           # Per-page / per-section content
    metadata: dict = field(default_factory=dict)  # page_count, word_count, etc.
    needs_ocr: bool = False            # True if scanned PDF detected


# ---------------------------------------------------------------------------
# Supported MIME helpers
# ---------------------------------------------------------------------------

_PDF_TYPES = {"pdf", "application/pdf"}
_DOCX_TYPES = {
    "docx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_TEXT_TYPES = {"txt", "text", "text/plain", "md", "csv"}
_IMAGE_TYPES = {"png", "jpg", "jpeg", "tiff", "bmp", "image/png", "image/jpeg", "image/tiff"}


# ---------------------------------------------------------------------------
# TextExtractor
# ---------------------------------------------------------------------------

class TextExtractor:
    """Stateless extractor — call ``TextExtractor.extract(path, file_type)``."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def extract(file_path: str, file_type: str) -> ExtractionResult:
        """
        Extract text from *file_path* based on *file_type*.

        Parameters
        ----------
        file_path:
            Absolute or relative path to the file on disk.
        file_type:
            File extension (e.g. ``"pdf"``) or MIME type.

        Returns
        -------
        ExtractionResult
        """
        ft = file_type.lower().strip().lstrip(".")
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            if ft in _PDF_TYPES:
                return TextExtractor._extract_pdf(path)
            if ft in _DOCX_TYPES:
                return TextExtractor._extract_docx(path)
            if ft in _TEXT_TYPES:
                return TextExtractor._extract_text(path)
            if ft in _IMAGE_TYPES:
                return TextExtractor._extract_image(path)
        except FileNotFoundError:
            raise
        except Exception as exc:
            logger.error("Extraction failed for %s: %s", file_path, exc)
            raise ExtractionError(f"Failed to extract text from {path.name}: {exc}") from exc

        raise UnsupportedFileType(f"Unsupported file type: {file_type}")

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_pdf(path: Path) -> ExtractionResult:
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader  # type: ignore[no-redef]

        reader = PdfReader(str(path))
        pages: list[PageContent] = []
        needs_ocr = False
        total_text_chars = 0

        for idx, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            has_text = bool(text)
            if not has_text:
                needs_ocr = True
            total_text_chars += len(text)
            pages.append(PageContent(page_number=idx, text=text, has_text=has_text))

        full_text = "\n\n".join(p.text for p in pages if p.text)
        word_count = len(full_text.split()) if full_text else 0

        # Heuristic: if the majority of pages have no text, flag for OCR
        empty_ratio = sum(1 for p in pages if not p.has_text) / max(len(pages), 1)
        if empty_ratio > 0.5:
            needs_ocr = True

        has_images = False
        try:
            for page in reader.pages:
                if "/XObject" in (page.get("/Resources") or {}):
                    has_images = True
                    break
        except Exception:
            pass

        return ExtractionResult(
            text=full_text,
            pages=pages,
            metadata={
                "page_count": len(pages),
                "word_count": word_count,
                "char_count": total_text_chars,
                "has_images": has_images,
                "source": path.name,
            },
            needs_ocr=needs_ocr,
        )

    # ------------------------------------------------------------------
    # Word (.docx)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_docx(path: Path) -> ExtractionResult:
        from docx import Document as DocxDocument

        doc = DocxDocument(str(path))
        pages: list[PageContent] = []
        paragraphs: list[str] = []

        for idx, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            if not text:
                continue

            # Preserve heading structure with lightweight markers
            style_name = (para.style.name or "").lower()
            if "heading" in style_name:
                level = "".join(c for c in style_name if c.isdigit()) or "1"
                prefix = "#" * int(level) + " "
                text = prefix + text

            paragraphs.append(text)
            pages.append(PageContent(page_number=idx + 1, text=text))

        full_text = "\n\n".join(paragraphs)
        word_count = len(full_text.split()) if full_text else 0

        return ExtractionResult(
            text=full_text,
            pages=pages,
            metadata={
                "page_count": 1,  # docx has no reliable page notion
                "paragraph_count": len(paragraphs),
                "word_count": word_count,
                "char_count": len(full_text),
                "has_images": bool(doc.inline_shapes),
                "source": path.name,
            },
            needs_ocr=False,
        )

    # ------------------------------------------------------------------
    # Plain text
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(path: Path) -> ExtractionResult:
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="latin-1")

        word_count = len(content.split()) if content else 0

        return ExtractionResult(
            text=content,
            pages=[PageContent(page_number=1, text=content)],
            metadata={
                "page_count": 1,
                "word_count": word_count,
                "char_count": len(content),
                "has_images": False,
                "source": path.name,
            },
            needs_ocr=False,
        )

    # ------------------------------------------------------------------
    # Image OCR (optional)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_image(path: Path) -> ExtractionResult:
        try:
            import pytesseract
            from PIL import Image

            image = Image.open(path)
            text = pytesseract.image_to_string(image).strip()

            return ExtractionResult(
                text=text,
                pages=[PageContent(page_number=1, text=text, has_text=bool(text))],
                metadata={
                    "page_count": 1,
                    "word_count": len(text.split()) if text else 0,
                    "char_count": len(text),
                    "has_images": True,
                    "ocr_applied": True,
                    "source": path.name,
                },
                needs_ocr=not bool(text),
            )
        except ImportError:
            logger.info("pytesseract not installed — OCR not available for %s", path.name)
            return ExtractionResult(
                text="",
                pages=[PageContent(page_number=1, text="", has_text=False)],
                metadata={
                    "page_count": 1,
                    "word_count": 0,
                    "char_count": 0,
                    "has_images": True,
                    "ocr_applied": False,
                    "ocr_message": "OCR not available — install pytesseract and Tesseract to enable image text extraction.",
                    "source": path.name,
                },
                needs_ocr=True,
            )


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ExtractionError(Exception):
    """Raised when text extraction fails due to a corrupt or unreadable file."""


class UnsupportedFileType(ValueError):
    """Raised when the provided file type is not supported."""
