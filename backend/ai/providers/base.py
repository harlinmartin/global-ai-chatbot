from abc import ABC, abstractmethod
from typing import AsyncGenerator, Callable, Coroutine, Any


class AIProvider(ABC):
    """Base class for all AI providers. Every provider must implement these."""

    @abstractmethod
    async def stream(
        self, messages: list[dict], **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from the model."""
        ...

    async def stream_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        on_tool_status: Callable[[str, str], Coroutine[Any, Any, None]] | None = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """
        Stream tokens with optional tool-calling support.

        Default implementation ignores tools and falls back to plain stream().
        Providers that support function/tool calling should override this.

        Args:
            messages: The conversation messages.
            tools: OpenAI/Groq-compatible tool JSON-Schema definitions.
            on_tool_status: Async callback(tool_name, label) called when a
                            tool starts executing, so the API layer can emit
                            SSE status events.
        """
        async for token in self.stream(messages, **kwargs):
            yield token

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier string."""
        ...

    @property
    @abstractmethod
    def max_tokens(self) -> int:
        """Return the maximum context window in tokens."""
        ...
