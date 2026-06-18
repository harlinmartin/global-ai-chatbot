"""
test_phase_4.py — RAG Integration & Evaluation Logging tests.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

@pytest.fixture(autouse=True)
def mock_ai_and_rag():
    """Mock the AI provider and Qdrant so we don't hit real APIs."""
    
    # Mock AI Provider
    class FakeProvider:
        @property
        def model_name(self): return "fake-model"
        
        async def stream(self, messages, **kwargs):
            yield "Hello "
            yield "World!"

    # Mock Qdrant
    def _fake_qdrant_search(*args, **kwargs):
        # Return fake chunks
        return [
            {"text": "Fake chunk 1", "filename": "doc1.txt", "score": 0.99},
            {"text": "Fake chunk 2", "filename": "doc2.txt", "score": 0.85},
        ]

    with patch("api.chat.get_ai_provider", return_value=FakeProvider()), \
         patch("api.widget.get_ai_provider", return_value=FakeProvider()), \
         patch("docs.embedder.embed_texts", new=AsyncMock(return_value=[[0.1]*384])), \
         patch("docs.qdrant_service.search", side_effect=_fake_qdrant_search):
        yield

async def _seed(client: AsyncClient, email: str = "rag@test.com"):
    """Register → login → fetch auto-created workspace → (headers, workspace_id)."""
    await client.post("/api/auth/register", json={"email": email, "password": "TestPass123!"})
    r = await client.post("/api/auth/login", data={"username": email, "password": "TestPass123!"})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    from tests.conftest import TestSessionLocal
    from auth.models import User
    from chat.models import Workspace
    from sqlalchemy import select

    async with TestSessionLocal() as s:
        user = (await s.execute(select(User).filter(User.email == email))).scalar_one()
        ws = (await s.execute(select(Workspace).filter(Workspace.owner_id == user.id))).scalar_one()
        api_key = ws.api_key

    return headers, str(ws.id), api_key

async def test_chat_rag_integration_and_logging(client: AsyncClient):
    """Test standard chat endpoint injects RAG and logs to EvalLog."""
    headers, ws_id, _ = await _seed(client)
    
    # Create a chat
    chat_resp = await client.post("/api/chats", headers=headers, json={"title": "Test Chat"})
    chat_id = chat_resp.json()["id"]

    # Send a message
    stream_resp = await client.post(
        "/api/chat/stream",
        headers=headers,
        json={
            "chat_id": chat_id,
            "messages": [{"role": "user", "content": "What is the return policy?"}]
        }
    )
    
    assert stream_resp.status_code == 200
    
    # Verify the SSE events contain "searching knowledge base"
    text = stream_resp.text
    assert '"step": "searching"' in text
    assert "Hello World!" in text

    # Verify EvalLog was created
    from tests.conftest import TestSessionLocal
    from chat.models import EvalLog
    from sqlalchemy import select
    
    async with TestSessionLocal() as db:
        logs = (await db.execute(select(EvalLog))).scalars().all()
        assert len(logs) == 1
        log = logs[0]
        assert log.question == "What is the return policy?"
        assert log.model_name == "fake-model"
        assert len(log.retrieved_chunks) == 2
        assert log.retrieved_chunks[0]["text"] == "Fake chunk 1"


async def test_widget_rag_integration_and_logging(client: AsyncClient):
    """Test anonymous widget chat injects RAG and logs to EvalLog."""
    _, ws_id, api_key = await _seed(client, "widgetrag@test.com")
    
    # Send anonymous message using API key
    stream_resp = await client.post(
        "/api/widget/stream",
        headers={"api-key": api_key},
        json={
            "session_id": "anon-session-123",
            "messages": [{"role": "user", "content": "How much does it cost?"}]
        }
    )
    
    assert stream_resp.status_code == 200
    text = stream_resp.text
    assert '"step": "searching"' in text
    assert "Hello World!" in text

    # Verify EvalLog
    from tests.conftest import TestSessionLocal
    from chat.models import EvalLog
    from sqlalchemy import select
    
    async with TestSessionLocal() as db:
        logs = (await db.execute(select(EvalLog).filter(EvalLog.workspace_id == ws_id))).scalars().all()
        assert len(logs) == 1
        assert logs[0].question == "How much does it cost?"
