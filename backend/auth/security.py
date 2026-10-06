from datetime import datetime, timedelta, timezone
from typing import Any
import secrets

import bcrypt
from jose import JWTError, jwt

from utils.config import get_settings


settings = get_settings()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    # Bcrypt has a 72-byte limit; truncate password if necessary
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    # Bcrypt has a 72-byte limit; truncate password if necessary
    password_bytes = plain_password.encode('utf-8')[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def generate_otp() -> str:
    """Generate a secure 6-digit OTP code."""
    return f"{secrets.randbelow(1000000):06d}"


def create_access_token(subject: str, claims: dict[str, Any] | None = None) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expires_at}
    if claims:
        payload.update(claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid authentication token") from exc
