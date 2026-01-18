"""
Authentication API routes.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from auth import LoginRequest, Token, verify_admin, verify_user, verify_password
from database import get_db
from database.repositories import UserRepository

router = APIRouter(prefix="/api/auth", tags=["auth"])


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest):
    """Login endpoint for admin or users"""
    from auth import ADMIN_USERNAME, get_admin_password, create_access_token
    
    # Try admin login first
    admin_password = get_admin_password()
    if login_data.username == ADMIN_USERNAME and login_data.password == admin_password:
        access_token = create_access_token(data={"sub": ADMIN_USERNAME, "role": "admin"})
        return {"access_token": access_token, "token_type": "bearer"}
    
    # Try user login
    db = await get_db()
    async with db.async_session_maker() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_username(login_data.username)
        
        if not user:
            # Also try email
            user = await user_repo.get_by_email(login_data.username)
        
        if user and user.password_hash:
            if verify_password(login_data.password, user.password_hash):
                access_token = create_access_token(data={
                    "sub": user.username or f"user_{user.user_id}",
                    "user_id": user.user_id,
                    "role": "user"
                })
                return {"access_token": access_token, "token_type": "bearer"}
    
    raise HTTPException(
        status_code=401,
        detail="Incorrect username or password"
    )


@router.get("/me")
async def get_current_user(current_user: dict = Depends(verify_user)):
    """Get current authenticated user info"""
    return {
        "username": current_user["username"],
        "role": current_user.get("role", "admin"),
        "user_id": current_user.get("user_id")
    }


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: dict = Depends(verify_user)
):
    """Change password (admin or user)"""
    from auth import get_admin_password, set_admin_password, hash_password
    
    role = current_user.get("role", "admin")
    user_id = current_user.get("user_id")
    
    # Validate new password
    if not password_data.new_password or len(password_data.new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="New password must be at least 6 characters long"
        )
    
    if role == "admin":
        # Admin password change
        current_password = get_admin_password()
        if password_data.current_password != current_password:
            raise HTTPException(
                status_code=400,
                detail="Current password is incorrect"
            )
        
        if set_admin_password(password_data.new_password):
            return {"message": "Password changed successfully"}
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to update password"
            )
    else:
        # User password change
        if not user_id:
            raise HTTPException(
                status_code=400,
                detail="User ID not found in token"
            )
        
        db = await get_db()
        async with db.async_session_maker() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_id)
            
            if not user or not user.password_hash:
                raise HTTPException(
                    status_code=404,
                    detail="User not found"
                )
            
            # Verify current password
            if not verify_password(password_data.current_password, user.password_hash):
                raise HTTPException(
                    status_code=400,
                    detail="Current password is incorrect"
                )
            
            # Update password
            await user_repo.update(user_id, password=password_data.new_password)
            return {"message": "Password changed successfully"}

