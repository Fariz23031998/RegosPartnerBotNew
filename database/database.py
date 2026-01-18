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
        
        # Run migrations for existing tables
        await self._migrate_subscription_fields()
    
    async def _migrate_subscription_fields(self):
        """Add subscription fields to existing bots table if they don't exist"""
        import logging
        from sqlalchemy import text
        logger = logging.getLogger(__name__)
        
        try:
            async with self.engine.begin() as conn:
                # Check if bots table exists first
                table_check = await conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='bots'")
                )
                if not table_check.fetchone():
                    logger.info("Bots table does not exist yet, skipping migration")
                    return
                
                # Check if subscription_active column exists
                result = await conn.execute(text("PRAGMA table_info(bots)"))
                rows = result.fetchall()
                columns = [row[1] for row in rows] if rows else []
                
                # Add subscription_active if it doesn't exist
                if 'subscription_active' not in columns:
                    logger.info("Adding subscription_active column to bots table")
                    await conn.execute(
                        text("ALTER TABLE bots ADD COLUMN subscription_active BOOLEAN NOT NULL DEFAULT 0")
                    )
                
                # Add subscription_expires_at if it doesn't exist
                if 'subscription_expires_at' not in columns:
                    logger.info("Adding subscription_expires_at column to bots table")
                    await conn.execute(
                        text("ALTER TABLE bots ADD COLUMN subscription_expires_at DATETIME")
                    )
                
                # Add subscription_price if it doesn't exist
                if 'subscription_price' not in columns:
                    logger.info("Adding subscription_price column to bots table")
                    await conn.execute(
                        text("ALTER TABLE bots ADD COLUMN subscription_price NUMERIC(10, 2) DEFAULT 0.0")
                    )
                
                # Check if users table exists and add password_hash column
                users_table_check = await conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                )
                if users_table_check.fetchone():
                    users_result = await conn.execute(text("PRAGMA table_info(users)"))
                    users_rows = users_result.fetchall()
                    users_columns = [row[1] for row in users_rows] if users_rows else []
                    
                    if 'password_hash' not in users_columns:
                        logger.info("Adding password_hash column to users table")
                        await conn.execute(
                            text("ALTER TABLE users ADD COLUMN password_hash TEXT")
                        )
                
                # Check if subscriptions table exists, create it if not
                result = await conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='subscriptions'")
                )
                if not result.fetchone():
                    logger.info("Creating subscriptions table")
                    await conn.execute(
                        text("""CREATE TABLE subscriptions (
                            subscription_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                            bot_id INTEGER NOT NULL,
                            amount NUMERIC(10, 2) NOT NULL,
                            started_at DATETIME NOT NULL,
                            expires_at DATETIME NOT NULL,
                            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(bot_id) REFERENCES bots (bot_id) ON DELETE CASCADE
                        )""")
                    )
                
                logger.info("Database migration completed successfully")
        except Exception as e:
            logger.error(f"Error during database migration: {e}", exc_info=True)
            # Don't raise - allow app to continue even if migration fails
            # (columns might already exist)
    
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
