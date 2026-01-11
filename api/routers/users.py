"""
User management API routes.
"""
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from database.repositories import UserRepository
from api.schemas import UserCreate, UserUpdate, UserResponse
from auth import verify_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["users"])


async def get_user_repo() -> UserRepository:
    """Get UserRepository instance"""
    db = await get_db()
    session = db.async_session_maker()
    async with session() as s:
        return UserRepository(s)


@router.post("", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    current_user: dict = Depends(verify_admin)
):
    """Create a new user"""
    try:
        db = await get_db()
        async with db.async_session_maker() as session:
            repo = UserRepository(session)
            user_obj = await repo.create(user.username, user.email)
            return user_obj.to_dict()
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: dict = Depends(verify_admin)
):
    """Get user by ID"""
    db = await get_db()
    async with db.async_session_maker() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user.to_dict()


@router.get("", response_model=List[UserResponse])
async def get_all_users(
    current_user: dict = Depends(verify_admin)
):
    """Get all users"""
    db = await get_db()
    async with db.async_session_maker() as session:
        repo = UserRepository(session)
        users = await repo.get_all()
        return [user.to_dict() for user in users]


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: dict = Depends(verify_admin)
):
    """Update user (username and/or email)"""
    db = await get_db()
    async with db.async_session_maker() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        updated_user = await repo.update(
            user_id,
            username=user_update.username,
            email=user_update.email
        )
        
        if not updated_user:
            raise HTTPException(status_code=500, detail="Failed to update user")
        
        return updated_user.to_dict()


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: dict = Depends(verify_admin)
):
    """Delete a user (cascades to bots)"""
    db = await get_db()
    async with db.async_session_maker() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        success = await repo.delete(user_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete user")
        
        return {"ok": True, "message": "User deleted successfully"}

