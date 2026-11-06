import contextlib
import math
import socket
import threading
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


@contextlib.contextmanager
def raw_server(reply: bytes):
    """A listener that answers the first request with the bytes ``reply``."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)

        def serve():
            conn, _ = listener.accept()
            with conn:
                conn.settimeout(2)
                with contextlib.suppress(OSError):
                    conn.recv(65536)
                    conn.sendall(reply)

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        yield f"http://127.0.0.1:{listener.getsockname()[1]}"
        thread.join()


def http_reply(status: str, body: bytes, length=None, **headers) -> bytes:
    headers = {
        "Content-Length": str(len(body) if length is None else length),
        "Connection": "close",
        **headers,
    }
    head = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
    return f"HTTP/1.1 {status}\r\n{head}\r\n".encode() + body


def test_client_garbage_reply_is_a_client_error():
    with raw_server(b"hello world, this is not http\r\n\r\n") as url:
        with pytest.raises(WebClientError) as info:
            WebClient(url, "1.x", 2).status()
    assert info.value.status is None
    assert "hello world" not in str(info.value)


def test_client_truncated_reply_is_a_client_error():
    reply = http_reply("200 OK", b"abcd", length=100)
    with raw_server(reply) as url:
        with pytest.raises(WebClientError) as info:
            WebClient(url, "1.x", 2).status()
    assert info.value.status is None


def test_client_redirect_is_not_followed():
    reply = http_reply("302 Found", b"", Location="http://127.0.0.1:1/elsewhere")
    with raw_server(reply) as url:
        with pytest.raises(WebClientError) as info:
            WebClient(url, "1.secret", 2).status()
    assert info.value.status == 302
    assert "secret" not in str(info.value)


def test_client_html_error_from_a_proxy():
    reply = http_reply("502 Bad Gateway", b"<html><body>Bad gateway</body></html>")
    with raw_server(reply) as url:
        with pytest.raises(WebClientError) as info:
            WebClient(url, "1.x", 2).status()
    assert info.value.status == 502
    assert "<html>" not in str(info.value)


def test_client_success_without_json():
    with raw_server(http_reply("200 OK", b"<html>captive portal</html>")) as url:
        with pytest.raises(WebClientError, match="not JSON") as info:
            WebClient(url, "1.x", 2).status()
    assert info.value.status == 200


def test_client_success_with_json_that_is_not_an_object():
    with raw_server(http_reply("200 OK", b"[1, 2]")) as url:
        with pytest.raises(WebClientError, match="not a JSON object") as info:
            WebClient(url, "1.x", 2).status()
    assert info.value.status == 200


def test_client_rejects_bad_token_and_userinfo():
    with pytest.raises(ValueError) as info:
        WebClient("http://example.org", "1.s\u00e9cret")
    assert "cret" not in str(info.value)
    with pytest.raises(ValueError) as info:
        WebClient("http://alice:hunter2@example.org", "1.x")
    assert "hunter2" not in str(info.value)
    assert "alice" not in str(info.value)
    with pytest.raises(ValueError):
        WebClient("http://alice@example.org", "1.x")


def test_client_events_query_is_encoded():
    reply = http_reply("200 OK", b'{"now": 1.0, "events": []}')
    with raw_server(reply) as url:
        assert WebClient(url, "1.x", 2).events(12.5) == {"now": 1.0, "events": []}


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


class _FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b'{"ok": true}'


class _FakeOpener:
    def __init__(self, error=None):
        self.error = error
        self.calls = 0

    def open(self, request, timeout=None):
        import urllib.error

        self.calls += 1
        if self.error:
            raise urllib.error.URLError(self.error)
        return _FakeResponse()


def _cert_error():
    import ssl

    return ssl.SSLCertVerificationError(1, "unable to get local issuer certificate")


def test_client_falls_back_to_certifi_on_cert_failure():
    pytest.importorskip("certifi")
    client = WebClient("https://example.org", "1.x")
    client._opener = _FakeOpener(_cert_error())
    good = _FakeOpener()
    client._build_opener = lambda context: good
    assert client._request("/x") == {"ok": True}
    assert good.calls == 1
    assert client._ca_fallback is False
    assert client._context.cert_store_stats()["x509_ca"] > 0
    assert client._context.verify_mode.name == "CERT_REQUIRED"


def test_client_cert_failure_without_certifi(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "certifi", None)  # ImportError
    client = WebClient("https://example.org", "1.x")
    opener = _FakeOpener(_cert_error())
    client._opener = opener
    for _ in range(2):  # the fallback is tried once, then the plain error
        with pytest.raises(WebClientError) as info:
            client._request("/x")
        assert "certificate verification failed" in str(info.value)
        assert "SSL_CERT_FILE" in str(info.value)
    assert opener.calls == 2


def test_client_cert_failure_still_failing_after_certifi():
    pytest.importorskip("certifi")
    client = WebClient("https://example.org", "1.x")
    client._opener = _FakeOpener(_cert_error())
    still_bad = _FakeOpener(_cert_error())
    client._build_opener = lambda context: still_bad
    with pytest.raises(WebClientError, match="certificate verification failed"):
        client._request("/x")
    assert still_bad.calls == 1  # one retry, no loop


def test_client_no_certifi_fallback_when_unverified_or_http():
    assert (
        WebClient("https://example.org", "1.x", verify_tls=False)._ca_fallback is False
    )
    assert WebClient("http://example.org", "1.x")._ca_fallback is False


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


def test_backlog_nan_value_becomes_unknown(backlog):
    backlog.add(
        [
            point("a", 1.0, math.nan),
            point("a", 2.0, math.inf),
            point("a", 3.0, -math.inf),
            point("a", 4.0, 1.5),
        ],
        [],
        [],
    )
    assert [p["v"] for p in backlog.take().points] == [None, None, None, 1.5]


def test_backlog_prune_boundary(tmp_path):
    b = Backlog(tmp_path / "backlog.sqlite", max_age=100.0)
    try:
        b.add([point("a", 900.0, 1.0)], [900.0], [event(900.0)])  # t == now - max_age
        assert b.prune(now=1000.0) == 0
        assert b.count() == 3
        assert b.prune(now=1000.5) == 3
    finally:
        b.close()
