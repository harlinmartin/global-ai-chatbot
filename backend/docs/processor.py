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

def _extract_pages(filename: str, content: bytes) -> list[tuple[str, int | None]]:
    """
    Extract text from file bytes as a list of (text, page) tuples.

    For PDFs each tuple is one page with a 1-based page number, so citations can
    point at the exact page. For everything else (plain text, crawled HTML) the
    whole document is a single tuple with page=None.
    """
    if filename.lower().endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        return [(page.extract_text() or "", i + 1) for i, page in enumerate(reader.pages)]
    # Treat everything else as plain text (utf-8, fallback to latin-1)
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    return [(text, None)]


def _extract_text(filename: str, content: bytes) -> str:
    """Backwards-compatible flat text extraction (no page boundaries)."""
    return "\n\n".join(text for text, _ in _extract_pages(filename, content))


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


def _chunk_pages(pages: list[tuple[str, int | None]]) -> list[tuple[str, int | None]]:
    """
    Chunk each page independently so every chunk carries the page it came from.
    Chunking per page (rather than over the whole document) keeps a chunk from
    straddling a page boundary, which would make its citation ambiguous.
    Returns a list of (chunk_text, page) tuples.
    """
    chunks: list[tuple[str, int | None]] = []
    for text, page in pages:
        if not text.strip():
            continue
        for chunk in _chunk_text(text):
            chunks.append((chunk, page))
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
        # 1. Extract (page-aware)
        pages = _extract_pages(filename, content)
        if not any(text.strip() for text, _ in pages):
            raise ValueError("No text could be extracted from the file.")

        # 2. Chunk (each chunk keeps the page it came from)
        chunks_with_pages = _chunk_pages(pages)
        chunks = [text for text, _ in chunks_with_pages]

        # 3. Embed (batch call — one network/CPU round-trip)
        vectors = await embedder.embed_texts(chunks)

        # 4. Ensure the workspace Qdrant collection exists
        qdrant_service.ensure_collection(workspace_id)

        # 5. Build Qdrant points + PG rows
        qdrant_points: list[dict] = []
        db_chunks: list[DocumentChunk] = []

        for i, ((chunk_text, page), vector) in enumerate(zip(chunks_with_pages, vectors)):
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
                    "page": page,
                },
            })
            db_chunks.append(DocumentChunk(
                document_id=doc_id,
                workspace_id=workspace_id,
                chunk_index=i,
                text_preview=chunk_text[:200],
                text_content=chunk_text,
                filename=filename,
                page=page,
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
