# src/core/otp.py
"""
OTP helpers for password reset and account unlock.

- 6-digit numeric codes.
- Stored in plaintext in `users.telegram_otp` (PoC trade-off).
- TTL controlled by `users.telegram_otp_expires` (ISO 8601, UTC).
"""

from __future__ import annotations

import os
import secrets
from datetime import UTC, datetime, timedelta

OTP_TTL_MINUTES: int = int(os.getenv("AUTH_OTP_TTL_MINUTES", "10"))
OTP_LENGTH: int = 6


def generate_otp() -> str:
    """Return a random 6-digit numeric OTP (zero-padded)."""
    return f"{secrets.randbelow(10**OTP_LENGTH):0{OTP_LENGTH}d}"


def otp_expires_at(now: datetime | None = None) -> str:
    """Return the OTP expiry timestamp as an ISO 8601 string (UTC)."""
    base = now or datetime.now(UTC)
    return (base + timedelta(minutes=OTP_TTL_MINUTES)).isoformat()


def is_otp_expired(expires_at: str | None, now: datetime | None = None) -> bool:
    """Return True if the OTP expiry is missing or in the past."""
    if not expires_at:
        return True
    try:
        exp = datetime.fromisoformat(expires_at)
    except ValueError:
        return True

    base = now or datetime.now(UTC)
    return exp < base
