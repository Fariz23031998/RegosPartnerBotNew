"""
SQLAlchemy ORM models for the Telegram bot engine.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, Time, JSON, Numeric
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all ORM models"""
    pass


class User(Base):
    """User ORM model"""
    __tablename__ = "users"
    
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationship to Bot
    bots: Mapped[list["Bot"]] = relationship(
        "Bot",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None
            # Note: password_hash is intentionally excluded from to_dict for security
        }


class Bot(Base):
    """Bot ORM model"""
    __tablename__ = "bots"
    
    bot_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    telegram_token: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    regos_integration_token: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    bot_name: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Subscription fields
    subscription_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    subscription_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationship to User
    user: Mapped["User"] = relationship("User", back_populates="bots")
    # Relationship to BotSettings
    bot_settings: Mapped[Optional["BotSettings"]] = relationship(
        "BotSettings",
        back_populates="bot",
        uselist=False,
        cascade="all, delete-orphan"
    )
    # Relationship to BotSchedule
    bot_schedules: Mapped[list["BotSchedule"]] = relationship(
        "BotSchedule",
        back_populates="bot",
        cascade="all, delete-orphan"
    )
    
    def to_dict(self):
        return {
            "bot_id": self.bot_id,
            "user_id": self.user_id,
            "bot_name": self.bot_name,
            "is_active": self.is_active,
            "subscription_active": self.subscription_active,
            "subscription_expires_at": self.subscription_expires_at.isoformat() if self.subscription_expires_at else None,
            "subscription_price": float(self.subscription_price) if self.subscription_price else 0.0,
            "created_at": self.created_at.isoformat() if self.created_at else None
            # Note: telegram_token and regos_integration_token are intentionally excluded from to_dict for security
        }


class BotSettings(Base):
    """Bot settings ORM model"""
    __tablename__ = "bot_settings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bot_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bots.bot_id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )
    online_store_stock_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    online_store_price_type_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    online_store_currency_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    currency_name: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="сум")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationship to Bot
    bot: Mapped["Bot"] = relationship("Bot", back_populates="bot_settings")
    
    def to_dict(self):
        return {
            "id": self.id,
            "bot_id": self.bot_id,
            "online_store_stock_id": self.online_store_stock_id,
            "online_store_price_type_id": self.online_store_price_type_id,
            "online_store_currency_id": self.online_store_currency_id,
            "currency_name": self.currency_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class BotSchedule(Base):
    """Bot schedule ORM model"""
    __tablename__ = "bot_schedules"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bot_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bots.bot_id", ondelete="CASCADE"),
        nullable=False
    )
    schedule_type: Mapped[str] = mapped_column(String, nullable=False)  # e.g., "send_partner_balance"
    time: Mapped[str] = mapped_column(String, nullable=False)  # Time in HH:MM format
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    schedule_option: Mapped[str] = mapped_column(String, nullable=False)  # "daily", "weekdays", "monthly"
    schedule_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # JSON array as string, e.g., "[1,3,5]"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationship to Bot
    bot: Mapped["Bot"] = relationship("Bot", back_populates="bot_schedules")
    
    def to_dict(self):
        import json
        schedule_value = None
        if self.schedule_value:
            try:
                schedule_value = json.loads(self.schedule_value)
            except:
                schedule_value = None
        
        return {
            "id": self.id,
            "bot_id": self.bot_id,
            "schedule_type": self.schedule_type,
            "time": self.time,
            "enabled": self.enabled,
            "schedule_option": self.schedule_option,
            "schedule_value": schedule_value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Subscription(Base):
    """Subscription history/payment tracking ORM model"""
    __tablename__ = "subscriptions"
    
    subscription_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bot_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bots.bot_id", ondelete="CASCADE"),
        nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationship to Bot
    bot: Mapped["Bot"] = relationship("Bot", foreign_keys=[bot_id])
    
    def to_dict(self):
        return {
            "subscription_id": self.subscription_id,
            "bot_id": self.bot_id,
            "amount": float(self.amount),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
