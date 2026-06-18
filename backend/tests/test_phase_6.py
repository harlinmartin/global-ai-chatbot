"""
test_phase_6.py — Citations in the SSE `done` event + persistence.

Covers:
  * processor extracts page-tagged chunks (PDF page numbers / None for the rest)
  * build_sources de-duplicates chunks into {name, type, page?} citation sources
  * the chat `done` event carries those sources
  * sources are persisted on the assistant message and survive a history reload
"""

import json
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


# ---------------------------------------------------------------------------
# Unit-level: page-aware extraction / chunking / source building
# ---------------------------------------------------------------------------

def test_extract_pages_plain_text_has_no_page():
    from docs.processor import _extract_pages
    pages = _extract_pages("notes.txt", b"hello world")
    assert pages == [("hello world", None)]


def test_chunk_pages_tags_each_chunk_with_its_page():
    from docs.processor import _chunk_pages
    chunks = _chunk_pages([("first page text", 1), ("second page text", 2), ("", 3)])
    pages = [page for _, page in chunks]
    # Empty pages are dropped; the rest keep their page numbers.
    assert pages == [1, 2]


def test_build_sources_dedupes_and_classifies():
    from api.chat import build_sources
    chunks = [
        {"filename": "manual.pdf", "page": 3, "text": "a"},
        {"filename": "manual.pdf", "page": 3, "text": "b"},   # duplicate (name, page)
        {"filename": "manual.pdf", "page": 7, "text": "c"},   # same file, new page
        {"filename": "https://example.com/faq", "page": None, "text": "d"},
        {"text": "no filename — skipped"},
    ]
    sources = build_sources(chunks)

    assert sources == [
        {"name": "manual.pdf", "type": "file", "page": 3},
        {"name": "manual.pdf", "type": "file", "page": 7},
        {"name": "https://example.com/faq", "type": "url"},
    ]


# ---------------------------------------------------------------------------
# Integration: sources in the SSE `done` event + persistence
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ai_and_rag():
    class FakeProvider:
        @property
        def model_name(self):
            return "fake-model"

        async def stream(self, messages, **kwargs):
            yield "Grounded "
            yield "answer."

    def _fake_qdrant_search(*args, **kwargs):
        return [
            {"text": "chunk a", "filename": "manual.pdf", "page": 3, "score": 0.99},
            {"text": "chunk b", "filename": "manual.pdf", "page": 3, "score": 0.90},  # dup
            {"text": "chunk c", "filename": "https://example.com/faq", "page": None, "score": 0.80},
        ]

    with patch("api.chat.get_ai_provider", return_value=FakeProvider()), \
         patch("docs.embedder.embed_texts", new=AsyncMock(return_value=[[0.1] * 384])), \
         patch("docs.qdrant_service.search", side_effect=_fake_qdrant_search):
        yield


async def _seed(client: AsyncClient, email: str = "cite@test.com"):
    await client.post("/api/auth/register", json={"email": email, "password": "TestPass123!"})
    r = await client.post("/api/auth/login", data={"username": email, "password": "TestPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _parse_done_sources(sse_text: str) -> list[dict]:
    """Pull the `sources` array out of the SSE `done` event."""
    for line in sse_text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            try:
                data = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            if "sources" in data and "model" in data:
                return data["sources"]
    raise AssertionError("No done event with sources found in SSE stream")


async def test_chat_done_event_carries_and_persists_sources(client: AsyncClient, mock_ai_and_rag):
    headers = await _seed(client)
    chat_id = (await client.post("/api/chats", headers=headers, json={"title": "Cite"})).json()["id"]

    resp = await client.post(
        "/api/chat/stream",
        headers=headers,
        json={"chat_id": chat_id, "messages": [{"role": "user", "content": "What is the return policy?"}]},
    )
    assert resp.status_code == 200

    # The done event carries de-duplicated, page-tagged citation sources.
    sources = _parse_done_sources(resp.text)
    assert sources == [
        {"name": "manual.pdf", "type": "file", "page": 3},
        {"name": "https://example.com/faq", "type": "url"},
    ]

    # Sources persist on the assistant message and survive a history reload.
    msgs = (await client.get(f"/api/chats/{chat_id}/messages", headers=headers)).json()
    assistant = [m for m in msgs if m["role"] == "assistant"][0]
    persisted = assistant["metadata_"]["sources"]
    assert persisted == sources
