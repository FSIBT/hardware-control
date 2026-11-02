"""Tests for the remote access interface of the App and the client."""

import json
import socket
import threading
import time

import pytest
import zmq

from hardware_control.base.App import App
from hardware_control.base.hooks import call_hooks, call_hooks_traced, Ramp
from hardware_control.base.Instrument import Instrument
from hardware_control.base.remote_access import RemoteAccess
from hardware_control.base.ZMQRemoteAdapter import ZMQSingleInstrument
from hardware_control.remote import formatters, HardwareControlClient


class Publisher:
    """Record the messages that the App sends to the instruments."""

    closed = False

    def __init__(self):
        self.messages = []

    def send_string(self, msg):
        self.messages.append(msg)


class FakeApp:
    """Use the App methods without a QApplication and ZMQ sockets."""

    app_name = "fake"
    WRITE_COMMANDS = App.WRITE_COMMANDS
    get_instrument_parameters_and_commands = App.get_instrument_parameters_and_commands
    get_instrument_parameter = App.get_instrument_parameter
    set_instrument_parameter = App.set_instrument_parameter
    call_instrument_command = App.call_instrument_command
    call_continuous_commands = App.call_continuous_commands
    list_instrument_parameters = App.list_instrument_parameters
    handle_request = App.handle_request
    _send_set_request = App._send_set_request
    _check_readable = App._check_readable
    _check_settable = App._check_settable
    _handle_get_parameters = App._handle_get_parameters
    _handle_set_parameters = App._handle_set_parameters
    _handle_list_parameters = App._handle_list_parameters
    _handle_list_instruments = App._handle_list_instruments
    _handle_app_info = App._handle_app_info
    _handle_access_info = App._handle_access_info
    _check_access = App._check_access
    _process_ipc_command = App._process_ipc_command

    def __init__(self, dummy=False, directory=None):
        self.dummy = dummy
        self.remote_access = RemoteAccess(self.app_name, directory)
        self.zmq_publisher = Publisher()
        self.stop_threads_event = threading.Event()
        self.continuous_commands = set()
        self._data = {"PSU": self._instrument()}

    @staticmethod
    def _instrument():
        def parameter():
            return {
                "read_value": None,
                "set_value": None,
                "post_read_hooks": [],
                "pre_set_hooks": [],
                "widgets": [],
            }

        return {
            "__capabilities__": {
                "read_parameters": ["V_READ", "V_SET", "ONLINE"],
                "set_parameters": ["V_SET"],
                "commands": ["ON"],
            },
            "V_READ": parameter(),
            "V_SET": parameter(),
            "ONLINE": parameter(),
            "ON": {"pre_call_hooks": [], "widgets": []},
            "IGNORE": False,
        }

    def set_one(self, parameter="V_SET", value="1", instrument="PSU"):
        update = {"instrument": instrument, "parameter": parameter, "value": value}
        return self._handle_set_parameters([update])["data"][0]


def test_set_success():
    app = FakeApp()
    assert app.set_one()["status"] == "success"
    assert app.zmq_publisher.messages == ["PSU 1 set V_SET 1"]
    assert app._data["PSU"]["V_SET"]["set_value"] == "1"


@pytest.mark.parametrize(
    "kwargs, reason",
    [
        ({"instrument": "NOPE"}, "Unknown instrument"),
        ({"parameter": "NOPE"}, "Unknown parameter"),
        ({"parameter": "__capabilities__"}, "Unknown parameter"),
        ({"parameter": "IGNORE"}, "Unknown parameter"),
        ({"parameter": "V_READ"}, "read-only"),
        ({"parameter": "ON"}, "is a command"),
        ({"value": "1 2"}, "whitespace"),
        ({"value": ""}, "whitespace"),
    ],
)
def test_set_rejected_without_sending(kwargs, reason):
    app = FakeApp()
    result = app.set_one(**kwargs)
    assert result["status"] == "error"
    assert reason in result["error"]
    assert app.zmq_publisher.messages == []


def test_set_offline_instrument():
    app = FakeApp()
    app._data["PSU"]["ONLINE"]["read_value"] = "False"
    assert "offline" in app.set_one()["error"]
    assert app.zmq_publisher.messages == []


def test_set_blocked_by_hook():
    def limit(value):
        return None

    app = FakeApp()
    app._data["PSU"]["V_SET"]["pre_set_hooks"].append(limit)
    result = app.set_one(value="5000")
    assert result["status"] == "error"
    assert "limit" in result["error"]
    assert app.zmq_publisher.messages == []
    assert app._data["PSU"]["V_SET"]["set_value"] is None


def test_set_deferred_by_ramp():
    def ramp(value):
        return None

    ramp.defers_set = True
    app = FakeApp()
    app._data["PSU"]["V_SET"]["pre_set_hooks"].append(ramp)
    assert app.set_one()["status"] == "deferred"
    assert app.zmq_publisher.messages == []


def test_ramp_hook_is_deferred():
    assert Ramp.defers_set


def test_set_in_dummy_mode():
    app = FakeApp(dummy=True)
    assert app.set_one()["status"] == "skipped"
    assert app.zmq_publisher.messages == []


def test_set_continues_after_error():
    app = FakeApp()
    updates = [
        {"instrument": "PSU", "parameter": "NOPE", "value": "1"},
        {"instrument": "PSU", "parameter": "V_SET", "value": "2"},
    ]
    data = app._handle_set_parameters(updates)["data"]
    assert [d["status"] for d in data] == ["error", "success"]


