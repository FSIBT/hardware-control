"""Tests for WebPublisher and its status indicator against a real server."""

import os
import socket
import threading
import time
from unittest.mock import MagicMock

import pytest

pytest.importorskip("flask")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from hardware_control.base.alarm import Alarm  # noqa: E402
from hardware_control.base.alarm_manager import AlarmManager  # noqa: E402
from hardware_control.base.remote_access import RemoteAccess  # noqa: E402
from hardware_control.web import WebClient, WebPublisher  # noqa: E402
from hardware_control.web.backlog import Backlog  # noqa: E402
from hardware_control.web.publisher import default_backlog_file  # noqa: E402
from hardware_control.web.status_gui import WebPublisherIndicator  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    # no display is needed, e.g. in CI
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    yield QApplication.instance() or QApplication([])


def wait_until(predicate, timeout=10.0):
    """Process Qt events (the status signal is queued) until ``predicate()``."""
    app = QApplication.instance()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    app.processEvents()
    return bool(predicate())


class FakeApp:
    """What the publisher needs of an App: values in a dict, a real AlarmManager."""

    def __init__(self):
        self.values = {}
        self.app_name = "publisher test"
        self.aboutToQuit = MagicMock()
        self.auto_updates = []
        self.alarm_manager = AlarmManager(app=self)

    def get_instrument_parameter(self, instrument, parameter, return_set_value=False):
        return self.values[(instrument, parameter)]

    def add_auto_update_instrument_parameter(self, instrument, parameter):
        self.auto_updates.append((instrument, parameter))


@pytest.fixture
def app(qapp):
    return FakeApp()


@pytest.fixture
def make_publisher(app, tmp_path):
    """Create publishers; at the end stop them and check no thread is left."""
    publishers = []

    def make(url, token, interval=10.0, name="backlog", **kwargs):
        pub = WebPublisher(
            app, url, token, interval=interval, backlog_file=tmp_path / name, **kwargs
        )
        publishers.append(pub)
        pub.backlog = tmp_path / name
        return pub

    yield make
    for pub in publishers:
        pub.stop()
    assert wait_until(
        lambda: not [t for t in threading.enumerate() if t.name == "web-publisher"],
        timeout=5,
    )


def start_manual(pub):
    """Start the worker, but tick by hand: the timer would make runs unpredictable."""
    pub.start()
    pub._timer.stop()


def tick(pub):
    pub.tick()
    time.sleep(0.002)  # every tick gets its own time


def reader(live_server):
    url, _write, read_token = live_server
    return WebClient(url, read_token)


def last_values(web):
    """channel name -> last value, from /api/v1/status."""
    experiment = web.status()["experiments"].get("B")
    if experiment is None:
        return {}
    return {c["name"]: c["last"] and c["last"][1] for c in experiment["channels"]}


def backlog_rows(path):
    """(points, ticks, events) waiting in the backlog file, from this thread."""
    backlog = Backlog(path)
    try:
        batch = backlog.take(10000)
    finally:
        backlog.close()
    return batch.points, batch.ticks, batch.events


def test_sampled_and_state_reach_server(app, live_server, make_publisher):
    url, write_token, _ = live_server
    pub = make_publisher(url, write_token)
    pub.publish("psu", "V", unit="V", label="HV")
    pub.publish("ng", "on", channel="ng_on", kind="state")
    assert app.auto_updates == [("psu", "V"), ("ng", "on")]
    app.values = {("psu", "V"): "12.5", ("ng", "on"): "1"}
    start_manual(pub)
    tick(pub)
    web = reader(live_server)
    assert wait_until(lambda: last_values(web) == {"psu_V": 12.5, "ng_on": "1"})
    assert wait_until(lambda: pub.status[0] == "connected")
    channels = {c["name"]: c for c in web.status()["experiments"]["B"]["channels"]}
    assert channels["psu_V"]["kind"] == "sampled"
    assert channels["psu_V"]["unit"] == "V"
    assert channels["psu_V"]["label"] == "HV"
    assert channels["ng_on"]["kind"] == "state"


def test_timer_ticks(app, live_server, make_publisher):
    url, write_token, _ = live_server
    pub = make_publisher(url, write_token, interval=0.1)
    pub.publish("psu", "V")
    app.values = {("psu", "V"): 3.0}
    pub.start()
    web = reader(live_server)
    assert wait_until(lambda: last_values(web) == {"psu_V": 3.0})
    assert pub.run_id and len(pub.run_id) == 32


@pytest.mark.parametrize("bad", ["ERROR", "None", "nan", "inf", "", None, float("nan")])
def test_non_numeric_sampled_values_sent_as_null(app, live_server, make_publisher, bad):
    url, write_token, _ = live_server
    pub = make_publisher(url, write_token)
    pub.publish("psu", "V")
    app.values = {("psu", "V"): 1.0}
    start_manual(pub)
    tick(pub)
    web = reader(live_server)
    assert wait_until(lambda: last_values(web) == {"psu_V": 1.0})
    app.values[("psu", "V")] = bad
    tick(pub)
    assert wait_until(
        lambda: len(web.data(["B/psu_V"], 0)["channels"]["B/psu_V"]["points"]) == 2
    )
    points = web.data(["B/psu_V"], 0)["channels"]["B/psu_V"]["points"]
    assert points[-1][1] is None
    assert pub.status[0] == "connected"


def test_state_sent_only_on_change(app, restartable_server, make_publisher):
    server, write_token, _ = restartable_server
    server.stop()  # nothing is pushed: what is queued stays in the backlog
    pub = make_publisher(server.url, write_token, interval=60)
    pub.publish("ng", "on", kind="state")
    pub.publish("psu", "V")
    app.values = {("ng", "on"): "0", ("psu", "V"): 1.0}
    start_manual(pub)
    for value in ["0", "0", "1", "1", "None", "nan", "0", "0"]:
        app.values[("ng", "on")] = value
        tick(pub)
    assert wait_until(lambda: len(backlog_rows(pub.backlog)[1]) == 8)
    points, ticks, _events = backlog_rows(pub.backlog)
    states = [p["v"] for p in points if p["channel"] == "ng_on"]
    # first tick, then each change; "None" and "nan" are both unknown
    assert states == ["0", "1", None, "0"]
    assert len([p for p in points if p["channel"] == "psu_V"]) == 8


def test_server_down_then_up_no_loss(app, restartable_server, make_publisher):
    server, write_token, read_token = restartable_server
    pub = make_publisher(server.url, write_token, interval=0.1)
    pub.publish("psu", "V")
    app.values = {("psu", "V"): 1.0}
    pushed = []
    original = pub.client.push

    def spy(body):
        result = original(body)
        pushed.extend((p["channel"], p["t"]) for p in body["points"])
        return result

    pub.client.push = spy
    start_manual(pub)
    tick(pub)
    assert wait_until(lambda: pub.status[0] == "connected")

    server.stop()
    for i in range(5):
        app.values[("psu", "V")] = float(i)
        tick(pub)
    assert wait_until(lambda: pub.status[0] == "buffering")
    assert wait_until(lambda: len(backlog_rows(pub.backlog)[0]) == 5)
    assert pub.status[1] > 0

    server.start()
    assert wait_until(lambda: pub.status[0] == "connected" and pub.status[1] == 0)
    assert backlog_rows(pub.backlog) == ([], [], [])
    assert len(pushed) == 6
    assert len(set(pushed)) == 6  # nothing sent twice
    web = WebClient(server.url, read_token)
    points = web.data(["B/psu_V"], 0)["channels"]["B/psu_V"]["points"]
    assert [p[1] for p in points] == [1.0, 0.0, 1.0, 2.0, 3.0, 4.0]
    assert web.status()["experiments"]["B"]["online"] is True


def test_conflict_keeps_backlog(app, live_server, make_publisher):
    url, write_token, _ = live_server
    app.values = {("psu", "V"): 1.0}
    first = make_publisher(url, write_token, interval=5.0, name="first")
    first.publish("psu", "V")
    start_manual(first)
    tick(first)
    assert wait_until(lambda: first.status[0] == "connected")

    second = make_publisher(url, write_token, interval=0.1, name="second")
    second.publish("psu", "V")
    start_manual(second)
    tick(second)
    assert wait_until(lambda: second.status[0] == "error")
    assert "another run is active" in second.status[2]
    points, ticks, _ = backlog_rows(second.backlog)
    assert len(points) == 1 and len(ticks) == 1

    # once the first run has shut down, the second one gets through
    first.stop()
    assert wait_until(lambda: second.status[0] == "connected" and second.status[1] == 0)
    assert backlog_rows(second.backlog) == ([], [], [])


