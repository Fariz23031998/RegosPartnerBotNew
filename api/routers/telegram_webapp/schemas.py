"""
Pydantic schemas for Telegram Web App API.
"""
from typing import List, Optional
from pydantic import BaseModel


class TelegramAuth(BaseModel):
    """Telegram Web App authentication data"""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str


class OrderItem(BaseModel):
    product_id: int
    quantity: int
    price: float


class CreateOrderRequest(BaseModel):
    telegram_user_id: int
    partner_id: int
    address: str
    phone: Optional[str] = None
    is_takeaway: bool
    items: List[OrderItem]
