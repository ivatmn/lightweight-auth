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


@asynccontextmanager
async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    """
    Open a SQLite connection for the duration of the operation.

    Usage:
        async with get_db() as db:
            async with db.execute("SELECT ...", (param,)) as cur:
                row = await cur.fetchone()
    """
    db_file = Path(DB_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    # Foreign keys are disabled by default in SQLite
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
    """
    Seed the admin/user roles and a default admin user if the DB is empty.

    The password is read from AUTH_ADMIN_PASSWORD. Change it in production.
    """
    admin_password = os.getenv("AUTH_ADMIN_PASSWORD", "admin")
    admin_username = os.getenv("AUTH_ADMIN_USERNAME", "admin")

    async with get_db() as db:
        # Roles
        await db.execute(
            "INSERT OR IGNORE INTO roles (name, description) VALUES (?, ?)",
            ("admin", "System administrator"),
        )
        await db.execute(
            "INSERT OR IGNORE INTO roles (name, description) VALUES (?, ?)",
            ("user", "Regular user"),
        )
        await db.commit()

        # Admin user
        async with db.execute(
            "SELECT id FROM users WHERE username = ?", (admin_username,)
        ) as cur:
            if await cur.fetchone() is None:
                async with db.execute(
                    "SELECT id FROM roles WHERE name = 'admin'"
                ) as cur_role:
                    role_row = await cur_role.fetchone()
                    role_id = role_row["id"] if role_row else None

                await db.execute(
                    """
                    INSERT INTO users (username, password_hash, role_id, is_active, api_key)
                    VALUES (?, ?, ?, 1, ?)
                    """,
                    (
                        admin_username,
                        hash_password(admin_password),
                        role_id,
                        None,
                    ),
                )
                await db.commit()
