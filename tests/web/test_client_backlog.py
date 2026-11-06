import socket
import time

import pytest

pytest.importorskip("flask")

from hardware_control.web import WebClient, WebClientConflict, WebClientError  # noqa: E402
from hardware_control.web.backlog import Backlog, Batch  # noqa: E402


def test_reexports_one_implementation():
    from hc_web import client

    assert WebClient is client.WebClient
    assert WebClientError is client.WebClientError
    assert WebClientConflict is client.WebClientConflict
    assert issubclass(WebClientConflict, WebClientError)


def test_client_push_and_data(live_server):
    url, write_token, read_token = live_server
    now = time.time()
    writer = WebClient(url + "/", write_token)  # trailing slash is stripped
    assert writer.push(
        {
            "run": "A",
            "interval": 10.0,
            "channels": [
                {"name": "temp", "kind": "sampled", "unit": "C", "label": None},
                {"name": "ng_on", "kind": "state", "unit": None, "label": "NG on"},
            ],
            "points": [
                {"channel": "temp", "t": now - 5, "v": 21.5},
                {"channel": "temp", "t": now - 4, "v": None},
                {"channel": "ng_on", "t": now - 5, "v": "1"},
            ],
            "ticks": [now - 5, now],
        }
    ) == {"ok": True}

    reader = WebClient(url, read_token)
    result = reader.data(["B/temp", "B/ng_on"], since=now - 60)
    assert result["channels"]["B/temp"]["points"] == [[now - 5, 21.5], [now - 4, None]]
    assert result["channels"]["B/ng_on"]["points"] == [[now - 5, "1"]]
    assert result["experiments"]["B"]["online"] is True
    assert reader.data(["B/temp"], since=now - 60, until=now - 4.5)["channels"][
        "B/temp"
    ]["points"] == [[now - 5, 21.5]]

    status = reader.status()
    assert {c["name"] for c in status["experiments"]["B"]["channels"]} == {
        "temp",
        "ng_on",
    }
    assert reader.events(0.0)["events"] == []
    writer.push(
        {
            "run": "A",
            "points": [],
            "events": [
                {"t": now, "alarm": "HV high", "action": "triggered", "message": "x"}
            ],
        }
    )
    assert [e["alarm"] for e in reader.events(now - 1)["events"]] == ["HV high"]


def test_client_send_minimal(live_server):
    url, write_token, read_token = live_server
    t = time.time()
    client = WebClient(url, write_token)
    assert client.send([("temp", t, 21.5), ("temp", t + 1, 22), ("hum", t, None)]) == {
        "ok": True
    }
    result = WebClient(url, read_token).data(["B/temp", "B/hum"], since=t - 1)
    assert result["channels"]["B/temp"]["kind"] == "sampled"
    assert result["channels"]["B/temp"]["points"] == [[t, 21.5], [t + 1, 22.0]]
    assert result["channels"]["B/hum"]["points"] == [[t, None]]
    assert result["experiments"]["B"]["online"] is True


def test_client_send_nan_is_unknown(live_server):
    url, write_token, read_token = live_server
    t = time.time()
    WebClient(url, write_token).send([("temp", t, 1.0), ("temp", t + 1, float("nan"))])
    points = WebClient(url, read_token).data(["B/temp"], since=t - 1)["channels"][
        "B/temp"
    ]["points"]
    assert points == [[t, 1.0], [t + 1, None]]


def test_client_errors(live_server):
    url, write_token, read_token = live_server

    with socket.socket() as s:  # a port nobody listens on
        s.bind(("127.0.0.1", 0))
        dead = f"http://127.0.0.1:{s.getsockname()[1]}"
    with pytest.raises(WebClientError) as info:
        WebClient(dead, write_token, timeout=2).status()
    assert info.value.status is None
    assert not isinstance(info.value, WebClientConflict)

    bad = WebClient(url, "1.nottherightsecret")
    with pytest.raises(WebClientError, match="invalid token") as info:
        bad.status()
    assert info.value.status == 401
    assert "nottherightsecret" not in str(info.value)

    with pytest.raises(WebClientError) as info:
        WebClient(url, read_token).send([("temp", 1.0, 1.0)])
    assert info.value.status == 403

    with pytest.raises(WebClientError, match="points is required") as info:
        WebClient(url, write_token).push({})
    assert info.value.status == 400

    with pytest.raises(WebClientError, match="unknown channel B/nope") as info:
        WebClient(url, read_token).data(["B/nope"], since=0)
    assert info.value.status == 404

    now = time.time()
    writer = WebClient(url, write_token)
    writer.push({"run": "A", "points": [], "ticks": [now]})
    with pytest.raises(WebClientConflict, match="another run is active") as info:
        writer.push({"run": "B", "points": [], "ticks": [now]})
    assert info.value.status == 409


