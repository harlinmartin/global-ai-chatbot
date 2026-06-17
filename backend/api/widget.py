import json
import asyncio
import uuid
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sse_starlette.sse import EventSourceResponse

from database import get_db
from chat.models import Workspace, Chat, Message as DBMessage, ChatSummary
from api.chat import SYSTEM_PROMPT, Message, status_event
from ai.factory import get_ai_provider

router = APIRouter()

class WidgetChatRequest(BaseModel):
    session_id: str
    messages: list[Message]
    provider: str = None
    origin: str = None

import time
# Simple in-memory rate limiter: { "ip_address": [timestamp1, timestamp2, ...] }
IP_RATE_LIMITS = {}
RATE_LIMIT_WINDOW_SEC = 60
RATE_LIMIT_MAX_REQUESTS = 10

async def get_workspace_from_api_key(
    authorization: Optional[str] = Header(None),
    api_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    # Accept the key from either the standard "Authorization: Bearer <key>"
    # header (what the widget sends) or a plain "api-key" header.
    raw_key = authorization or api_key
    if not raw_key:
        raise HTTPException(status_code=401, detail="Missing API Key")

    # Strip Bearer if present
    key = raw_key.replace("Bearer ", "").strip()
    
    result = await db.execute(select(Workspace).filter(Workspace.api_key == key))
    workspace = result.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    return workspace

@router.post("/stream")
async def widget_stream_chat(
    body: WidgetChatRequest, 
    request: Request, 
    workspace: Workspace = Depends(get_workspace_from_api_key),
    db: AsyncSession = Depends(get_db)
):
    # Rate Limiting Check (per IP)
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()
    if client_ip not in IP_RATE_LIMITS:
        IP_RATE_LIMITS[client_ip] = []
    
    # Filter out old requests outside the window
    IP_RATE_LIMITS[client_ip] = [t for t in IP_RATE_LIMITS[client_ip] if current_time - t < RATE_LIMIT_WINDOW_SEC]
    
    if len(IP_RATE_LIMITS[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
        
    IP_RATE_LIMITS[client_ip].append(current_time)

    # Origin Verification
    allowed_domains = workspace.config.get("allowed_domains", [])
    if allowed_domains and body.origin:
        # Check if the requested origin is in the allowed list
        # E.g., origin: "http://localhost:8080"
        if body.origin not in allowed_domains:
            raise HTTPException(status_code=403, detail="Domain not allowed")

    # Get or create chat for this anonymous session
    chat_result = await db.execute(
        select(Chat).filter(
            Chat.workspace_id == workspace.id,
            Chat.session_id == body.session_id
        ).order_by(desc(Chat.created_at)).limit(1)
    )
    chat = chat_result.scalar_one_or_none()
    
    if not chat:
        chat = Chat(
            workspace_id=workspace.id,
            session_id=body.session_id,
            title="Widget Chat"
        )
        db.add(chat)
        await db.commit()
        await db.refresh(chat)

    async def generate():
        full_response = ""
        try:
            # Step 1: Save user message
            user_msg = body.messages[-1]
            if user_msg.role == "user":
                db.add(DBMessage(chat_id=chat.id, role="user", content=user_msg.content))
                await db.commit()

            # Fetch summary
            summary_result = await db.execute(
                select(ChatSummary)
                .filter(ChatSummary.chat_id == chat.id)
                .order_by(desc(ChatSummary.created_at))
                .limit(1)
            )
            latest_summary = summary_result.scalar_one_or_none()

            # Build messages
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

            # Step 2: Save assistant response
            if full_response:
                db.add(DBMessage(chat_id=chat.id, role="assistant", content=full_response))
                await db.commit()
                
                # Check for summarization
                if len(body.messages) + 1 >= 30:
                    from chat.summarizer import summarize_chat_background
                    asyncio.create_task(summarize_chat_background(str(chat.id)))

        except Exception as e:
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(generate())
