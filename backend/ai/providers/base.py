from abc import ABC, abstractmethod
from typing import AsyncGenerator


class AIProvider(ABC):
    """Base class for all AI providers. Every provider must implement these."""

    @abstractmethod
    async def stream(
        self, messages: list[dict], **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from the model."""
        ...

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
