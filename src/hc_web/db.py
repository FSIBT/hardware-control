"""SQLite storage: connection setup, schema and migrations.

The schema version is ``PRAGMA user_version``. Version 0 is a database made
before versioning (or an empty file). ``SCHEMA`` is always the current schema;
a database of an older version is brought up to date by ``_migrate`` in one
transaction, one numbered step at a time.
"""

import sqlite3
import time
from pathlib import Path

SCHEMA_VERSION = 1

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
    created REAL,
    last_heard REAL
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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


class SchemaVersionError(RuntimeError):
    """The database was made by a newer version of hc_web."""


def _user_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def _check_version(path: Path, version: int) -> None:
    if version > SCHEMA_VERSION:
        raise SchemaVersionError(
            f"database {path} has schema version {version}, which is newer than "
            f"the version {SCHEMA_VERSION} this hc_web understands; "
            "upgrade hardware-control"
        )


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]


def _rebuild_events(conn: sqlite3.Connection) -> None:
    """Give ``events`` an AUTOINCREMENT id (ids stay as they are)."""
    conn.execute("ALTER TABLE events RENAME TO events_v0")
    conn.execute(_statement("events"))
    conn.execute(
        "INSERT INTO events (id, experiment_id, t, alarm, action, message) "
        "SELECT id, experiment_id, t, alarm, action, message "
        "FROM events_v0 ORDER BY id"
    )
    conn.execute("DROP TABLE events_v0")


def _upgrade_v0(conn: sqlite3.Connection) -> None:
    """Version 0 to 1: ``experiments.last_heard`` and monotonic event ids.

    ``last_heard`` is backfilled from the newest coverage of the experiment,
    the best the old schema knows (it is the publisher's clock, but only for
    this one time).
    """
    if "last_heard" not in _columns(conn, "experiments"):
        conn.execute("ALTER TABLE experiments ADD COLUMN last_heard REAL")
        conn.execute(
            "UPDATE experiments SET last_heard = "
            "(SELECT MAX(end) FROM coverage WHERE experiment_id = experiments.id)"
        )
    _rebuild_events(conn)


def _statements() -> list[str]:
    return [part.strip() for part in SCHEMA.split(";") if part.strip()]


def _statement(table: str) -> str:
    """The ``CREATE TABLE`` statement of ``table`` in ``SCHEMA``."""
    prefix = f"CREATE TABLE IF NOT EXISTS {table} ("
    return next(s for s in _statements() if s.startswith(prefix))


def _migrate(conn: sqlite3.Connection, path: Path) -> None:
    """Create the schema, or bring an older one up to ``SCHEMA_VERSION``.

    Takes the write lock first, so that of several workers starting at once
    only one migrates; the others wait, then see the new version and do nothing.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        version = _user_version(conn)
        _check_version(path, version)
        if version < 1:
            known = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' "
                "AND name = 'experiments'"
            ).fetchone()
            if known:  # made before versioning
                _upgrade_v0(conn)
            for statement in _statements():  # whatever is missing (all if new)
                conn.execute(statement)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()
    except BaseException:
        conn.rollback()
        raise


def _enable_wal(conn: sqlite3.Connection) -> None:
    """Switch to WAL mode. Changing the mode of a new file is not covered by
    the busy timeout, so workers that start together retry for a moment."""
    deadline = time.monotonic() + 10
    while True:
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            return
        except sqlite3.OperationalError as e:
            if "locked" not in str(e) or time.monotonic() > deadline:
                raise
            time.sleep(0.01)


def connect(path: Path) -> sqlite3.Connection:
    """Open the database (WAL mode); create or migrate the schema if needed.

    Raises ``SchemaVersionError`` for a database of a newer version.
    """
    conn = sqlite3.connect(path)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 30000")
        _enable_wal(conn)
        conn.execute("PRAGMA foreign_keys = ON")
        version = _user_version(conn)
        _check_version(path, version)
        if version < SCHEMA_VERSION:
            _migrate(conn, path)
    except BaseException:
        conn.close()
        raise
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