def test_alarm_events_and_latched(app, live_server, make_publisher):
    url, write_token, _ = live_server
    pub = make_publisher(url, write_token)
    pub.publish("psu", "V")
    app.values = {("psu", "V"): 1.0}
    alarm = Alarm("psu", "V", "HV high", ">", 30000, action=lambda a: None)
    manager = app.alarm_manager
    manager.add_alarm(alarm)
    start_manual(pub)
    tick(pub)
    web = reader(live_server)
    assert wait_until(lambda: pub.status[0] == "connected")
    assert web.status()["experiments"]["B"]["latched"] == []

    manager.process_update("psu", "V", 31000)
    assert wait_until(
        lambda: web.status()["experiments"]["B"]["latched"] == ["HV high"]
    )
    events = web.events(0)["events"]
    assert [(e["alarm"], e["action"], e["message"]) for e in events] == [
        ("HV high", "triggered", "psu:V > 30000")
    ]

    manager.clear(alarm)
    assert wait_until(lambda: web.status()["experiments"]["B"]["latched"] == [])
    events = web.events(0)["events"]
    assert [(e["action"], e["message"]) for e in events] == [
        ("triggered", "psu:V > 30000"),
        ("cleared", "psu:V > 30000"),
    ]


def test_stop_sends_shutdown(app, live_server, make_publisher):
    url, write_token, _ = live_server
    pub = make_publisher(url, write_token)
    pub.publish("psu", "V")
    app.values = {("psu", "V"): 1.0}
    start_manual(pub)
    tick(pub)
    web = reader(live_server)
    assert wait_until(lambda: web.status()["experiments"].get("B", {}).get("online"))
    pub.stop()
    assert web.status()["experiments"]["B"]["online"] is False
    pub.stop()  # twice is fine


def test_stop_without_start(app, live_server, make_publisher):
    url, write_token, _ = live_server
    pub = make_publisher(url, write_token)
    pub.stop()
    pub.stop()


def test_start_connects_about_to_quit_once(app, live_server, make_publisher):
    url, write_token, _ = live_server
    pub = make_publisher(url, write_token)
    start_manual(pub)
    pub.stop()
    start_manual(pub)  # a second run gets a new run id
    pub.stop()
    app.aboutToQuit.connect.assert_called_once_with(pub.stop)


def test_stop_does_not_hang_on_a_silent_server(app, make_publisher):
    with socket.socket() as listener:  # accepts, never answers
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        url = f"http://127.0.0.1:{listener.getsockname()[1]}"
        pub = make_publisher(url, "token")
        pub.client.timeout = 0.5
        pub.publish("psu", "V")
        app.values = {("psu", "V"): 1.0}
        start_manual(pub)
        tick(pub)
        begin = time.monotonic()
        pub.stop(timeout=2.0)
        assert time.monotonic() - begin < 2.5


def test_publish_checks(app, live_server, make_publisher):
    url, write_token, _ = live_server
    pub = make_publisher(url, write_token)
    with pytest.raises(ValueError, match="channel name"):
        pub.publish("my psu", "V")
    with pytest.raises(ValueError, match="kind"):
        pub.publish("psu", "V", kind="weird")
    pub.publish("psu", "V")
    with pytest.raises(ValueError, match="already"):
        pub.publish("psu", "V")
    with pytest.raises(ValueError):
        WebPublisher(app, url, write_token, interval=0)


def test_default_backlog_file(app):
    pub = WebPublisher(app, "http://localhost:1", "token")
    path = pub.backlog_file
    assert path.parent.name == "web_backlog"
    assert path.suffix == ".sqlite"
    assert path == default_backlog_file("publisher test")
    assert path.stem == RemoteAccess("publisher test").filename.stem
    assert path.stem.startswith("publisher_test-")


def test_indicator_text_follows_status(app, qapp):
    pub = WebPublisher(app, "http://localhost:1", "token")
    indicator = WebPublisherIndicator(pub)
    pub.status_changed.emit("connected", 0, "all good")
    assert indicator.text() == "Web ✓"
    assert indicator.toolTip() == "all good"
    assert "green" in indicator.styleSheet()
    pub.status_changed.emit("buffering", 12, "cannot reach the server")
    assert indicator.text() == "Web: buffering 12"
    assert indicator.toolTip() == "cannot reach the server"
    assert "orange" in indicator.styleSheet()
    pub.status_changed.emit("error", 3, "HTTP 409: another run is active")
    assert indicator.text() == "Web: error"
    assert indicator.toolTip() == "HTTP 409: another run is active"
    assert "red" in indicator.styleSheet()
    assert pub.status == ("error", 3, "HTTP 409: another run is active")
