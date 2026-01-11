"""
Authentication API routes.
"""
from fastapi import APIRouter, HTTPException, Depends
from auth import LoginRequest, Token, verify_admin

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest):
    """Admin login endpoint"""
    from auth import ADMIN_USERNAME, ADMIN_PASSWORD, create_access_token
    
    if login_data.username != ADMIN_USERNAME or login_data.password != ADMIN_PASSWORD:
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

