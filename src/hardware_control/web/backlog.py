"""Outbound buffer for the web publisher: what could not be sent yet.

An SQLite file with three tables (points, ticks, events). Rows get an
autoincrement id and the time ``t`` they belong to. The connection is used
from the creating thread only. No Qt in this module.
"""

import json
import math
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS points (
    id INTEGER PRIMARY KEY AUTOINCREMENT, t REAL NOT NULL, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ticks (
    id INTEGER PRIMARY KEY AUTOINCREMENT, t REAL NOT NULL);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, t REAL NOT NULL, data TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS points_t ON points (t);
CREATE INDEX IF NOT EXISTS ticks_t ON ticks (t);
CREATE INDEX IF NOT EXISTS events_t ON events (t);
"""

TABLES = ("points", "ticks", "events")


def _finite(point: dict) -> dict:
    """``point`` with a NaN or infinite value (unknown) replaced by None."""
    v = point.get("v")
    if isinstance(v, float) and not math.isfinite(v):
        return {**point, "v": None}
    return point


def _dumps(row: dict) -> str:
    """Strict JSON: a stored row must always be sendable."""
    return json.dumps(row, allow_nan=False)


@dataclass
class Batch:
    """Rows taken from the backlog; pass it to ``Backlog.remove`` once sent."""

    point_ids: list[int] = field(default_factory=list)
    tick_ids: list[int] = field(default_factory=list)
    event_ids: list[int] = field(default_factory=list)
    points: list[dict] = field(default_factory=list)
    ticks: list[float] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)


class Backlog:
    """Points, ticks and events waiting to be pushed, oldest first.

    ``max_age`` (seconds) is what ``prune`` keeps.
    """

    def __init__(self, path: Path, max_age: float = 7 * 86400):
        self.max_age = max_age
        self._conn = sqlite3.connect(path)
        try:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(SCHEMA)
            self._conn.commit()
        except BaseException:
            self._conn.close()
            raise

    def close(self) -> None:
        self._conn.close()

    def add(self, points: list[dict], ticks: list[float], events: list[dict]) -> None:
        with self._conn:
            self._conn.executemany(
                "INSERT INTO points (t, data) VALUES (?, ?)",
                [(p["t"], _dumps(_finite(p))) for p in points],
            )
            self._conn.executemany(
                "INSERT INTO ticks (t) VALUES (?)", [(t,) for t in ticks]
            )
            self._conn.executemany(
                "INSERT INTO events (t, data) VALUES (?, ?)",
                [(e["t"], _dumps(e)) for e in events],
            )

    def take(self, limit: int = 500) -> Batch:
        """The oldest ``limit`` rows of all three tables together, by ``t``."""
        rows = self._conn.execute(
            "SELECT kind, id, t, data FROM ("
            " SELECT 0 AS kind, id, t, data FROM points"
            " UNION ALL SELECT 1, id, t, NULL FROM ticks"
            " UNION ALL SELECT 2, id, t, data FROM events"
            ") ORDER BY t, kind, id LIMIT ?",
            (limit,),
        ).fetchall()
        batch = Batch()
        for kind, row_id, t, data in rows:
            if kind == 0:
                batch.point_ids.append(row_id)
                batch.points.append(json.loads(data))
            elif kind == 1:
                batch.tick_ids.append(row_id)
                batch.ticks.append(t)
            else:
                batch.event_ids.append(row_id)
                batch.events.append(json.loads(data))
        return batch

    def remove(self, batch: Batch) -> None:
        with self._conn:
            for table, ids in (
                ("points", batch.point_ids),
                ("ticks", batch.tick_ids),
                ("events", batch.event_ids),
            ):
                self._conn.executemany(
                    f"DELETE FROM {table} WHERE id = ?", [(i,) for i in ids]
                )

    def count(self) -> int:
        return sum(
            self._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in TABLES
        )

    def prune(self, now: float) -> int:
        """Delete rows older than ``max_age``; returns how many."""
        deleted = 0
        with self._conn:
            for table in TABLES:
                cur = self._conn.execute(
                    f"DELETE FROM {table} WHERE t < ?", (now - self.max_age,)
                )
                deleted += cur.rowcount
        return deleted
