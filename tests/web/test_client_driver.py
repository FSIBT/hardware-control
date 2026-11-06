"""Tests for ChannelHistory and the HCWebServer pull driver against a real server."""

import importlib
import logging
import math
import os
import threading
import time

import pytest

from hardware_control.instruments import HCWebServer
from hardware_control.web import ChannelHistory, WebClient

CHANNELS = [
    {"name": "hv", "kind": "sampled", "unit": "V", "label": "HV"},
    {"name": "ng_on", "kind": "state", "unit": None, "label": "NG on"},
]


class Clock:
    now = 1000.0


@pytest.fixture
def clock(monkeypatch):
    """Move the clock of the server (``time.time`` is patched for everybody)."""
    c = Clock()
    c.now = time.time()
    monkeypatch.setattr("hc_web.api.time.time", lambda: c.now)
    return c


class Publisher:
    """Pushes straight to the server with a write token, like a WebPublisher would."""

    def __init__(self, url, token, run="A", interval=10.0):
        self.web = WebClient(url, token)
        self.run = run
        self.interval = interval

    def push(self, points=(), now=None, ticks=None, shutdown=False):
        """``points`` are ``(channel name, t, value)``; every point is a heartbeat."""
        now = time.time() if now is None else now
        if ticks is None:
            ticks = sorted({t for _name, t, _v in points} or {now})
        self.web.push(
            {
                "run": self.run,
                "sent_at": now,
                "interval": self.interval,
                "channels": CHANNELS,
                "points": [{"channel": n, "t": t, "v": v} for n, t, v in points],
                "ticks": ticks,
                "shutdown": shutdown,
            }
        )


def server_points(read_token_url, channel):
    """All points of a channel on the server."""
    url, token = read_token_url
    return WebClient(url, token).data([channel], since=0)["channels"][channel]["points"]


@pytest.fixture
def make_driver(tmp_path):
    """Create drivers (poll interval one hour); close them at the end."""
    drivers = []

    def make(url, token, channels=("B/hv", "B/ng_on"), **kwargs):
        kwargs.setdefault("history_file", tmp_path / "history.sqlite")
        kwargs.setdefault("poll_interval", 3600)
        driver = HCWebServer("web", url, token, list(channels), **kwargs)
        drivers.append(driver)
        return driver

    yield make
    for driver in drivers:
        driver.close()


def record_since(driver, monkeypatch):
    """The ``(channels, since)`` of every ``data`` request of the driver."""
    calls = []
    original = driver._client.data

    def spy(channels, since, until=None):
        calls.append((list(channels), since))
        return original(channels, since, until)

    monkeypatch.setattr(driver._client, "data", spy)
    return calls


# -- ChannelHistory ----------------------------------------------------------


def test_history_points_gaps_and_dedupe(tmp_path):
    history = ChannelHistory(tmp_path / "h.sqlite")
    history.add_points("B/hv", [(1.0, 1.5), (2.0, None), (3.0, 3.5)])
    history.add_points("B/hv", [(3.0, 99.0), (4.0, 4.5)])  # 3.0 is kept as it was
    history.add_points("B/ng_on", [(2.0, "1")])
    assert history.points("B/hv") == [(1.0, 1.5), (2.0, None), (3.0, 3.5), (4.0, 4.5)]
    assert history.points("B/hv", start=2.0, end=3.0) == [(2.0, None), (3.0, 3.5)]
    assert history.points("B/ng_on") == [(2.0, "1")]
    assert history.last_time("B/hv") == 4.0
    assert history.last_time("B/none") is None
    assert history.last_point("B/hv") == (4.0, 4.5)
    assert history.last_point("B/none") is None
    history.close()


def test_history_nan_value_is_stored_as_unknown(tmp_path):
    history = ChannelHistory(tmp_path / "h.sqlite")
    history.add_points("B/hv", [(1.0, math.nan), (2.0, math.inf)])
    assert history.points("B/hv") == [(1.0, None), (2.0, None)]
    history.close()


