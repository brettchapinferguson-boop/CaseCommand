"""
CaseCommand — RAG Query Engine

Orchestrates the retrieval-augmented generation pipeline:
  1. Embed the user's query via EmbeddingService
  2. Search the VectorStore for relevant chunks
  3. Format results with source references

This module is consumed by the Casey agent's search_case_documents tool.
"""

from __future__ import annotations

import logging
from typing import Any

from src.rag.embeddings import EmbeddingService
from src.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RAGQueryEngine:
    """End-to-end document search: embed query -> vector search -> format."""

    def __init__(self, supabase_client: Any):
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore(supabase_client)
        self.db = supabase_client

    async def search(
        self,
        query: str,
        *,
        org_id: str | None = None,
        case_id: str | None = None,
        top_k: int = 8,
    ) -> list[dict]:
        """Search case documents and return formatted results.

        Returns a list of dicts, each containing:
            content   - the matched text excerpt
            source    - filename of the source document
            file_id   - ID of the source file
            case_id   - associated case (if any)
            chunk_index - position within the document
            similarity - cosine similarity score
        """
        # 1. Embed the query
        query_embedding = await self.embedding_service.embed_query(query)

        # 2. Vector search
        raw_results = self.vector_store.search(
            query_embedding,
            org_id=org_id,
            case_id=case_id,
            top_k=top_k,
        )

        if not raw_results:
            return []

        # 3. Enrich with file metadata (filename, case_id)
        file_ids = list({r["file_id"] for r in raw_results if r.get("file_id")})
        file_map: dict[str, dict] = {}
        if file_ids:
            try:
                result = (
                    self.db.table("uploaded_files")
                    .select("id, filename, case_id")
                    .in_("id", file_ids)
                    .execute()
                )
                for f in result.data or []:
                    file_map[f["id"]] = f
            except Exception as e:
                logger.warning("Failed to fetch file metadata: %s", e)

        # 4. Format results
        formatted = []
        for r in raw_results:
            file_info = file_map.get(r.get("file_id", ""), {})
            formatted.append({
                "content": r.get("content", ""),
                "source": file_info.get("filename", "unknown"),
                "file_id": r.get("file_id", ""),
                "case_id": file_info.get("case_id"),
                "chunk_index": r.get("chunk_index", 0),
                "similarity": round(r.get("similarity", 0.0), 4),
            })

        return formatted
