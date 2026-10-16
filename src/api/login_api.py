# src/api/login_api.py
"""
Login / logout endpoints.

- POST /login  — verify credentials, issue JWT, set HttpOnly cookie.
- POST /logout — clear the auth cookie.
- GET  /me     — return the current user from the JWT.
"""

from __future__ import annotations

from typing import Any

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.api.dto.login_dto import LoginRequest, LoginResponse
from src.core.access import (
    clear_auth_cookie,
    create_access_token,
    get_current_user,
    set_auth_cookie,
)
from src.core.database import get_db, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# Lockout policy
MAX_FAILED_ATTEMPTS = 5


async def _fetch_user_by_username(
    db: aiosqlite.Connection, username: str
) -> aiosqlite.Row | None:
    async with db.execute(
        """
        SELECT u.id, u.username, u.password_hash, u.role_id, u.is_active,
               u.is_locked, u.failed_login_attempts, r.name AS role_name
        FROM users u
        LEFT JOIN roles r ON r.id = u.role_id
        WHERE u.username = ?
        """,
        (username,),
    ) as cur:
        return await cur.fetchone()


async def _register_failed_attempt(
    db: aiosqlite.Connection, user_id: int, current: int
) -> None:
    """Increment failed counter and lock the account if threshold reached."""
    new_count = current + 1
    is_locked = 1 if new_count >= MAX_FAILED_ATTEMPTS else 0

    await db.execute(
        """
        UPDATE users
        SET failed_login_attempts = ?,
            is_locked = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (new_count, is_locked, user_id),
    )
    await db.commit()


async def _reset_failed_attempts(db: aiosqlite.Connection, user_id: int) -> None:
    await db.execute(
        """
        UPDATE users
        SET failed_login_attempts = 0,
            is_locked = 0,
            last_login = datetime('now'),
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (user_id,),
    )
    await db.commit()


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    db: aiosqlite.Connection = Depends(get_db),
) -> LoginResponse:
    """
    Verify credentials, issue a JWT, and set it in an HttpOnly cookie.

    On success returns the token in the body as well — useful for
    non-browser clients (agents, CLI) that cannot use cookies.
    """
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password",
    )

    row = await _fetch_user_by_username(db, payload.username)

    if row is None:
        # Do not leak whether the username exists
        raise invalid_credentials

    if not row["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    if row["is_locked"]:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is locked due to too many failed attempts",
        )

    if not verify_password(payload.password, row["password_hash"]):
        await _register_failed_attempt(db, row["id"], row["failed_login_attempts"])
        raise invalid_credentials

    await _reset_failed_attempts(db, row["id"])

    token = create_access_token(
        {
            "sub": str(row["id"]),
            "username": row["username"],
            "role": row["role_name"] or "user",
        }
    )

    set_auth_cookie(response, token)

    return LoginResponse(access_token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    """Clear the auth cookie."""
    clear_auth_cookie(response)


@router.get("/me")
async def me(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Return the identity claims from the current JWT."""
    return user
