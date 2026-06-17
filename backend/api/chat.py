import json
import asyncio
from fastapi import APIRouter, Request, HTTPException
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


import uuid
from database import get_db
from chat.models import Message as DBMessage, Chat
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends

from typing import Optional

class ChatRequest(BaseModel):
    chat_id: uuid.UUID
    messages: list[Message]
    provider: Optional[str] = None

def status_event(step: str, label: str, state: str) -> dict:
    return {
        "event": "status",
        "data": json.dumps({"step": step, "label": label, "state": state}),
    }

@router.post("/stream")
async def stream_chat(body: ChatRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # Verify chat exists
    chat_result = await db.execute(select(Chat).filter(Chat.id == body.chat_id))
    chat = chat_result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    async def generate():
        full_response = ""
        try:
            # Step 1: Save the user's latest message
            user_msg = body.messages[-1]
            if user_msg.role == "user":
                db.add(DBMessage(chat_id=body.chat_id, role="user", content=user_msg.content))
                await db.commit()

            # Fetch summary
            from chat.models import ChatSummary
            from sqlalchemy import desc
            summary_result = await db.execute(
                select(ChatSummary)
                .filter(ChatSummary.chat_id == body.chat_id)
                .order_by(desc(ChatSummary.created_at))
                .limit(1)
            )
            latest_summary = summary_result.scalar_one_or_none()

            # Build messages: system prompt + summary + last 10 conversation turns
            system_content = SYSTEM_PROMPT
            if latest_summary:
                system_content += f"\n\nHere is a summary of the earlier conversation for context:\n{latest_summary.summary}"
                
            system = [{"role": "system", "content": system_content}]
            history = [{"role": m.role, "content": m.content} for m in body.messages[-10:]]
            messages = system + history

            yield status_event("thinking", "Understanding your message...", "active")
            await asyncio.sleep(0.2)
            yield status_event("thinking", "Understanding your message...", "done")

            yield status_event("generating", "Generating response...", "active")

            provider = get_ai_provider(body.provider)
            async for token in provider.stream(messages):
                if await request.is_disconnected():
                    break
                full_response += token
                yield {"event": "token", "data": json.dumps({"token": token})}

            yield status_event("generating", "Generating response...", "done")
            yield {"event": "done", "data": json.dumps({"model": provider.model_name})}

            # Step 2: Save the AI's response
            if full_response:
                db.add(DBMessage(chat_id=body.chat_id, role="assistant", content=full_response))
                await db.commit()
                
                # Check if we should trigger background summarization
                if len(body.messages) + 1 >= 30:
                    from chat.summarizer import summarize_chat_background
                    asyncio.create_task(summarize_chat_background(body.chat_id))

        except Exception as e:
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(generate())
