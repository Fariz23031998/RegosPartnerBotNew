"""
Authentication and authorization for admin panel.
"""
import secrets
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
SECRET_KEY = secrets.token_urlsafe(32)  # Generate a random secret key
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
        if username is None:
            raise credentials_exception
        return {"username": username}
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


