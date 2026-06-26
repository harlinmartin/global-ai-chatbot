import json
from typing import AsyncGenerator, Callable, Coroutine, Any
from groq import AsyncGroq
from ai.providers.base import AIProvider
from ai.tool_registry import execute_tool, get_tool_label, TOOL_DEFINITIONS
from config import settings

# Model that reliably supports Groq tool calling
TOOL_CALLING_MODEL = "llama-3.3-70b-versatile"

# Maximum number of tool-call round-trips before we force a text response
MAX_TOOL_ITERATIONS = 5


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

    async def stream_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        on_tool_status: Callable[[str, str], Coroutine[Any, Any, None]] | None = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """
        Agentic tool-calling loop.

        1. Send messages + tool definitions to Groq (non-streaming).
        2. If Groq requests tool calls, execute them, append results,
           and re-prompt (up to MAX_TOOL_ITERATIONS).
        3. Once Groq returns a plain text response, stream it out
           token-by-token.
        """
        # Use the tool-capable model
        model = TOOL_CALLING_MODEL

        # Build a mutable copy of the conversation
        conversation = list(messages)

        for _iteration in range(MAX_TOOL_ITERATIONS):
            # Non-streaming call so we can inspect tool_calls
            response = await self.client.chat.completions.create(
                model=model,
                messages=conversation,
                tools=tools,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=2048,
                stream=False,
            )

            choice = response.choices[0]
            assistant_message = choice.message

            # If the model wants to call tools
            if assistant_message.tool_calls:
                # Append the assistant's tool-call request to conversation
                conversation.append({
                    "role": "assistant",
                    "content": assistant_message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in assistant_message.tool_calls
                    ],
                })

                # Execute each tool call
                for tc in assistant_message.tool_calls:
                    tool_name = tc.function.name
                    tool_label = get_tool_label(tool_name)

                    # Notify the UI about tool execution
                    if on_tool_status:
                        await on_tool_status(tool_name, tool_label)

                    # Parse arguments and execute
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}

                    try:
                        result = execute_tool(tool_name, args)
                    except Exception as e:
                        result = json.dumps({"error": str(e)})

                    # Append the tool result to the conversation
                    conversation.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })

                # Loop back to let Groq process the tool results
                continue

            # No tool calls — this is the final text response
            # Now stream it for a nice UX
            final_text = assistant_message.content or ""
            if final_text:
                # Re-request with streaming for the final response
                # We append the non-streamed answer to avoid re-generation
                # and just yield the already-generated text token-by-token
                # for consistent UX with the rest of the app.
                for i in range(0, len(final_text), 4):
                    yield final_text[i : i + 4]

            return

        # If we exhausted iterations, yield a fallback message
        yield "I attempted to use several tools but couldn't complete the request. Please try rephrasing your question."

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def max_tokens(self) -> int:
        return 8192
