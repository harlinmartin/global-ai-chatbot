"""
RAG Service — Hybrid retrieval (vector + keyword) with RRF fusion.

Phase 7.5 upgrade: instead of pure vector search (Qdrant only), we now
run two searches in parallel and merge results with Reciprocal Rank Fusion
(RRF). This dramatically improves recall for exact terms like product codes,
names, and clause numbers that vector search misses.

RRF formula: score(d) = Σ 1 / (k + rank(d))  where k=60 is a smoothing constant.
"""

from __future__ import annotations
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from docs import embedder, qdrant_service, fts_service


# RRF smoothing constant — 60 is the standard value from the original paper
_RRF_K = 60


def _rrf_merge(
    vector_results: list[dict],
    keyword_results: list[dict],
    top_k: int,
) -> list[dict]:
    """
    Merge two ranked lists using Reciprocal Rank Fusion.

    Each item is identified by its Qdrant point text (unique per chunk).
    Returns the top_k items from the merged ranking.
    """
    scores: dict[str, float] = {}
    # Map from dedup key → the full chunk dict (vector results take precedence)
    chunks: dict[str, dict] = {}

    for rank, item in enumerate(vector_results):
        key = item.get("text", "")[:120]   # first 120 chars as dedup key
        scores[key] = scores.get(key, 0.0) + 1.0 / (_RRF_K + rank + 1)
        chunks[key] = item

    for rank, item in enumerate(keyword_results):
        key = item.get("text", "")[:120]
        scores[key] = scores.get(key, 0.0) + 1.0 / (_RRF_K + rank + 1)
        if key not in chunks:
            chunks[key] = item

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [chunks[k] for k, _ in ranked[:top_k]]


async def get_context(
    workspace_id: str | uuid.UUID,
    query: str,
    db: AsyncSession | None = None,
    top_k: int = 5,
) -> tuple[str, list[dict]]:
    """
    Hybrid retrieval: run vector search (Qdrant) and keyword search (PG FTS)
    in parallel, merge with RRF, return formatted context + raw chunks.

    `db` is optional for backwards compatibility — if None, falls back to
    pure vector search (Phase 4 behaviour).
    """
    # 1. Embed the user's query
    vectors = await embedder.embed_texts([query])
    query_vector = vectors[0]

    # 2. Vector search (always)
    try:
        vector_results = qdrant_service.search(workspace_id, query_vector, top_k=top_k * 2)
    except Exception:
        vector_results = []

    # 3. Keyword search (when a DB session is available)
    keyword_results: list[dict] = []
    if db is not None:
        try:
            keyword_results = await fts_service.keyword_search(
                workspace_id, query, db, top_k=top_k * 2
            )
        except Exception:
            keyword_results = []

    # 4. If both searches returned nothing, return empty context
    if not vector_results and not keyword_results:
        return "", []

    # 5. Merge with RRF (or fall back to vector-only if no keyword results)
    if keyword_results:
        results = _rrf_merge(vector_results, keyword_results, top_k)
    else:
        results = vector_results[:top_k]

    # 6. Format the context string
    context_str = "[CONTEXT]\n"
    for idx, r in enumerate(results):
        text = r.get("text", "")
        filename = r.get("filename", "unknown")
        page = r.get("page")
        location = f"p.{page}" if page else f"chunk {idx + 1}"
        context_str += f"--- Document: {filename} ({location}) ---\n{text}\n\n"

    context_str += (
        "You MUST use the above context to answer the user's question. "
        "If the answer is not contained in the context, clearly state that "
        "you don't know based on the provided documents.\n"
    )

    return context_str, results
