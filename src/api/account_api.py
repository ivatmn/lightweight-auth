# src/api/account_api.py
"""
Account management endpoints.

- POST /account/signup       — register a new user.
- POST /account/otp/request  — generate an OTP (password reset or unlock).
- POST /account/otp/confirm  — confirm OTP and reset password / unlock.

OTP is stored in plaintext with a 10-minute TTL (PoC trade-off).
Each successful request/confirm regenerates the OTP.
"""

from __future__ import annotations

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, status
from src.api.dto.account_dto import (
    MessageResponse,
    OtpConfirmRequest,
    OtpRequest,
    SignupRequest,
    SignupResponse,
)

from src.core.database import get_db, hash_password
from src.core.otp import (
    generate_otp,
    is_otp_expired,
    otp_expires_at,
)

router = APIRouter(prefix="/account", tags=["account"])


async def _get_user(db: aiosqlite.Connection, username: str) -> aiosqlite.Row | None:
    async with db.execute(
        """
        SELECT id, username, is_active, is_locked, telegram_otp, telegram_otp_expires
        FROM users
        WHERE username = ?
        """,
        (username,),
    ) as cur:
        return await cur.fetchone()


async def _issue_otp(db: aiosqlite.Connection, user_id: int) -> str:
    """Generate a fresh OTP, store it with a new expiry, return plaintext."""
    plain = generate_otp()
    await db.execute(
        """
        UPDATE users
        SET telegram_otp = ?,
            telegram_otp_expires = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (plain, otp_expires_at(), user_id),
    )
    await db.commit()
    return plain


# ==================== SIGNUP ====================


@router.post(
    "/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED
)
async def signup(
    payload: SignupRequest,
    db: aiosqlite.Connection = Depends(get_db),
) -> SignupResponse:
    """Register a new user with the default role `user`."""
    async with db.execute(
        "SELECT id FROM users WHERE username = ?", (payload.username,)
    ) as cur:
        if await cur.fetchone() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken",
            )

    async with db.execute("SELECT id FROM roles WHERE name = 'user'") as cur:
        role_row = await cur.fetchone()
    role_id = role_row["id"] if role_row else None

    try:
        cursor = await db.execute(
            """
            INSERT INTO users (username, password_hash, email, full_name, role_id, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (
                payload.username,
                hash_password(payload.password),
                payload.email,
                payload.full_name,
                role_id,
            ),
        )
        await db.commit()
    except aiosqlite.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    return SignupResponse(id=cursor.lastrowid, username=payload.username)


# ==================== OTP: REQUEST ====================


@router.post("/otp/request", response_model=MessageResponse)
async def request_otp(
    payload: OtpRequest,
    db: aiosqlite.Connection = Depends(get_db),
) -> MessageResponse:
    """
    Generate an OTP for password reset or account unlock.

    Always returns 200 to avoid leaking whether the username exists.
    The plaintext OTP is delivered out-of-band (Telegram, email).
    """
    user = await _get_user(db, payload.username)

    if user is not None and user["is_active"]:
        plain = await _issue_otp(db, user["id"])
        # TODO: deliver via Telegram / email. For dev, log it.
        print(f"[OTP] user={user['username']} code={plain}")

    return MessageResponse(detail="If the account exists, an OTP has been sent")


# ==================== OTP: CONFIRM ====================


@router.post("/otp/confirm", response_model=MessageResponse)
async def confirm_otp(
    payload: OtpConfirmRequest,
    db: aiosqlite.Connection = Depends(get_db),
) -> MessageResponse:
    """
    Confirm an OTP to reset the password and/or unlock the account.

    Rules:
    - OTP must be valid and not expired (10 min TTL).
    - If `new_password` is provided → reset password.
    - If the account is locked → unlock it (reset failed attempts).
    - On success, the OTP is invalidated (set to NULL).
    """
    invalid_otp = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired OTP",
    )

    user = await _get_user(db, payload.username)
    if user is None or not user["is_active"]:
        raise invalid_otp

    if is_otp_expired(user["telegram_otp_expires"]):
        raise invalid_otp

    if user["telegram_otp"] != payload.otp:
        raise invalid_otp

    updates: list[str] = [
        "telegram_otp = NULL",
        "telegram_otp_expires = NULL",
        "updated_at = datetime('now')",
    ]
    params: list[object] = []

    if payload.new_password is not None:
        updates.append("password_hash = ?")
        params.append(hash_password(payload.new_password))

    if user["is_locked"]:
        updates.append("is_locked = 0")
        updates.append("failed_login_attempts = 0")

    params.append(user["id"])

    await db.execute(
        f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
        params,
    )
    await db.commit()

    return MessageResponse(detail="OTP confirmed")
