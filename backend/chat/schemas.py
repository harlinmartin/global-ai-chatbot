from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

class MessageBase(BaseModel):
    role: str
    content: str
    metadata_: Dict[str, Any] = {}

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    id: uuid.UUID
    chat_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

class ChatBase(BaseModel):
    title: str

class ChatCreate(ChatBase):
    workspace_id: Optional[uuid.UUID] = None

class ChatResponse(ChatBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    session_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ChatWithMessagesResponse(ChatResponse):
    messages: List[MessageResponse] = []

class WorkspaceBase(BaseModel):
    name: str

class WorkspaceCreate(WorkspaceBase):
    pass

class WorkspaceResponse(WorkspaceBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    api_key: str
    config: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
