import logging

import pytest

pytest.importorskip("flask")

from hc_web import db  # noqa: E402
from hc_web.cli import main  # noqa: E402
from hc_web.query import gaps, get_data  # noqa: E402
from hc_web.retention import cleanup, maybe_cleanup  # noqa: E402
from hc_web.tokens import create_token, get_or_create_experiment  # noqa: E402

DAY = 86400.0
NOW = 100 * DAY


@pytest.fixture
def conn(config):
    c = db.connect(config.database)
    yield c
    c.close()


@pytest.fixture
def exp(conn):
    experiment_id = get_or_create_experiment(conn, "B")
    with conn:
        conn.execute(
            "UPDATE experiments SET interval = 10, current_run = 'A' WHERE id = ?",
            (experiment_id,),
        )
    return experiment_id


def add_channel(conn, experiment_id, name, kind, points=()):
    with conn:
        cur = conn.execute(
            "INSERT INTO channels (experiment_id, name, kind) VALUES (?, ?, ?)",
            (experiment_id, name, kind),
        )
        conn.executemany(
            "INSERT INTO points (channel_id, t, v) VALUES (?, ?, ?)",
            [(cur.lastrowid, t, v) for t, v in points],
        )
    return cur.lastrowid


def add_coverage(conn, experiment_id, start, end, run="A"):
    with conn:
        conn.execute(
            "INSERT INTO coverage (experiment_id, run, start, end) VALUES (?, ?, ?, ?)",
            (experiment_id, run, start, end),
        )


def times(conn, table, column="t"):
    return [r[0] for r in conn.execute(f"SELECT {column} FROM {table} ORDER BY 1")]


def point_times(conn, channel_id):
    return [
        r[0]
        for r in conn.execute(
            "SELECT t FROM points WHERE channel_id = ? ORDER BY t", (channel_id,)
        )
    ]


def test_cleanup_deletes_old_points(conn, exp):
    cutoff = NOW - 7 * DAY
    ch = add_channel(
        conn,
        exp,
        "temp",
        "sampled",
        [(cutoff - 2 * DAY, 1.0), (cutoff - 1.0, 2.0), (cutoff, 3.0), (NOW, 4.0)],
    )
    deleted = cleanup(conn, NOW, 7)
    assert point_times(conn, ch) == [cutoff, NOW]
    assert deleted["points"] == 2


def test_retention_keeps_last_state_before_cutoff(conn, exp):
    ch = add_channel(conn, exp, "ng_on", "state", [(NOW - 10 * DAY, "0")])
    add_coverage(conn, exp, NOW - 1000, NOW)
    cleanup(conn, NOW, 7)
    since = NOW - 7 * DAY
    data = get_data(conn, ["B/ng_on"], since, None, NOW)
    assert data["channels"]["B/ng_on"]["before"] == [NOW - 10 * DAY, "0"]
    assert point_times(conn, ch) == [NOW - 10 * DAY]


def test_only_newest_state_point_before_cutoff_is_kept(conn, exp):
    cutoff = NOW - 7 * DAY
    ch = add_channel(
        conn,
        exp,
        "ng_on",
        "state",
        [(cutoff - 9 * DAY, "0"), (cutoff - 5 * DAY, "1"), (cutoff - 2 * DAY, "0")],
    )
    assert cleanup(conn, NOW, 7)["points"] == 2
    assert point_times(conn, ch) == [cutoff - 2 * DAY]


def test_state_channel_without_old_points_keeps_nothing_special(conn, exp):
    cutoff = NOW - 7 * DAY
    ch = add_channel(conn, exp, "ng_on", "state", [(cutoff + 1, "1")])
    assert cleanup(conn, NOW, 7)["points"] == 0
    assert point_times(conn, ch) == [cutoff + 1]


def test_sampled_channel_keeps_nothing_before_cutoff(conn, exp):
    ch = add_channel(conn, exp, "temp", "sampled", [(NOW - 10 * DAY, 1.0)])
    cleanup(conn, NOW, 7)
    assert point_times(conn, ch) == []


def test_state_retention_is_per_channel(conn, exp):
    other = get_or_create_experiment(conn, "C")
    a = add_channel(
        conn, exp, "s", "state", [(NOW - 9 * DAY, "a"), (NOW - 8 * DAY, "b")]
    )
    b = add_channel(conn, other, "s", "state", [(NOW - 20 * DAY, "x")])
    cleanup(conn, NOW, 7)
    assert point_times(conn, a) == [NOW - 8 * DAY]
    assert point_times(conn, b) == [NOW - 20 * DAY]


def test_events_warnings_invites(conn, exp):
    cutoff = NOW - 7 * DAY
    with conn:
        conn.executemany(
            "INSERT INTO events (experiment_id, t, alarm, action) VALUES (?, ?, 'HV', ?)",
            [(exp, cutoff - 1, "old"), (exp, cutoff, "edge"), (exp, NOW, "new")],
        )
        conn.executemany(
            "INSERT INTO warnings (experiment_id, t, message) VALUES (?, ?, ?)",
            [(exp, cutoff - 1, "old"), (exp, cutoff, "edge"), (None, NOW, "new")],
        )
        conn.executemany(
            "INSERT INTO invites (code_hash, role, created, expires) VALUES (?, 'viewer', 0, ?)",
            [
                ("expired-long", NOW - DAY - 1),
                ("expired-recent", NOW - DAY + 1),
                ("unexpired", NOW + DAY),
            ],
        )
    deleted = cleanup(conn, NOW, 7)
    assert [r[0] for r in conn.execute("SELECT action FROM events ORDER BY t")] == [
        "edge",
        "new",
    ]
    assert [r[0] for r in conn.execute("SELECT message FROM warnings ORDER BY t")] == [
        "edge",
        "new",
    ]
    assert sorted(times(conn, "invites", "code_hash")) == [
        "expired-recent",
        "unexpired",
    ]
    assert deleted["events"] == 1
    assert deleted["warnings"] == 1
    assert deleted["invites"] == 1


