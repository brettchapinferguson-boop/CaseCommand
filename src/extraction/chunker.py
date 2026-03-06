"""
CaseCommand — Text Chunking

Splits extracted text into overlapping chunks suitable for embedding.
Respects paragraph boundaries where possible.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field

from src.extraction.extractor import ExtractionResult

logger = logging.getLogger(__name__)

# Approximate characters per token (conservative estimate)
_CHARS_PER_TOKEN = 4


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    """A single text chunk ready for embedding."""

    content: str
    chunk_index: int
    page_number: int | None
    token_count: int
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# TextChunker
# ---------------------------------------------------------------------------

class TextChunker:
    """
    Split an :class:`ExtractionResult` into overlapping chunks for embedding.

    Parameters
    ----------
    chunk_size:
        Target chunk size in *tokens* (approximate via char count).
        Default ``512`` tokens  (~2048 chars).
    overlap:
        Number of *tokens* to overlap between consecutive chunks.
        Default ``50`` tokens (~200 chars).
    """

    def __init__(self, chunk_size: int = 512, overlap: int = 50) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0:
            raise ValueError("overlap must be non-negative")
        if overlap >= chunk_size:
            raise ValueError("overlap must be less than chunk_size")

        self.chunk_size = chunk_size
        self.overlap = overlap
        self._chunk_chars = chunk_size * _CHARS_PER_TOKEN
        self._overlap_chars = overlap * _CHARS_PER_TOKEN

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chunk(self, extraction_result: ExtractionResult) -> list[Chunk]:
        """
        Split *extraction_result* into a list of :class:`Chunk` objects.

        The chunker first tries to respect paragraph boundaries.  If a
        single paragraph exceeds the chunk size it is split at sentence
        boundaries, and as a last resort at the character limit.
        """
        if not extraction_result.text:
            return []

        # Build a list of (text, page_number) segments from pages
        segments = self._build_segments(extraction_result)

        chunks: list[Chunk] = []
        buffer = ""
        buffer_page: int | None = None
        char_cursor = 0  # position in the full concatenated text

        for segment_text, page_num in segments:
            paragraphs = re.split(r"\n{2,}", segment_text)

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                # If adding this paragraph exceeds the limit, flush the buffer
                if buffer and len(buffer) + len(para) + 2 > self._chunk_chars:
                    chunks.append(self._make_chunk(
                        content=buffer,
                        index=len(chunks),
                        page_number=buffer_page,
                        char_start=char_cursor - len(buffer),
                        char_end=char_cursor,
                    ))
                    # Carry over overlap from end of buffer
                    overlap_text = buffer[-self._overlap_chars:] if self._overlap_chars else ""
                    char_cursor = char_cursor - len(overlap_text)
                    buffer = overlap_text
                    buffer_page = page_num

                # If the paragraph itself is larger than the chunk limit, split it
                if len(para) > self._chunk_chars:
                    # Flush any existing buffer first
                    if buffer:
                        chunks.append(self._make_chunk(
                            content=buffer,
                            index=len(chunks),
                            page_number=buffer_page,
                            char_start=char_cursor - len(buffer),
                            char_end=char_cursor,
                        ))
                        overlap_text = buffer[-self._overlap_chars:] if self._overlap_chars else ""
                        char_cursor = char_cursor - len(overlap_text)
                        buffer = overlap_text

                    sub_chunks = self._split_large_paragraph(para)
                    for sc in sub_chunks:
                        combined = (buffer + "\n\n" + sc).strip() if buffer else sc
                        if len(combined) > self._chunk_chars:
                            if buffer:
                                chunks.append(self._make_chunk(
                                    content=buffer,
                                    index=len(chunks),
                                    page_number=page_num,
                                    char_start=char_cursor - len(buffer),
                                    char_end=char_cursor,
                                ))
                                overlap_text = buffer[-self._overlap_chars:] if self._overlap_chars else ""
                                char_cursor = char_cursor - len(overlap_text)
                                buffer = overlap_text
                            combined = (buffer + "\n\n" + sc).strip() if buffer else sc

                        buffer = combined
                        buffer_page = page_num
                        char_cursor += len(sc) + 2  # +2 for paragraph separator
                    continue

                # Normal case: append paragraph to buffer
                if buffer:
                    buffer += "\n\n" + para
                else:
                    buffer = para
                    buffer_page = page_num
                char_cursor += len(para) + 2

        # Flush remaining buffer
        if buffer.strip():
            chunks.append(self._make_chunk(
                content=buffer,
                index=len(chunks),
                page_number=buffer_page,
                char_start=max(char_cursor - len(buffer), 0),
                char_end=char_cursor,
            ))

        return chunks

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_segments(result: ExtractionResult) -> list[tuple[str, int | None]]:
        """Build ordered (text, page_number) segments from the extraction result."""
        if result.pages:
            return [(p.text, p.page_number) for p in result.pages if p.text]
        # Fallback: treat full text as a single segment
        return [(result.text, None)]

    def _split_large_paragraph(self, text: str) -> list[str]:
        """Split an oversized paragraph, preferring sentence boundaries."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        parts: list[str] = []
        current = ""

        for sentence in sentences:
            if current and len(current) + len(sentence) + 1 > self._chunk_chars:
                parts.append(current)
                # Keep overlap from end of current
                current = current[-self._overlap_chars:] + " " + sentence if self._overlap_chars else sentence
            else:
                current = (current + " " + sentence).strip() if current else sentence

        # If a single sentence is still too large, hard-split on character boundary
        if current:
            if len(current) > self._chunk_chars:
                while current:
                    parts.append(current[: self._chunk_chars])
                    current = current[self._chunk_chars - self._overlap_chars:]
                    if len(current) <= self._overlap_chars:
                        break
            else:
                parts.append(current)

        return parts

    @staticmethod
    def _make_chunk(
        content: str,
        index: int,
        page_number: int | None,
        char_start: int,
        char_end: int,
    ) -> Chunk:
        content = content.strip()
        token_est = max(len(content) // _CHARS_PER_TOKEN, 1)
        return Chunk(
            content=content,
            chunk_index=index,
            page_number=page_number,
            token_count=token_est,
            metadata={
                "page_number": page_number,
                "chunk_index": index,
                "char_start": max(char_start, 0),
                "char_end": char_end,
            },
        )
