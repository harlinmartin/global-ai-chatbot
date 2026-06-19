"""
Full-Text Search service — PostgreSQL keyword search for hybrid RAG.

Uses PostgreSQL's built-in `to_tsvector` / `to_tsquery` over the
`document_chunks.text_content` column. Results are formatted the same
way as qdrant_service.search() so they can be merged with RRF.
"""
from __future__ import annotations
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def keyword_search(
    workspace_id: str | uuid.UUID,
    query: str,
    db: AsyncSession,
    top_k: int = 10,
) -> list[dict]:
    """
    Run a full-text search against document_chunks for the given workspace.

    Returns a list of dicts with the same keys as qdrant_service.search()
    so they can be passed directly to the RRF merger:
        { text, filename, page, document_id, workspace_id, chunk_index, score }

    The `score` here is the PostgreSQL ts_rank (0–1), used only by RRF
    for ordering — not shown to the user.
    """
    ws_id = str(workspace_id)

    # plainto_tsquery turns the user's raw query into a safe boolean FTS query
    # (it handles punctuation, stop words, etc. automatically)
    sql = text("""
        SELECT
            text_content   AS text,
            filename,
            page,
            document_id::text,
            workspace_id::text,
            chunk_index,
            ts_rank(
                to_tsvector('english', text_content),
                plainto_tsquery('english', :query)
            ) AS score
        FROM document_chunks
        WHERE workspace_id = :ws_id
          AND to_tsvector('english', text_content) @@ plainto_tsquery('english', :query)
        ORDER BY score DESC
        LIMIT :top_k
    """)

    result = await db.execute(sql, {"ws_id": ws_id, "query": query, "top_k": top_k})
    rows = result.mappings().all()
    return [dict(r) for r in rows]
