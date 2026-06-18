"""
Document processor — the core Phase 3 pipeline.

Given an uploaded file and a workspace_id it:
  1. Extracts raw text  (PDF via pypdf, plain text as-is)
  2. Chunks the text    (512-token chunks, 50-token overlap)
  3. Embeds each chunk  (bge-small via embedder.py)
  4. Stores in Qdrant   (one point per chunk)
  5. Stores in PG       (DocumentChunk rows)
  6. Flips Document.status → "ready" (or "failed" on error)
"""

from __future__ import annotations
import uuid
import io
import tiktoken
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from chat.models import Document, DocumentChunk
from docs import embedder, qdrant_service

CHUNK_TOKENS = 512
OVERLAP_TOKENS = 50


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def _extract_text(filename: str, content: bytes) -> str:
    """Extract raw text from file bytes. Supports PDF and plain text."""
    if filename.lower().endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)
    # Treat everything else as plain text (utf-8, fallback to latin-1)
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _chunk_text(text: str) -> list[str]:
    """
    Split text into overlapping token-based chunks.
    Returns a list of raw text strings (not token ids).
    """
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + CHUNK_TOKENS, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(enc.decode(chunk_tokens))
        if end == len(tokens):
            break
        start += CHUNK_TOKENS - OVERLAP_TOKENS
    return chunks


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

async def process_document(
    doc_id: str,
    workspace_id: str,
    filename: str,
    content: bytes,
    db: AsyncSession,
) -> None:
    """
    Run the full extract → chunk → embed → store pipeline.
    Updates Document.status to 'ready' on success, 'failed' on error.
    Call this in the background after creating the Document row.
    """
    # Fetch the Document row
    result = await db.execute(select(Document).filter(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        return

    try:
        # 1. Extract
        text = _extract_text(filename, content)
        if not text.strip():
            raise ValueError("No text could be extracted from the file.")

        # 2. Chunk
        chunks = _chunk_text(text)

        # 3. Embed (batch call — one network/CPU round-trip)
        vectors = await embedder.embed_texts(chunks)

        # 4. Ensure the workspace Qdrant collection exists
        qdrant_service.ensure_collection(workspace_id)

        # 5. Build Qdrant points + PG rows
        qdrant_points: list[dict] = []
        db_chunks: list[DocumentChunk] = []

        for i, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
            point_id = str(uuid.uuid4())
            qdrant_points.append({
                "id": point_id,
                "vector": vector,
                "payload": {
                    "document_id": str(doc_id),
                    "workspace_id": str(workspace_id),
                    "chunk_index": i,
                    "text": chunk_text,
                    "filename": filename,
                },
            })
            db_chunks.append(DocumentChunk(
                document_id=doc_id,
                workspace_id=workspace_id,
                chunk_index=i,
                text_preview=chunk_text[:200],
                qdrant_point_id=point_id,
            ))

        # 6. Store in Qdrant
        qdrant_service.upsert_chunks(workspace_id, qdrant_points)

        # 7. Store chunks in PG
        for chunk in db_chunks:
            db.add(chunk)

        # 8. Update document status
        doc.status = "ready"
        doc.chunk_count = len(chunks)
        db.add(doc)
        await db.commit()

    except Exception as exc:
        doc.status = "failed"
        doc.error = str(exc)[:500]
        db.add(doc)
        await db.commit()
        raise
