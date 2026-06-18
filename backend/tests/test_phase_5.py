import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock

async def _seed(client: AsyncClient, email: str = "crawl@test.com"):
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


@pytest.mark.asyncio
async def test_crawler_strips_html_and_chunks(client: AsyncClient):
    headers, ws_id = await _seed(client)

    fake_html = """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <nav>Don't read me</nav>
            <main>
                <h1>Return Policy</h1>
                <p>We accept returns within 30 days.</p>
                <a href="/faq">FAQ</a>
            </main>
            <footer>Copyright 2026</footer>
        </body>
    </html>
    """

    # Mock httpx response
    mock_resp = MagicMock()
    mock_resp.text = fake_html
    mock_resp.raise_for_status = MagicMock()

    # We mock both httpx.AsyncClient.get and process_document so we can verify the extracted text
    with patch("httpx.AsyncClient.get", return_value=mock_resp), \
         patch("docs.crawler.process_document") as mock_proc:
        
        # Trigger crawl API
        resp = await client.post(
            "/api/docs/crawl",
            headers=headers,
            json={"workspace_id": ws_id, "url": "https://example.com"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "started"

        # The crawl runs as a detached background task doing real DB I/O. Wait for
        # it to reach a terminal status rather than sleeping a fixed amount — this
        # is deterministic and (crucially) guarantees the task has finished before
        # the init_db fixture tears down the schema, avoiding a drop_all deadlock.
        import asyncio
        from tests.conftest import TestSessionLocal
        from chat.models import WebsiteSource
        from sqlalchemy import select

        source = None
        for _ in range(200):  # up to ~10s
            await asyncio.sleep(0.05)
            async with TestSessionLocal() as db:
                source = (
                    await db.execute(
                        select(WebsiteSource).filter(WebsiteSource.workspace_id == ws_id)
                    )
                ).scalar_one_or_none()
            if source and source.status in ("completed", "failed"):
                break

        # Verify process_document was called with cleaned text
        assert mock_proc.called
        call_kwargs = mock_proc.call_args.kwargs
        content = call_kwargs["content"].decode("utf-8")

        # It should contain the main content
        assert "We accept returns within 30 days." in content

        # It should NOT contain the nav or footer
        assert "Don't read me" not in content
        assert "Copyright" not in content

        # Verify WebsiteSource was created and completed
        assert source is not None
        assert source.status == "completed"
        assert source.base_url == "https://example.com"
