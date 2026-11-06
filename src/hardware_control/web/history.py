"""Local copy of what the web monitor server knows about some channels.

An SQLite file with two tables: ``points`` (channel, t, v) and ``gaps``
(experiment, start, end), where an ``end`` of NULL is a gap that is still open
(the experiment was offline at the last poll). An unknown value is NULL, as on
the server. No Qt in this module.

The instrument driver writes from the thread of its adapter while a GUI or a
script reads, so one connection is shared by all threads and every call holds
a lock. The connection is opened by the first call and again after ``close``,
so a closed history can still be read, and building a ``ChannelHistory`` does
not touch the disk.
"""

import math
import sqlite3
import threading
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS points (
    channel TEXT NOT NULL, t REAL NOT NULL, v,
    PRIMARY KEY (channel, t)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS gaps (
    experiment TEXT NOT NULL, start REAL NOT NULL, end REAL);
CREATE INDEX IF NOT EXISTS gaps_experiment ON gaps (experiment, start);
"""


def _clean(v):
    """Unknown is NULL: map NaN and infinity to None."""
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def _experiment(channel: str) -> str:
    """The experiment of an ``experiment/channel`` name."""
    return channel.partition("/")[0]


class ChannelHistory:
    """Points and gaps of ``experiment/channel`` names, in a file at ``path``."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None

    def _connection(self) -> sqlite3.Connection:
        """The connection (the lock must be held); opens it if needed."""
        if self._conn is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.path, check_same_thread=False)
            try:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.executescript(SCHEMA)
                conn.commit()
            except BaseException:
                conn.close()
                raise
            self._conn = conn
        return self._conn

    def close(self) -> None:
        """Close the file. The next call opens it again."""
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    # -- writing --------------------------------------------------------------

    def add_points(self, channel: str, points: list[tuple[float, object]]) -> None:
        """Store ``(t, value)`` points; a point at a known time is left as it is."""
        with self._lock:
            conn = self._connection()
            with conn:
                conn.executemany(
                    "INSERT OR IGNORE INTO points (channel, t, v) VALUES (?, ?, ?)",
                    [(channel, t, _clean(v)) for t, v in points],
                )

    def replace_gaps(
        self,
        experiment: str,
        since: float,
        until: float,
        gaps: list[tuple[float, float | None]],
    ) -> None:
        """Replace what is known about gaps in ``[since, until]``, in one transaction.

        The stored gaps that overlap the range are deleted and ``gaps`` (the
        server's answer for the range, so they begin at ``since`` at the
        earliest) are inserted. A stored gap that began before ``since`` keeps
        its start: it is cut at ``since`` and joined to the new gap that starts
        there, if any.
        """
        with self._lock:
            conn = self._connection()
            with conn:
                earlier = conn.execute(
                    "SELECT MIN(start) FROM gaps WHERE experiment = ? AND start < ? "
                    "AND (end IS NULL OR end >= ?)",
                    (experiment, since, since),
                ).fetchone()[0]
                conn.execute(
                    "DELETE FROM gaps WHERE experiment = ? AND start <= ? "
                    "AND (end IS NULL OR end >= ?)",
                    (experiment, until, since),
                )
                new = sorted(gaps, key=lambda g: g[0])
                if earlier is not None:
                    if new and new[0][0] <= since:
                        new[0] = (earlier, new[0][1])
                    else:
                        new.insert(0, (earlier, since))
                conn.executemany(
                    "INSERT INTO gaps (experiment, start, end) VALUES (?, ?, ?)",
                    [(experiment, start, end) for start, end in new],
                )

    # -- reading --------------------------------------------------------------

    def last_time(self, channel: str) -> float | None:
        """Time of the newest point of the channel, None if there is none."""
        with self._lock:
            return (
                self._connection()
                .execute("SELECT MAX(t) FROM points WHERE channel = ?", (channel,))
                .fetchone()[0]
            )

    def last_point(self, channel: str) -> tuple[float, object] | None:
        """The newest ``(t, value)`` of the channel, None if there is none."""
        with self._lock:
            row = (
                self._connection()
                .execute(
                    "SELECT t, v FROM points WHERE channel = ? ORDER BY t DESC LIMIT 1",
                    (channel,),
                )
                .fetchone()
            )
        return None if row is None else (row[0], row[1])

    def open_gap_start(self, experiment: str) -> float | None:
        """Start of the gap that is still open, None if there is none."""
        with self._lock:
            return (
                self._connection()
                .execute(
                    "SELECT MIN(start) FROM gaps WHERE experiment = ? AND end IS NULL",
                    (experiment,),
                )
                .fetchone()[0]
            )

    def points(
        self, channel: str, start: float | None = None, end: float | None = None
    ) -> list[tuple[float, object]]:
        """``(t, value)`` of the channel with ``start <= t <= end``, oldest first."""
        with self._lock:
            rows = (
                self._connection()
                .execute(
                    "SELECT t, v FROM points WHERE channel = ? AND t >= ? AND t <= ? "
                    "ORDER BY t",
                    (
                        channel,
                        -math.inf if start is None else start,
                        math.inf if end is None else end,
                    ),
                )
                .fetchall()
            )
        return [(t, v) for t, v in rows]

    def gaps(
        self, experiment: str, start: float | None = None, end: float | None = None
    ) -> list[tuple[float, float | None]]:
        """Gaps overlapping ``[start, end]`` as ``(start, end or None)``, oldest first."""
        with self._lock:
            rows = (
                self._connection()
                .execute(
                    "SELECT start, end FROM gaps WHERE experiment = ? AND start <= ? "
                    "AND (end IS NULL OR end >= ?) ORDER BY start",
                    (
                        experiment,
                        math.inf if end is None else end,
                        -math.inf if start is None else start,
                    ),
                )
                .fetchall()
            )
        return [(s, e) for s, e in rows]

    def to_pandas(
        self, channel: str, start: float | None = None, end: float | None = None
    ):
        """The points as a DataFrame with columns ``time`` and ``value``.

        ``time`` is unix seconds and ``value`` is numeric if all values are
        numbers (or unknown), else it keeps the text. Each gap that starts in
        the range adds a row with an unknown value at its start, so a plot of
        the frame breaks there instead of drawing a line across the gap.
        """
        import pandas as pd

        rows = [(t, v, 0) for t, v in self.points(channel, start, end)]
        if rows:  # a channel without points has nothing to break
            for gap_start, _gap_end in self.gaps(_experiment(channel), start, end):
                if start is None or gap_start >= start:
                    rows.append((gap_start, None, 1))
        rows.sort(key=lambda row: (row[0], row[2]))
        frame = pd.DataFrame(
            {"time": [r[0] for r in rows], "value": [r[1] for r in rows]},
            columns=["time", "value"],
        )
        frame["time"] = frame["time"].astype(float)
        try:
            frame["value"] = pd.to_numeric(frame["value"])
        except (ValueError, TypeError):
            pass
        return frame