def test_history_replace_gaps(tmp_path):
    history = ChannelHistory(tmp_path / "h.sqlite")
    history.replace_gaps("B", 0, 100, [(10, 20), (50, None)])
    assert history.gaps("B") == [(10, 20), (50, None)]
    assert history.open_gap_start("B") == 50
    assert history.open_gap_start("C") is None

    # a gap of another experiment is not touched; the new list replaces the old
    history.replace_gaps("C", 0, 100, [(1, 2)])
    history.replace_gaps("B", 40, 200, [(50, 60)])
    assert history.gaps("B") == [(10, 20), (50, 60)]
    assert history.open_gap_start("B") is None
    assert history.gaps("C") == [(1, 2)]

    # nothing overlaps: nothing is deleted
    history.replace_gaps("B", 70, 80, [])
    assert history.gaps("B") == [(10, 20), (50, 60)]
    assert history.gaps("B", start=15, end=40) == [(10, 20)]
    assert history.gaps("B", start=25, end=40) == []
    history.close()


def test_history_replace_gaps_keeps_the_start_of_a_straddling_gap(tmp_path):
    """A gap that began before ``since`` is shortened, not forgotten."""
    history = ChannelHistory(tmp_path / "h.sqlite")
    history.replace_gaps("B", 0, 100, [(10, 60)])
    history.replace_gaps("B", 30, 100, [(30, 50)])
    assert history.gaps("B") == [(10, 50)]
    history.replace_gaps("B", 30, 100, [])  # now covered after 30
    assert history.gaps("B") == [(10, 30)]
    history.close()


def test_history_replace_gaps_is_atomic(tmp_path):
    history = ChannelHistory(tmp_path / "h.sqlite")
    history.replace_gaps("B", 0, 100, [(10, 20)])
    with pytest.raises(Exception):
        history.replace_gaps("B", 0, 100, [(30, 40), ("bad",)])
    assert history.gaps("B") == [(10, 20)]
    history.close()


def test_history_is_lazy_and_reopens(tmp_path):
    path = tmp_path / "sub" / "dir" / "h.sqlite"
    history = ChannelHistory(path)
    assert not path.parent.exists()  # building one touches no disk
    history.add_points("B/hv", [(1.0, 1.0)])
    assert path.exists()
    history.close()
    history.close()  # twice is fine
    assert history.points("B/hv") == [(1.0, 1.0)]  # it opens again
    history.close()


def test_history_survives_use_from_two_threads(tmp_path):
    history = ChannelHistory(tmp_path / "h.sqlite")
    errors = []

    def writer():
        try:
            for i in range(200):
                history.add_points("B/hv", [(float(i), float(i))])
                history.replace_gaps("B", float(i), float(i) + 1, [(float(i), None)])
        except Exception as e:  # pragma: no cover - reported below
            errors.append(e)

    thread = threading.Thread(target=writer)
    thread.start()
    try:
        while thread.is_alive():
            history.points("B/hv")
            history.last_time("B/hv")
            history.open_gap_start("B")
            history.to_pandas("B/hv")
    finally:
        thread.join()
    assert errors == []
    assert len(history.points("B/hv")) == 200
    history.close()


def test_to_pandas_breaks_at_gaps(tmp_path):
    history = ChannelHistory(tmp_path / "h.sqlite")
    history.add_points("B/hv", [(1.0, 1.5), (2.0, 2.5), (10.0, 3.5), (11.0, 4.5)])
    history.replace_gaps("B", 0, 20, [(2.0, 10.0), (11.0, None)])
    frame = history.to_pandas("B/hv")
    assert list(frame.columns) == ["time", "value"]
    assert list(frame["time"]) == [1.0, 2.0, 2.0, 10.0, 11.0, 11.0]
    values = list(frame["value"])
    assert values[:2] == [1.5, 2.5]
    assert math.isnan(values[2])  # the line breaks at the start of the gap
    assert values[3:5] == [3.5, 4.5]
    assert math.isnan(values[5])
    assert frame["value"].dtype.kind == "f"

    # only what is in the range; a gap that started before it adds no row
    part = history.to_pandas("B/hv", start=3.0, end=10.5)
    assert list(part["time"]) == [10.0]

    # text stays text, an empty channel is an empty frame
    history.add_points("B/ng_on", [(1.0, "on"), (5.0, "off")])
    states = history.to_pandas("B/ng_on")
    assert list(states["time"]) == [1.0, 2.0, 5.0, 11.0]  # the gaps of B
    assert states["value"][0] == "on" and states["value"][2] == "off"
    assert states["value"].isna().tolist() == [False, True, False, True]
    assert history.to_pandas("B/none").empty
    assert list(history.to_pandas("B/none").columns) == ["time", "value"]
    history.close()


