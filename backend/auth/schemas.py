from pydantic import BaseModel, EmailStr
import uuid

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
