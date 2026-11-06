"""Read side: liveness, gaps, and the data, status and events queries.

This module must not import ``ingest`` (``ingest`` imports it).
"""

import math
import sqlite3

DEFAULT_INTERVAL = 60.0
OFFLINE_FACTOR = 3


# Most points one CSV export may contain (it is built in memory).
MAX_CSV_POINTS = 500_000


class UnknownChannel(LookupError):
    """A requested ``experiment/channel`` does not exist."""


class TooManyPoints(Exception):
    """The requested range holds more points than the caller accepts."""


def timeout(interval: float | None) -> float:
    """Seconds without a heartbeat after which an experiment counts as offline."""
    return OFFLINE_FACTOR * (interval or DEFAULT_INTERVAL)


def _clean(v):
    """Unknown is null on the wire: map NaN and infinity to None."""
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def is_live(conn: sqlite3.Connection, experiment_id: int, now: float) -> bool:
    """True if the experiment's current run is still publishing.

    A run is live unless it was shut down cleanly or the server has not heard
    from it for ``3 * interval``. Both are judged on the server's clock
    (``experiments.last_heard``), never on the times the publisher sent.
    """
    exp = conn.execute(
        "SELECT interval, current_run, shutdown_run, last_heard FROM experiments "
        "WHERE id = ?",
        (experiment_id,),
    ).fetchone()
    if exp is None or exp["current_run"] is None or exp["last_heard"] is None:
        return False
    if exp["current_run"] == exp["shutdown_run"]:
        return False
    return exp["last_heard"] >= now - timeout(exp["interval"])


def gaps(
    conn: sqlite3.Connection,
    experiment_id: int,
    since: float,
    until: float,
    now: float,
) -> list[tuple[float, float | None]]:
    """Unknown intervals inside ``[since, until]``: the complement of coverage.

    Coverage of all runs is merged, and time before the first coverage counts
    as a gap. Time after the last coverage is a gap only if it is certain: when
    ``until >= now`` and the experiment is live, the newest data may simply not
    have arrived yet; when it is not live the last gap is ``(last_end, None)``
    (open, the experiment is offline now). Pass ``now=math.inf`` to ignore
    liveness and get the plain complement.
    """
    rows = conn.execute(
        "SELECT start, end FROM coverage WHERE experiment_id = ? "
        "AND end >= ? AND start <= ? ORDER BY start",
        (experiment_id, since, until),
    ).fetchall()
    result: list[tuple[float, float | None]] = []
    cursor = since
    for row in rows:
        if row["start"] > cursor:
            result.append((cursor, row["start"]))
        cursor = max(cursor, min(row["end"], until))
    if until >= now:
        if not is_live(conn, experiment_id, now):
            result.append((cursor, None))
    elif cursor < until:
        result.append((cursor, until))
    return result


def covered(conn: sqlite3.Connection, experiment_id: int, t0: float, t1: float):
    """True if coverage spans ``[t0, t1]`` without a gap."""
    return not gaps(conn, experiment_id, t0, t1, math.inf)