def test_expired_challenges_deleted(conn):
    with conn:
        conn.executemany(
            "INSERT INTO challenges (id, challenge, purpose, expires) "
            "VALUES (?, x'00', 'login', ?)",
            [("expired", NOW - 1), ("live", NOW + 1)],
        )
    assert cleanup(conn, NOW, 7)["challenges"] == 1
    assert [r[0] for r in conn.execute("SELECT id FROM challenges")] == ["live"]


def test_coverage_deleted_and_clamped(conn, exp):
    cutoff = NOW - 7 * DAY
    add_coverage(conn, exp, cutoff - 3 * DAY, cutoff - 2 * DAY)
    add_coverage(conn, exp, cutoff - DAY, cutoff + DAY)
    add_coverage(conn, exp, cutoff + 2 * DAY, cutoff + 3 * DAY)
    deleted = cleanup(conn, NOW, 7)
    rows = [
        tuple(r) for r in conn.execute("SELECT start, end FROM coverage ORDER BY start")
    ]
    assert rows == [
        (cutoff, cutoff + DAY),
        (cutoff + 2 * DAY, cutoff + 3 * DAY),
    ]
    assert deleted["coverage"] == 1


def test_gaps_after_clamp_are_not_spurious(conn, exp):
    cutoff = NOW - 7 * DAY
    add_coverage(conn, exp, cutoff - DAY, NOW)
    with conn:
        conn.execute("UPDATE experiments SET last_heard = ?", (NOW,))
    add_channel(conn, exp, "ng_on", "state", [(cutoff - DAY, "0")])
    before = gaps(conn, exp, cutoff, NOW, NOW)
    cleanup(conn, NOW, 7)
    assert gaps(conn, exp, cutoff, NOW, NOW) == before == []
    data = get_data(conn, ["B/ng_on"], cutoff, None, NOW)
    assert data["channels"]["B/ng_on"]["before"] == [cutoff - DAY, "0"]
    assert data["experiments"]["B"]["gaps"] == []


def test_returns_count_per_table_and_is_idempotent(conn, exp):
    add_channel(conn, exp, "temp", "sampled", [(NOW - 10 * DAY, 1.0)])
    add_coverage(conn, exp, 0, NOW - 9 * DAY)
    first = cleanup(conn, NOW, 7)
    assert first == {
        "points": 1,
        "events": 0,
        "coverage": 1,
        "warnings": 0,
        "invites": 0,
        "challenges": 0,
    }
    assert cleanup(conn, NOW, 7) == dict.fromkeys(first, 0)


def test_fractional_retention_days(conn, exp):
    ch = add_channel(
        conn, exp, "temp", "sampled", [(NOW - 0.6 * DAY, 1.0), (NOW - 0.4 * DAY, 2.0)]
    )
    cleanup(conn, NOW, 0.5)
    assert point_times(conn, ch) == [NOW - 0.4 * DAY]


def test_maybe_cleanup_runs_hourly(conn, exp):
    ch = add_channel(conn, exp, "temp", "sampled", [(NOW - 10 * DAY, 1.0)])
    first = maybe_cleanup(conn, NOW, 7)
    assert first["points"] == 1
    assert db.get_meta(conn, "last_cleanup") is not None
    add_channel(conn, exp, "temp2", "sampled", [(NOW - 10 * DAY, 1.0)])
    assert maybe_cleanup(conn, NOW + 3600, 7) is None
    assert times(conn, "points") == [NOW - 10 * DAY]
    second = maybe_cleanup(conn, NOW + 3601, 7)
    assert second["points"] == 1
    assert point_times(conn, ch) == []


def test_push_runs_cleanup(client, conn, exp, monkeypatch):
    token = create_token(conn, "B", "pc")
    add_channel(conn, exp, "temp", "sampled", [(NOW - 10 * DAY, 1.0)])
    monkeypatch.setattr("hc_web.api.time.time", lambda: NOW)
    r = client.post(
        "/api/v1/push",
        json={"points": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert times(conn, "points") == []


def test_push_survives_cleanup_failure(client, conn, caplog, monkeypatch):
    token = create_token(conn, "B", "pc")

    def boom(*args):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr("hc_web.api.maybe_cleanup", boom)
    with caplog.at_level(logging.ERROR):
        r = client.post(
            "/api/v1/push",
            json={"points": [{"channel": "temp", "t": 1000.0, "v": 1.5}]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200
    assert r.get_json() == {"ok": True}
    assert any("disk on fire" in (rec.exc_text or "") for rec in caplog.records)
    assert conn.execute("SELECT COUNT(*) FROM points").fetchone()[0] == 1


@pytest.fixture
def cfg(config, tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        f'origin = "http://localhost"\ndatabase = "{config.database}"\n'
        "retention_days = 1\n"
    )
    return str(path)


def test_cli_cleanup(conn, exp, cfg, capsys):
    import time

    add_channel(conn, exp, "temp", "sampled", [(time.time() - 3 * DAY, 1.0)])
    assert main(["cleanup", "--config", cfg]) == 0
    out = capsys.readouterr().out
    assert "points" in out and "1" in out
    assert times(conn, "points") == []
    assert main(["cleanup", "--config", cfg]) == 0
    assert "points: 0" in capsys.readouterr().out
