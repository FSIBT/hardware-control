import json
import math

import pytest

pytest.importorskip("flask")

from hc_web import db  # noqa: E402
from hc_web.query import gaps  # noqa: E402
from hc_web.tokens import create_token, get_or_create_experiment  # noqa: E402


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
def exp(conn):
    """Experiment B: interval 10, run A current (and so live while recent)."""
    experiment_id = get_or_create_experiment(conn, "B")
    with conn:
        conn.execute(
            "UPDATE experiments SET interval = 10, current_run = 'A' WHERE id = ?",
            (experiment_id,),
        )
    return experiment_id


def add_coverage(conn, experiment_id, start, end, run="A"):
    with conn:
        conn.execute(
            "INSERT INTO coverage (experiment_id, run, start, end) VALUES (?, ?, ?, ?)",
            (experiment_id, run, start, end),
        )


def hear(conn, experiment_id, t):
    """The server last accepted a push of the experiment at (its clock) ``t``."""
    with conn:
        conn.execute(
            "UPDATE experiments SET last_heard = ? WHERE id = ?", (t, experiment_id)
        )


def add_channel(conn, experiment_id, name, kind, points=(), unit=None, label=None):
    with conn:
        cur = conn.execute(
            "INSERT INTO channels (experiment_id, name, kind, unit, label) "
            "VALUES (?, ?, ?, ?, ?)",
            (experiment_id, name, kind, unit, label),
        )
        conn.executemany(
            "INSERT INTO points (channel_id, t, v) VALUES (?, ?, ?)",
            [(cur.lastrowid, t, v) for t, v in points],
        )


def add_event(conn, experiment_id, t, alarm="HV", action="triggered", message=None):
    with conn:
        conn.execute(
            "INSERT INTO events (experiment_id, t, alarm, action, message) "
            "VALUES (?, ?, ?, ?, ?)",
            (experiment_id, t, alarm, action, message),
        )


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# gaps
# ---------------------------------------------------------------------------


def test_gaps_between_runs(conn, exp):
    add_coverage(conn, exp, 0, 100, run="A")
    add_coverage(conn, exp, 200, 300, run="B")
    with conn:
        conn.execute("UPDATE experiments SET current_run = 'B' WHERE id = ?", (exp,))
    hear(conn, exp, 300)
    assert gaps(conn, exp, since=0, until=305, now=305) == [(100, 200)]


def test_gap_open_when_offline(conn, exp):
    add_coverage(conn, exp, 0, 100)
    hear(conn, exp, 100)  # nothing for 400 s: more than the timeout of 30 s
    assert gaps(conn, exp, since=0, until=500, now=500) == [(100, None)]


def test_no_tail_gap_while_heard_even_if_the_coverage_lags(conn, exp):
    """A publisher clock 40 s behind: the coverage ends before now - timeout."""
    add_coverage(conn, exp, 0, 960)
    hear(conn, exp, 1000)
    assert gaps(conn, exp, since=0, until=1000, now=1000) == []


def test_gap_open_after_clean_shutdown(conn, exp):
    add_coverage(conn, exp, 0, 100)
    with conn:
        conn.execute("UPDATE experiments SET shutdown_run = 'A' WHERE id = ?", (exp,))
    assert gaps(conn, exp, since=0, until=105, now=105) == [(100, None)]


def test_gap_before_first_coverage(conn, exp):
    add_coverage(conn, exp, 0, 100)
    hear(conn, exp, 105)
    assert gaps(conn, exp, since=-50, until=105, now=105) == [(-50, 0)]


def test_gap_closed_when_window_ends_before_now(conn, exp):
    add_coverage(conn, exp, 0, 100)
    assert gaps(conn, exp, since=0, until=300, now=500) == [(100, 300)]


def test_no_coverage_is_one_gap(conn, exp):
    assert gaps(conn, exp, since=0, until=500, now=500) == [(0, None)]
    assert gaps(conn, exp, since=0, until=300, now=500) == [(0, 300)]


