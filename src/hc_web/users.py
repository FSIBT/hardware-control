"""Users, passkey credentials and invites.

Invite codes are random (``secrets.token_urlsafe(32)``) and only a SHA-256 of
the code is stored, like the API tokens. The code carries 256 bits of entropy,
so a plain unsalted hash is enough and lets us look the invite up by hash.
"""

import contextlib
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


class LastAdminError(Exception):
    """The change would leave the server without an administrator."""


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


def hash_code(code: str) -> str:
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
            (hash_code(code), role, created_by, now, now + expires_s),
        )
    return code


def invite_url(config: Config, code: str) -> str:
    return f"{config.origin.rstrip('/')}/invite/{code}"


def invite_is_valid(conn: sqlite3.Connection, code: str, now: float) -> bool:
    """Whether ``code`` is unused and unexpired. Does not redeem it."""
    row = conn.execute(
        "SELECT 1 FROM invites WHERE code_hash = ? AND used_at IS NULL AND expires > ?",
        (hash_code(code), now),
    ).fetchone()
    return row is not None


def _redeem(conn: sqlite3.Connection, h: str, now: float) -> str | None:
    """Mark the invite with code hash ``h`` used (no commit).

    One UPDATE, so only one caller wins.
    """
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
        return _redeem(conn, hash_code(code), now)


def register_with_invite(
    conn: sqlite3.Connection,
    invite_hash: str,
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
        role = _redeem(conn, invite_hash, now)
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


@contextlib.contextmanager
def _write_transaction(conn: sqlite3.Connection):
    """One transaction that holds the write lock from its first statement.

    Unlike ``with conn:`` the lock is taken before anything is read, so a check
    made inside cannot be invalidated by another writer before the change.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.rollback()
        raise
    conn.commit()


def _guard_last_admin(conn: sqlite3.Connection, user_id: int, new_role: str | None):
    """Return the user row; raise ``LastAdminError`` if they are the last admin.

    ``new_role`` is the role they are about to get, None when being deleted.
    Must run inside ``_write_transaction``. Returns None for an unknown user.
    """
    user = get_user(conn, user_id)
    if user is None or user["role"] != "admin" or new_role == "admin":
        return user
    admins = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()
    if admins[0] <= 1:
        raise LastAdminError("cannot remove the last administrator")
    return user


def set_role_keeping_an_admin(
    conn: sqlite3.Connection, user_id: int, role: str
) -> bool:
    """``set_role``, refusing to demote the last admin (``LastAdminError``).

    The check and the change are one transaction. False for an unknown user.
    """
    _check_role(role)
    with _write_transaction(conn):
        if _guard_last_admin(conn, user_id, role) is None:
            return False
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    return True


def delete_user_keeping_an_admin(conn: sqlite3.Connection, user_id: int) -> bool:
    """``delete_user``, refusing to delete the last admin (``LastAdminError``).

    The check and the change are one transaction. False for an unknown user.
    """
    with _write_transaction(conn):
        if _guard_last_admin(conn, user_id, None) is None:
            return False
        conn.execute("DELETE FROM credentials WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return True


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
