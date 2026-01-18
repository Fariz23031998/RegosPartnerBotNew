"""
Pydantic schemas for API requests and responses.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None


class UserChangePassword(BaseModel):
    current_password: str
    new_password: str


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
    subscription_active: bool
    subscription_expires_at: Optional[str]
    subscription_price: float
    created_at: str


class BotSettingsCreate(BaseModel):
    bot_id: int
    online_store_stock_id: Optional[int] = None
    online_store_price_type_id: Optional[int] = None
    online_store_currency_id: int = 1


class BotSettingsUpdate(BaseModel):
    online_store_stock_id: Optional[int] = None
    online_store_price_type_id: Optional[int] = None
    online_store_currency_id: Optional[int] = None


class BotSettingsResponse(BaseModel):
    id: int
    bot_id: int
    online_store_stock_id: Optional[int]
    online_store_price_type_id: Optional[int]
    online_store_currency_id: int
    created_at: str
    updated_at: str


class BotScheduleCreate(BaseModel):
    bot_id: int
    schedule_type: str
    time: str  # HH:MM format
    schedule_option: str  # "daily", "weekdays", "monthly"
    schedule_value: Optional[List[int]] = None  # Array of days/weekdays/monthly days
    enabled: bool = True


class BotScheduleUpdate(BaseModel):
    schedule_type: Optional[str] = None
    time: Optional[str] = None
    schedule_option: Optional[str] = None
    schedule_value: Optional[List[int]] = None
    enabled: Optional[bool] = None


class BotScheduleResponse(BaseModel):
    id: int
    bot_id: int
    schedule_type: str
    time: str
    enabled: bool
    schedule_option: str
    schedule_value: Optional[List[int]]
    created_at: str
    updated_at: str


class SubscriptionActivate(BaseModel):
    months: int = Field(1, ge=1, le=12, description="Number of months to activate subscription")


class SubscriptionSetPrice(BaseModel):
    price: float = Field(..., ge=0, description="Monthly subscription price")


class SubscriptionResponse(BaseModel):
    subscription_id: int
    bot_id: int
    amount: float
    started_at: str
    expires_at: str
    created_at: str


class RevenueStats(BaseModel):
    total_revenue: float
    monthly_revenue: float
    active_subscriptions: int
    expired_subscriptions: int

