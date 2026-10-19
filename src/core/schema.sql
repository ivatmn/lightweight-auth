-- ==================== SCHEMA ====================
-- lightweight-auth: SQLite schema
-- Applied on startup via init_db() in src/core/database.py

-- Environments (deployment stages: sb / gf / bf)
CREATE TABLE IF NOT EXISTS environments (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    code         TEXT    NOT NULL UNIQUE,
    name         TEXT    NOT NULL,
    frontend_url TEXT    NOT NULL,
    health_url   TEXT,
    is_active    INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_environments_code ON environments(code);

-- Users
CREATE TABLE IF NOT EXISTS users (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    username                TEXT    NOT NULL UNIQUE,
    email                   TEXT    UNIQUE,
    password_hash           TEXT    NOT NULL,
    full_name               TEXT,
    phone                   TEXT,
    role_id                 INTEGER,
    environment_id          INTEGER,
    is_active               INTEGER NOT NULL DEFAULT 1,
    is_locked               INTEGER NOT NULL DEFAULT 0,
    failed_login_attempts   INTEGER NOT NULL DEFAULT 0,
    api_key                 TEXT    UNIQUE,
    telegram_chat_id        TEXT,
    telegram_otp            TEXT,
    telegram_otp_expires    TEXT,
    last_login              TEXT,
    created_at              TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE SET NULL,
    FOREIGN KEY (environment_id) REFERENCES environments(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_api_key  ON users(api_key);
CREATE INDEX IF NOT EXISTS idx_users_environment ON users(environment_id);

-- Roles
CREATE TABLE IF NOT EXISTS roles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    description TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Groups
CREATE TABLE IF NOT EXISTS groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT    NOT NULL UNIQUE,
    name        TEXT    NOT NULL,
    access_type TEXT    NOT NULL,
    description TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_groups_access_type ON groups(access_type);

-- User <-> Group
CREATE TABLE IF NOT EXISTS user_groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    group_id    INTEGER NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_id, group_id),
    FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE CASCADE,
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_groups_user  ON user_groups(user_id);
CREATE INDEX IF NOT EXISTS idx_user_groups_group ON user_groups(group_id);


-- ==================== SEED DATA ====================

-- Deployment environments (sb / gf / bf)
INSERT OR IGNORE INTO environments (code, name, frontend_url, health_url) VALUES
    ('sb', 'Sandbox',    'http://localhost/sb', 'http://sb:8000/health'),
    ('gf', 'Greenfield', 'http://localhost/gf', 'http://gf:8000/health'),
    ('bf', 'Bluefield',  'http://localhost/bf', 'http://bf:8000/health');

-- Roles
INSERT OR IGNORE INTO roles (name, description) VALUES
    ('admin', 'System administrator'),
    ('user',  'Regular user');