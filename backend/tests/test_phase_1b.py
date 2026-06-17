import pytest
import uuid
from httpx import AsyncClient

# DB setup/teardown + get_db override live in conftest.py (NullPool test engine).

async def test_register_returns_201(client: AsyncClient):
    response = await client.post("/api/auth/register", json={"email": "test@example.com", "password": "password123"})
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

async def test_register_duplicate_email_returns_409(client: AsyncClient):
    await client.post("/api/auth/register", json={"email": "test@example.com", "password": "password123"})
    response = await client.post("/api/auth/register", json={"email": "test@example.com", "password": "password123"})
    assert response.status_code == 409

async def test_login_valid_returns_jwt(client: AsyncClient):
    await client.post("/api/auth/register", json={"email": "test@example.com", "password": "password123"})
    response = await client.post("/api/auth/login", data={"username": "test@example.com", "password": "password123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

async def test_login_wrong_password_returns_401(client: AsyncClient):
    await client.post("/api/auth/register", json={"email": "test@example.com", "password": "password123"})
    response = await client.post("/api/auth/login", data={"username": "test@example.com", "password": "wrongpassword"})
    assert response.status_code == 401

async def test_protected_route_without_token_returns_401(client: AsyncClient):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401

@pytest.fixture
async def auth_headers(client: AsyncClient):
    await client.post("/api/auth/register", json={"email": "test@example.com", "password": "password123"})
    response = await client.post("/api/auth/login", data={"username": "test@example.com", "password": "password123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
async def workspace_id(client: AsyncClient, auth_headers):
    # For testing, we need a workspace. Since we don't have a workspace endpoint yet, 
    # we'll create it directly in the db.
    from auth.models import User
    from chat.models import Workspace
    from sqlalchemy import select
    from database import async_session_maker
    
    async with async_session_maker() as session:
        user = (await session.execute(select(User).filter_by(email="test@example.com"))).scalar_one()
        ws = Workspace(owner_id=user.id, name="Test Workspace")
        session.add(ws)
        await session.commit()
        await session.refresh(ws)
        return ws.id

async def test_create_chat_returns_chat_object(client: AsyncClient, auth_headers, workspace_id):
    response = await client.post("/api/chats", json={"title": "My Chat", "workspace_id": str(workspace_id)}, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "My Chat"
    assert "id" in data

async def test_list_chats_returns_array(client: AsyncClient, auth_headers, workspace_id):
    await client.post("/api/chats", json={"title": "Chat 1", "workspace_id": str(workspace_id)}, headers=auth_headers)
    await client.post("/api/chats", json={"title": "Chat 2", "workspace_id": str(workspace_id)}, headers=auth_headers)
    response = await client.get("/api/chats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

async def test_delete_chat_removes_from_db(client: AsyncClient, auth_headers, workspace_id):
    chat_resp = await client.post("/api/chats", json={"title": "To Delete", "workspace_id": str(workspace_id)}, headers=auth_headers)
    chat_id = chat_resp.json()["id"]
    
    del_resp = await client.delete(f"/api/chats/{chat_id}", headers=auth_headers)
    assert del_resp.status_code == 204
    
    get_resp = await client.get("/api/chats", headers=auth_headers)
    assert len(get_resp.json()) == 0

async def test_rename_chat_updates_title(client: AsyncClient, auth_headers, workspace_id):
    chat_resp = await client.post("/api/chats", json={"title": "Old Title", "workspace_id": str(workspace_id)}, headers=auth_headers)
    chat_id = chat_resp.json()["id"]
    
    patch_resp = await client.patch(f"/api/chats/{chat_id}?title=New%20Title", headers=auth_headers)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "New Title"

async def test_message_history_empty_initially(client: AsyncClient, auth_headers, workspace_id):
    chat_resp = await client.post("/api/chats", json={"title": "Chat", "workspace_id": str(workspace_id)}, headers=auth_headers)
    chat_id = chat_resp.json()["id"]
    
    msg_resp = await client.get(f"/api/chats/{chat_id}/messages", headers=auth_headers)
    assert msg_resp.status_code == 200
    assert len(msg_resp.json()) == 0

async def test_message_stored_after_stream(client: AsyncClient, auth_headers, workspace_id):
    # Setup mock provider inside the test
    from unittest.mock import patch, MagicMock
    from tests.test_phase_1a import mock_stream_generator, reset_sse_event_loop
    reset_sse_event_loop()
    
    chat_resp = await client.post("/api/chats", json={"title": "Chat", "workspace_id": str(workspace_id)}, headers=auth_headers)
    chat_id = chat_resp.json()["id"]
    
    with patch("api.chat.get_ai_provider") as mock_factory:
        mock_provider = MagicMock()
        mock_provider.model_name = "test-model"
        mock_provider.stream = lambda msgs, **kw: mock_stream_generator()
        mock_factory.return_value = mock_provider

        resp = await client.post(
            "/api/chat/stream",
            json={"chat_id": chat_id, "messages": [{"role": "user", "content": "hello"}]},
            headers=auth_headers
        )
        assert resp.status_code == 200
        
        # consume the stream
        async for chunk in resp.aiter_text():
            pass

    msg_resp = await client.get(f"/api/chats/{chat_id}/messages", headers=auth_headers)
    assert msg_resp.status_code == 200
    messages = msg_resp.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "hello"
    assert messages[1]["role"] == "assistant"
    assert "Hello, world!" in messages[1]["content"]
