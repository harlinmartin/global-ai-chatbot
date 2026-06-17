import pytest
from httpx import AsyncClient
from main import app
from database import get_db
from sqlalchemy import select
from chat.models import Workspace, Chat, Message
from api.widget import IP_RATE_LIMITS

@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Clear rate limits between tests"""
    IP_RATE_LIMITS.clear()
    yield

@pytest.fixture
async def test_workspace():
    from auth.models import User
    import database
    
    async with database.async_session_maker() as s:
        user = User(email="widget@test.com", password="x")
        s.add(user)
        await s.commit()
        await s.refresh(user)

        ws = Workspace(owner_id=user.id, name="Widget WS")
        s.add(ws)
        await s.commit()
        await s.refresh(ws)
        return ws

@pytest.mark.asyncio
async def test_widget_auth_missing_api_key(client: AsyncClient):
    response = await client.post(
        "/api/widget/stream",
        json={"session_id": "123", "messages": []}
    )
    assert response.status_code == 401
    assert "Missing API Key" in response.json()["detail"]

@pytest.mark.asyncio
async def test_widget_auth_invalid_api_key(client: AsyncClient):
    response = await client.post(
        "/api/widget/stream",
        headers={"Authorization": "Bearer invalid_key"},
        json={"session_id": "123", "messages": []}
    )
    assert response.status_code == 401
    assert "Invalid API Key" in response.json()["detail"]

@pytest.mark.asyncio
async def test_widget_origin_check_allowed(client: AsyncClient, test_workspace: Workspace):
    # Setup allowed domains
    async for session in get_db():
        test_workspace.config = {"allowed_domains": ["http://allowed.com"]}
        session.add(test_workspace)
        await session.commit()
        break

    response = await client.post(
        "/api/widget/stream",
        headers={"Authorization": f"Bearer {test_workspace.api_key}"},
        json={
            "session_id": "origin_test", 
            "messages": [{"role": "user", "content": "Hi"}],
            "origin": "http://allowed.com"
        }
    )
    # 200 means allowed
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_widget_origin_check_rejected(client: AsyncClient, test_workspace: Workspace):
    # Setup allowed domains
    async for session in get_db():
        test_workspace.config = {"allowed_domains": ["http://allowed.com"]}
        session.add(test_workspace)
        await session.commit()
        break

    response = await client.post(
        "/api/widget/stream",
        headers={"Authorization": f"Bearer {test_workspace.api_key}"},
        json={
            "session_id": "origin_test", 
            "messages": [{"role": "user", "content": "Hi"}],
            "origin": "http://malicious.com"
        }
    )
    # 403 Forbidden
    assert response.status_code == 403
    assert "Domain not allowed" in response.json()["detail"]

@pytest.mark.asyncio
async def test_widget_rate_limiting(client: AsyncClient, test_workspace: Workspace):
    async for session in get_db():
        test_workspace.config = {}  # clear allowed domains for this test
        session.add(test_workspace)
        await session.commit()
        break
        
    # Send 10 requests (the limit is 10)
    for _ in range(10):
        response = await client.post(
            "/api/widget/stream",
            headers={"Authorization": f"Bearer {test_workspace.api_key}"},
            json={
                "session_id": "rate_limit_test", 
                "messages": [{"role": "user", "content": "Hi"}],
            }
        )
        assert response.status_code == 200

    # The 11th request should be rate limited
    response = await client.post(
        "/api/widget/stream",
        headers={"Authorization": f"Bearer {test_workspace.api_key}"},
        json={
            "session_id": "rate_limit_test", 
            "messages": [{"role": "user", "content": "Hi"}],
        }
    )
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["detail"]
