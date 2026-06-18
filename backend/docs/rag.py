"""
RAG Service — handles retrieval and context formatting.
"""

from __future__ import annotations
import uuid
from docs import embedder, qdrant_service

async def get_context(workspace_id: str | uuid.UUID, query: str, top_k: int = 5) -> tuple[str, list[dict]]:
    """
    Given a user query, embed it, search Qdrant for top_k matches,
    and return a formatted context string + the raw chunks for logging.
    """
    # 1. Embed the user's query
    vectors = await embedder.embed_texts([query])
    query_vector = vectors[0]

    # 2. Search Qdrant
    try:
        results = qdrant_service.search(workspace_id, query_vector, top_k=top_k)
    except Exception:
        # If Qdrant is down or collection doesn't exist, gracefully return empty context
        return "", []

    # 3. Format the context
    if not results:
        return "", []

    context_str = "[CONTEXT]\n"
    for idx, r in enumerate(results):
        text = r.get("text", "")
        filename = r.get("filename", "unknown")
        context_str += f"--- Document: {filename} (Chunk {idx+1}) ---\n{text}\n\n"
    
    context_str += "You MUST use the above context to answer the user's question. If the answer is not contained in the context, clearly state that you don't know based on the provided documents.\n"

    return context_str, results