def test_public_set_is_unchanged():
    """Hooks treat None as blocked, so this needs to keep returning None."""
    app = FakeApp()
    assert app.set_instrument_parameter("PSU", "V_SET", "1") is None
    # the GUI path does not apply the checks for remote requests
    assert app.set_instrument_parameter("PSU", "V_SET", "1 2") is None
    assert app.zmq_publisher.messages[-1] == "PSU 1 set V_SET 1 2"


def test_hooks_only_run_once():
    calls = []

    def count(value):
        calls.append(value)
        return value

    app = FakeApp()
    app._data["PSU"]["V_SET"]["pre_set_hooks"].append(count)
    app.set_one()
    assert calls == ["1"]


def test_call_hooks():
    assert call_hooks([], "1") == "1"
    assert call_hooks([lambda x: None], "1") is None
    assert call_hooks([], "None") is None
    assert call_hooks_traced([], None) == (None, None)


def test_get_errors():
    app = FakeApp()
    app._data["PSU"]["V_READ"]["read_value"] = "3"
    queries = [
        {"instrument": "PSU", "parameter": "V_READ"},
        {"instrument": "PSU", "parameter": "IGNORE"},
        {"instrument": "PSU", "parameter": "NOPE"},
        {"instrument": "NOPE", "parameter": "V_READ"},
        {"instrument": "PSU", "parameter": "ON"},
    ]
    data = app._handle_get_parameters(queries)["data"]
    assert data[0]["value"] == "3"
    assert data[1]["value"] is False
    assert all("error" in d for d in data[2:])


def test_list_parameters():
    app = FakeApp()
    assert "__capabilities__" not in app._handle_list_parameters("PSU")["data"]
    assert app._handle_list_parameters("NOPE")["status"] == "error"


def test_continuous_commands_skip_only_offline_instruments():
    app = FakeApp()
    app._data["PSU2"] = app._instrument()
    app._data["PSU"]["ONLINE"]["read_value"] = "False"
    app._data["PSU2"]["ONLINE"]["read_value"] = "True"
    app.continuous_commands = {("PSU", "ON", True), ("PSU2", "ON", True)}
    app.call_continuous_commands()
    assert app.zmq_publisher.messages == ["PSU2 0 command ON"]


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def rep_socket():
    context = zmq.Context()
    sock = context.socket(zmq.REP)
    sock.setsockopt(zmq.RCVTIMEO, 2000)
    sock.setsockopt(zmq.LINGER, 0)
    port = sock.bind_to_random_port("tcp://127.0.0.1")
    yield sock, f"tcp://127.0.0.1:{port}"
    sock.close()
    context.term()


def test_handle_request_always_replies(rep_socket, tmp_path):
    sock, address = rep_socket
    app = FakeApp(directory=tmp_path)
    app.remote_access.configure("read-only")
    app.zmq_info = sock

    context = zmq.Context()
    client = context.socket(zmq.REQ)
    client.setsockopt(zmq.RCVTIMEO, 2000)
    client.setsockopt(zmq.LINGER, 0)
    client.connect(address)

    for request, expected in [
        ("get_instrument_parameter(one_argument)", "ERROR"),
        ("something else", "ERROR"),
        ("get_instrument_parameter(PSU,V_READ)", "None"),
    ]:
        client.send_string(request)
        deadline = time.time() + 2
        while not sock.poll(10) and time.time() < deadline:
            pass
        app.handle_request()
        assert client.recv_string().startswith(expected)

    client.close()
    context.term()


def test_client_recovers_after_timeout(rep_socket):
    sock, address = rep_socket
    client = HardwareControlClient(address, pid=1, timeout=200, app_name="test")
    client.is_alive = lambda: True

    with pytest.raises(RuntimeError, match="Timeout"):
        client.list_instruments()
    sock.recv_string()
    sock.send_string("{}")

    def answer():
        sock.recv_string()
        sock.send_string(json.dumps({"status": "success"}))

    thread = threading.Thread(target=answer)
    thread.start()
    assert client.list_instruments() == {"status": "success"}
    thread.join()
    client.close()


def test_single_instrument_stop():
    instrument = Instrument("remote", "127.0.0.1:1")
    instrument._dummy = True
    instrument.try_connect = lambda: True
    address = f"127.0.0.1:{free_port()}"

    thread = threading.Thread(
        target=ZMQSingleInstrument, args=(instrument, address), daemon=True
    )
    thread.start()

    context = zmq.Context()
    client = context.socket(zmq.REQ)
    client.setsockopt(zmq.RCVTIMEO, 2000)
    client.setsockopt(zmq.LINGER, 0)
    client.connect(f"tcp://{address}")
    try:
        client.send_string("APP")
        assert client.recv_string() == "Unknown command"
        client.send_string("APP tcp://127.0.0.1:1")
        assert client.recv_string().startswith("remote")
        client.send_string("STOP")
        assert client.recv_string() == "ACK"
        thread.join(timeout=5)
        assert not thread.is_alive()
    finally:
        client.close()
        context.term()


def test_formatters_show_errors_of_later_entries():
    data = {
        "status": "success",
        "data": [
            {"instrument": "A", "parameter": "B", "status": "success"},
            {"instrument": "A", "parameter": "C", "status": "error", "error": "bad"},
        ],
    }
    for name in ["format_markdown", "format_csv", "format_sheets", "format_compact"]:
        assert "bad" in getattr(formatters, name)(data)
