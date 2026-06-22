import json
import httpx
from typing import AsyncGenerator
from ai.providers.base import AIProvider
from config import settings


class OllamaProvider(AIProvider):
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self._model = settings.ollama_model

    async def stream(
        self, messages: list[dict], **kwargs
    ) -> AsyncGenerator[str, None]:
        
        is_vision = False
        formatted_messages = []
        for m in messages:
            if isinstance(m.get("content"), list):
                is_vision = True
                text_parts = []
                images = []
                for part in m["content"]:
                    if part["type"] == "text":
                        text_parts.append(part["text"])
                    elif part["type"] == "image_url":
                        # Ollama expects just the raw base64 string, not the data URI
                        b64 = part["image_url"]["url"].split(",")[-1]
                        images.append(b64)
                
                formatted_messages.append({
                    "role": m["role"],
                    "content": "\n".join(text_parts),
                    "images": images
                })
            else:
                formatted_messages.append(m)

        # Force vision model if images are present
        model_to_use = "llava:latest" if is_vision else self._model

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={"model": model_to_use, "messages": formatted_messages, "stream": True},
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if data.get("done"):
                            break

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def max_tokens(self) -> int:
        return 8192
