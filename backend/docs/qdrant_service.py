"""
Qdrant service — thin wrapper around the qdrant-client.

Tenant isolation rule:
  Each workspace gets its own collection named  ws_<workspace_id>.
  No cross-workspace queries are ever possible at the client level.
"""

from __future__ import annotations
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from config import settings


def _client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


def _collection_name(workspace_id: str | uuid.UUID) -> str:
    return f"ws_{str(workspace_id).replace('-', '_')}"


def ensure_collection(workspace_id: str | uuid.UUID) -> None:
    """Create the workspace collection if it doesn't exist yet."""
    client = _client()
    name = _collection_name(workspace_id)
    existing = [c.name for c in client.get_collections().collections]
    if name not in existing:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=settings.embedding_dim,
                distance=Distance.COSINE,
            ),
        )


def upsert_chunks(
    workspace_id: str | uuid.UUID,
    points: list[dict],
) -> None:
    """
    Upsert vector points into the workspace collection.

    Each point dict must have:
      id: str (UUID)
      vector: list[float]
      payload: dict (document_id, chunk_index, text_preview, etc.)
    """
    client = _client()
    name = _collection_name(workspace_id)
    qdrant_points = [
        PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"])
        for p in points
    ]
    client.upsert(collection_name=name, points=qdrant_points)


def delete_by_document(
    workspace_id: str | uuid.UUID,
    document_id: str | uuid.UUID,
) -> None:
    """Delete all vectors that belong to a specific document."""
    client = _client()
    name = _collection_name(workspace_id)
    client.delete(
        collection_name=name,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=str(document_id)),
                )
            ]
        ),
    )


def search(
    workspace_id: str | uuid.UUID,
    query_vector: list[float],
    top_k: int = 5,
) -> list[dict]:
    """
    Vector similarity search within a workspace collection.
    Returns a list of payload dicts for the top-k results.
    Used in Phase 4 (RAG).
    """
    client = _client()
    name = _collection_name(workspace_id)
    results = client.search(
        collection_name=name,
        query_vector=query_vector,
        limit=top_k,
        with_payload=True,
    )
    return [
        {"score": r.score, **r.payload}
        for r in results
    ]
