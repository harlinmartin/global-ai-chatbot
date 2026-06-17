"""
Phase 1A Test Suite
====================
Tests for:
  - Health endpoint
  - AI provider factory
  - Groq provider interface
  - Chat SSE stream (mocked Groq, no real API calls)
  - SSE event format validation
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ─────────────────────────────────────────────
# 1. Health endpoint
# ─────────────────────────────────────────────

class TestHealth:
    async def test_health_returns_200(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200

    async def test_health_has_required_fields(self, client):
        data = (await client.get("/health")).json()
        assert "status" in data
        assert "provider" in data
        assert "model" in data

    async def test_health_status_is_ok(self, client):
        data = (await client.get("/health")).json()
        assert data["status"] == "ok"

    async def test_health_provider_is_groq(self, client):
        """Default provider must be groq per .env"""
        data = (await client.get("/health")).json()
        assert data["provider"] == "groq"


# ─────────────────────────────────────────────
# 2. AI Provider Factory
# ─────────────────────────────────────────────

class TestProviderFactory:
    def test_factory_returns_groq_for_groq_setting(self):
        with patch("ai.factory.settings") as mock_settings:
            mock_settings.ai_provider = "groq"
            mock_settings.groq_api_key = "test-key"
            mock_settings.groq_model = "llama-3.1-8b-instant"
            with patch("ai.providers.groq_provider.settings", mock_settings):
                from ai.factory import get_ai_provider
                provider = get_ai_provider()
                assert provider.__class__.__name__ == "GroqProvider"

    def test_factory_returns_ollama_for_ollama_setting(self):
        with patch("ai.factory.settings") as mock_settings:
            mock_settings.ai_provider = "ollama"
            mock_settings.ollama_base_url = "http://localhost:11434"
            mock_settings.ollama_model = "qwen3:8b"
            with patch("ai.providers.ollama_provider.settings", mock_settings):
                from ai.factory import get_ai_provider
                provider = get_ai_provider()
                assert provider.__class__.__name__ == "OllamaProvider"

    def test_factory_raises_on_unknown_provider(self):
        with patch("ai.factory.settings") as mock_settings:
            mock_settings.ai_provider = "unknown_model_xyz"
            from ai.factory import get_ai_provider
            with pytest.raises(ValueError, match="Unknown AI_PROVIDER"):
                get_ai_provider()


# ─────────────────────────────────────────────
# 3. Groq Provider interface contract
# ─────────────────────────────────────────────

class TestGroqProvider:
    def test_groq_provider_has_model_name(self):
        with patch("ai.providers.groq_provider.settings") as s:
            s.groq_api_key = "test"
            s.groq_model = "llama-3.1-8b-instant"
            from ai.providers.groq_provider import GroqProvider
            p = GroqProvider()
            assert isinstance(p.model_name, str)
            assert len(p.model_name) > 0

    def test_groq_provider_has_max_tokens(self):
        with patch("ai.providers.groq_provider.settings") as s:
            s.groq_api_key = "test"
            s.groq_model = "llama-3.1-8b-instant"
            from ai.providers.groq_provider import GroqProvider
            p = GroqProvider()
            assert isinstance(p.max_tokens, int)
            assert p.max_tokens > 0

    async def test_groq_provider_stream_yields_strings(self):
        """stream() must yield str tokens — mocked to avoid real API call."""
        with patch("ai.providers.groq_provider.settings") as s:
            s.groq_api_key = "test"
            s.groq_model = "llama-3.1-8b-instant"

            # Mock the groq client
            mock_chunk = MagicMock()
            mock_chunk.choices = [MagicMock()]
            mock_chunk.choices[0].delta.content = "hello"

            async def mock_aiter():
                yield mock_chunk

            mock_stream = MagicMock()
            mock_stream.__aiter__ = lambda self: mock_aiter()

            mock_create = AsyncMock(return_value=mock_stream)

            from ai.providers.groq_provider import GroqProvider
            p = GroqProvider()
            p.client.chat.completions.create = mock_create

            tokens = []
            async for token in p.stream([{"role": "user", "content": "hi"}]):
                tokens.append(token)

            assert len(tokens) > 0
            assert all(isinstance(t, str) for t in tokens)


# ─────────────────────────────────────────────
# 4. Chat SSE stream endpoint
# ─────────────────────────────────────────────

async def mock_stream_generator(tokens=None):
    """Yields fake tokens like a real provider."""
    for token in (tokens or ["Hello", ", ", "world", "!"]):
        yield token


def reset_sse_event_loop():
    """
    sse-starlette stores an asyncio.Event at module level (AppStatus).
    In tests each test function gets its own event loop, so we must
    reset the cached Event to the current loop before each SSE test.
    """
    import asyncio
    from sse_starlette import sse as sse_mod
    sse_mod.AppStatus.should_exit_event = asyncio.Event()


class TestChatStream:
    async def test_stream_endpoint_returns_200(self, client, chat_id):
        reset_sse_event_loop()
        with patch("api.chat.get_ai_provider") as mock_factory:
            mock_provider = MagicMock()
            mock_provider.model_name = "llama-3.1-8b-instant"
            mock_provider.stream = lambda msgs, **kw: mock_stream_generator()
            mock_factory.return_value = mock_provider

            resp = await client.post(
                "/api/chat/stream",
                json={"chat_id": chat_id, "messages": [{"role": "user", "content": "hi"}]},
            )
            assert resp.status_code == 200

    async def test_stream_content_type_is_event_stream(self, client, chat_id):
        reset_sse_event_loop()
        with patch("api.chat.get_ai_provider") as mock_factory:
            mock_provider = MagicMock()
            mock_provider.model_name = "test-model"
            mock_provider.stream = lambda msgs, **kw: mock_stream_generator()
            mock_factory.return_value = mock_provider

            resp = await client.post(
                "/api/chat/stream",
                json={"chat_id": chat_id, "messages": [{"role": "user", "content": "test"}]},
            )
            assert "text/event-stream" in resp.headers.get("content-type", "")

    async def test_stream_contains_status_events(self, client, chat_id):
        reset_sse_event_loop()
        with patch("api.chat.get_ai_provider") as mock_factory:
            mock_provider = MagicMock()
            mock_provider.model_name = "test-model"
            mock_provider.stream = lambda msgs, **kw: mock_stream_generator()
            mock_factory.return_value = mock_provider

            resp = await client.post(
                "/api/chat/stream",
                json={"chat_id": chat_id, "messages": [{"role": "user", "content": "test"}]},
            )
            body = resp.text
            assert "event: status" in body

    async def test_stream_contains_token_events(self, client, chat_id):
        reset_sse_event_loop()
        with patch("api.chat.get_ai_provider") as mock_factory:
            mock_provider = MagicMock()
            mock_provider.model_name = "test-model"
            mock_provider.stream = lambda msgs, **kw: mock_stream_generator(["Hi"])
            mock_factory.return_value = mock_provider

            resp = await client.post(
                "/api/chat/stream",
                json={"chat_id": chat_id, "messages": [{"role": "user", "content": "test"}]},
            )
            body = resp.text
            assert "event: token" in body

    async def test_stream_contains_done_event(self, client, chat_id):
        reset_sse_event_loop()
        with patch("api.chat.get_ai_provider") as mock_factory:
            mock_provider = MagicMock()
            mock_provider.model_name = "test-model"
            mock_provider.stream = lambda msgs, **kw: mock_stream_generator()
            mock_factory.return_value = mock_provider

            resp = await client.post(
                "/api/chat/stream",
                json={"chat_id": chat_id, "messages": [{"role": "user", "content": "test"}]},
            )
            body = resp.text
            assert "event: done" in body

    async def test_stream_token_data_is_valid_json(self, client, chat_id):
        reset_sse_event_loop()
        with patch("api.chat.get_ai_provider") as mock_factory:
            mock_provider = MagicMock()
            mock_provider.model_name = "test-model"
            mock_provider.stream = lambda msgs, **kw: mock_stream_generator(["test"])
            mock_factory.return_value = mock_provider

            resp = await client.post(
                "/api/chat/stream",
                json={"chat_id": chat_id, "messages": [{"role": "user", "content": "hi"}]},
            )
            body = resp.text
            for line in body.splitlines():
                if line.startswith("data:"):
                    payload = line[5:].strip()
                    parsed = json.loads(payload)  # Must not raise
                    assert isinstance(parsed, dict)

    async def test_stream_rejects_empty_messages(self, client, chat_id):
        reset_sse_event_loop()
        """Empty messages list should still return a valid SSE stream (not 500)."""
        with patch("api.chat.get_ai_provider") as mock_factory:
            mock_provider = MagicMock()
            mock_provider.model_name = "test-model"
            mock_provider.stream = lambda msgs, **kw: mock_stream_generator()
            mock_factory.return_value = mock_provider

            resp = await client.post(
                "/api/chat/stream",
                json={"chat_id": chat_id, "messages": []},
            )
            assert resp.status_code == 200

    async def test_stream_only_sends_last_10_messages(self, client, chat_id):
        reset_sse_event_loop()
        """Context window: only last 10 user messages should be sent to provider."""
        captured_messages = []

        async def capture_stream(msgs, **kw):
            captured_messages.extend(msgs)
            yield "ok"

        with patch("api.chat.get_ai_provider") as mock_factory:
            mock_provider = MagicMock()
            mock_provider.model_name = "test-model"
            mock_provider.stream = capture_stream
            mock_factory.return_value = mock_provider

            # Send 15 messages
            messages = [{"role": "user", "content": f"msg {i}"} for i in range(15)]
            await client.post(
                "/api/chat/stream",
                json={"chat_id": chat_id, "messages": messages},
            )

            # system prompt + 10 messages = 11 total (system is prepended in api/chat.py)
            assert len(captured_messages) <= 11
