"""
SQLAlchemy ORM models for the Telegram bot engine.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey
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
    bot_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationship to User
    user: Mapped["User"] = relationship("User", back_populates="bots")
    
    def to_dict(self):
        return {
            "bot_id": self.bot_id,
            "user_id": self.user_id,
            "bot_name": self.bot_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
            # Note: telegram_token and regos_integration_token are intentionally excluded from to_dict for security
        }