# -- HCWebServer: construction -----------------------------------------------


def make_plain(channels, tmp_path, **kwargs):
    return HCWebServer(
        "web",
        "http://127.0.0.1:1",
        "token",
        channels,
        history_file=tmp_path / "h.sqlite",
        **kwargs,
    )


def test_channel_names_become_parameters(tmp_path):
    driver = make_plain(["B/ng_on", "B/hv", "C/temp.1"], tmp_path)
    reads, sets, commands = driver.list_parameters()
    assert sorted(reads) == sorted(
        ["B_ng_on", "B_hv", "C_temp.1", "B_online", "C_online", "ONLINE"]
    )
    assert sets == []
    assert commands == ["refresh"]
    assert driver["B_hv"] == "nan"  # nothing was polled yet
    assert driver["B_online"] == "nan"

    driver = make_plain({"hv": "B/hv", "hv_again": "B/hv", "t": "C/temp"}, tmp_path)
    reads = driver.list_parameters()[0]
    assert sorted(reads) == sorted(
        ["hv", "hv_again", "t", "B_online", "C_online", "ONLINE"]
    )


@pytest.mark.parametrize(
    "channels, message",
    [
        (["A/b_c", "A_b/c"], "A_b_c"),  # both become A_b_c
        (["A/b", "A/b"], "A_b"),
        (["B/online"], "B_online"),  # the online parameter of experiment B
        ({"B_online": "B/hv"}, "B_online"),
        ({"ONLINE": "B/hv"}, "ONLINE"),
        ({"has space": "B/hv"}, "has space"),
        (["hv"], "experiment/channel"),
        (["B/"], "experiment/channel"),
        (["a/b/c"], "experiment/channel"),
        (["B/h v"], "experiment/channel"),
        ([3], "experiment/channel"),
        ([], "no channels"),
        ({}, "no channels"),
    ],
)
def test_bad_channels_are_rejected(channels, message, tmp_path):
    with pytest.raises(ValueError, match=message):
        make_plain(channels, tmp_path)


def test_a_string_is_not_a_list_of_channels(tmp_path):
    with pytest.raises(TypeError):
        make_plain("B/hv", tmp_path)


def test_bad_url_and_numbers_are_rejected(tmp_path):
    with pytest.raises(ValueError):
        HCWebServer("web", "ftp://x", "token", ["B/hv"], history_file=tmp_path / "h")
    with pytest.raises(ValueError, match="poll_interval"):
        make_plain(["B/hv"], tmp_path, poll_interval=0)
    with pytest.raises(ValueError, match="backfill_hours"):
        make_plain(["B/hv"], tmp_path, backfill_hours=0)


def test_default_history_file(tmp_path, monkeypatch):
    module = importlib.import_module("hardware_control.instruments.hc_web.HCWebServer")
    monkeypatch.setattr(module, "user_data_dir", lambda *args: str(tmp_path))
    driver = HCWebServer("my web/1", "http://127.0.0.1:1", "token", ["B/hv"])
    path = driver.history.path
    assert path.parent == tmp_path / "web_history"
    assert path.suffix == ".sqlite"
    assert "/" not in path.name
    assert not path.parent.exists()  # created when it is first used
    driver.history.last_time("B/hv")
    assert path.exists()
    plain = HCWebServer("web", "http://127.0.0.1:1", "token", ["B/hv"])
    assert plain.history.path == tmp_path / "web_history" / "web.sqlite"
    driver.close()


