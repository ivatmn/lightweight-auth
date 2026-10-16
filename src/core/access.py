# src/core/access.py
"""
JWT access layer for lightweight-auth.

- Sync JWT encode/decode (jose), used from FastAPI dependencies.
- Access token stored in an HttpOnly cookie (`access_token`).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Cookie, HTTPException, Response, status
from jose import JWTError, jwt

# ==================== CONFIG ====================

SECRET_KEY: str = os.getenv("AUTH_SECRET_KEY", "change-me-in-production")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

COOKIE_NAME: str = "access_token"
COOKIE_SECURE: bool = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE: str = os.getenv("AUTH_COOKIE_SAMESITE", "lax")


# ==================== TOKEN ====================


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Encode a JWT with the given payload.

    Adds `exp` and `iat` claims. Caller supplies identity claims
    (e.g. `sub`, `role`, `groups`).
    """
    to_encode = data.copy()

    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT.

    Raises HTTPException(401) on any validation failure.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception

    if not payload.get("sub"):
        raise credentials_exception

    return payload


# ==================== DEPENDENCY ====================


def get_current_user(
    access_token: str | None = Cookie(None, alias=COOKIE_NAME),
) -> dict[str, Any]:
    """
    FastAPI dependency: resolve the current user from the auth cookie.

    Usage:
        @router.get("/me")
        def me(user: dict = Depends(get_current_user)):
            ...
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = access_token.removeprefix("Bearer ")
    return decode_access_token(token)


# ==================== COOKIE HELPERS ====================


def set_auth_cookie(
    response: Response,
    token: str,
    expires_minutes: int | None = None,
) -> None:
    """Attach the auth cookie to the response."""
    minutes = expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
    max_age = minutes * 60

    response.set_cookie(
        key=COOKIE_NAME,
        value=f"Bearer {token}",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=max_age,
        expires=max_age,
    )


def clear_auth_cookie(response: Response) -> None:
    """Remove the auth cookie (used on logout)."""
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )
