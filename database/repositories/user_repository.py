"""
User repository for database operations.
"""
from typing import Optional, List
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User


class UserRepository:
    """Repository for User database operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self, 
        username: Optional[str] = None, 
        email: Optional[str] = None,
        password: Optional[str] = None
    ) -> User:
        """Create a new user"""
        # Convert empty strings to None to avoid UNIQUE constraint violations
        # SQLite treats empty strings as distinct values, so multiple empty strings violate UNIQUE
        username = username if username and username.strip() else None
        email = email if email and email.strip() else None
        
        # Hash password if provided
        password_hash = None
        if password:
            from auth import hash_password
            password_hash = hash_password(password)
        
        user = User(username=username, email=email, password_hash=password_hash)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        result = await self.session.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self) -> List[User]:
        """Get all users"""
        result = await self.session.execute(select(User))
        return list(result.scalars().all())
    
    async def update(
        self,
        user_id: int,
        username: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None
    ) -> Optional[User]:
        """Update user"""
        # Convert empty strings to None to avoid UNIQUE constraint violations
        update_values = {}
        if username is not None:
            update_values["username"] = username if username and username.strip() else None
        if email is not None:
            update_values["email"] = email if email and email.strip() else None
        if password is not None:
            from auth import hash_password
            update_values["password_hash"] = hash_password(password)
        
        if update_values:
            from sqlalchemy import update as sql_update
            await self.session.execute(
                sql_update(User)
                .where(User.user_id == user_id)
                .values(**update_values)
            )
            await self.session.commit()
        
        # Fetch updated user
        result = await self.session.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def delete(self, user_id: int) -> bool:
        """Delete a user (cascade will delete bots)"""
        result = await self.session.execute(
            delete(User).where(User.user_id == user_id)
        )
        await self.session.commit()
        return result.rowcount > 0

