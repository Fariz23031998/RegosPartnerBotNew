"""
Authentication and authorization for admin panel and users.
"""
import os
import secrets
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

# Admin credentials
ADMIN_USERNAME = "admin"
# Password is stored in a file for security and to allow changes
PASSWORD_FILE = Path("admin_password.txt")

def get_admin_password() -> str:
    """Get admin password from file or use default"""
    if PASSWORD_FILE.exists():
        try:
            return PASSWORD_FILE.read_text().strip()
        except Exception:
            pass
    # Default password on first run
    default_password = "masterkey"
    # Store it for future use
    try:
        PASSWORD_FILE.write_text(default_password)
    except Exception:
        pass
    return default_password

def set_admin_password(new_password: str) -> bool:
    """Update admin password"""
    try:
        PASSWORD_FILE.write_text(new_password.strip())
        return True
    except Exception as e:
        print(f"Error saving password: {e}")
        return False

# JWT settings
# SECRET_KEY must be persistent - read from env or file, otherwise tokens become invalid on restart
SECRET_KEY_FILE = Path("jwt_secret.key")

def get_or_create_secret_key() -> str:
    """Get secret key from file or create a new one"""
    if SECRET_KEY_FILE.exists():
        try:
            return SECRET_KEY_FILE.read_text().strip()
        except Exception:
            pass
    # Generate new secret key
    secret_key = secrets.token_urlsafe(32)
    try:
        SECRET_KEY_FILE.write_text(secret_key)
        SECRET_KEY_FILE.chmod(0o600)  # Restrict permissions
    except Exception:
        pass  # Continue even if we can't write the file
    return secret_key

SECRET_KEY = os.getenv("JWT_SECRET_KEY") or get_or_create_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 days

security = HTTPBearer()


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    username: str
    password: str


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify JWT token and return payload"""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: Optional[int] = payload.get("user_id")
        role: str = payload.get("role", "admin" if username == ADMIN_USERNAME else "user")
        
        if username is None:
            raise credentials_exception
        
        result = {"username": username, "role": role}
        if user_id is not None:
            result["user_id"] = user_id
        return result
    except JWTError:
        raise credentials_exception


def verify_admin(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify that the token belongs to an admin user"""
    token_data = verify_token(credentials)
    if token_data["username"] != ADMIN_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return token_data


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def verify_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify that the token belongs to a valid user (admin or regular user)"""
    token_data = verify_token(credentials)
    # Token data contains username and user_id (if user) or just username (if admin)
    return token_data


async def check_bot_ownership(bot_id: int, current_user: dict) -> bool:
    """Check if the current user owns the bot (or is admin)"""
    if current_user.get("role") == "admin":
        return True
    
    user_id = current_user.get("user_id")
    if not user_id:
        return False
    
    from database import get_db
    from database.repositories import BotRepository
    
    db = await get_db()
    async with db.async_session_maker() as session:
        bot_repo = BotRepository(session)
        bot = await bot_repo.get_by_id(bot_id)
        return bot is not None and bot.user_id == user_id
