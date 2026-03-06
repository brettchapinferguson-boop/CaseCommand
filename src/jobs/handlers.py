"""
CaseCommand — Job Handlers

Handler functions for background jobs.  Each handler receives the full
job row dict and a Supabase client, and returns a result dict.

Handler signature::

    async def handle_xxx(job: dict, supabase_client) -> dict:
        ...
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Storage bucket for uploaded case files
FILES_BUCKET = "case-files"


# ------------------------------------------------------------------
# extract_text
# ------------------------------------------------------------------

async def handle_extract_text(job: dict, supabase_client) -> dict:
    """
    Download a file from storage, extract text, chunk it,
    and store the chunks in ``document_chunks``.

    Expected payload keys:
        file_id      — UUID of the uploaded_files row
        org_id       — (also on the job row itself)
    """
    from src.extraction.extractor import TextExtractor
    from src.extraction.chunker import TextChunker

    payload = job.get("payload", {})
    file_id = payload["file_id"]
    org_id = job["org_id"]

    # 1. Fetch file metadata
    file_row = (
        supabase_client.table("uploaded_files")
        .select("*")
        .eq("id", file_id)
        .single()
        .execute()
    ).data
    if not file_row:
        raise ValueError(f"uploaded_files row not found: {file_id}")

    storage_path = file_row["storage_path"]
    file_type = file_row["file_type"]
    original_filename = file_row.get("original_filename", "file")

    # 2. Mark file as processing
    supabase_client.table("uploaded_files").update(
        {"status": "processing"}
    ).eq("id", file_id).execute()

    # 3. Download to a temp file
    try:
        file_data = supabase_client.storage.from_(FILES_BUCKET).download(storage_path)
    except Exception as exc:
        supabase_client.table("uploaded_files").update(
            {"status": "error", "metadata": {"error": str(exc)}}
        ).eq("id", file_id).execute()
        raise

    suffix = Path(original_filename).suffix or f".{file_type}"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_data)
        tmp_path = tmp.name

    # 4. Extract text
    try:
        extraction = TextExtractor.extract(tmp_path, file_type)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # 5. Chunk the extracted text
    chunker = TextChunker()
    chunks = chunker.chunk(extraction.text, metadata={
        "file_id": file_id,
        "source": original_filename,
    })

    # 6. Store chunks in document_chunks
    chunk_rows = []
    for idx, chunk in enumerate(chunks):
        chunk_rows.append({
            "file_id": file_id,
            "org_id": org_id,
            "chunk_index": idx,
            "content": chunk["content"],
            "token_count": chunk.get("token_count"),
            "page_number": chunk.get("page_number"),
            "metadata": chunk.get("metadata", {}),
        })

    if chunk_rows:
        supabase_client.table("document_chunks").insert(chunk_rows).execute()

    # 7. Update file status
    supabase_client.table("uploaded_files").update({
        "status": "ready",
        "metadata": {
            "page_count": extraction.metadata.get("page_count"),
            "word_count": extraction.metadata.get("word_count"),
            "chunk_count": len(chunk_rows),
            "needs_ocr": extraction.needs_ocr,
        },
    }).eq("id", file_id).execute()

    logger.info(
        "extract_text complete  file=%s  chunks=%d",
        file_id, len(chunk_rows),
    )
    return {
        "file_id": file_id,
        "chunk_count": len(chunk_rows),
        "word_count": extraction.metadata.get("word_count", 0),
        "needs_ocr": extraction.needs_ocr,
    }


# ------------------------------------------------------------------
# generate_embeddings
# ------------------------------------------------------------------

async def handle_generate_embeddings(job: dict, supabase_client) -> dict:
    """
    Generate vector embeddings for all chunks of a file and store
    them in the ``embedding`` column of ``document_chunks``.

    Expected payload keys:
        file_id  — UUID of the uploaded_files row whose chunks need embeddings
    """
    from src.rag.embeddings import EmbeddingService
    from src.rag.vector_store import VectorStore

    payload = job.get("payload", {})
    file_id = payload["file_id"]

    # 1. Load chunks that don't have embeddings yet
    result = (
        supabase_client.table("document_chunks")
        .select("id, content")
        .eq("file_id", file_id)
        .is_("embedding", "null")
        .order("chunk_index")
        .execute()
    )
    chunks = result.data or []

    if not chunks:
        logger.info("No chunks needing embeddings for file %s", file_id)
        return {"file_id": file_id, "embedded_count": 0}

    # 2. Generate embeddings in batch
    embedding_service = EmbeddingService()
    texts = [c["content"] for c in chunks]
    embeddings = await embedding_service.embed_batch(texts)

    # 3. Store embeddings
    vector_store = VectorStore(supabase_client)
    await vector_store.store_embeddings(
        chunk_ids=[c["id"] for c in chunks],
        embeddings=embeddings,
    )

    logger.info(
        "generate_embeddings complete  file=%s  embedded=%d",
        file_id, len(chunks),
    )
    return {"file_id": file_id, "embedded_count": len(chunks)}


# ------------------------------------------------------------------
# process_file  (meta-job: extract_text -> generate_embeddings)
# ------------------------------------------------------------------

async def handle_process_file(job: dict, supabase_client) -> dict:
    """
    Full file processing pipeline: extract text, chunk, then embed.

    Expected payload keys:
        file_id  — UUID of the uploaded_files row
    """
    # Step 1: extract text and chunk
    extract_result = await handle_extract_text(job, supabase_client)

    # Step 2: generate embeddings (only if we got chunks)
    embed_result = {"embedded_count": 0}
    if extract_result.get("chunk_count", 0) > 0:
        embed_result = await handle_generate_embeddings(job, supabase_client)

    return {
        "file_id": extract_result["file_id"],
        "chunk_count": extract_result.get("chunk_count", 0),
        "embedded_count": embed_result.get("embedded_count", 0),
        "word_count": extract_result.get("word_count", 0),
        "needs_ocr": extract_result.get("needs_ocr", False),
    }