def test_gaps_merge_overlapping_coverage(conn, exp):
    add_coverage(conn, exp, 0, 100)
    add_coverage(conn, exp, 50, 150)
    add_coverage(conn, exp, 150, 160)
    assert gaps(conn, exp, since=0, until=160, now=165) == []


def test_gaps_clip_to_window(conn, exp):
    add_coverage(conn, exp, 0, 100)
    add_coverage(conn, exp, 200, 300)
    assert gaps(conn, exp, since=120, until=180, now=1000) == [(120, 180)]
    assert gaps(conn, exp, since=50, until=250, now=1000) == [(100, 200)]


def test_plain_complement_ignores_liveness(conn, exp):
    add_coverage(conn, exp, 0, 100)
    assert gaps(conn, exp, 0, 200, math.inf) == [(100, 200)]


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------


def test_data_before_for_state(client, conn, exp, clock):
    add_channel(conn, exp, "ng", "state", [(10.0, "1"), (50.0, "0")])
    token = create_token(conn, "B", "viewer", scope="read")
    r = client.get("/api/v1/data?channels=B/ng&since=30", headers=auth(token))
    assert r.status_code == 200
    ch = r.get_json()["channels"]["B/ng"]
    assert ch["before"] == [10.0, "1"]
    assert ch["points"] == [[50.0, "0"]]
    assert ch["kind"] == "state"


def test_data_sampled_has_no_before(client, conn, exp, clock):
    add_channel(
        conn,
        exp,
        "temp",
        "sampled",
        [(10.0, 1.5), (50.0, 2.5), (60.0, 3.5)],
        unit="C",
        label="T",
    )
    add_coverage(conn, exp, 0, 995)
    hear(conn, exp, 995)
    token = create_token(conn, "B", "viewer", scope="read")
    r = client.get(
        "/api/v1/data?channels=B/temp&since=20&until=55", headers=auth(token)
    )
    body = r.get_json()
    assert body["now"] == 1000.0
    assert body["channels"]["B/temp"] == {
        "kind": "sampled",
        "unit": "C",
        "label": "T",
        "before": None,
        "points": [[50.0, 2.5]],
    }
    info = body["experiments"]["B"]
    assert info["online"] is True
    assert info["last_seen"] == 995.0
    assert info["timeout"] == 30.0
    assert info["gaps"] == []
    assert info["latched"] == []


def test_data_experiment_gaps_and_latched(client, conn, exp, clock):
    add_channel(conn, exp, "temp", "sampled")
    add_coverage(conn, exp, 100, 200)
    with conn:
        conn.execute(
            "INSERT INTO latched (experiment_id, alarm) VALUES (?, 'HV')", (exp,)
        )
    token = create_token(conn, "B", "viewer", scope="read")
    r = client.get("/api/v1/data?channels=B/temp&since=50", headers=auth(token))
    info = r.get_json()["experiments"]["B"]
    assert info["online"] is False
    assert info["gaps"] == [[50.0, 100.0], [200.0, None]]
    assert info["latched"] == ["HV"]


def test_data_multiple_channels_two_experiments(client, conn, exp, clock):
    other = get_or_create_experiment(conn, "C")
    add_channel(conn, exp, "temp", "sampled", [(10.0, 1.0)])
    add_channel(conn, other, "temp", "sampled", [(10.0, 2.0)])
    token = create_token(conn, "B", "viewer", scope="read")
    r = client.get(
        "/api/v1/data?channels=B/temp,C/temp,B/temp&since=0", headers=auth(token)
    )
    body = r.get_json()
    assert list(body["channels"]) == ["B/temp", "C/temp"]
    assert set(body["experiments"]) == {"B", "C"}
    assert body["channels"]["C/temp"]["points"] == [[10.0, 2.0]]


