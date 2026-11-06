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
        {"points": [{"channel": "temp", "t": float("nan"), "v": 1}]},
        {"points": [{"channel": "temp", "t": float("inf"), "v": 1}]},
        {"points": [{"channel": "temp", "t": 10**400, "v": 1}]},
        {"points": [{"channel": "temp", "t": 1.0, "v": [1]}]},
        {"points": [{"channel": "temp", "t": 1.0, "v": {"a": 1}}]},
        {"sent_at": 10**400},
        {"interval": 10**400},
        {"ticks": [10**400]},
        {"events": [{"t": 10**400, "alarm": "HV", "action": "triggered"}]},
        {
            "channels": [{"name": "ng", "kind": "state"}],
            "points": [{"channel": "ng", "t": 1.0, "v": True}],
        },
        {
            "channels": [{"name": "ng", "kind": "state"}],
            "points": [{"channel": "ng", "t": 1.0, "v": float("nan")}],
        },
        {
            "channels": [{"name": "ng", "kind": "state"}],
            "points": [{"channel": "ng", "t": 1.0, "v": 10**400}],
        },
        {"points": [{"t": 1.0, "v": 1}]},
        {"points": ["x"]},
        {"channels": [{"name": "c", "kind": "weird"}]},
        {"channels": "x"},
        {"interval": 0},
        {"interval": -1},
        {"interval": 86401},
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


def test_interval_up_to_a_day_is_accepted(client, conn, clock, write_token):
    assert push(client, write_token, interval=86400).status_code == 200
    assert conn.execute("SELECT interval FROM experiments").fetchone()[0] == 86400


@pytest.mark.parametrize("depth", [100_000, 2_000_000])
def test_deeply_nested_json_is_a_400_not_a_500(client, conn, clock, write_token, depth):
    raw = b"[" * depth + b"]" * depth
    r = push(client, write_token, raw=raw)
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_deep_nesting_inside_a_field_is_a_400(client, conn, clock, write_token):
    nested = '{"points": [{"channel": "temp", "t": 1.0, "v": ' + "[" * 500_000
    nested += "]" * 500_000 + "}]}"
    r = push(client, write_token, raw=nested.encode())
    assert r.status_code == 400
    assert count(conn, "points") == 0


def test_recursion_while_validating_is_a_400(
    client, conn, clock, write_token, monkeypatch
):
    def too_deep(body, now):
        raise RecursionError("maximum recursion depth exceeded")

    monkeypatch.setattr("hc_web.ingest._parse", too_deep)
    r = push(client, write_token)
    assert r.status_code == 400
    assert "nested" in r.get_json()["error"]


def test_an_oversized_body_gets_a_json_413(client, conn, clock, write_token):
    limit = client.application.config["MAX_CONTENT_LENGTH"]
    assert limit == 16 * 1024 * 1024
    r = push(client, write_token, raw=b" " * (limit + 1))
    assert r.status_code == 413
    assert r.is_json and "too large" in r.get_json()["error"]
    assert count(conn, "points") == 0


def test_a_body_at_the_limit_is_read(client, conn, clock, write_token):
    limit = client.application.config["MAX_CONTENT_LENGTH"]
    r = push(client, write_token, raw=b"[]" + b" " * (limit - 2))
    assert r.status_code == 400  # read, and then not an object
    assert "JSON object" in r.get_json()["error"]


def test_body_must_be_json_object(client, clock, write_token):
    assert push(client, write_token, raw=b"not json").status_code == 400
    assert push(client, write_token, raw=b"[1, 2]").status_code == 400
    assert push(client, write_token, raw=b"{}").status_code == 400  # no points