def test_client_timeout_has_no_status():
    import threading

    with socket.socket() as listener:  # accepts, never answers
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        done = threading.Event()

        def hold():
            conn, _ = listener.accept()
            done.wait(5)
            conn.close()

        thread = threading.Thread(target=hold, daemon=True)
        thread.start()
        client = WebClient(f"http://127.0.0.1:{listener.getsockname()[1]}", "1.x", 0.3)
        with pytest.raises(WebClientError) as info:
            client.status()
        done.set()
        thread.join()
    assert info.value.status is None


def test_client_validation_and_no_token_leak():
    with pytest.raises(ValueError):
        WebClient("ftp://example.org", "1.secret")
    with pytest.raises(ValueError):
        WebClient("example.org", "1.secret")
    with pytest.raises(ValueError) as info:
        WebClient("http://example.org", "1.sec\nret")
    assert "sec" not in str(info.value)
    client = WebClient("http://example.org/", "1.verysecret")
    assert client.url == "http://example.org"
    assert "verysecret" not in repr(client)
    assert "verysecret" not in str(client)


def test_client_verify_tls(monkeypatch):
    import ssl

    assert WebClient("https://example.org", "1.x")._context.verify_mode == (
        ssl.CERT_REQUIRED
    )
    unverified = WebClient("https://example.org", "1.x", verify_tls=False)._context
    assert unverified.verify_mode == ssl.CERT_NONE
    assert unverified.check_hostname is False
    assert WebClient("http://example.org", "1.x", verify_tls=False)._context is None


# ---------------------------------------------------------------------------
# Backlog
# ---------------------------------------------------------------------------


def point(channel, t, v):
    return {"channel": channel, "t": t, "v": v}


def event(t, alarm="HV high"):
    return {"t": t, "alarm": alarm, "action": "triggered", "message": None}


@pytest.fixture
def backlog(tmp_path):
    b = Backlog(tmp_path / "backlog.sqlite")
    yield b
    b.close()


def test_backlog_order_and_remove(backlog):
    backlog.add([point("a", 3.0, "1"), point("a", 1.0, 2.5)], [4.0, 2.0], [event(5.0)])
    backlog.add([point("b", 6.0, None)], [], [event(0.5)])
    assert backlog.count() == 7

    batch = backlog.take()
    assert isinstance(batch, Batch)
    assert batch.points == [
        point("a", 1.0, 2.5),
        point("a", 3.0, "1"),
        point("b", 6.0, None),
    ]
    assert batch.ticks == [2.0, 4.0]
    assert batch.events == [event(0.5), event(5.0)]
    assert len(batch.point_ids) == 3
    assert len(batch.tick_ids) == 2
    assert len(batch.event_ids) == 2

    # the limit applies across the tables, in t order
    small = backlog.take(limit=4)
    assert small.events == [event(0.5)]
    assert small.points == [point("a", 1.0, 2.5), point("a", 3.0, "1")]
    assert small.ticks == [2.0]

    backlog.remove(small)
    assert backlog.count() == 3
    rest = backlog.take()
    assert rest.points == [point("b", 6.0, None)]
    assert rest.ticks == [4.0]
    assert rest.events == [event(5.0)]
    backlog.remove(rest)
    assert backlog.count() == 0
    empty = backlog.take()
    assert (empty.points, empty.ticks, empty.events) == ([], [], [])


def test_backlog_survives_reopen(tmp_path):
    path = tmp_path / "backlog.sqlite"
    first = Backlog(path)
    first.add([point("a", 1.0, 1.5)], [1.0], [event(1.0)])
    first.close()
    second = Backlog(path)
    try:
        assert second.count() == 3
        batch = second.take()
        assert batch.points == [point("a", 1.0, 1.5)]
        assert batch.events == [event(1.0)]
    finally:
        second.close()


def test_backlog_prune(tmp_path):
    b = Backlog(tmp_path / "backlog.sqlite", max_age=100.0)
    try:
        b.add(
            [point("a", 800.0, 1.0), point("a", 950.0, 2.0)],
            [800.0, 950.0],
            [event(800.0), event(950.0)],
        )
        assert b.prune(now=1000.0) == 3  # t < 900 goes
        assert b.count() == 3
        assert b.take().points == [point("a", 950.0, 2.0)]
        assert b.prune(now=1000.0) == 0
    finally:
        b.close()
