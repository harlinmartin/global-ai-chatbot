"""
Phase 12 Part 2 — Agentic Tool Calling tests.

Tests:
1. Tool registry: execute known tools, reject unknown ones.
2. Weather tool: hits the real Open-Meteo API.
3. Agent loop: mocks Groq to simulate a tool-call round-trip.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Tool Registry unit tests
# ---------------------------------------------------------------------------

class TestToolRegistry:
    """Direct tests on the tool registry module."""

    def test_check_order_status_found(self):
        from ai.tool_registry import execute_tool
        result = json.loads(execute_tool("check_order_status", {"order_id": "1024"}))
        assert result["order_id"] == "1024"
        assert result["status"] == "Shipped"
        assert result["tracking_number"] == "UPS-9876543210"

    def test_check_order_status_not_found(self):
        from ai.tool_registry import execute_tool
        result = json.loads(execute_tool("check_order_status", {"order_id": "9999"}))
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_book_meeting(self):
        from ai.tool_registry import execute_tool
        result = json.loads(execute_tool("book_meeting", {"date": "2026-06-28", "time": "3:00 PM"}))
        assert result["confirmation"] is True
        assert result["date"] == "2026-06-28"
        assert result["time"] == "3:00 PM"
        assert "meeting_link" in result

    def test_unknown_tool_raises(self):
        from ai.tool_registry import execute_tool
        with pytest.raises(ValueError, match="Unknown tool"):
            execute_tool("hack_the_pentagon", {"target": "area51"})

    def test_get_tool_label(self):
        from ai.tool_registry import get_tool_label
        assert "order" in get_tool_label("check_order_status").lower()
        assert "weather" in get_tool_label("get_weather").lower()
        assert "meeting" in get_tool_label("book_meeting").lower()
        # Unknown tool should still return something
        assert get_tool_label("unknown_tool") != ""

    def test_tool_definitions_schema(self):
        """Verify TOOL_DEFINITIONS has the correct OpenAI/Groq schema shape."""
        from ai.tool_registry import TOOL_DEFINITIONS
        assert len(TOOL_DEFINITIONS) == 3
        for tool in TOOL_DEFINITIONS:
            assert tool["type"] == "function"
            assert "function" in tool
            func = tool["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert func["parameters"]["type"] == "object"


# ---------------------------------------------------------------------------
# Weather tool (real API)
# ---------------------------------------------------------------------------

class TestWeatherTool:
    def test_get_weather_real_api(self):
        """Hit the real Open-Meteo API — requires internet."""
        from ai.tool_registry import execute_tool
        result = json.loads(execute_tool("get_weather", {"location": "London"}))

        # Should have resolved to London, GB or similar
        assert "London" in result.get("location", "")
        assert "temperature_celsius" in result
        assert isinstance(result["temperature_celsius"], (int, float))

    def test_get_weather_unknown_location(self):
        from ai.tool_registry import execute_tool
        result = json.loads(execute_tool("get_weather", {"location": "xyznonexistentplace12345"}))
        assert "error" in result


# ---------------------------------------------------------------------------
# Groq Provider — stream_with_tools agent loop (mocked)
# ---------------------------------------------------------------------------

class TestAgentLoop:
    @pytest.mark.asyncio
    async def test_stream_with_tools_no_tool_call(self):
        """When Groq returns a plain text response, tokens should stream through."""
        from ai.providers.groq_provider import GroqProvider

        provider = GroqProvider()

        # Mock the Groq client
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.tool_calls = None  # No tool calls
        mock_message.content = "Hello! How can I help you today?"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        provider.client = AsyncMock()
        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        tokens = []
        async for token in provider.stream_with_tools(
            [{"role": "user", "content": "Hi there"}],
            tools=[],
        ):
            tokens.append(token)

        full_text = "".join(tokens)
        assert full_text == "Hello! How can I help you today?"

    @pytest.mark.asyncio
    async def test_stream_with_tools_executes_tool(self):
        """
        Simulate Groq requesting a tool call, then returning a final answer.
        Verify the agent loop:
        1. First call → tool_call response
        2. Tool is executed
        3. Second call → final text response
        """
        from ai.providers.groq_provider import GroqProvider
        from ai.tool_registry import TOOL_DEFINITIONS

        provider = GroqProvider()

        # --- First response: Groq requests a tool call ---
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_abc123"
        mock_tool_call.function.name = "check_order_status"
        mock_tool_call.function.arguments = '{"order_id": "1024"}'

        mock_message_1 = MagicMock()
        mock_message_1.tool_calls = [mock_tool_call]
        mock_message_1.content = ""
        mock_choice_1 = MagicMock()
        mock_choice_1.message = mock_message_1
        mock_response_1 = MagicMock()
        mock_response_1.choices = [mock_choice_1]

        # --- Second response: Groq returns the final answer ---
        mock_message_2 = MagicMock()
        mock_message_2.tool_calls = None
        mock_message_2.content = "Your order #1024 has been shipped via UPS!"
        mock_choice_2 = MagicMock()
        mock_choice_2.message = mock_message_2
        mock_response_2 = MagicMock()
        mock_response_2.choices = [mock_choice_2]

        # Wire up the mock to return tool-call first, then text
        provider.client = AsyncMock()
        provider.client.chat.completions.create = AsyncMock(
            side_effect=[mock_response_1, mock_response_2]
        )

        # Track tool status callbacks
        tool_statuses = []

        async def on_tool_status(name: str, label: str):
            tool_statuses.append((name, label))

        tokens = []
        async for token in provider.stream_with_tools(
            [{"role": "user", "content": "Where is my order #1024?"}],
            tools=TOOL_DEFINITIONS,
            on_tool_status=on_tool_status,
        ):
            tokens.append(token)

        full_text = "".join(tokens)

        # Assertions
        assert "shipped" in full_text.lower() or "UPS" in full_text
        assert len(tool_statuses) == 1
        assert tool_statuses[0][0] == "check_order_status"
        assert "order" in tool_statuses[0][1].lower()

        # Verify Groq was called twice
        assert provider.client.chat.completions.create.call_count == 2

        # Verify the second call included the tool result
        second_call_args = provider.client.chat.completions.create.call_args_list[1]
        second_messages = second_call_args.kwargs.get("messages", [])
        tool_result_msgs = [m for m in second_messages if m.get("role") == "tool"]
        assert len(tool_result_msgs) == 1
        tool_result_data = json.loads(tool_result_msgs[0]["content"])
        assert tool_result_data["status"] == "Shipped"

    @pytest.mark.asyncio
    async def test_on_tool_status_callback_not_required(self):
        """stream_with_tools should work without an on_tool_status callback."""
        from ai.providers.groq_provider import GroqProvider

        provider = GroqProvider()

        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.tool_calls = None
        mock_message.content = "Sure thing!"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        provider.client = AsyncMock()
        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        tokens = []
        async for token in provider.stream_with_tools(
            [{"role": "user", "content": "Hello"}],
            tools=[],
            on_tool_status=None,  # No callback
        ):
            tokens.append(token)

        assert "".join(tokens) == "Sure thing!"