@pytest.mark.parametrize(
    "bad",
    ["warm", True, float("nan"), float("inf"), float("-inf"), 10**400],
    ids=["string", "bool", "nan", "inf", "-inf", "huge-int"],
)
def test_declared_sampled_channel_stores_non_numbers_as_null(
    client, conn, clock, write_token, bad
):
    """A bad reading never rejects the batch: it is stored as NULL."""
    r = push(
        client,
        write_token,
        points=[
            {"channel": "temp", "t": 1.0, "v": 20.0},
            {"channel": "temp", "t": 2.0, "v": bad},
            {"channel": "temp", "t": 3.0, "v": 22},
        ],
        ticks=[3.0],
    )
    assert r.status_code == 200
    rows = conn.execute("SELECT t, v FROM points ORDER BY t").fetchall()
    assert [tuple(r) for r in rows] == [(1.0, 20.0), (2.0, None), (3.0, 22.0)]


def test_stored_sampled_channel_also_nulls_non_numbers(
    client, conn, clock, write_token
):
    """The kind may come from an earlier push rather than this body."""
    push(client, write_token)
    r = push(
        client,
        write_token,
        channels=[],
        points=[{"channel": "temp", "t": 1.0, "v": float("nan")}],
    )
    assert r.status_code == 200
    assert conn.execute("SELECT v FROM points").fetchone()[0] is None


def test_large_numbers_do_not_overflow_sqlite(client, conn, clock, write_token):
    state = [{"name": "ng", "kind": "state"}]
    r = push(
        client,
        write_token,
        channels=state + [{"name": "temp", "kind": "sampled"}],
        points=[
            {"channel": "temp", "t": 1.0, "v": 2**64},
            {"channel": "ng", "t": 1.0, "v": 2**64},
            {"channel": "ng", "t": 2.0, "v": 5},
        ],
        ticks=[2.0],
    )
    assert r.status_code == 200
    temp = conn.execute(
        "SELECT v FROM points p JOIN channels c ON c.id = p.channel_id "
        "WHERE c.name = 'temp'"
    ).fetchone()[0]
    assert temp == float(2**64)
    ng = conn.execute(
        "SELECT t, v FROM points p JOIN channels c ON c.id = p.channel_id "
        "WHERE c.name = 'ng' ORDER BY t"
    ).fetchall()
    assert [tuple(r) for r in ng] == [(1.0, float(2**64)), (2.0, 5)]


def test_undeclared_channel_rejects_bad_numbers(client, conn, clock, write_token):
    for bad in (True, float("nan"), float("inf"), 10**400):
        r = push(
            client,
            write_token,
            channels=[],
            points=[{"channel": "mystery", "t": 1.0, "v": bad}],
        )
        assert r.status_code == 400
    assert count(conn, "channels") == 0


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


def test_clock_skew_jitter_does_not_flood_warnings(client, conn, clock, write_token):
    clock.now = 1000.0
    for i in range(5):
        skew = 60.0 + 0.1 * i
        r = push(
            client, write_token, sent_at=clock.now - skew, ticks=[clock.now - skew]
        )
        assert r.status_code == 200
        clock.now += 10
    assert count(conn, "warnings") == 1
    offset = conn.execute("SELECT clock_offset FROM experiments").fetchone()[0]
    assert offset == pytest.approx(60.4)


def test_clock_offset_cleared_when_clock_fixed(client, conn, clock, write_token):
    push(client, write_token, sent_at=940.0, ticks=[940.0])
    assert conn.execute("SELECT clock_offset FROM experiments").fetchone()[0] == 60.0
    clock.now = 1010.0
    push(client, write_token, sent_at=1009.0, ticks=[1009.0])
    assert conn.execute("SELECT clock_offset FROM experiments").fetchone()[0] is None


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


# -- liveness follows the server clock ---------------------------------------


def status_of(client, conn):
    """The ``B`` entry of /api/v1/status, read with a read token."""
    token = create_token(conn, "B", "viewer", scope="read")
    r = client.get("/api/v1/status", headers={"Authorization": f"Bearer {token}"})
    return r.get_json()["experiments"]["B"]


