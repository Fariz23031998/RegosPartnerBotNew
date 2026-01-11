"""
Database connection and session management using SQLAlchemy async ORM.
"""
from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine
)

from .models import Base


class Database:
    """Database manager using SQLAlchemy async ORM"""
    
    def __init__(self, db_path: str = "sqlite+aiosqlite:///./telegram_bots.db"):
        self.db_path = db_path
        self.engine: Optional[AsyncEngine] = None
        self.async_session_maker: Optional[async_sessionmaker[AsyncSession]] = None
    
    async def connect(self):
        """Initialize database connection and create tables"""
        self.engine = create_async_engine(
            self.db_path,
            echo=False,
            future=True
        )
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        await self.create_tables()
    
    async def disconnect(self):
        """Close database connection"""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.async_session_maker = None
    
    async def create_tables(self):
        """Create all tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async session (context manager)"""
        if not self.async_session_maker:
            raise RuntimeError("Database not initialized. Call connect() first.")
        async with self.async_session_maker() as session:
            yield session
    
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get session factory"""
        if not self.async_session_maker:
            raise RuntimeError("Database not initialized. Call connect() first.")
        return self.async_session_maker


# Global database instance
_db_instance: Optional[Database] = None


async def get_db() -> Database:
    """Get database instance (dependency injection for FastAPI)"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
        await _db_instance.connect()
    return _db_instance


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session (dependency injection for FastAPI routes)"""
    db = await get_db()
    async for session in db.get_session():
        yield session


async def init_db(db_path: str = "sqlite+aiosqlite:///./telegram_bots.db"):
    """Initialize database (call on startup)"""
    global _db_instance
    _db_instance = Database(db_path)
    await _db_instance.connect()
    return _db_instance


async def close_db():
    """Close database connection (call on shutdown)"""
    global _db_instance
    if _db_instance:
        await _db_instance.disconnect()
        _db_instance = None