def test_token_is_not_in_repr(tmp_path):
    driver = make_plain(["B/hv"], tmp_path)
    assert "token" not in repr(driver._client).replace("token=<hidden>", "")


# -- HCWebServer: polling ----------------------------------------------------


def test_backfill_on_first_start(live_server, make_driver):
    url, write, read = live_server
    now = time.time()
    Publisher(url, write).push(
        [
            ("hv", now - 7200, 1.0),
            ("hv", now - 3000, 2.0),
            ("hv", now - 100, 3.0),
            ("hv", now - 10, 4.0),
        ],
        now=now,
    )
    driver = make_driver(url, read, ["B/hv"], backfill_hours=1)
    assert driver.poll(force=True)
    assert driver.history.points("B/hv") == [
        (now - 3000, 2.0),
        (now - 100, 3.0),
        (now - 10, 4.0),
    ]
    assert driver["B_hv"] == "4.0"
    assert driver["B_online"] == "True"


def test_restart_and_overlap_no_duplicates(live_server, make_driver, monkeypatch):
    url, write, read = live_server
    pub = Publisher(url, write)
    now = time.time()
    pub.push([("hv", now - 100 + i, float(i)) for i in range(0, 60, 10)], now=now)
    first = make_driver(url, read, ["B/hv"], backfill_hours=1)
    assert first.poll(force=True)
    first.close()

    # a new driver (a restart) on the same file, then more data
    second = make_driver(url, read, ["B/hv"], backfill_hours=1)
    calls = record_since(second, monkeypatch)
    pub.push([("hv", now - 30 + i, 100.0 + i) for i in range(0, 20, 10)], now=now)
    assert second.poll(force=True)
    assert second.poll(force=True)
    assert second.poll(force=True)

    last_before = now - 100 + 50
    # it asks from the last point it has, minus 60 s, not from the backfill window
    assert calls[0] == (["B/hv"], pytest.approx(last_before - 60))
    expected = server_points((url, read), "B/hv")
    assert len(expected) == 8
    assert [list(p) for p in second.history.points("B/hv")] == expected


def test_filled_gap_replaced(live_server, clock, make_driver):
    url, write, read = live_server
    pub = Publisher(url, write)
    t0 = clock.now
    pub.push([("hv", t0 - 10, 1.0), ("hv", t0, 2.0)], now=t0)
    clock.now = t0 + 100  # past the timeout of 30 s: offline
    driver = make_driver(url, read, ["B/hv"], backfill_hours=1)
    assert driver.poll(force=True)
    assert driver.history.open_gap_start("B") == pytest.approx(t0)
    assert driver["B_online"] == "False"

    # the publisher comes back with its backlog, which covers the gap
    backlog = [("hv", t0 + i, float(i)) for i in range(10, 101, 10)]
    pub.push(backlog, now=t0 + 100)
    assert driver.poll(force=True)
    assert driver.history.open_gap_start("B") is None
    # what is left is the time before the first data, as on the server
    assert [g for g in driver.history.gaps("B") if g[1] is None or g[1] > t0 - 10] == []
    assert len(driver.history.points("B/hv")) == 12
    assert driver["B_online"] == "True"
    assert driver["B_hv"] == "100.0"


def test_open_gap_start_does_not_creep(live_server, clock, make_driver):
    """Polling an experiment that stays offline keeps the start of its gap."""
    url, write, read = live_server
    Publisher(url, write).push([("hv", clock.now, 1.0)], now=clock.now)
    t0 = clock.now
    clock.now = t0 + 100
    driver = make_driver(url, read, ["B/hv"])
    for _ in range(3):
        assert driver.poll(force=True)
    assert driver.history.open_gap_start("B") == pytest.approx(t0)
    assert len([g for g in driver.history.gaps("B") if g[1] is None]) == 1


