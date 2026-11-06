import pytest

pytest.importorskip("flask")

from hc_web import db  # noqa: E402
from hc_web.tokens import create_token  # noqa: E402


class Clock:
    now = 1000.0


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    c.now = 1000.0
    monkeypatch.setattr("hc_web.api.time.time", lambda: c.now)
    return c


@pytest.fixture
def conn(config):
    c = db.connect(config.database)
    yield c
    c.close()


@pytest.fixture
def write_token(conn):
    return create_token(conn, "B", "lab pc")


def push(client, token, raw=None, **overrides):
    """POST a full push body (run A, interval 10) with ``overrides``."""
    body = {
        "run": "A",
        "sent_at": 1000.0,
        "interval": 10.0,
        "channels": [{"name": "temp", "kind": "sampled", "unit": "C", "label": "T"}],
        "points": [],
        "ticks": [],
        "events": [],
        "latched": [],
        "shutdown": False,
    }
    body.update(overrides)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if raw is not None:
        return client.post("/api/v1/push", data=raw, headers=headers)
    return client.post("/api/v1/push", json=body, headers=headers)


def count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_push_stores_points_and_coverage(client, conn, clock, write_token):
    clock.now = 10.0
    r = push(client, write_token, sent_at=10.0, ticks=[0.0, 10.0])
    assert r.status_code == 200
    assert r.get_json() == {"ok": True}
    clock.now = 20.0
    r = push(
        client,
        write_token,
        sent_at=20.0,
        ticks=[20.0],
        points=[{"channel": "temp", "t": 20.0, "v": 21.5}],
    )
    assert r.status_code == 200
    rows = conn.execute("SELECT run, start, end FROM coverage").fetchall()
    assert [tuple(r) for r in rows] == [("A", 0.0, 20.0)]
    pts = conn.execute("SELECT t, v FROM points").fetchall()
    assert [tuple(p) for p in pts] == [(20.0, 21.5)]
    exp = conn.execute("SELECT interval, current_run FROM experiments").fetchone()
    assert tuple(exp) == (10.0, "A")
    ch = conn.execute("SELECT name, kind, unit, label FROM channels").fetchone()
    assert tuple(ch) == ("temp", "sampled", "C", "T")


def test_far_apart_ticks_make_separate_coverage_rows(client, conn, clock, write_token):
    r = push(client, write_token, ticks=[0.0, 5.0, 100.0])
    assert r.status_code == 200
    rows = conn.execute("SELECT start, end FROM coverage ORDER BY start").fetchall()
    assert [tuple(r) for r in rows] == [(0.0, 5.0), (100.0, 100.0)]


def test_push_idempotent(client, conn, clock, write_token):
    body = dict(
        channels=[{"name": "ng", "kind": "state"}],
        points=[
            {"channel": "ng", "t": 1.0, "v": "1"},
            {"channel": "ng", "t": 2.0, "v": "0"},
            {"channel": "ng", "t": 3.0, "v": "1"},
        ],
        ticks=[1.0, 2.0, 3.0],
        events=[{"t": 2.0, "alarm": "HV", "action": "triggered", "message": "m"}],
    )
    assert push(client, write_token, **body).status_code == 200
    first = [count(conn, t) for t in ("points", "coverage", "events")]
    assert first == [3, 1, 1]
    assert push(client, write_token, **body).status_code == 200
    assert [count(conn, t) for t in ("points", "coverage", "events")] == first


def test_state_only_changes_stored(client, conn, clock, write_token):
    values = [1, 1, 0, 0, 1]
    r = push(
        client,
        write_token,
        channels=[{"name": "ng", "kind": "state"}],
        points=[{"channel": "ng", "t": float(i), "v": v} for i, v in enumerate(values)],
        ticks=[float(i) for i in range(5)],
    )
    assert r.status_code == 200
    rows = conn.execute("SELECT t, v FROM points ORDER BY t").fetchall()
    assert [tuple(r) for r in rows] == [(0.0, 1), (2.0, 0), (4.0, 1)]


def test_state_point_after_gap_is_stored(client, conn, clock, write_token):
    state = [{"name": "ng", "kind": "state"}]
    push(
        client,
        write_token,
        channels=state,
        points=[{"channel": "ng", "t": 0.0, "v": 1}],
        ticks=[0.0],
    )
    # Same value, but after a gap (no coverage between 0 and 500).
    r = push(
        client,
        write_token,
        channels=state,
        points=[{"channel": "ng", "t": 500.0, "v": 1}],
        ticks=[500.0],
    )
    assert r.status_code == 200
    assert count(conn, "points") == 2


