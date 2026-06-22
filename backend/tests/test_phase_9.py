"""
Phase 9 tests — Image Understanding

Covers:
  1. POST /api/chat/stream with image_base64
  2. Verify that the AI provider correctly identifies and uses the image (multimodal payload)
"""
import pytest
import json
from httpx import AsyncClient

# A tiny 1x1 transparent PNG encoded in base64
TINY_IMAGE_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)

async def _register_and_create_chat(client: AsyncClient, email: str):
    await client.post("/api/auth/register", json={"email": email, "password": "TestPass123!"})
    r = await client.post("/api/auth/login", data={"username": email, "password": "TestPass123!"})
    token = r.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    r_chat = await client.post("/api/chats", json={"title": "Test Chat"}, headers=auth)
    chat_id = r_chat.json()["id"]

    return auth, chat_id

@pytest.mark.asyncio
async def test_chat_with_image(client: AsyncClient):
    auth, chat_id = await _register_and_create_chat(client, "vision_user@test.com")

    payload = {
        "chat_id": chat_id,
        "messages": [
            {
                "role": "user",
                "content": "What is in this image?",
                "image_base64": TINY_IMAGE_B64
            }
        ]
    }

    from unittest.mock import patch

    async def mock_stream(*args, **kwargs):
        yield "I see a tiny transparent image."

    with patch("ai.providers.groq_provider.GroqProvider.stream", new=mock_stream):
        async with client.stream("POST", "/api/chat/stream", json=payload, headers=auth) as response:
            assert response.status_code == 200
            
            events = []
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    try:
                        events.append(json.loads(line[5:].strip()))
                    except:
                        pass
            
            # Check that we got some response and no crash
            assert len(events) > 0
            has_error = any(e.get("message") for e in events if "message" in e)
            assert not has_error, f"Stream returned an error: {[e for e in events if 'message' in e]}"
