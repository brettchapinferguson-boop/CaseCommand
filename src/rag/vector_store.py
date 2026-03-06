"""
CaseCommand — Vector Store

Thin wrapper around the Supabase 'file_chunks' table for storing and
retrieving document chunk embeddings. Uses pgvector's cosine distance
operator for similarity search.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class VectorStore:
    """Interface to the file_chunks table with vector search capabilities."""

    def __init__(self, supabase_client: Any):
        self.db = supabase_client

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def upsert_chunks(self, chunks: list[dict]) -> int:
        """Insert or update chunk records (with embeddings) into file_chunks.

        Each dict should contain at minimum:
            id, file_id, org_id, content, embedding, chunk_index
        Returns the number of rows written.
        """
        if not chunks:
            return 0
        try:
            result = self.db.table("file_chunks").upsert(chunks).execute()
            return len(result.data) if result.data else 0
        except Exception as e:
            logger.error("Failed to upsert %d chunks: %s", len(chunks), e)
            raise

    # ------------------------------------------------------------------
    # Read — vector similarity search
    # ------------------------------------------------------------------

    def search(
        self,
        query_embedding: list[float],
        *,
        org_id: str | None = None,
        case_id: str | None = None,
        top_k: int = 8,
        similarity_threshold: float = 0.0,
    ) -> list[dict]:
        """Search for the most similar chunks using cosine similarity.

        Calls the Supabase RPC function 'match_file_chunks' which is
        expected to exist as a Postgres function leveraging pgvector.

        Returns a list of dicts with keys:
            id, file_id, content, chunk_index, similarity, metadata
        """
        params: dict[str, Any] = {
            "query_embedding": query_embedding,
            "match_count": top_k,
            "similarity_threshold": similarity_threshold,
        }
        if org_id:
            params["filter_org_id"] = org_id
        if case_id:
            params["filter_case_id"] = case_id

        try:
            result = self.db.rpc("match_file_chunks", params).execute()
            return result.data or []
        except Exception as e:
            logger.error("Vector search failed: %s", e)
            return []

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_by_file(self, file_id: str) -> None:
        """Remove all chunks associated with a file."""
        try:
            self.db.table("file_chunks").delete().eq("file_id", file_id).execute()
        except Exception as e:
            logger.warning("Failed to delete chunks for file %s: %s", file_id, e)
