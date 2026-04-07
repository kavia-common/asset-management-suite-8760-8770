from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from src.api.core.config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# PUBLIC_INTERFACE
def hash_password(password: str) -> str:
    """Hash a plain text password using bcrypt."""
    return _pwd_context.hash(password)


# PUBLIC_INTERFACE
def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plain text password against a stored hash."""
    return _pwd_context.verify(password, password_hash)


# PUBLIC_INTERFACE
def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Create a JWT access token.

    subject: typically the user_id (string).
    extra_claims: additional claims like roles.
    """
    settings = get_settings()
    if not settings.jwt_secret:
        raise RuntimeError("JWT is not configured. Please set JWT_SECRET environment variable.")

    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.access_token_exp_minutes)

    payload: dict[str, Any] = {"sub": subject, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# PUBLIC_INTERFACE
def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate JWT token and return claims."""
    settings = get_settings()
    if not settings.jwt_secret:
        raise RuntimeError("JWT is not configured. Please set JWT_SECRET environment variable.")
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