def get_data(
    conn: sqlite3.Connection,
    channels: list[str],
    since: float,
    until: float | None,
    now: float,
    max_points: int | None = None,
) -> dict:
    """Points and gaps for ``experiment/channel`` names, in the wire format.

    Raises ``UnknownChannel``, and ``TooManyPoints`` if ``max_points`` is given
    and the channels together hold more (never more than ``max_points + 1`` are
    read). Without ``until`` the points are not capped at
    ``now`` (a skewed publisher clock must not hide its newest points), while
    the gaps cover ``[since, now]``.
    """
    found = []
    for full in dict.fromkeys(channels):
        experiment, _, name = full.partition("/")
        row = conn.execute(
            "SELECT c.id, c.kind, c.unit, c.label, e.id AS experiment_id, "
            "e.name AS experiment, e.interval "
            "FROM channels c JOIN experiments e ON e.id = c.experiment_id "
            "WHERE e.name = ? AND c.name = ?",
            (experiment, name),
        ).fetchone()
        if row is None:
            raise UnknownChannel(full)
        found.append((full, row))

    upper = math.inf if until is None else until
    out_channels = {}
    experiments = {}
    remaining = -1 if max_points is None else max_points  # -1: no LIMIT
    for full, row in found:
        points = [
            [r["t"], _clean(r["v"])]
            for r in conn.execute(
                "SELECT t, v FROM points WHERE channel_id = ? AND t >= ? AND t <= ? "
                "ORDER BY t LIMIT ?",
                (row["id"], since, upper, -1 if remaining < 0 else remaining + 1),
            )
        ]
        if remaining >= 0:
            remaining -= len(points)
            if remaining < 0:
                raise TooManyPoints(max_points)
        before = None
        if row["kind"] == "state":
            prev = conn.execute(
                "SELECT t, v FROM points WHERE channel_id = ? AND t < ? "
                "ORDER BY t DESC LIMIT 1",
                (row["id"], since),
            ).fetchone()
            if prev is not None:
                before = [prev["t"], _clean(prev["v"])]
        out_channels[full] = {
            "kind": row["kind"],
            "unit": row["unit"],
            "label": row["label"],
            "before": before,
            "points": points,
        }
        if row["experiment"] not in experiments:
            experiments[row["experiment"]] = _experiment_data(
                conn, row, since, now if until is None else until, now
            )
    return {"now": now, "experiments": experiments, "channels": out_channels}


def _latched(conn: sqlite3.Connection, experiment_id: int) -> list[str]:
    return [
        r["alarm"]
        for r in conn.execute(
            "SELECT alarm FROM latched WHERE experiment_id = ? ORDER BY alarm",
            (experiment_id,),
        )
    ]


def _last_seen(conn: sqlite3.Connection, experiment_id: int) -> float | None:
    """When the server last accepted a push of the experiment (its own clock)."""
    return conn.execute(
        "SELECT last_heard FROM experiments WHERE id = ?", (experiment_id,)
    ).fetchone()[0]


def _experiment_data(conn, row, since: float, end: float, now: float) -> dict:
    experiment_id = row["experiment_id"]
    return {
        "online": is_live(conn, experiment_id, now),
        "last_seen": _last_seen(conn, experiment_id),
        "timeout": timeout(row["interval"]),
        "gaps": [list(g) for g in gaps(conn, experiment_id, since, end, now)],
        "latched": _latched(conn, experiment_id),
    }


def get_status(conn: sqlite3.Connection, now: float) -> dict:
    """Every experiment with its channels and their newest point."""
    experiments = {}
    for exp in conn.execute("SELECT id, name, interval FROM experiments ORDER BY name"):
        channels = []
        for ch in conn.execute(
            "SELECT id, name, kind, unit, label FROM channels "
            "WHERE experiment_id = ? ORDER BY name",
            (exp["id"],),
        ):
            last = conn.execute(
                "SELECT t, v FROM points WHERE channel_id = ? ORDER BY t DESC LIMIT 1",
                (ch["id"],),
            ).fetchone()
            channels.append(
                {
                    "name": ch["name"],
                    "kind": ch["kind"],
                    "unit": ch["unit"],
                    "label": ch["label"],
                    "last": None if last is None else [last["t"], _clean(last["v"])],
                }
            )
        experiments[exp["name"]] = {
            "online": is_live(conn, exp["id"], now),
            "last_seen": _last_seen(conn, exp["id"]),
            "timeout": timeout(exp["interval"]),
            "latched": _latched(conn, exp["id"]),
            "channels": channels,
        }
    return {"now": now, "experiments": experiments}


def get_events(conn: sqlite3.Connection, since: float) -> list[dict]:
    """Events with ``t >= since`` of all experiments, oldest first."""
    rows = conn.execute(
        "SELECT e.name AS experiment, v.t, v.alarm, v.action, v.message "
        "FROM events v JOIN experiments e ON e.id = v.experiment_id "
        "WHERE v.t >= ? ORDER BY v.t, v.id",
        (since,),
    )
    return [dict(r) for r in rows]
