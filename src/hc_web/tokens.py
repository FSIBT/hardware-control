"""Experiments and API tokens.

Tokens look like ``<id>.<secret>``. Only a salted SHA-256 of the secret is
stored; the plaintext is shown once, when the token is created. The hashing
mirrors ``hardware_control.remote_access`` but is reimplemented here because
``hc_web`` must not import ``hardware_control``.
"""

import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from dataclasses import dataclass

NAME_RE = re.compile(r"[A-Za-z0-9_.-]{1,64}")
SCOPES = ("write", "read")


@dataclass
class TokenInfo:
    id: int
    experiment_id: int
    experiment: str
    scope: str


def valid_name(name: str) -> bool:
    return isinstance(name, str) and NAME_RE.fullmatch(name) is not None


def _hash(salt: str, secret: str) -> str:
    return hashlib.sha256((salt + secret).encode()).hexdigest()


def get_or_create_experiment(conn: sqlite3.Connection, name: str) -> int:
    """Return the id of experiment ``name``, creating it if needed."""
    if not valid_name(name):
        raise ValueError(
            f"Invalid experiment name {name!r}: use 1-64 of A-Z a-z 0-9 _ . -"
        )
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO experiments (name, created) VALUES (?, ?)",
            (name, time.time()),
        )
    return conn.execute(
        "SELECT id FROM experiments WHERE name = ?", (name,)
    ).fetchone()["id"]


def create_token(
    conn: sqlite3.Connection, experiment: str, name: str, scope: str = "write"
) -> str:
    """Create a token for ``experiment`` and return its plaintext (once)."""
    if scope not in SCOPES:
        raise ValueError(f"Invalid scope {scope!r}: expected one of {SCOPES}")
    experiment_id = get_or_create_experiment(conn, experiment)
    secret = secrets.token_urlsafe(32)
    salt = secrets.token_hex(16)
    with conn:
        cur = conn.execute(
            "INSERT INTO tokens (experiment_id, name, scope, salt, hash, created) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (experiment_id, name, scope, salt, _hash(salt, secret), time.time()),
        )
    return f"{cur.lastrowid}.{secret}"


def check_token(conn: sqlite3.Connection, token: str | None) -> TokenInfo | None:
    """Validate ``token``; return its info and update ``last_used``, or None."""
    if not token or "." not in token:
        return None
    id_part, secret = token.split(".", 1)
    # Cap the length: ids beyond 18 digits overflow SQLite's 64-bit INTEGER.
    if not id_part.isascii() or not id_part.isdigit() or len(id_part) > 18:
        return None
    row = conn.execute(
        "SELECT t.id, t.experiment_id, t.scope, t.salt, t.hash, e.name AS experiment "
        "FROM tokens t JOIN experiments e ON e.id = t.experiment_id "
        "WHERE t.id = ? AND t.revoked = 0",
        (int(id_part),),
    ).fetchone()
    if row is None:
        return None
    if not hmac.compare_digest(_hash(row["salt"], secret), row["hash"]):
        return None
    with conn:
        conn.execute(
            "UPDATE tokens SET last_used = ? WHERE id = ?", (time.time(), row["id"])
        )
    return TokenInfo(
        id=row["id"],
        experiment_id=row["experiment_id"],
        experiment=row["experiment"],
        scope=row["scope"],
    )


def list_tokens(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT t.id, e.name AS experiment, t.name, t.scope, t.created, "
        "t.last_used, t.revoked "
        "FROM tokens t LEFT JOIN experiments e ON e.id = t.experiment_id "
        "ORDER BY t.id"
    ).fetchall()
    return [dict(r) for r in rows]


def revoke_token(conn: sqlite3.Connection, token_id: int) -> bool:
    """Revoke a token. Returns False if no such token exists."""
    with conn:
        cur = conn.execute("UPDATE tokens SET revoked = 1 WHERE id = ?", (token_id,))
    return cur.rowcount > 0


def delete_token(conn: sqlite3.Connection, token_id: int) -> bool:
    """Remove a token's row for good. Returns False if no such token exists."""
    with conn:
        cur = conn.execute("DELETE FROM tokens WHERE id = ?", (token_id,))
    return cur.rowcount > 0


def delete_experiment(conn: sqlite3.Connection, name: str) -> bool:
    """Remove an experiment with its data, events and tokens (cascading)."""
    with conn:
        cur = conn.execute("DELETE FROM experiments WHERE name = ?", (name,))
    return cur.rowcount > 0