def test_data_null_values_are_json_null(client, conn, exp, clock):
    add_channel(conn, exp, "temp", "sampled", [(10.0, None), (20.0, math.inf)])
    add_channel(conn, exp, "ng", "state", [(5.0, None), (50.0, None)])
    token = create_token(conn, "B", "viewer", scope="read")
    r = client.get("/api/v1/data?channels=B/temp,B/ng&since=30", headers=auth(token))
    text = r.get_data(as_text=True)
    for bad in ("NaN", "Infinity"):
        assert bad not in text
    body = json.loads(text, parse_constant=pytest.fail)
    assert body["channels"]["B/ng"]["before"] == [5.0, None]
    assert body["channels"]["B/ng"]["points"] == [[50.0, None]]
    r = client.get("/api/v1/data?channels=B/temp&since=0", headers=auth(token))
    body = json.loads(r.get_data(as_text=True), parse_constant=pytest.fail)
    assert body["channels"]["B/temp"]["points"] == [[10.0, None], [20.0, None]]


def test_data_points_beyond_now_included_without_until(client, conn, exp, clock):
    add_channel(conn, exp, "temp", "sampled", [(1010.0, 1.0)])
    token = create_token(conn, "B", "viewer", scope="read")
    r = client.get("/api/v1/data?channels=B/temp&since=0", headers=auth(token))
    assert r.get_json()["channels"]["B/temp"]["points"] == [[1010.0, 1.0]]


def test_data_unknown_channel_404(client, conn, exp, clock):
    add_channel(conn, exp, "temp", "sampled")
    token = create_token(conn, "B", "viewer", scope="read")
    for channels in ("B/x", "X/temp", "temp", "B/temp,B/x"):
        r = client.get(f"/api/v1/data?channels={channels}&since=0", headers=auth(token))
        assert r.status_code == 404
        assert "unknown channel" in r.get_json()["error"]
    r = client.get("/api/v1/data?channels=B/x&since=0", headers=auth(token))
    assert r.get_json() == {"error": "unknown channel B/x"}


@pytest.mark.parametrize(
    "query",
    [
        "",
        "since=0",
        "channels=&since=0",
        "channels=B/temp",
        "channels=B/temp&since=abc",
        "channels=B/temp&since=",
        "channels=B/temp&since=nan",
        "channels=B/temp&since=inf",
        "channels=B/temp&since=-inf",
        "channels=B/temp&since=1e999",
        "channels=B/temp&since=0&until=abc",
        "channels=B/temp&since=0&until=nan",
        "channels=B/temp&since=0&until=1e999",
        "channels=B/temp&since=10&until=5",
    ],
)
def test_data_bad_query_is_400(client, conn, exp, clock, query):
    add_channel(conn, exp, "temp", "sampled")
    token = create_token(conn, "B", "viewer", scope="read")
    r = client.get(f"/api/v1/data?{query}", headers=auth(token))
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_data_huge_finite_values_do_not_fail(client, conn, exp, clock):
    add_channel(conn, exp, "temp", "sampled", [(10.0, 1.0)])
    token = create_token(conn, "B", "viewer", scope="read")
    r = client.get(
        "/api/v1/data?channels=B/temp&since=-1e308&until=1e308", headers=auth(token)
    )
    assert r.status_code == 200
    assert r.get_json()["channels"]["B/temp"]["points"] == [[10.0, 1.0]]


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


def test_status_lists_channels_with_last(client, conn, exp, clock):
    add_channel(
        conn, exp, "temp", "sampled", [(10.0, 1.5), (20.0, 2.5)], unit="C", label="T"
    )
    add_channel(conn, exp, "ng", "state")
    add_coverage(conn, exp, 0, 990)
    hear(conn, exp, 990)
    with conn:
        conn.execute(
            "INSERT INTO latched (experiment_id, alarm) VALUES (?, 'HV')", (exp,)
        )
    get_or_create_experiment(conn, "Empty")
    token = create_token(conn, "B", "viewer", scope="read")
    r = client.get("/api/v1/status", headers=auth(token))
    assert r.status_code == 200
    body = r.get_json()
    assert body["now"] == 1000.0
    assert body["experiments"]["B"] == {
        "online": True,
        "last_seen": 990.0,
        "timeout": 30.0,
        "latched": ["HV"],
        "channels": [
            {"name": "ng", "kind": "state", "unit": None, "label": None, "last": None},
            {
                "name": "temp",
                "kind": "sampled",
                "unit": "C",
                "label": "T",
                "last": [20.0, 2.5],
            },
        ],
    }
    assert body["experiments"]["Empty"] == {
        "online": False,
        "last_seen": None,
        "timeout": 180.0,
        "latched": [],
        "channels": [],
    }


