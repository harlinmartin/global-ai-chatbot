from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Annotated
import uuid

from database import get_db
from chat.models import Chat, Message
from chat.schemas import MessageResponse
from auth.models import User
from auth.security import get_current_user

router = APIRouter(prefix="/api/chats/{chat_id}/messages", tags=["messages"])

@router.get("", response_model=List[MessageResponse])
async def list_messages(
    chat_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    # Verify chat belongs to user
    chat_result = await db.execute(select(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id))
    if not chat_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    result = await db.execute(
        select(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at.asc())
    )
    return result.scalars().all()
