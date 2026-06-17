import json
import asyncio
from fastapi import APIRouter, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ai.factory import get_ai_provider

router = APIRouter()

SYSTEM_PROMPT = """You are a helpful, friendly AI assistant embedded in a website.

Rules:
- If the user's message is vague or unclear, ask ONE short clarifying question before answering. Never ask multiple questions.
- Use the conversation history to understand what "it", "that", or "this" refers to.
- Keep answers focused and well-structured.
- Use markdown for code blocks, lists, and headings when helpful.
"""


class Message(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


def status_event(step: str, label: str, state: str) -> dict:
    return {
        "event": "status",
        "data": json.dumps({"step": step, "label": label, "state": state}),
    }


@router.post("/stream")
async def stream_chat(body: ChatRequest, request: Request):
    async def generate():
        try:
            # Build messages: system prompt + last 10 conversation turns
            system = [{"role": "system", "content": SYSTEM_PROMPT}]
            history = [{"role": m.role, "content": m.content} for m in body.messages[-10:]]
            messages = system + history

            # Step 1 — thinking
            yield status_event("thinking", "Understanding your message...", "active")
            await asyncio.sleep(0.2)
            yield status_event("thinking", "Understanding your message...", "done")

            # Step 2 — generating
            yield status_event("generating", "Generating response...", "active")

            provider = get_ai_provider()
            async for token in provider.stream(messages):
                if await request.is_disconnected():
                    break
                yield {"event": "token", "data": json.dumps({"token": token})}

            yield status_event("generating", "Generating response...", "done")
            yield {"event": "done", "data": json.dumps({"model": provider.model_name})}

        except Exception as e:
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(generate())