def test_current_value_and_offline_nan(live_server, clock, make_driver):
    url, write, read = live_server
    pub = Publisher(url, write)
    t0 = clock.now
    pub.push([("hv", t0, 3.5), ("ng_on", t0, "1")], now=t0)
    driver = make_driver(url, read)
    assert driver.poll(force=True)
    assert driver["B_hv"] == "3.5"
    assert driver["B_ng_on"] == "1"
    assert driver["B_online"] == "True"

    # the publisher dies without a shutdown; the server waits for 3 intervals
    clock.now = t0 + 100
    assert driver.poll(force=True)
    assert driver["B_hv"] == "nan"
    assert driver["B_ng_on"] == "nan"
    assert driver["B_online"] == "False"

    pub.push([("hv", t0 + 100, 4.0)], now=t0 + 100)
    assert driver.poll(force=True)
    assert driver["B_hv"] == "4.0"
    assert driver["B_ng_on"] == "1"
    assert driver["B_online"] == "True"


def test_state_value_before_the_window_seeds_the_current_value(
    live_server, make_driver, monkeypatch
):
    url, write, read = live_server
    now = time.time()
    pub = Publisher(url, write)
    # the state changed 2 h ago and not since; the sampled channel keeps going
    pub.push([("ng_on", now - 7200, "1")], now=now - 7200)
    pub.push([("hv", now - 20, 1.0), ("hv", now - 10, 2.0)], now=now - 10)
    driver = make_driver(url, read, backfill_hours=1)
    assert driver.poll(force=True)
    assert driver["B_ng_on"] == "1"
    assert driver.history.points("B/ng_on") == [(pytest.approx(now - 7200), "1")]

    # the old state point does not drag the requests two hours back
    calls = record_since(driver, monkeypatch)
    pub.push([("hv", now, 3.0)], now=now)
    assert driver.poll(force=True)
    assert calls[0][1] > now - 200
    assert driver["B_ng_on"] == "1"
    assert driver["B_hv"] == "3.0"


def test_null_value_is_nan(live_server, make_driver):
    url, write, read = live_server
    now = time.time()
    pub = Publisher(url, write)
    pub.push([("hv", now - 10, 1.0), ("hv", now, None)], now=now)
    driver = make_driver(url, read, ["B/hv"])
    assert driver.poll(force=True)
    assert driver["B_hv"] == "nan"
    assert driver["B_online"] == "True"
    assert driver.history.points("B/hv")[-1] == (pytest.approx(now), None)


def test_unreachable_server_makes_values_nan(restartable_server, make_driver, caplog):
    server, write, read = restartable_server
    now = time.time()
    Publisher(server.url, write).push([("hv", now, 2.5)], now=now)
    driver = make_driver(server.url, read, ["B/hv"])
    assert driver.poll(force=True)
    assert driver["B_hv"] == "2.5"

    server.stop()
    with caplog.at_level(logging.DEBUG):
        assert driver.poll(force=True) is False
    assert driver["B_hv"] == "nan"
    assert driver["B_online"] == "nan"
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("cannot reach" in r.getMessage() for r in warnings)
    assert read not in caplog.text and write not in caplog.text
    assert driver.history.points("B/hv")  # what we have stays

    server.start()
    assert driver.poll(force=True) is True
    assert driver["B_hv"] == "2.5"
    assert driver["B_online"] == "True"


def test_poll_never_raises(live_server, make_driver, monkeypatch, caplog):
    url, _write, read = live_server
    driver = make_driver(url, read, ["B/hv"])

    def boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(driver._client, "status", boom)
    with caplog.at_level(logging.WARNING):
        assert driver.poll(force=True) is False
        assert driver.check_connection() is True  # still not offline
    assert "boom" in caplog.text
    assert driver["B_hv"] == "nan"


def test_http_errors_are_not_fatal(live_server, make_driver, caplog):
    url, _write, _read = live_server
    driver = make_driver(url, "not-a-valid-token", ["B/hv"])
    with caplog.at_level(logging.WARNING):
        assert driver.poll(force=True) is False
    assert "401" in caplog.text
    assert "not-a-valid-token" not in caplog.text


