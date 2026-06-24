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
        import base64
        import io
        try:
            import pytesseract
            from PIL import Image
            has_ocr = True
        except ImportError:
            has_ocr = False

        formatted_messages = []
        for m in messages:
            if isinstance(m.get("content"), list):
                if not has_ocr:
                    yield "⚠️ **OCR Not Installed:** Groq vision models are unavailable, and the Tesseract OCR fallback is not installed in the backend."
                    return
                    
                text_parts = []
                for part in m["content"]:
                    if part["type"] == "text":
                        text_parts.append(part["text"])
                    elif part["type"] == "image_url":
                        try:
                            # Extract base64
                            b64_str = part["image_url"]["url"].split(",")[-1]
                            image_data = base64.b64decode(b64_str)
                            img = Image.open(io.BytesIO(image_data))
                            extracted_text = pytesseract.image_to_string(img)
                            if extracted_text.strip():
                                text_parts.append(f"\n[Extracted text from image using OCR]:\n{extracted_text.strip()}\n")
                            else:
                                text_parts.append("\n[Image attached, but no text could be extracted via OCR.]\n")
                        except Exception as e:
                            text_parts.append(f"\n[Failed to process image: {str(e)}]\n")
                
                formatted_messages.append({
                    "role": m["role"],
                    "content": " ".join(text_parts)
                })
            else:
                formatted_messages.append(m)

        model_to_use = self._model

        response = await self.client.chat.completions.create(
            model=model_to_use,
            messages=formatted_messages,
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