def test_status_last_null_value(client, conn, exp, clock):
    add_channel(conn, exp, "temp", "sampled", [(10.0, 1.5), (20.0, None)])
    token = create_token(conn, "B", "viewer", scope="read")
    r = client.get("/api/v1/status", headers=auth(token))
    ch = r.get_json()["experiments"]["B"]["channels"][0]
    assert ch["last"] == [20.0, None]


# ---------------------------------------------------------------------------
# events
# ---------------------------------------------------------------------------


def test_events_since_sorted(client, conn, exp, clock):
    other = get_or_create_experiment(conn, "C")
    add_event(conn, exp, 30.0, "HV", "triggered", "psu:V > 30000")
    add_event(conn, other, 10.0, "Door", "triggered", None)
    add_event(conn, exp, 20.0, "HV", "reset", None)
    add_event(conn, exp, 5.0, "Old", "triggered", None)
    token = create_token(conn, "B", "viewer", scope="read")
    r = client.get("/api/v1/events?since=10", headers=auth(token))
    assert r.status_code == 200
    body = r.get_json()
    assert body["now"] == 1000.0
    assert body["events"] == [
        {
            "experiment": "C",
            "t": 10.0,
            "alarm": "Door",
            "action": "triggered",
            "message": None,
        },
        {
            "experiment": "B",
            "t": 20.0,
            "alarm": "HV",
            "action": "reset",
            "message": None,
        },
        {
            "experiment": "B",
            "t": 30.0,
            "alarm": "HV",
            "action": "triggered",
            "message": "psu:V > 30000",
        },
    ]


def test_events_without_since_returns_all(client, conn, exp, clock):
    add_event(conn, exp, 5.0)
    token = create_token(conn, "B", "viewer", scope="read")
    r = client.get("/api/v1/events", headers=auth(token))
    assert [e["t"] for e in r.get_json()["events"]] == [5.0]


@pytest.mark.parametrize("since", ["abc", "nan", "inf", "1e999", ""])
def test_events_bad_since_is_400(client, conn, exp, clock, since):
    token = create_token(conn, "B", "viewer", scope="read")
    r = client.get(f"/api/v1/events?since={since}", headers=auth(token))
    assert r.status_code == 400
    assert "error" in r.get_json()


# ---------------------------------------------------------------------------
# authentication
# ---------------------------------------------------------------------------

URLS = [
    "/api/v1/data?channels=B/temp&since=0",
    "/api/v1/status",
    "/api/v1/events?since=0",
]


@pytest.mark.parametrize("url", URLS)
@pytest.mark.parametrize("scope", ["read", "write"])
def test_any_token_scope_can_read(client, conn, exp, clock, url, scope):
    add_channel(conn, exp, "temp", "sampled")
    token = create_token(conn, "B", "tok", scope=scope)
    assert client.get(url, headers=auth(token)).status_code == 200


@pytest.mark.parametrize("url", URLS)
def test_no_auth_is_401(client, conn, exp, clock, url):
    add_channel(conn, exp, "temp", "sampled")
    r = client.get(url)
    assert r.status_code == 401
    assert r.get_json() == {"error": "missing or invalid token"}
    assert r.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("url", URLS)
def test_bad_or_revoked_token_is_401(client, conn, exp, clock, url):
    from hc_web.tokens import revoke_token

    add_channel(conn, exp, "temp", "sampled")
    assert client.get(url, headers=auth("1.nonsense")).status_code == 401
    token = create_token(conn, "B", "tok", scope="read")
    revoke_token(conn, int(token.split(".")[0]))
    assert client.get(url, headers=auth(token)).status_code == 401


@pytest.mark.parametrize("url", URLS)
def test_session_user_can_read(client, conn, exp, clock, monkeypatch, url):
    add_channel(conn, exp, "temp", "sampled")
    monkeypatch.setattr("hc_web.auth.current_user", lambda: {"name": "arun"})
    assert client.get(url).status_code == 200
