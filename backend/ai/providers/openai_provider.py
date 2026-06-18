from typing import AsyncGenerator
from openai import AsyncOpenAI
from ai.providers.base import AIProvider
from config import settings


class OpenAIProvider(AIProvider):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

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
            if chunk.choices and chunk.choices[0].delta:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def max_tokens(self) -> int:
        return 128000  # Based on gpt-4o-mini limits
