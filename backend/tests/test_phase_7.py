"""
Phase 7 tests — Workspaces hardened + WIDGET v1

Covers:
  1. GET /api/widget/config  — returns branding fields with defaults.
  2. GET /api/widget/config  — returns workspace custom brand_color / greeting.
  3. POST /api/widget/stream — blocked by quota cap when usage >= cap.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register_and_workspace(client: AsyncClient, email: str):
    """Register a user, login, and return (api_key, workspace_id, auth_headers)."""
    await client.post("/api/auth/register", json={"email": email, "password": "TestPass123!"})
    r = await client.post("/api/auth/login", data={"username": email, "password": "TestPass123!"})
    token = r.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    # Get the auto-created workspace
    from tests.conftest import TestSessionLocal
    from auth.models import User
    from chat.models import Workspace
    async with TestSessionLocal() as s:
        user = (await s.execute(select(User).filter(User.email == email))).scalar_one()
        ws = (await s.execute(select(Workspace).filter(Workspace.owner_id == user.id))).scalar_one()
        api_key = ws.api_key
        ws_id = str(ws.id)

    return api_key, ws_id, auth


# ---------------------------------------------------------------------------
# Test 1: config endpoint returns defaults
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_widget_config_defaults(client: AsyncClient):
    api_key, ws_id, _ = await _register_and_workspace(client, "cfg_default@test.com")

    r = await client.get(
        "/api/widget/config",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    assert r.status_code == 200
    data = r.json()
    assert "brand_color" in data
    assert "greeting" in data
    assert data["brand_color"] == "#4F46E5"   # default


# ---------------------------------------------------------------------------
# Test 2: config endpoint returns custom branding
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_widget_config_custom_branding(client: AsyncClient):
    from tests.conftest import TestSessionLocal
    from chat.models import Workspace

    api_key, ws_id, _ = await _register_and_workspace(client, "cfg_custom@test.com")

    # Patch workspace config directly in DB
    async with TestSessionLocal() as s:
        ws = (await s.execute(select(Workspace).filter(Workspace.id == ws_id))).scalar_one()
        ws.config = {"brand_color": "#FF0000", "greeting": "Welcome to our store!"}
        s.add(ws)
        await s.commit()

    r = await client.get(
        "/api/widget/config",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["brand_color"] == "#FF0000"
    assert data["greeting"] == "Welcome to our store!"


# ---------------------------------------------------------------------------
# Test 3: quota cap blocks requests at limit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_widget_stream_quota_cap_enforced(client: AsyncClient):
    from tests.conftest import TestSessionLocal
    from chat.models import Workspace

    api_key, ws_id, _ = await _register_and_workspace(client, "quota_block@test.com")

    # Set quota_cap=0 so the next request is immediately blocked
    async with TestSessionLocal() as s:
        ws = (await s.execute(select(Workspace).filter(Workspace.id == ws_id))).scalar_one()
        ws.config = {"quota_cap": 0}
        s.add(ws)
        await s.commit()

    r = await client.post(
        "/api/widget/stream",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"session_id": "test-session", "messages": [{"role": "user", "content": "hi"}]}
    )
    assert r.status_code == 402
    assert "quota" in r.json()["detail"].lower()
