"""Users, passkey credentials and invites.

Invite codes are random (``secrets.token_urlsafe(32)``) and only a SHA-256 of
the code is stored, like the API tokens. The code carries 256 bits of entropy,
so a plain unsalted hash is enough and lets us look the invite up by hash.
"""

import hashlib
import secrets
import sqlite3
import time

from .config import Config

ROLES = ("viewer", "admin")
DEFAULT_INVITE_LIFETIME = 3 * 86400.0
MAX_NAME_LENGTH = 64


class RegistrationError(Exception):
    """Registration could not be completed; nothing was created."""


def valid_name(name) -> bool:
    """A display name: a non-empty printable string of at most 64 characters."""
    return (
        isinstance(name, str)
        and 0 < len(name) <= MAX_NAME_LENGTH
        and name.isprintable()
        and name == name.strip()
    )


def _check_role(role: str) -> None:
    if role not in ROLES:
        raise ValueError(f"Invalid role {role!r}: expected one of {ROLES}")


def _code_hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


# --- invites ---------------------------------------------------------------


def create_invite(
    conn: sqlite3.Connection,
    role: str,
    created_by: int | None,
    expires_s: float = DEFAULT_INVITE_LIFETIME,
) -> str:
    """Create a single-use invite and return its code (shown once)."""
    _check_role(role)
    if not expires_s > 0:
        raise ValueError("An invite must expire in the future")
    code = secrets.token_urlsafe(32)
    now = time.time()
    with conn:
        conn.execute(
            "INSERT INTO invites (code_hash, role, created_by, created, expires) "
            "VALUES (?, ?, ?, ?, ?)",
            (_code_hash(code), role, created_by, now, now + expires_s),
        )
    return code


def invite_url(config: Config, code: str) -> str:
    return f"{config.origin.rstrip('/')}/invite/{code}"


def invite_is_valid(conn: sqlite3.Connection, code: str, now: float) -> bool:
    """Whether ``code`` is unused and unexpired. Does not redeem it."""
    row = conn.execute(
        "SELECT 1 FROM invites WHERE code_hash = ? AND used_at IS NULL AND expires > ?",
        (_code_hash(code), now),
    ).fetchone()
    return row is not None


def _redeem(conn: sqlite3.Connection, code: str, now: float) -> str | None:
    """Mark the invite used (no commit). One UPDATE, so only one caller wins."""
    h = _code_hash(code)
    cur = conn.execute(
        "UPDATE invites SET used_at = ? "
        "WHERE code_hash = ? AND used_at IS NULL AND expires > ?",
        (now, h, now),
    )
    if cur.rowcount != 1:
        return None
    return conn.execute(
        "SELECT role FROM invites WHERE code_hash = ?", (h,)
    ).fetchone()["role"]


def redeem_invite(conn: sqlite3.Connection, code: str, now: float) -> str | None:
    """Mark ``code`` used and return its role; None if unknown, used or expired."""
    with conn:
        return _redeem(conn, code, now)


def register_with_invite(
    conn: sqlite3.Connection,
    code: str,
    name: str,
    cred_id: str,
    public_key: bytes,
    sign_count: int,
    now: float,
) -> int:
    """Redeem an invite and create the user and first credential atomically.

    Raises ``RegistrationError`` and leaves the invite unused if the invite is
    no longer valid, the name is taken or the credential id is already known.
    """
    with conn:  # one transaction: rolled back on any exception
        role = _redeem(conn, code, now)
        if role is None:
            raise RegistrationError("invite is invalid or has expired")
        try:
            user_id = _insert_user(conn, name, role, now)
        except sqlite3.IntegrityError:
            raise RegistrationError("that name is already taken") from None
        try:
            _insert_credential(
                conn, user_id, cred_id, public_key, sign_count, "Passkey", now
            )
        except sqlite3.IntegrityError:
            raise RegistrationError("that passkey is already registered") from None
    return user_id


# --- users -----------------------------------------------------------------


def _insert_user(conn: sqlite3.Connection, name: str, role: str, now: float) -> int:
    return conn.execute(
        "INSERT INTO users (name, role, created) VALUES (?, ?, ?)", (name, role, now)
    ).lastrowid


def create_user(conn: sqlite3.Connection, name: str, role: str) -> int:
    _check_role(role)
    if not valid_name(name):
        raise ValueError(f"Invalid user name {name!r}")
    with conn:
        return _insert_user(conn, name, role, time.time())


def get_user(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def list_users(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM users ORDER BY id").fetchall()


def set_role(conn: sqlite3.Connection, user_id: int, role: str) -> bool:
    """Change a user's role; False if there is no such user."""
    _check_role(role)
    with conn:
        cur = conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    return cur.rowcount == 1


def delete_user(conn: sqlite3.Connection, user_id: int) -> bool:
    """Delete a user and their credentials; False if there is no such user."""
    with conn:
        conn.execute("DELETE FROM credentials WHERE user_id = ?", (user_id,))
        cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return cur.rowcount == 1


# --- credentials -----------------------------------------------------------


def _insert_credential(
    conn: sqlite3.Connection,
    user_id: int,
    cred_id: str,
    public_key: bytes,
    sign_count: int,
    label: str,
    now: float,
) -> None:
    conn.execute(
        "INSERT INTO credentials "
        "(id, user_id, public_key, sign_count, label, created) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (cred_id, user_id, public_key, sign_count, label, now),
    )


def add_credential(
    conn: sqlite3.Connection,
    user_id: int,
    cred_id: str,
    public_key: bytes,
    sign_count: int,
    label: str,
) -> None:
    """Store a passkey. Raises ``sqlite3.IntegrityError`` for a known id."""
    with conn:
        _insert_credential(
            conn, user_id, cred_id, public_key, sign_count, label, time.time()
        )


def touch_credential(
    conn: sqlite3.Connection, cred_id: str, sign_count: int, now: float
) -> None:
    """Record a login: the authenticator's new signature counter and the time."""
    with conn:
        conn.execute(
            "UPDATE credentials SET sign_count = ?, last_used = ? WHERE id = ?",
            (sign_count, now, cred_id),
        )


def get_credential(conn: sqlite3.Connection, cred_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM credentials WHERE id = ?", (cred_id,)).fetchone()


def list_credentials(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM credentials WHERE user_id = ? ORDER BY created", (user_id,)
    ).fetchall()
