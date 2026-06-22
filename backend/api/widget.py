import json
import asyncio
import uuid
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sse_starlette.sse import EventSourceResponse

from database import get_db
from chat.models import Workspace, Chat, Message as DBMessage, ChatSummary, EvalLog
from api.chat import SYSTEM_PROMPT, Message, status_event, build_sources
from ai.factory import get_ai_provider

router = APIRouter()

class WidgetChatRequest(BaseModel):
    session_id: str
    messages: list[Message]
    provider: str = None
    origin: str = None
    image_base64: str = None

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


@router.get("/config")
async def get_widget_config(workspace: Workspace = Depends(get_workspace_from_api_key)):
    """
    Public endpoint — returns the workspace's branding configuration.
    Called by widget.js before rendering so the launcher button and iframe
    can pick up the correct brand_color, greeting, and allowed_domains.
    """
    cfg = workspace.config or {}
    return {
        "brand_color": cfg.get("brand_color", "#4F46E5"),
        "greeting": cfg.get("greeting", "Hi! How can I help you today?"),
        "allowed_domains": cfg.get("allowed_domains", []),
    }


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
        if body.origin not in allowed_domains:
            raise HTTPException(status_code=403, detail="Domain not allowed")

    # Quota Cap Enforcement — block when workspace message count >= cap
    quota_cap = workspace.config.get("quota_cap", 1000)
    usage_count_result = await db.execute(
        select(func.count()).select_from(EvalLog).filter(EvalLog.workspace_id == workspace.id)
    )
    usage_count = usage_count_result.scalar_one()
    if usage_count >= quota_cap:
        raise HTTPException(
            status_code=402,
            detail=f"Workspace quota of {quota_cap} messages has been reached. Please upgrade your plan."
        )

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
        t0 = time.perf_counter()
        retrieved_chunks: list[dict] = []
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

            # Step 1.5: RAG — retrieve relevant context from the workspace knowledge base
            yield status_event("searching", "Searching knowledge base...", "active")
            from docs import rag
            context_str, retrieved_chunks = await rag.get_context(workspace.id, user_msg.content, db=db)
            yield status_event("searching", "Searching knowledge base...", "done")

            # Build messages
            system_content = SYSTEM_PROMPT
            if latest_summary:
                system_content += f"\n\nHere is a summary of the earlier conversation for context:\n{latest_summary.summary}"
            if context_str:
                system_content += f"\n\n{context_str}"

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

            # Extract sources
            sources = build_sources(retrieved_chunks)

            # Step 2: Save assistant response (persist sources alongside it)
            if full_response:
                assistant_msg = DBMessage(
                    chat_id=chat.id,
                    role="assistant",
                    content=full_response,
                    metadata_={"sources": sources},
                )
                db.add(assistant_msg)
                await db.commit()
                await db.refresh(assistant_msg)

                # Send the final ID down to the client so they can send feedback
                yield {"event": "done", "data": json.dumps({
                    "model": provider.model_name, 
                    "message_id": str(assistant_msg.id), 
                    "answer": full_response,
                    "sources": sources
                })}

                # Check for summarization
                if len(body.messages) + 1 >= 30:
                    from chat.summarizer import summarize_chat_background
                    asyncio.create_task(summarize_chat_background(str(chat.id)))
            else:
                yield {"event": "done", "data": json.dumps({"model": provider.model_name, "sources": sources})}

            # Step 3: Evaluation logging — every answer is recorded for the Phase 8 dashboard
            from chat.models import EvalLog
            db.add(EvalLog(
                workspace_id=workspace.id,
                chat_id=chat.id,
                message_id=assistant_msg.id if full_response else None,
                question=user_msg.content,
                answer=full_response or None,
                model_name=provider.model_name,
                retrieved_chunks=retrieved_chunks,
                latency_ms=int((time.perf_counter() - t0) * 1000),
            ))
            await db.commit()

        except Exception as e:
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(generate())

class FeedbackRequest(BaseModel):
    feedback: str # 'up' or 'down'

@router.patch("/messages/{message_id}/feedback")
async def widget_message_feedback(
    message_id: str,
    body: FeedbackRequest,
    workspace: Workspace = Depends(get_workspace_from_api_key),
    db: AsyncSession = Depends(get_db)
):
    # Verify the message belongs to a chat in this workspace
    result = await db.execute(
        select(DBMessage)
        .join(Chat)
        .filter(DBMessage.id == message_id, Chat.workspace_id == workspace.id)
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
        
    # Update metadata
    current_meta = message.metadata_ or {}
    current_meta['feedback'] = body.feedback
    message.metadata_ = current_meta
    
    db.add(message)

    # Update EvalLog
    eval_log_result = await db.execute(
        select(EvalLog).filter(EvalLog.message_id == message.id)
    )
    eval_log = eval_log_result.scalar_one_or_none()
    if eval_log:
        eval_log.feedback = body.feedback
        db.add(eval_log)

    await db.commit()
    
    return {"status": "ok", "feedback": body.feedback}
