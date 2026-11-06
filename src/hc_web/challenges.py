"""Server-side WebAuthn challenges.

A challenge lives in the database, not in the session cookie: the cookie only
carries a random id. A cookie that is copied before a ceremony finishes then
cannot replay it, because the row is deleted the first time it is used.
"""

import secrets
import sqlite3

CHALLENGE_TTL = 300.0
PURPOSES = ("register", "login")


def create_challenge(
    conn: sqlite3.Connection,
    purpose: str,
    challenge: bytes,
    now: float,
    user_id: int | None = None,
    invite_hash: str | None = None,
    name: str | None = None,
) -> str:
    """Store a challenge and return its random id. Expired rows are dropped."""
    if purpose not in PURPOSES:
        raise ValueError(f"Invalid purpose {purpose!r}")
    challenge_id = secrets.token_urlsafe(32)
    with conn:
        conn.execute("DELETE FROM challenges WHERE expires < ?", (now,))
        conn.execute(
            "INSERT INTO challenges "
            "(id, challenge, purpose, user_id, invite_hash, name, expires) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                challenge_id,
                challenge,
                purpose,
                user_id,
                invite_hash,
                name,
                now + CHALLENGE_TTL,
            ),
        )
    return challenge_id


def consume_challenge(
    conn: sqlite3.Connection, challenge_id: str | None, purpose: str, now: float
) -> sqlite3.Row | None:
    """Delete the challenge and return it, or None.

    The row is deleted on every call, so it is usable once whatever the outcome.
    None means it is unknown, already used, expired or of another purpose. The
    ``DELETE`` is guarded by its row count, so two concurrent callers cannot
    both get the row.
    """
    if not isinstance(challenge_id, str):
        return None
    with conn:
        row = conn.execute(
            "SELECT * FROM challenges WHERE id = ?", (challenge_id,)
        ).fetchone()
        if row is None:
            return None
        deleted = conn.execute("DELETE FROM challenges WHERE id = ?", (challenge_id,))
    if deleted.rowcount != 1:
        return None
    if row["purpose"] != purpose or row["expires"] < now:
        return None
    return row
