"""
CaseCommand — Embedding Service

Generates vector embeddings via the Voyage AI API (voyage-3 model).
Falls back to a simple TF-IDF-based embedding when VOYAGE_API_KEY is not set,
enabling local development and testing without an external API.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

import httpx

from src.config import get_settings

# Voyage API constants
VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"
VOYAGE_MODEL = "voyage-3"
VOYAGE_DIMENSION = 1024
VOYAGE_MAX_BATCH = 128


class EmbeddingService:
    """Generate vector embeddings for text chunks and queries."""

    def __init__(self, api_key: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.VOYAGE_API_KEY
        self._use_voyage = bool(self.api_key)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts (documents/chunks).

        Automatically batches into groups of up to 128 for the Voyage API.
        Returns a list of 1024-dimensional vectors.
        """
        if not texts:
            return []

        if self._use_voyage:
            return await self._voyage_embed_batched(texts, input_type="document")

        return [self._tfidf_embed(t) for t in texts]

    async def embed_query(self, query: str) -> list[float]:
        """Generate a single embedding for a search query.

        Uses input_type='query' for Voyage, which optimises for retrieval.
        """
        if self._use_voyage:
            results = await self._voyage_embed_batched([query], input_type="query")
            return results[0]

        return self._tfidf_embed(query)

    # ------------------------------------------------------------------
    # Voyage API helpers
    # ------------------------------------------------------------------

    async def _voyage_embed_batched(
        self, texts: list[str], input_type: str = "document"
    ) -> list[list[float]]:
        """Call the Voyage API in batches of VOYAGE_MAX_BATCH."""
        all_embeddings: list[list[float]] = []
        settings = get_settings()

        async with httpx.AsyncClient(
            timeout=60.0, trust_env=False, proxy=settings.get_proxy()
        ) as client:
            for start in range(0, len(texts), VOYAGE_MAX_BATCH):
                batch = texts[start : start + VOYAGE_MAX_BATCH]
                payload = {
                    "model": VOYAGE_MODEL,
                    "input": batch,
                    "input_type": input_type,
                }
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                resp = await client.post(
                    VOYAGE_API_URL, json=payload, headers=headers
                )
                resp.raise_for_status()
                data = resp.json()
                # Voyage returns {"data": [{"embedding": [...], "index": 0}, ...]}
                batch_embeddings = [
                    item["embedding"]
                    for item in sorted(data["data"], key=lambda x: x["index"])
                ]
                all_embeddings.extend(batch_embeddings)

        return all_embeddings

    # ------------------------------------------------------------------
    # TF-IDF fallback (no external API required)
    # ------------------------------------------------------------------

    @staticmethod
    def _tfidf_embed(text: str) -> list[float]:
        """Produce a deterministic 1024-dim pseudo-embedding from text.

        This is NOT suitable for production search quality — it exists so
        the rest of the pipeline can be exercised without a Voyage API key.
        """
        # Tokenise: lowercase, split on non-alphanumeric
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        if not tokens:
            return [0.0] * VOYAGE_DIMENSION

        # Count term frequencies
        tf = Counter(tokens)

        # Build a sparse vector by hashing each token into a dimension
        vec = [0.0] * VOYAGE_DIMENSION
        for token, count in tf.items():
            # Deterministic bucket from token
            h = int(hashlib.sha256(token.encode()).hexdigest(), 16)
            idx = h % VOYAGE_DIMENSION
            # Use log-scaled TF as the value
            vec[idx] += 1.0 + math.log(count)

        # L2-normalise so cosine similarity works correctly
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]

        return vec