def test_push_accepts_null_values(client, conn, clock, write_token):
    r = push(
        client,
        write_token,
        channels=[
            {"name": "temp", "kind": "sampled"},
            {"name": "ng", "kind": "state"},
        ],
        points=[
            {"channel": "temp", "t": 1.0, "v": None},
            {"channel": "ng", "t": 1.0, "v": None},
        ],
        ticks=[1.0],
    )
    assert r.status_code == 200
    rows = conn.execute("SELECT t, v FROM points").fetchall()
    assert len(rows) == 2
    assert all(r["v"] is None for r in rows)


def test_auth_errors(client, conn, clock, write_token):
    assert push(client, None).status_code == 401
    assert push(client, "999.nope").status_code == 401
    assert push(client, "garbage").status_code == 401
    r = client.post("/api/v1/push", json={}, headers={"Authorization": "Basic abc"})
    assert r.status_code == 401
    read_token = create_token(conn, "B", "viewer", scope="read")
    assert push(client, read_token).status_code == 403
    assert push(client, write_token, points="nope").status_code == 400
    assert count(conn, "points") == 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"points": [{"channel": "temp", "t": "x", "v": 1}]},
        {"points": [{"channel": "bad name!", "t": 1.0, "v": 1}]},
        {"points": [{"channel": "temp", "t": 1.0, "v": "warm"}]},
        {"points": [{"channel": "temp", "t": 1.0, "v": True}]},
        {"points": [{"channel": "temp", "t": float("nan"), "v": 1}]},
        {"points": [{"t": 1.0, "v": 1}]},
        {"points": ["x"]},
        {"channels": [{"name": "c", "kind": "weird"}]},
        {"channels": "x"},
        {"interval": 0},
        {"interval": "10"},
        {"sent_at": "now"},
        {"run": ""},
        {"ticks": ["a"]},
        {"ticks": 5},
        {"latched": "HV"},
        {"latched": [1]},
        {"shutdown": "yes"},
        {"events": [{"t": 1.0, "alarm": None, "action": "triggered"}]},
        {"events": [{"t": 1.0, "alarm": "", "action": "triggered"}]},
        {"events": [{"t": 1.0, "alarm": "HV", "action": None}]},
        {"events": [{"t": 1.0, "alarm": "HV", "action": ""}]},
        {"events": [{"t": None, "alarm": "HV", "action": "triggered"}]},
        {"events": "x"},
    ],
)
def test_malformed_bodies_rejected(client, conn, clock, write_token, overrides):
    r = push(client, write_token, **overrides)
    assert r.status_code == 400
    assert "error" in r.get_json()
    assert count(conn, "points") == 0
    assert count(conn, "coverage") == 0


def test_body_must_be_json_object(client, clock, write_token):
    assert push(client, write_token, raw=b"not json").status_code == 400
    assert push(client, write_token, raw=b"[1, 2]").status_code == 400
    assert push(client, write_token, raw=b"{}").status_code == 400  # no points


def test_sampled_channel_rejects_string_value(client, conn, clock, write_token):
    r = push(
        client,
        write_token,
        points=[{"channel": "temp", "t": 1.0, "v": "warm"}],
    )
    assert r.status_code == 400
    assert count(conn, "points") == 0


def test_restart_within_timeout_rejected_then_accepted(
    client, conn, clock, write_token
):
    clock.now = 100.0
    r = push(
        client,
        write_token,
        run="A",
        sent_at=100.0,
        ticks=[100.0],
        points=[{"channel": "temp", "t": 100.0, "v": 1.0}],
    )
    assert r.status_code == 200

    clock.now = 110.0
    r = push(
        client,
        write_token,
        run="B",
        sent_at=110.0,
        ticks=[110.0],
        points=[{"channel": "temp", "t": 110.0, "v": 2.0}],
        latched=["HV"],
    )
    assert r.status_code == 409
    assert r.get_json() == {"error": "another run is active"}
    assert count(conn, "warnings") == 1
    # The rejected push left nothing else behind.
    assert count(conn, "points") == 1
    assert count(conn, "latched") == 0
    assert conn.execute("SELECT current_run FROM experiments").fetchone()[0] == "A"

    # A retry of the rejected push does not flood the warnings table.
    clock.now = 112.0
    assert (
        push(client, write_token, run="B", sent_at=112.0, ticks=[112.0]).status_code
        == 409
    )
    assert count(conn, "warnings") == 1

    clock.now = 131.0
    r = push(
        client,
        write_token,
        run="B",
        sent_at=131.0,
        ticks=[131.0],
        points=[{"channel": "temp", "t": 131.0, "v": 2.0}],
    )
    assert r.status_code == 200
    rows = conn.execute("SELECT run, start, end FROM coverage ORDER BY id").fetchall()
    assert [tuple(r) for r in rows] == [("A", 100.0, 100.0), ("B", 131.0, 131.0)]
    assert conn.execute("SELECT current_run FROM experiments").fetchone()[0] == "B"


