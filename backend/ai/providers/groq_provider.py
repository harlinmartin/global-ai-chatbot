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
        response = await self.client.chat.completions.create(
            model=self._model,
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
