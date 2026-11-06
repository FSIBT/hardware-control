"""Schema version and migration of the hc_web database."""

import sqlite3
import threading

import pytest

pytest.importorskip("flask")

from hc_web import db  # noqa: E402

# The schema as it was before ``user_version``, ``experiments.last_heard`` and
# the autoincrement event ids.
V0_SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE experiments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    interval REAL,
    current_run TEXT,
    shutdown_run TEXT,
    clock_offset REAL,
    created REAL
);
CREATE TABLE coverage (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    run TEXT,
    start REAL,
    end REAL
);
CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    t REAL,
    alarm TEXT,
    action TEXT,
    message TEXT,
    UNIQUE (experiment_id, t, alarm, action)
);
"""


def make_v0(path):
    """A version 0 database with two experiments, coverage and events."""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode = WAL")  # as connect() always did
    conn.executescript(V0_SCHEMA)
    conn.executescript(
        """
        INSERT INTO experiments (id, name, interval, current_run, created)
            VALUES (1, 'B', 10, 'A', 1.0), (2, 'C', 10, NULL, 1.0);
        INSERT INTO coverage (experiment_id, run, start, end)
            VALUES (1, 'A', 100, 200), (1, 'A', 300, 400), (1, 'old', 1, 50);
        INSERT INTO events (id, experiment_id, t, alarm, action, message)
            VALUES (3, 1, 150, 'HV', 'triggered', 'm'),
                   (7, 1, 160, 'HV', 'cleared', 'm');
        """
    )
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 0
    conn.commit()
    conn.close()


def user_version(conn):
    return conn.execute("PRAGMA user_version").fetchone()[0]


def columns(conn, table):
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]


def test_fresh_database_has_the_current_version(tmp_path):
    conn = db.connect(tmp_path / "new.sqlite")
    try:
        assert user_version(conn) == db.SCHEMA_VERSION == 1
        assert "last_heard" in columns(conn, "experiments")
        sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'events'"
        ).fetchone()[0]
        assert "AUTOINCREMENT" in sql
    finally:
        conn.close()


def test_v0_database_is_migrated(tmp_path):
    path = tmp_path / "old.sqlite"
    make_v0(path)
    conn = db.connect(path)
    try:
        assert user_version(conn) == 1
        assert "last_heard" in columns(conn, "experiments")
        heard = {
            r["name"]: r["last_heard"]
            for r in conn.execute("SELECT name, last_heard FROM experiments")
        }
        assert heard == {"B": 400.0, "C": None}  # backfilled from the coverage
        # the new tables exist and the old rows are kept, with their ids
        assert conn.execute("SELECT id FROM events ORDER BY id").fetchall()[0][0] == 3
        assert [r[0] for r in conn.execute("SELECT id FROM events ORDER BY id")] == [
            3,
            7,
        ]
        assert conn.execute("SELECT COUNT(*) FROM tokens").fetchone()[0] == 0
        # the event ids are monotonic: the id of a deleted last row is not reused
        with conn:
            conn.execute("DELETE FROM events WHERE id = 7")
            conn.execute(
                "INSERT INTO events (experiment_id, t, alarm, action) "
                "VALUES (1, 170, 'HV', 'triggered')"
            )
        assert conn.execute("SELECT MAX(id) FROM events").fetchone()[0] == 8
    finally:
        conn.close()
    # connecting again changes nothing
    conn = db.connect(path)
    try:
        assert user_version(conn) == 1
        assert conn.execute("SELECT COUNT(*) FROM coverage").fetchone()[0] == 3
    finally:
        conn.close()


def test_v0_experiment_without_coverage_is_never_heard(tmp_path):
    path = tmp_path / "old.sqlite"
    make_v0(path)
    conn = db.connect(path)
    try:
        row = conn.execute("SELECT last_heard FROM experiments WHERE id = 2").fetchone()
        assert row[0] is None
    finally:
        conn.close()


def test_a_newer_database_is_refused(tmp_path):
    path = tmp_path / "future.sqlite"
    raw = sqlite3.connect(path)
    raw.execute(f"PRAGMA user_version = {db.SCHEMA_VERSION + 1}")
    raw.commit()
    raw.close()
    with pytest.raises(db.SchemaVersionError, match="newer"):
        db.connect(path)
    # and it was left alone
    raw = sqlite3.connect(path)
    try:
        assert raw.execute("PRAGMA user_version").fetchone()[0] == 2
        assert not raw.execute("SELECT name FROM sqlite_master").fetchall()
    finally:
        raw.close()


def test_failed_migration_leaves_the_database_unchanged(tmp_path, monkeypatch):
    path = tmp_path / "old.sqlite"
    make_v0(path)

    def boom(conn):
        raise RuntimeError("disk full")

    monkeypatch.setattr(db, "_rebuild_events", boom)
    with pytest.raises(RuntimeError, match="disk full"):
        db.connect(path)
    raw = sqlite3.connect(path)
    try:
        assert raw.execute("PRAGMA user_version").fetchone()[0] == 0
        cols = [r[1] for r in raw.execute("PRAGMA table_info(experiments)")]
        assert "last_heard" not in cols
    finally:
        raw.close()


def test_concurrent_connects_migrate_once(tmp_path, monkeypatch):
    path = tmp_path / "old.sqlite"
    make_v0(path)
    real = db._upgrade_v0
    calls = []
    barrier = threading.Barrier(4)

    def counting(conn):
        calls.append(1)
        real(conn)

    monkeypatch.setattr(db, "_upgrade_v0", counting)
    results = []

    def worker():
        barrier.wait()
        try:
            conn = db.connect(path)
            results.append(user_version(conn))
            conn.close()
        except Exception as e:  # reported by the assertion below
            results.append(e)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
        assert not t.is_alive()
    assert results == [1, 1, 1, 1]
    assert len(calls) == 1


def test_concurrent_connects_to_a_new_file(tmp_path):
    path = tmp_path / "new.sqlite"
    barrier = threading.Barrier(4)
    results = []

    def worker():
        barrier.wait()
        try:
            conn = db.connect(path)
            results.append(user_version(conn))
            conn.close()
        except Exception as e:  # reported by the assertion below
            results.append(e)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert results == [1, 1, 1, 1]


def test_connecting_a_current_database_does_not_write(tmp_path):
    path = tmp_path / "hc.sqlite"
    db.connect(path).close()
    conn = db.connect(path)
    try:
        before = conn.execute("PRAGMA data_version").fetchone()[0]
        db.connect(path).close()
        assert conn.execute("PRAGMA data_version").fetchone()[0] == before
    finally:
        conn.close()
