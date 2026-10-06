"""
Authentication dependencies for Recovery & Automation module.

Validates JWT tokens issued by the main Defendra API (port 8000).
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("auth")

security = HTTPBearer(auto_error=False)


class CurrentUser:
    """Represents the authenticated user from JWT token."""
    
    def __init__(self, user_id: str, email: str, role: str):
        self.id = user_id
        self.email = email
        self.role = role
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return (self.role or "").lower() == "admin"


def decode_access_token(token: str) -> dict:
    """
    Decode JWT token from main Defendra API.
    
    Raises HTTPException if token is invalid/expired.
    """
    settings = get_settings()
    # Use same secret as main API (should be in shared .env)
    secret_key = settings.jwt_secret_key
    algorithm = settings.jwt_algorithm
    
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload
    except JWTError as exc:
        logger.warning("JWT decode failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)]
) -> CurrentUser:
    """
    Extract and validate user from JWT token.
    
    Returns CurrentUser with id, email, and role.
    Raises 401 if token is missing or invalid.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    user_id = payload.get("sub")
    email = payload.get("email")
    role = payload.get("role", "user")
    
    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    return CurrentUser(user_id=user_id, email=email, role=role)


def require_admin(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    """
    Dependency that requires admin role.
    
    Raises 403 if user is not admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