def test_poll_waits_for_the_interval(live_server, make_driver, monkeypatch):
    url, write, read = live_server
    now = time.time()
    pub = Publisher(url, write)
    pub.push([("hv", now - 10, 1.0)], now=now)
    driver = make_driver(url, read, ["B/hv"], poll_interval=3600)
    calls = record_since(driver, monkeypatch)
    assert driver.poll() is True  # the first poll is immediate
    assert len(calls) == 1
    pub.push([("hv", now, 2.0)], now=now)
    assert driver.poll() is True  # too early: nothing is fetched
    assert len(calls) == 1
    assert driver["B_hv"] == "1.0"
    assert driver.poll(force=True) is True
    assert len(calls) == 2
    assert driver["B_hv"] == "2.0"


def test_failed_poll_is_retried_before_the_interval(restartable_server, make_driver):
    server, write, read = restartable_server
    now = time.time()
    Publisher(server.url, write).push([("hv", now, 2.5)], now=now)
    driver = make_driver(server.url, read, ["B/hv"], poll_interval=3600)
    server.stop()
    assert driver.poll() is False
    assert driver.poll() is False  # too early to try again: the old result
    server.start()
    driver._next_poll = 0  # as if the retry delay had passed
    assert driver.poll() is True
    assert driver["B_hv"] == "2.5"


def test_refresh_command_forces_poll(live_server, make_driver):
    url, write, read = live_server
    now = time.time()
    pub = Publisher(url, write)
    pub.push([("hv", now - 10, 1.0)], now=now)
    driver = make_driver(url, read, ["B/hv"], poll_interval=3600)
    assert driver.poll()
    assert driver["B_hv"] == "1.0"
    pub.push([("hv", now, 2.0)], now=now)
    assert driver.poll()
    assert driver["B_hv"] == "1.0"
    driver.command("refresh")
    assert driver["B_hv"] == "2.0"


def test_unknown_channel_does_not_spoil_the_others(live_server, make_driver, caplog):
    url, write, read = live_server
    now = time.time()
    Publisher(url, write).push([("hv", now, 7.0)], now=now)
    driver = make_driver(url, read, ["B/hv", "B/ghost", "X/foo"], poll_interval=3600)
    with caplog.at_level(logging.WARNING):
        assert driver.poll(force=True) is True  # nothing failed
    assert driver["B_hv"] == "7.0"
    assert driver["B_ghost"] == "nan"
    assert driver["X_foo"] == "nan"
    assert driver["B_online"] == "True"
    assert driver["X_online"] == "nan"  # no such experiment
    assert "B/ghost" in caplog.text and "X/foo" in caplog.text

    caplog.clear()
    with caplog.at_level(logging.WARNING):
        driver.poll(force=True)
    assert "B/ghost" not in caplog.text  # told once

    # the channel shows up later
    Publisher(url, write).web.push(
        {
            "run": "A",
            "sent_at": now,
            "interval": 10.0,
            "channels": [{"name": "ghost", "kind": "sampled"}],
            "points": [{"channel": "ghost", "t": now, "v": 9.0}],
            "ticks": [now],
        }
    )
    assert driver.poll(force=True) is True
    assert driver["B_ghost"] == "9.0"
    assert driver["B_hv"] == "7.0"