def test_shutdown_allows_new_run_immediately(client, conn, clock, write_token):
    clock.now = 100.0
    r = push(client, write_token, run="A", sent_at=100.0, ticks=[100.0], shutdown=True)
    assert r.status_code == 200
    assert conn.execute("SELECT shutdown_run FROM experiments").fetchone()[0] == "A"
    clock.now = 101.0
    r = push(client, write_token, run="B", sent_at=101.0, ticks=[101.0])
    assert r.status_code == 200
    assert conn.execute("SELECT current_run FROM experiments").fetchone()[0] == "B"


def test_clock_skew_warning(client, conn, clock, write_token):
    clock.now = 1000.0
    r = push(client, write_token, sent_at=940.0, ticks=[940.0])
    assert r.status_code == 200
    assert count(conn, "warnings") == 1
    offset = conn.execute("SELECT clock_offset FROM experiments").fetchone()[0]
    assert offset == pytest.approx(60.0)
    # At most one skew warning per experiment per hour.
    clock.now = 1010.0
    push(client, write_token, sent_at=950.0, ticks=[950.0])
    assert count(conn, "warnings") == 1
    clock.now = 1000.0 + 3601.0
    push(client, write_token, sent_at=clock.now - 60, ticks=[clock.now - 60])
    assert count(conn, "warnings") == 2


def test_small_skew_gives_no_warning(client, conn, clock, write_token):
    r = push(client, write_token, sent_at=997.0, ticks=[997.0])
    assert r.status_code == 200
    assert count(conn, "warnings") == 0


def test_latched_replaced(client, conn, clock, write_token):
    push(client, write_token, latched=["a", "b"])
    push(client, write_token, latched=["b"])
    rows = conn.execute("SELECT alarm FROM latched").fetchall()
    assert [r[0] for r in rows] == ["b"]


def test_minimal_push_defaults(client, conn, clock, write_token):
    clock.now = 1762200000.0
    body = {"points": [{"channel": "temp", "t": 1762199999.0, "v": 21.5}]}
    headers = {"Authorization": f"Bearer {write_token}"}
    r = client.post("/api/v1/push", json=body, headers=headers)
    assert r.status_code == 200
    ch = conn.execute("SELECT name, kind, unit, label FROM channels").fetchone()
    assert ch["name"] == "temp" and ch["kind"] == "sampled"
    exp = conn.execute("SELECT interval, current_run FROM experiments").fetchone()
    assert tuple(exp) == (60.0, "external")
    rows = conn.execute("SELECT start, end FROM coverage").fetchall()
    assert [tuple(r) for r in rows] == [(1762200000.0, 1762200000.0)]
    assert count(conn, "warnings") == 0

    clock.now += 30
    body = {"points": [{"channel": "temp", "t": clock.now, "v": 22.0}]}
    assert client.post("/api/v1/push", json=body, headers=headers).status_code == 200
    clock.now += 5
    assert client.post("/api/v1/push", json=body, headers=headers).status_code == 200
    assert count(conn, "points") == 2
    rows = conn.execute("SELECT start, end FROM coverage").fetchall()
    assert [tuple(r) for r in rows] == [(1762200000.0, 1762200035.0)]
    assert count(conn, "warnings") == 0


def test_minimal_push_with_curl_content_type(client, conn, clock, write_token):
    """curl -d sends a form content type; the body is still JSON."""
    r = client.post(
        "/api/v1/push",
        data='{"points":[{"channel":"temp","t":1000,"v":21.5}]}',
        headers={
            "Authorization": f"Bearer {write_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    assert r.status_code == 200
    assert count(conn, "points") == 1


def test_undeclared_channel_needs_numeric_value(client, conn, clock, write_token):
    r = push(
        client,
        write_token,
        channels=[],
        points=[{"channel": "mystery", "t": 1.0, "v": "on"}],
    )
    assert r.status_code == 400
    assert r.get_json() == {
        "error": "undeclared channel needs a numeric value; declare it in channels"
    }
    assert count(conn, "channels") == 0
    # null is fine: the channel is created as sampled.
    r = push(
        client,
        write_token,
        channels=[],
        points=[{"channel": "mystery", "t": 1.0, "v": None}],
    )
    assert r.status_code == 200
    kind = conn.execute("SELECT kind FROM channels WHERE name='mystery'").fetchone()
    assert kind[0] == "sampled"


def test_events_with_same_key_not_duplicated(client, conn, clock, write_token):
    ev = {"t": 5.0, "alarm": "HV", "action": "triggered", "message": None}
    push(client, write_token, events=[ev, ev])
    push(client, write_token, events=[ev])
    assert count(conn, "events") == 1
