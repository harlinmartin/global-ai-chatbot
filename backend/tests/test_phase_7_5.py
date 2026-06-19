"""
Phase 7.5 tests — Hybrid Search (Vector + Keyword + RRF Fusion)

Covers:
  1. Postgres FTS keyword search works and returns TS rank.
  2. RRF merger correctly combines results.
  3. `rag.get_context` calls both and returns merged results.
"""
import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from docs.fts_service import keyword_search
from docs.rag import _rrf_merge, get_context
from chat.models import DocumentChunk


@pytest.mark.asyncio
async def test_fts_keyword_search(init_db):
    from tests.conftest import TestSessionLocal
    async with TestSessionLocal() as db:
        from auth.models import User
        from chat.models import Workspace, Document
        
        user = User(email="hybrid@test.com", password="x")
        db.add(user)
        await db.commit()
        await db.refresh(user)

        ws = Workspace(owner_id=user.id, name="Test WS")
        db.add(ws)
        await db.commit()
        await db.refresh(ws)
        ws_id = ws.id

        doc = Document(workspace_id=ws_id, filename="policy.pdf")
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        doc_id = doc.id

        # Seed chunks
        db.add_all([
            DocumentChunk(
                document_id=doc_id, workspace_id=ws_id, chunk_index=0,
                text_preview="refunds", text_content="Our refund policy gives you 30 days.",
                filename="policy.pdf", qdrant_point_id="1"
            ),
            DocumentChunk(
                document_id=doc_id, workspace_id=ws_id, chunk_index=1,
                text_preview="shipping", text_content="Shipping is fast via FedEx.",
                filename="policy.pdf", qdrant_point_id="2"
            ),
            DocumentChunk(
                document_id=doc_id, workspace_id=ws_id, chunk_index=2,
                text_preview="refunds fast", text_content="If you want a fast refund, email us.",
                filename="policy.pdf", qdrant_point_id="3"
            )
        ])
        await db.commit()

        # Search for "refund"
        results = await keyword_search(str(ws_id), "refund", db, top_k=5)
        
        # Should return 2 chunks, ranked by relevance
        assert len(results) == 2
        texts = [r["text"] for r in results]
        assert any("Our refund policy" in t for t in texts)
        assert any("fast refund" in t for t in texts)


def test_rrf_merge():
    # Simulate vector search returning A, B, C
    vector = [
        {"text": "A", "score": 0.9},
        {"text": "B", "score": 0.8},
        {"text": "C", "score": 0.7},
    ]
    # Simulate keyword search returning B, D, A
    keyword = [
        {"text": "B", "score": 0.5},  # TS rank
        {"text": "D", "score": 0.4},
        {"text": "A", "score": 0.1},
    ]

    # Merge top 3
    merged = _rrf_merge(vector, keyword, top_k=3)

    # B was rank 2 (vector) and rank 1 (keyword). 1/62 + 1/61
    # A was rank 1 (vector) and rank 3 (keyword). 1/61 + 1/63
    # B > A > D/C
    assert len(merged) == 3
    assert merged[0]["text"] == "B"
    assert merged[1]["text"] == "A"
    
    # C was rank 3 (vector), D was rank 2 (keyword)
    # C score: 1/63. D score: 1/62. D > C
    assert merged[2]["text"] == "D"


@pytest.mark.asyncio
async def test_get_context_hybrid():
    from unittest.mock import patch, AsyncMock

    ws_id = uuid.uuid4()
    
    vector_mock = [
        {"text": "Semantic match about money return", "filename": "1.pdf", "page": 1},
        {"text": "Exact word: refund", "filename": "1.pdf", "page": 2},
    ]
    keyword_mock = [
        {"text": "Exact word: refund", "filename": "1.pdf", "page": 2},
        {"text": "Another refund mention", "filename": "2.pdf", "page": None},
    ]

    with patch("docs.embedder.embed_texts", new_callable=AsyncMock) as mock_embed, \
         patch("docs.qdrant_service.search", return_value=vector_mock), \
         patch("docs.fts_service.keyword_search", new_callable=AsyncMock, return_value=keyword_mock):
        
        mock_embed.return_value = [[0.1, 0.2]]

        context_str, raw_chunks = await get_context(ws_id, "refund policy", db=AsyncMock(), top_k=5)
        
        # Should deduplicate "Exact word: refund"
        assert len(raw_chunks) == 3
        
        # Check context formatting (both page and chunk formatting depending on presence)
        assert "p.2" in context_str
        assert "Semantic match" in context_str
        assert "Another refund mention" in context_str