def test_publisher_clock_behind_stays_online(client, conn, clock, write_token):
    """Liveness is judged on when the server heard, not on the publisher's t."""
    clock.now = 1000.0
    r = push(client, write_token, sent_at=960.0, ticks=[960.0])  # 40 s behind
    assert r.status_code == 200
    info = status_of(client, conn)
    assert info["online"] is True
    assert info["last_seen"] == 1000.0
    assert info["timeout"] == 30.0
    clock.now = 1029.0
    assert status_of(client, conn)["online"] is True
    clock.now = 1031.0
    assert status_of(client, conn)["online"] is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"sent_at": 1000.0 + 3600.0},
        {"ticks": [1000.0, 1000.0 + 3600.0]},
        {"points": [{"channel": "temp", "t": 1000.0 + 3600.0, "v": 1.0}]},
        {"events": [{"t": 1000.0 + 3600.0, "alarm": "a", "action": "triggered"}]},
        {"sent_at": 1010.0 + 61.0, "interval": 10.0},
    ],
)
def test_future_dated_push_is_rejected_and_not_heard(
    client, conn, clock, write_token, overrides
):
    clock.now = 1000.0
    assert push(client, write_token, ticks=[1000.0]).status_code == 200
    clock.now = 1010.0
    r = push(client, write_token, **overrides)
    assert r.status_code == 400
    assert "ahead" in r.get_json()["error"]
    assert "clock" in r.get_json()["error"]
    assert count(conn, "points") == 0 and count(conn, "events") == 0
    assert conn.execute("SELECT last_heard FROM experiments").fetchone()[0] == 1000.0
    assert status_of(client, conn)["last_seen"] == 1000.0
    # the bad push neither pins the experiment live nor blocks another run
    clock.now = 1100.0
    assert status_of(client, conn)["online"] is False
    r = push(client, write_token, run="B", sent_at=1100.0, ticks=[1100.0])
    assert r.status_code == 200


def test_slightly_future_push_is_accepted(client, conn, clock, write_token):
    clock.now = 1000.0
    r = push(client, write_token, sent_at=1059.0, ticks=[1059.0])
    assert r.status_code == 200
    # a long interval widens the allowance: max(60, interval)
    r = push(client, write_token, interval=300.0, sent_at=1250.0, ticks=[1250.0])
    assert r.status_code == 200
    r = push(client, write_token, interval=300.0, sent_at=1301.0, ticks=[1301.0])
    assert r.status_code == 400


def test_last_heard_survives_an_offline_period_longer_than_retention(
    client, conn, clock, write_token
):
    from hc_web.retention import cleanup

    clock.now = 1000.0
    push(client, write_token, ticks=[1000.0])
    clock.now = 1000.0 + 30 * 86400.0
    cleanup(conn, clock.now, retention_days=7)
    assert count(conn, "coverage") == 0
    info = status_of(client, conn)
    assert info["online"] is False
    assert info["last_seen"] == 1000.0


def test_shutdown_marks_offline_at_once(client, conn, clock, write_token):
    clock.now = 1000.0
    push(client, write_token, ticks=[1000.0])
    assert status_of(client, conn)["online"] is True
    clock.now = 1001.0
    push(client, write_token, ticks=[1001.0], shutdown=True)
    info = status_of(client, conn)
    assert info["online"] is False
    assert info["last_seen"] == 1001.0


def test_rejected_run_does_not_count_as_heard(client, conn, clock, write_token):
    clock.now = 1000.0
    push(client, write_token, run="A", ticks=[1000.0])
    clock.now = 1010.0
    assert push(client, write_token, run="B", ticks=[1010.0]).status_code == 409
    assert conn.execute("SELECT last_heard FROM experiments").fetchone()[0] == 1000.0


def test_repeated_state_value_adds_no_row_while_covered(
    client, conn, clock, write_token
):
    """A publisher sends its state at every tick; the server keeps the changes."""
    state = [{"name": "ng", "kind": "state"}]
    for i, v in enumerate(["1", "1", "1", "0", "0"]):
        clock.now = 10.0 * (i + 1)
        r = push(
            client,
            write_token,
            channels=state,
            sent_at=clock.now,
            ticks=[clock.now],
            points=[{"channel": "ng", "t": clock.now, "v": v}],
        )
        assert r.status_code == 200
    rows = conn.execute("SELECT t, v FROM points ORDER BY t").fetchall()
    assert [tuple(r) for r in rows] == [(10.0, "1"), (40.0, "0")]
