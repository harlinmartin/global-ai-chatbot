"""
test_phase_3.py — Document upload & knowledge base pipeline tests.

Qdrant is mocked so tests run without a running Qdrant container.
embed_texts is mocked so no model download happens.
tiktoken is mocked so no vocab download happens.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_heavy_deps():
    """
    Patch out all network/heavy-download dependencies for every Phase-3 test:
      1. docs.embedder.embed_texts   → returns fake 384-dim vectors
      2. docs.qdrant_service._client → returns a MagicMock (no Qdrant needed)
      3. docs.processor.tiktoken     → returns a MagicMock encoder (no vocab download)
    """
    def _fake_qdrant():
        m = MagicMock()
        m.get_collections.return_value.collections = []
        return m

    async def _fake_embed(texts):
        return [[0.1] * 384 for _ in texts]

    fake_enc = MagicMock()
    fake_enc.encode.side_effect = lambda t: list(t.encode("utf-8"))
    fake_enc.decode.side_effect = lambda toks: bytes(toks).decode("utf-8", errors="replace")

    with patch("docs.embedder.embed_texts", new=AsyncMock(side_effect=_fake_embed)), \
         patch("docs.qdrant_service._client", side_effect=_fake_qdrant), \
         patch("docs.processor.tiktoken") as mock_tiktoken:
        mock_tiktoken.get_encoding.return_value = fake_enc
        yield


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _seed(client: AsyncClient, email: str = "docstest@test.com"):
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

    return headers, str(ws.id)


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

async def test_upload_txt_file(client: AsyncClient):
    """Upload a .txt file → status==ready, chunk_count>0."""
    headers, ws_id = await _seed(client)
    resp = await client.post(
        "/api/docs/upload",
        headers=headers,
        data={"workspace_id": ws_id},
        files={"file": ("faq.txt", b"Q: What is this?\nA: A test.", "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ready"
    assert body["chunk_count"] > 0
    assert body["filename"] == "faq.txt"


async def test_upload_pdf_file(client: AsyncClient):
    """Upload a minimal PDF — must not 500."""
    import io
    from pypdf import PdfWriter

    headers, ws_id = await _seed(client)
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)

    resp = await client.post(
        "/api/docs/upload",
        headers=headers,
        data={"workspace_id": ws_id},
        files={"file": ("doc.pdf", buf.getvalue(), "application/pdf")},
    )
    assert resp.status_code in (200, 400), resp.text


async def test_upload_unsupported_type(client: AsyncClient):
    """Unsupported extension → 400 with helpful message."""
    headers, ws_id = await _seed(client)
    resp = await client.post(
        "/api/docs/upload",
        headers=headers,
        data={"workspace_id": ws_id},
        files={"file": ("bad.exe", b"MZ\x90", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert "Unsupported" in resp.json()["detail"]


async def test_upload_empty_file(client: AsyncClient):
    """Empty file → 400."""
    headers, ws_id = await _seed(client)
    resp = await client.post(
        "/api/docs/upload",
        headers=headers,
        data={"workspace_id": ws_id},
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

async def test_list_documents(client: AsyncClient):
    """Uploaded doc appears in the list."""
    headers, ws_id = await _seed(client)
    await client.post(
        "/api/docs/upload",
        headers=headers,
        data={"workspace_id": ws_id},
        files={"file": ("listed.txt", b"Hello world.", "text/plain")},
    )
    resp = await client.get(f"/api/docs/?workspace_id={ws_id}", headers=headers)
    assert resp.status_code == 200
    assert any(d["filename"] == "listed.txt" for d in resp.json())


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

async def test_delete_document(client: AsyncClient):
    """Deleted doc disappears from the list."""
    headers, ws_id = await _seed(client)
    upload = await client.post(
        "/api/docs/upload",
        headers=headers,
        data={"workspace_id": ws_id},
        files={"file": ("todelete.txt", b"Some content.", "text/plain")},
    )
    doc_id = upload.json()["id"]

    del_resp = await client.delete(f"/api/docs/{doc_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"

    list_resp = await client.get(f"/api/docs/?workspace_id={ws_id}", headers=headers)
    assert not any(d["id"] == doc_id for d in list_resp.json())


# ---------------------------------------------------------------------------
# Cross-workspace isolation
# ---------------------------------------------------------------------------

async def test_cross_workspace_delete_denied(client: AsyncClient):
    """User B cannot delete User A's document."""
    headers_a, ws_a = await _seed(client, "usera@test.com")

    await client.post("/api/auth/register", json={"email": "userb@test.com", "password": "TestPass123!"})
    r = await client.post("/api/auth/login", data={"username": "userb@test.com", "password": "TestPass123!"})
    headers_b = {"Authorization": f"Bearer {r.json()['access_token']}"}

    upload = await client.post(
        "/api/docs/upload",
        headers=headers_a,
        data={"workspace_id": ws_a},
        files={"file": ("secret.txt", b"User A secret.", "text/plain")},
    )
    doc_id = upload.json()["id"]

    resp = await client.delete(f"/api/docs/{doc_id}", headers=headers_b)
    assert resp.status_code == 404
