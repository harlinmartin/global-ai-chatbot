from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List, Annotated
import uuid

from database import get_db
from chat.models import Chat, Workspace
from chat.schemas import ChatCreate, ChatResponse
from auth.models import User
from auth.security import get_current_user

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    chat_in: ChatCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    workspace_id = chat_in.workspace_id
    if not workspace_id:
        ws_result = await db.execute(select(Workspace).filter(Workspace.owner_id == current_user.id).limit(1))
        ws = ws_result.scalar_one_or_none()
        if not ws:
            raise HTTPException(status_code=400, detail="No workspace found for user")
        workspace_id = ws.id
    else:
        # Verify workspace belongs to user
        ws_result = await db.execute(
            select(Workspace).filter(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
        )
        if not ws_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create chat in this workspace")

    new_chat = Chat(
        workspace_id=workspace_id,
        user_id=current_user.id,
        title=chat_in.title
    )
    db.add(new_chat)
    await db.commit()
    await db.refresh(new_chat)
    return new_chat


@router.get("", response_model=List[ChatResponse])
async def list_chats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Chat).filter(Chat.user_id == current_user.id).order_by(Chat.created_at.desc())
    )
    return result.scalars().all()


@router.patch("/{chat_id}", response_model=ChatResponse)
async def update_chat_title(
    chat_id: uuid.UUID,
    title: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    chat.title = title
    await db.commit()
    await db.refresh(chat)
    return chat


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    await db.delete(chat)
    await db.commit()
    return None
