from typing import AsyncGenerator
from groq import AsyncGroq
from ai.providers.base import AIProvider
from config import settings


class GroqProvider(AIProvider):
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.groq_api_key)
        self._model = settings.groq_model

    async def stream(
        self, messages: list[dict], **kwargs
    ) -> AsyncGenerator[str, None]:
        # Detect if any message content is a list (multimodal)
        is_vision = any(isinstance(m.get("content"), list) for m in messages)
        
        if is_vision:
            yield "⚠️ **Groq Vision Unavailable:** Groq has temporarily decommissioned their Llama 3.2 Vision models. To analyze images right now, please switch your AI Provider to **Ollama** (Local) in the top-right corner of the chat and try again!"
            return

        model_to_use = self._model

        response = await self.client.chat.completions.create(
            model=model_to_use,
            messages=messages,
            stream=True,
            temperature=0.7,
            max_tokens=2048,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def max_tokens(self) -> int:
        return 8192
