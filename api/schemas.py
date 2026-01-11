"""
Pydantic schemas for API requests and responses.
"""
from typing import Optional
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None


class UserResponse(BaseModel):
    user_id: int
    username: Optional[str]
    email: Optional[str]
    created_at: str


class BotCreate(BaseModel):
    user_id: int
    telegram_token: str = Field(..., description="Telegram bot token")
    regos_integration_token: Optional[str] = Field(None, description="REGOS integration token")
    bot_name: Optional[str] = None


class BotUpdate(BaseModel):
    telegram_token: Optional[str] = Field(None, description="Telegram bot token (updates token)")
    bot_name: Optional[str] = None
    regos_integration_token: Optional[str] = None
    is_active: Optional[bool] = None


class BotResponse(BaseModel):
    bot_id: int
    user_id: int
    bot_name: Optional[str]
    is_active: bool
    created_at: str

