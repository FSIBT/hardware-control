"""Retention: delete data older than the configured number of days."""

import sqlite3

from . import db

DAY = 86400.0
CLEANUP_INTERVAL = 3600.0
INVITE_GRACE = DAY


def cleanup(
    conn: sqlite3.Connection, now: float, retention_days: float
) -> dict[str, int]:
    """Delete expired rows in one transaction; return the rows deleted per table.

    Points older than the cutoff (``now - retention_days`` days) go, except the
    newest one before the cutoff of every state channel: it is the value the
    channel still had when the retained window starts. Coverage that straddles
    the cutoff is clamped to start there. Invites go one day after they expire; expired login challenges go at once.
    """
    cutoff = now - retention_days * DAY
    deleted = {}
    with conn:
        deleted["points"] = conn.execute(
            "DELETE FROM points WHERE t < :cutoff AND NOT ("
            " channel_id IN (SELECT id FROM channels WHERE kind = 'state')"
            " AND t = (SELECT MAX(p.t) FROM points p"
            "          WHERE p.channel_id = points.channel_id AND p.t < :cutoff))",
            {"cutoff": cutoff},
        ).rowcount
        deleted["events"] = conn.execute(
            "DELETE FROM events WHERE t < ?", (cutoff,)
        ).rowcount
        deleted["coverage"] = conn.execute(
            "DELETE FROM coverage WHERE end < ?", (cutoff,)
        ).rowcount
        conn.execute("UPDATE coverage SET start = ? WHERE start < ?", (cutoff, cutoff))
        deleted["warnings"] = conn.execute(
            "DELETE FROM warnings WHERE t < ?", (cutoff,)
        ).rowcount
        deleted["invites"] = conn.execute(
            "DELETE FROM invites WHERE expires < ?", (now - INVITE_GRACE,)
        ).rowcount
        deleted["challenges"] = conn.execute(
            "DELETE FROM challenges WHERE expires < ?", (now,)
        ).rowcount
    return deleted


def maybe_cleanup(
    conn: sqlite3.Connection, now: float, retention_days: float
) -> dict[str, int] | None:
    """Run ``cleanup`` unless it ran within the last hour; return its result or None."""
    last = db.get_meta(conn, "last_cleanup")
    if last is not None and 0 <= now - float(last) <= CLEANUP_INTERVAL:
        return None
    deleted = cleanup(conn, now, retention_days)
    db.set_meta(conn, "last_cleanup", str(now))
    return deleted
