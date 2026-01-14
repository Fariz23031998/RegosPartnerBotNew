"""
Authentication API routes.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from auth import LoginRequest, Token, verify_admin

router = APIRouter(prefix="/api/auth", tags=["auth"])


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest):
    """Admin login endpoint"""
    from auth import ADMIN_USERNAME, get_admin_password, create_access_token
    
    admin_password = get_admin_password()
    if login_data.username != ADMIN_USERNAME or login_data.password != admin_password:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )
    access_token = create_access_token(data={"sub": login_data.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
async def get_current_user(current_user: dict = Depends(verify_admin)):
    """Get current authenticated user info"""
    return {"username": current_user["username"]}


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: dict = Depends(verify_admin)
):
    """Change admin password"""
    from auth import get_admin_password, set_admin_password
    
    # Verify current password
    current_password = get_admin_password()
    if password_data.current_password != current_password:
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    if not password_data.new_password or len(password_data.new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="New password must be at least 6 characters long"
        )
    
    # Update password
    if set_admin_password(password_data.new_password):
        return {"message": "Password changed successfully"}
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to update password"
        )

