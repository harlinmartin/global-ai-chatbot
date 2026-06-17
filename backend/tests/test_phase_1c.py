"""
Phase 1C Test Suite — Context Handling
======================================
Tests for:
  - Context window: only the last 10 messages are sent to the provider
  - System prompt is always prepended
  - A stored conversation summary is injected into the system prompt
  - Background summarizer: triggers > 30 messages, persists a ChatSummary,
    sets covers_through_message correctly, and is idempotent.

These exercise chat/summarizer.py + api/chat.py, the paths where the
summary column-name bug previously lived.
"""

import uuid
import pytest
from unittest.mock import patch, MagicMock

from tests.test_phase_1a import mock_stream_generator, reset_sse_event_loop


# ── helpers ────────────────────────────────────────────────────────────

async def _seed_messages(chat_id: str, n: int):
    """Insert n alternating user/assistant messages into a chat."""
    from database import async_session_maker
    from chat.models import Message

    cid = uuid.UUID(chat_id)
    async with async_session_maker() as s:
        for i in range(n):
            role = "user" if i % 2 == 0 else "assistant"
            s.add(Message(chat_id=cid, role=role, content=f"msg {i}"))
        await s.commit()


async def _get_messages(chat_id: str):
    from database import async_session_maker
    from chat.models import Message
    from sqlalchemy import select

    cid = uuid.UUID(chat_id)
    async with async_session_maker() as s:
        result = await s.execute(
            select(Message).filter(Message.chat_id == cid).order_by(Message.created_at)
        )
        return result.scalars().all()


async def _get_summaries(chat_id: str):
    from database import async_session_maker
    from chat.models import ChatSummary
    from sqlalchemy import select

    cid = uuid.UUID(chat_id)
    async with async_session_maker() as s:
        result = await s.execute(select(ChatSummary).filter(ChatSummary.chat_id == cid))
        return result.scalars().all()


class _FakeSummaryProvider:
    """Provider stub whose stream() yields a fixed summary."""
    model_name = "fake-summarizer"
    max_tokens = 8192

    async def stream(self, messages, **kwargs):
        yield "SUMMARY_OF_EARLIER_CONVERSATION"


# ── Context window ─────────────────────────────────────────────────────

class TestContextWindow:
    async def test_only_last_10_messages_sent_to_provider(self, client, chat_id):
        reset_sse_event_loop()
        captured = []

        async def capture_stream(msgs, **kw):
            captured.extend(msgs)
            yield "ok"

        with patch("api.chat.get_ai_provider") as factory:
            provider = MagicMock()
            provider.model_name = "test-model"
            provider.stream = capture_stream
            factory.return_value = provider

            messages = [{"role": "user", "content": f"m{i}"} for i in range(20)]
            await client.post(
                "/api/chat/stream",
                json={"chat_id": chat_id, "messages": messages},
            )

        # system + last 10 == 11
        history = [m for m in captured if m["role"] != "system"]
        assert len(history) == 10
        assert history[0]["content"] == "m10"
        assert history[-1]["content"] == "m19"

    async def test_system_prompt_is_prepended(self, client, chat_id):
        reset_sse_event_loop()
        captured = []

        async def capture_stream(msgs, **kw):
            captured.extend(msgs)
            yield "ok"

        with patch("api.chat.get_ai_provider") as factory:
            provider = MagicMock()
            provider.model_name = "test-model"
            provider.stream = capture_stream
            factory.return_value = provider

            await client.post(
                "/api/chat/stream",
                json={"chat_id": chat_id, "messages": [{"role": "user", "content": "hi"}]},
            )

        assert captured[0]["role"] == "system"
        assert "assistant" in captured[0]["content"].lower()

    async def test_stored_summary_is_injected_into_system_prompt(self, client, chat_id):
        reset_sse_event_loop()
        # Pre-store a summary for this chat.
        from database import async_session_maker
        from chat.models import ChatSummary

        async with async_session_maker() as s:
            s.add(ChatSummary(chat_id=uuid.UUID(chat_id), summary="SECRET_SUMMARY_XYZ"))
            await s.commit()

        captured = []

        async def capture_stream(msgs, **kw):
            captured.extend(msgs)
            yield "ok"

        with patch("api.chat.get_ai_provider") as factory:
            provider = MagicMock()
            provider.model_name = "test-model"
            provider.stream = capture_stream
            factory.return_value = provider

            await client.post(
                "/api/chat/stream",
                json={"chat_id": chat_id, "messages": [{"role": "user", "content": "hi"}]},
            )

        assert "SECRET_SUMMARY_XYZ" in captured[0]["content"]

    async def test_no_summary_text_when_none_stored(self, client, chat_id):
        reset_sse_event_loop()
        captured = []

        async def capture_stream(msgs, **kw):
            captured.extend(msgs)
            yield "ok"

        with patch("api.chat.get_ai_provider") as factory:
            provider = MagicMock()
            provider.model_name = "test-model"
            provider.stream = capture_stream
            factory.return_value = provider

            await client.post(
                "/api/chat/stream",
                json={"chat_id": chat_id, "messages": [{"role": "user", "content": "hi"}]},
            )

        assert "summary of the earlier conversation" not in captured[0]["content"]


# ── Background summarizer ──────────────────────────────────────────────

class TestSummarizer:
    async def test_no_summary_created_under_30_messages(self, chat_id):
        await _seed_messages(chat_id, 10)
        from chat.summarizer import summarize_chat_background

        with patch("chat.summarizer.get_ai_provider", return_value=_FakeSummaryProvider()):
            await summarize_chat_background(chat_id)

        assert len(await _get_summaries(chat_id)) == 0

    async def test_summary_created_over_30_messages(self, chat_id):
        await _seed_messages(chat_id, 31)
        from chat.summarizer import summarize_chat_background

        with patch("chat.summarizer.get_ai_provider", return_value=_FakeSummaryProvider()):
            await summarize_chat_background(chat_id)

        summaries = await _get_summaries(chat_id)
        assert len(summaries) == 1
        assert summaries[0].summary == "SUMMARY_OF_EARLIER_CONVERSATION"

    async def test_summary_covers_through_correct_message(self, chat_id):
        await _seed_messages(chat_id, 31)
        msgs = await _get_messages(chat_id)
        # summarizer summarizes messages[:len-10]; last summarized is index len-10-1
        expected_last = msgs[len(msgs) - 10 - 1].id

        from chat.summarizer import summarize_chat_background
        with patch("chat.summarizer.get_ai_provider", return_value=_FakeSummaryProvider()):
            await summarize_chat_background(chat_id)

        summaries = await _get_summaries(chat_id)
        assert summaries[0].covers_through_message == expected_last

    async def test_summarizer_is_idempotent(self, chat_id):
        await _seed_messages(chat_id, 31)
        from chat.summarizer import summarize_chat_background

        with patch("chat.summarizer.get_ai_provider", return_value=_FakeSummaryProvider()):
            await summarize_chat_background(chat_id)
            await summarize_chat_background(chat_id)  # second run: already covered

        # No duplicate summary for the same coverage point.
        assert len(await _get_summaries(chat_id)) == 1
