"""Ingest of pushed data: validation, run conflicts, points, coverage, events."""

import math
import sqlite3

from .query import DEFAULT_INTERVAL, OFFLINE_FACTOR, covered, is_live
from .tokens import TokenInfo, valid_name

KINDS = ("sampled", "state")
DEFAULT_RUN = "external"
MAX_RUN_LENGTH = 128
SKEW_THRESHOLD = 5.0
MIN_FUTURE_LIMIT = 60.0  # seconds a time may be ahead of the server's clock
WARNING_INTERVAL = 3600.0


class PushError(Exception):
    """A rejected push. ``status`` is the HTTP status code."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


# ---------------------------------------------------------------------------
# Validation (no database access)
# ---------------------------------------------------------------------------


def _bad(message: str) -> PushError:
    return PushError(400, message)


def _is_number(x) -> bool:
    """True for a finite JSON number that converts to a float (no overflow)."""
    if not isinstance(x, int | float) or isinstance(x, bool):
        return False
    try:
        return math.isfinite(float(x))
    except OverflowError:  # an int too large for a float
        return False


def _optional_str(value, what: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise _bad(f"{what} must be a string or null")
    return value


def _list(body: dict, key: str, default):
    value = body.get(key, default)
    if not isinstance(value, list):
        raise _bad(f"{key} must be a list")
    return value


def _check_not_future(now: float, limit: float, groups: list) -> None:
    """400 if a time is more than ``limit`` seconds ahead of the server's clock.

    A time far in the future would be taken as the newest data, and a
    publisher with such a clock needs to be told, not silently corrected.
    """
    for what, times in groups:
        ahead = max((t - now for t in times), default=0.0)
        if ahead > limit:
            raise _bad(
                f"{what} is {ahead:.0f} s ahead of the server's clock (at most "
                f"{limit:.0f} s are accepted); check the clock of the sending "
                "computer"
            )


def _parse(body, now: float) -> dict:
    """Validate the shape and types of a push body and apply the defaults."""
    if not isinstance(body, dict):
        raise _bad("body must be a JSON object")
    if "points" not in body:
        raise _bad("points is required")

    run = body.get("run", DEFAULT_RUN)
    if not isinstance(run, str) or not 0 < len(run) <= MAX_RUN_LENGTH:
        raise _bad(f"run must be a string of 1-{MAX_RUN_LENGTH} characters")

    sent_at = body.get("sent_at", now)
    if not _is_number(sent_at):
        raise _bad("sent_at must be a number")

    interval = body.get("interval", DEFAULT_INTERVAL)
    if not _is_number(interval) or interval <= 0:
        raise _bad("interval must be a positive number")

    shutdown = body.get("shutdown", False)
    if not isinstance(shutdown, bool):
        raise _bad("shutdown must be a boolean")

    channels = []
    for ch in _list(body, "channels", []):
        if not isinstance(ch, dict) or not valid_name(ch.get("name")):
            raise _bad("channels need a name of 1-64 of A-Z a-z 0-9 _ . -")
        if ch.get("kind") not in KINDS:
            raise _bad(f"channel kind must be one of {KINDS}")
        channels.append(
            {
                "name": ch["name"],
                "kind": ch["kind"],
                "unit": _optional_str(ch.get("unit"), "channel unit"),
                "label": _optional_str(ch.get("label"), "channel label"),
            }
        )

    points = []
    for p in _list(body, "points", []):
        if not isinstance(p, dict) or not valid_name(p.get("channel")):
            raise _bad("points need a channel name of 1-64 of A-Z a-z 0-9 _ . -")
        if not _is_number(p.get("t")):
            raise _bad("point t must be a number")
        v = p.get("v")
        # Kind-specific checks follow in _normalize_points; here only the type.
        if v is not None and not isinstance(v, str | int | float):
            raise _bad("point v must be a number, string or null")
        points.append((p["channel"], float(p["t"]), v))

    ticks = _list(body, "ticks", [sent_at])
    if not all(_is_number(t) for t in ticks):
        raise _bad("ticks must be numbers")

    events = []
    for e in _list(body, "events", []):
        if not isinstance(e, dict) or not _is_number(e.get("t")):
            raise _bad("events need a numeric t")
        alarm, action = e.get("alarm"), e.get("action")
        if not isinstance(alarm, str) or not alarm:
            raise _bad("events need a non-empty alarm")
        if not isinstance(action, str) or not action:
            raise _bad("events need a non-empty action")
        events.append(
            (float(e["t"]), alarm, action, _optional_str(e.get("message"), "message"))
        )

    latched = _list(body, "latched", [])
    if not all(isinstance(a, str) and a for a in latched):
        raise _bad("latched must be a list of alarm names")

    _check_not_future(
        now,
        max(MIN_FUTURE_LIMIT, float(interval)),
        [("sent_at", [sent_at]), ("tick", ticks)]
        + [("point t", [p[1] for p in points]), ("event t", [e[0] for e in events])],
    )

    return {
        "run": run,
        "sent_at": float(sent_at),
        "interval": float(interval),
        "channels": channels,
        "points": points,
        "ticks": sorted(float(t) for t in ticks),
        "events": events,
        "latched": latched,
        "shutdown": shutdown,
    }


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


def _warn(conn, experiment_id, now, message, once_per: float | None = None) -> None:
    """Add a warning; with ``once_per``, skip it if the same message is recent."""
    if once_per is not None:
        recent = conn.execute(
            "SELECT 1 FROM warnings WHERE experiment_id = ? AND message = ? "
            "AND t > ? LIMIT 1",
            (experiment_id, message, now - once_per),
        ).fetchone()
        if recent is not None:
            return
    conn.execute(
        "INSERT INTO warnings (experiment_id, t, message) VALUES (?, ?, ?)",
        (experiment_id, now, message),
    )


def _store_ticks(conn, experiment_id, run, ticks, interval) -> None:
    timeout = OFFLINE_FACTOR * interval
    for t in ticks:
        row = conn.execute(
            "SELECT id, end FROM coverage WHERE experiment_id = ? AND run = ? "
            "AND start <= ? ORDER BY end DESC LIMIT 1",
            (experiment_id, run, t),
        ).fetchone()
        if row is None or t - row["end"] > timeout:
            conn.execute(
                "INSERT INTO coverage (experiment_id, run, start, end) "
                "VALUES (?, ?, ?, ?)",
                (experiment_id, run, t, t),
            )
        elif t > row["end"]:
            conn.execute("UPDATE coverage SET end = ? WHERE id = ?", (t, row["id"]))


def _channel_kinds(conn, experiment_id, declared) -> dict:
    """Map channel name -> kind: declared in the push, else stored."""
    kinds = {
        r["name"]: r["kind"]
        for r in conn.execute(
            "SELECT name, kind FROM channels WHERE experiment_id = ?",
            (experiment_id,),
        )
    }
    kinds.update({ch["name"]: ch["kind"] for ch in declared})
    return kinds


_INT64_MAX = 2**63 - 1


def _normalize_points(points, kinds) -> list:
    """Check and normalise each point's value according to its channel kind.

    - Declared sampled channel: any non-number (string, bool, NaN, inf, an int
      too large for a float) becomes NULL, so a bad reading never rejects the
      batch. Numbers are stored as floats.
    - State channel: null, a string, or a finite number (ints beyond SQLite's
      64-bit range are stored as floats); bool, NaN and inf give 400.
    - Undeclared channel (created as sampled): null or a finite number; any
      other value gives 400, because the kind is unknown.
    """
    out = []
    for name, t, v in points:
        if v is not None:
            numeric = _is_number(v)
            if name not in kinds:
                if not numeric:
                    raise _bad(
                        "undeclared channel needs a numeric value; "
                        "declare it in channels"
                    )
                v = float(v)
            elif kinds[name] == "sampled":
                v = float(v) if numeric else None
            elif not isinstance(v, str):
                if not numeric:
                    raise _bad(f"channel {name} is a state: v must be finite")
                if isinstance(v, int) and abs(v) > _INT64_MAX:
                    v = float(v)
        out.append((name, t, v))
    return out


def _store_points(conn, experiment_id, points, kinds) -> None:
    ids = {}
    for name, t, v in sorted(points, key=lambda p: p[1]):
        if name not in ids:
            ids[name] = conn.execute(
                "SELECT id FROM channels WHERE experiment_id = ? AND name = ?",
                (experiment_id, name),
            ).fetchone()["id"]
        channel_id = ids[name]
        if kinds.get(name) == "state":
            prev = conn.execute(
                "SELECT t, v FROM points WHERE channel_id = ? AND t < ? "
                "ORDER BY t DESC LIMIT 1",
                (channel_id, t),
            ).fetchone()
            if (
                prev is not None
                and prev["v"] == v
                and covered(conn, experiment_id, prev["t"], t)
            ):
                continue  # unchanged, with no gap in between
        conn.execute(
            "INSERT OR IGNORE INTO points (channel_id, t, v) VALUES (?, ?, ?)",
            (channel_id, t, v),
        )


def _apply(conn, token: TokenInfo, p: dict, now: float) -> None:
    experiment_id = token.experiment_id
    run = p["run"]
    exp = conn.execute(
        "SELECT current_run FROM experiments WHERE id = ?", (experiment_id,)
    ).fetchone()

    kinds = _channel_kinds(conn, experiment_id, p["channels"])
    points = _normalize_points(p["points"], kinds)

    # Run conflict: only one live run per experiment.
    current = exp["current_run"]
    if current is not None and current != run and is_live(conn, experiment_id, now):
        _warn(
            conn,
            experiment_id,
            now,
            f"Rejected push from run {run}: run {current} is still active",
            once_per=WARNING_INTERVAL,
        )
        conn.commit()  # keep the warning although the push is rejected
        raise PushError(409, "another run is active")
    conn.execute(  # heard now, by the server's clock
        "UPDATE experiments SET current_run = ?, last_heard = ? WHERE id = ?",
        (run, now, experiment_id),
    )

    # A constant message, so the once-per-hour dedupe holds while the skew
    # jitters; the current offset lives in clock_offset (NULL when in sync).
    skew = now - p["sent_at"]
    skewed = abs(skew) > SKEW_THRESHOLD
    if skewed:
        _warn(
            conn,
            experiment_id,
            now,
            f"clock skew exceeds {SKEW_THRESHOLD:g} s",
            once_per=WARNING_INTERVAL,
        )
    conn.execute(
        "UPDATE experiments SET clock_offset = ? WHERE id = ?",
        (skew if skewed else None, experiment_id),
    )

    conn.execute(
        "UPDATE experiments SET interval = ? WHERE id = ?",
        (p["interval"], experiment_id),
    )
    for ch in p["channels"]:
        conn.execute(
            "INSERT INTO channels (experiment_id, name, kind, unit, label) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT (experiment_id, name) DO UPDATE SET "
            "kind = excluded.kind, unit = excluded.unit, label = excluded.label",
            (experiment_id, ch["name"], ch["kind"], ch["unit"], ch["label"]),
        )
    for name in {name for name, _t, _v in points} - set(
        ch["name"] for ch in p["channels"]
    ):
        conn.execute(  # undeclared: created as sampled, kept if it exists
            "INSERT OR IGNORE INTO channels (experiment_id, name, kind) "
            "VALUES (?, ?, 'sampled')",
            (experiment_id, name),
        )
        kinds.setdefault(name, "sampled")

    # Ticks go first: the state rule needs to know where the gaps are.
    _store_ticks(conn, experiment_id, run, p["ticks"], p["interval"])
    _store_points(conn, experiment_id, points, kinds)

    for t, alarm, action, message in p["events"]:
        conn.execute(
            "INSERT OR IGNORE INTO events (experiment_id, t, alarm, action, message) "
            "VALUES (?, ?, ?, ?, ?)",
            (experiment_id, t, alarm, action, message),
        )

    conn.execute("DELETE FROM latched WHERE experiment_id = ?", (experiment_id,))
    conn.executemany(
        "INSERT OR IGNORE INTO latched (experiment_id, alarm) VALUES (?, ?)",
        [(experiment_id, alarm) for alarm in p["latched"]],
    )

    if p["shutdown"]:
        conn.execute(
            "UPDATE experiments SET shutdown_run = ? WHERE id = ?", (run, experiment_id)
        )


def ingest_push(
    conn: sqlite3.Connection, token: TokenInfo, body: dict, now: float
) -> None:
    """Store a push in one transaction. Raises ``PushError`` (400, 403, 409)."""
    if token.scope != "write":
        raise PushError(403, "token is read-only")
    parsed = _parse(body, now)
    # Take the write lock up front, so the run-conflict check cannot race.
    conn.execute("BEGIN IMMEDIATE")
    try:
        _apply(conn, token, parsed, now)
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
