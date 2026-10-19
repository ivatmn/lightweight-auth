# src/core/database.py
"""
Async SQLite layer for lightweight-auth.

- One connection per operation (safe for PoC / internal tools / agent auth).
- Schema is created on startup if tables do not exist.
- No ORM: raw SQL with parameter binding.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
import bcrypt

# ==================== CONFIG ====================

# Override via env (useful for docker / tests)
DB_PATH: str = os.getenv("AUTH_DB_PATH", "data/auth.db")

# External schema file (single source of truth for the DB schema)
SCHEMA_PATH: Path = Path(__file__).resolve().parent / "schema.sql"


# ==================== PASSWORD HELPERS ====================


def hash_password(password: str) -> str:
    """Return a bcrypt hash of the password. Input is truncated to 72 bytes (bcrypt limit)."""
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode(
        "utf-8"
    )


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8")[:72], password_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


# ==================== CONNECTION ====================


async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
    finally:
        await db.close()


@asynccontextmanager
async def open_db() -> AsyncIterator[aiosqlite.Connection]:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
    finally:
        await db.close()


# ==================== SCHEMA ====================


async def init_db() -> None:
    """Create tables if they do not exist. Called on application startup."""
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    db_file = Path(DB_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.executescript(schema)
        await db.commit()


# ==================== SEED ====================


async def seed_default_admin() -> None:
    """Create the default admin user if it does not exist."""
    admin_password = os.getenv("AUTH_ADMIN_PASSWORD", "admin")
    admin_username = os.getenv("AUTH_ADMIN_USERNAME", "admin")
    admin_environment = os.getenv("AUTH_ADMIN_ENVIRONMENT", "sb")

    async with open_db() as db:
        async with db.execute(
            "SELECT id FROM users WHERE username = ?", (admin_username,)
        ) as cur:
            if await cur.fetchone() is not None:
                return

        async with db.execute("SELECT id FROM roles WHERE name = 'admin'") as cur:
            role_row = await cur.fetchone()
            role_id = role_row["id"] if role_row else None

        async with db.execute(
            "SELECT id FROM environments WHERE code = ?", (admin_environment,)
        ) as cur:
            env_row = await cur.fetchone()
            environment_id = env_row["id"] if env_row else None

        await db.execute(
            """
            INSERT INTO users (username, password_hash, role_id, environment_id, is_active, api_key)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (
                admin_username,
                hash_password(admin_password),
                role_id,
                environment_id,
                None,
            ),
        )
        await db.commit()
