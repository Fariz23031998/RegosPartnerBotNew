"""
FastAPI dependencies.
"""
from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session
from database.repositories import UserRepository, BotRepository


async def get_user_repository(
    session: AsyncSession = Depends(get_db_session)
) -> AsyncGenerator[UserRepository, None]:
    """Dependency to get UserRepository"""
    async for session in get_db_session():
        yield UserRepository(session)
        break


async def get_bot_repository(
    session: AsyncSession = Depends(get_db_session)
) -> AsyncGenerator[BotRepository, None]:
    """Dependency to get BotRepository"""
    async for session in get_db_session():
        yield BotRepository(session)
        break