def test_experiments_are_polled_separately(
    live_server, config, clock, make_driver, monkeypatch
):
    from hc_web import db
    from hc_web.tokens import create_token

    url, write_b, read = live_server
    conn = db.connect(config.database)
    try:
        write_c = create_token(conn, "C", "other pc")
    finally:
        conn.close()
    t0 = clock.now
    Publisher(url, write_b).push([("hv", t0 - 5, 1.0)], now=t0)
    Publisher(url, write_c).push([("hv", t0, 2.0)], now=t0)
    driver = make_driver(url, read, ["B/hv", "C/hv"], backfill_hours=1)
    calls = record_since(driver, monkeypatch)
    assert driver.poll(force=True)
    assert driver["B_hv"] == "1.0" and driver["C_hv"] == "2.0"
    assert driver["B_online"] == "True" and driver["C_online"] == "True"
    assert sorted(c[0][0] for c in calls) == ["B/hv", "C/hv"]  # one request each

    # B keeps publishing, C does not: only C goes offline
    clock.now = t0 + 20
    Publisher(url, write_b).push([("hv", t0 + 20, 3.0)], now=t0 + 20)
    clock.now = t0 + 40
    calls.clear()
    assert driver.poll(force=True)
    since = {c[0][0]: c[1] for c in calls}
    assert since["B/hv"] == pytest.approx(t0 - 5 - 60)
    assert since["C/hv"] == pytest.approx(t0 - 60)
    assert driver["B_online"] == "True" and driver["B_hv"] == "3.0"
    assert driver["C_online"] == "False" and driver["C_hv"] == "nan"
    assert driver.history.open_gap_start("C") == pytest.approx(t0)
    assert driver.history.open_gap_start("B") is None


# -- HCWebServer: connection flow ---------------------------------------------


def test_establish_connection(live_server, make_driver):
    url, _write, read = live_server
    driver = make_driver(url, read, ["B/hv"])
    assert driver.establish_connection() is True
    bad = make_driver("http://127.0.0.1:1", read, ["B/hv"])
    assert bad.establish_connection() is False  # no exception


def test_try_connect_flow(restartable_server, make_driver):
    server, write, read = restartable_server
    now = time.time()
    Publisher(server.url, write).push([("hv", now, 2.5)], now=now)
    driver = make_driver(server.url, read, ["B/hv"], poll_interval=1e-9)

    server.stop()
    assert driver.try_connect() is False  # cannot connect the first time
    assert driver["ONLINE"] is False

    server.start()
    assert driver.try_connect() is True
    assert driver["ONLINE"] is True
    assert driver["B_hv"] == "2.5"  # connecting polled once

    server.stop()
    assert driver.try_connect() is True  # still online
    assert driver["ONLINE"] is True
    assert driver["B_hv"] == "nan"
    assert driver["B_online"] == "nan"

    server.start()
    assert driver.try_connect() is True
    assert driver["B_hv"] == "2.5"


def test_history_is_closed_with_the_driver_and_still_readable(live_server, make_driver):
    url, write, read = live_server
    now = time.time()
    Publisher(url, write).push([("hv", now, 2.5)], now=now)
    driver = make_driver(url, read, ["B/hv"])
    driver.poll(force=True)
    driver.close()
    assert driver.history.points("B/hv") == [(pytest.approx(now), 2.5)]


# -- HCWebServer in an App -----------------------------------------------------


def test_driver_in_app_dummy_mode(tmp_path, caplog):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from hardware_control.base.App import App

    driver = HCWebServer(
        "web",
        "http://127.0.0.1:1",
        "token",
        ["B/hv", "B/ng_on"],
        history_file=tmp_path / "h.sqlite",
    )
    app = App(dummy=True)
    try:
        app.add_instrument(driver)
        for name in driver.read_commands:
            driver.dummy_returns[name] = "nan"
        registered = set(app.list_instrument_parameters("web"))
        assert {"B_hv", "B_ng_on", "B_online", "ONLINE", "refresh"} <= registered
        assert driver.get_value("B_hv") == "nan"
        assert driver.get_value("B_online") == "nan"
        driver.command("refresh")  # a dummy command does nothing
        assert not (tmp_path / "h.sqlite").exists()  # and nothing was polled

        # a virtual instrument can be auto-updated (the web publisher does it
        # for what it publishes): there is nothing to query and no error
        app.add_virtual_instrument("source", ["hv"])
        app.add_auto_update_instrument_parameter("source", "hv")
        with caplog.at_level(logging.ERROR):
            app.update_instruments()
        assert "ONLINE" not in caplog.text
    finally:
        app.close()
    assert not [t for t in threading.enumerate() if t.name == "web"]
