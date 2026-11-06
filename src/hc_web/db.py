"""SQLite storage: connection setup and schema."""

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    interval REAL,
    current_run TEXT,
    shutdown_run TEXT,
    clock_offset REAL,
    created REAL
);

CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    kind TEXT,
    unit TEXT,
    label TEXT,
    UNIQUE (experiment_id, name)
);

CREATE TABLE IF NOT EXISTS points (
    channel_id INTEGER NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    t REAL NOT NULL,
    v,
    PRIMARY KEY (channel_id, t)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS coverage (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    run TEXT,
    start REAL,
    end REAL
);
CREATE INDEX IF NOT EXISTS coverage_experiment_end ON coverage (experiment_id, end);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    t REAL,
    alarm TEXT,
    action TEXT,
    message TEXT,
    UNIQUE (experiment_id, t, alarm, action)
);

CREATE TABLE IF NOT EXISTS latched (
    experiment_id INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    alarm TEXT NOT NULL,
    PRIMARY KEY (experiment_id, alarm)
);

CREATE TABLE IF NOT EXISTS warnings (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER REFERENCES experiments(id) ON DELETE CASCADE,
    t REAL,
    message TEXT
);

CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER REFERENCES experiments(id) ON DELETE CASCADE,
    name TEXT,
    scope TEXT,
    salt TEXT,
    hash TEXT,
    created REAL,
    last_used REAL,
    revoked INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    role TEXT,
    created REAL
);

CREATE TABLE IF NOT EXISTS credentials (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    public_key BLOB,
    sign_count INTEGER,
    label TEXT,
    created REAL,
    last_used REAL
);

CREATE TABLE IF NOT EXISTS invites (
    id INTEGER PRIMARY KEY,
    code_hash TEXT NOT NULL UNIQUE,
    role TEXT,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created REAL,
    expires REAL,
    used_at REAL
);

CREATE TABLE IF NOT EXISTS challenges (
    id TEXT PRIMARY KEY,
    challenge BLOB NOT NULL,
    purpose TEXT NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    invite_hash TEXT,
    name TEXT,
    expires REAL NOT NULL
);
"""


def connect(path: Path) -> sqlite3.Connection:
    """Open the database (WAL mode) and create the schema if it is missing."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    with conn:
        conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
