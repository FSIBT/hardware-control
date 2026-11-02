"""Tests for the access control of requests from other programs."""

import json
import os
import stat
import time

import pytest

from hardware_control.base.remote_access import (
    AccessMode,
    format_duration,
    generate_token,
    parse_duration,
    RemoteAccess,
)
from test_remote import FakeApp


BAD_TIME = (
    '{"mode": "full", "expires_at": "soon", "token_salt": null, "token_hash": null}'
)


@pytest.fixture
def access(tmp_path):
    return RemoteAccess("test", tmp_path)


@pytest.fixture
def app(tmp_path):
    return FakeApp(directory=tmp_path)


GET = {
    "command": "get_parameters",
    "queries": [{"instrument": "PSU", "parameter": "V_READ"}],
}
SET = {
    "command": "set_parameters",
    "updates": [{"instrument": "PSU", "parameter": "V_SET", "value": "1"}],
}


@pytest.mark.parametrize(
    "text, seconds",
    [
        ("", 0),
        ("0", 0),
        (0, 0),
        ("90", 90 * 60),
        (90, 90 * 60),
        ("4m", 4 * 60),
        ("8h", 8 * 3600),
        ("2d", 2 * 86400),
        ("2d8h4m", 2 * 86400 + 8 * 3600 + 4 * 60),
        ("2D 8H", 2 * 86400 + 8 * 3600),
    ],
)
def test_parse_duration(text, seconds):
    assert parse_duration(text) == seconds


@pytest.mark.parametrize("text", ["abc", "-5", "1.5", "4m2h", "5s", "h"])
def test_parse_duration_invalid(text):
    with pytest.raises(ValueError):
        parse_duration(text)


def test_format_duration():
    assert format_duration(2 * 86400 + 8 * 3600 + 4 * 60) == "2d8h4m"
    assert format_duration(61) == "2m"
    assert format_duration(0) == "0m"


def test_starts_off(access):
    assert access.mode is AccessMode.OFF
    assert not access.token_required
    assert access.remaining() is None


def test_invalid_mode_keeps_settings(access):
    access.configure("read-only")
    with pytest.raises(ValueError):
        access.configure("everything")
    assert access.mode is AccessMode.READ_ONLY


def test_invalid_duration_keeps_settings(access):
    access.configure("read-only")
    with pytest.raises(ValueError):
        access.configure("full", "soon", token="new")
    assert access.mode is AccessMode.READ_ONLY
    assert not access.token_required


def test_time_limit(access):
    access.configure("full", "1")
    assert 0 < access.remaining() <= 60
    access.expires_at = time.time() - 1
    assert access.mode is AccessMode.OFF
    assert access.expires_at is None


def test_off_ignores_time_limit(access):
    access.configure("off", "5")
    assert access.expires_at is None


def test_not_persisted_by_default(tmp_path):
    RemoteAccess("test", tmp_path).configure("full", token="secret")
    restarted = RemoteAccess("test", tmp_path)
    assert restarted.mode is AccessMode.OFF
    assert not restarted.token_required


def test_persisted_settings(tmp_path):
    first = RemoteAccess("test", tmp_path)
    first.configure("full", "1h", persist=True, token="secret")
    restarted = RemoteAccess("test", tmp_path)
    assert restarted.mode is AccessMode.FULL
    assert restarted.expires_at == first.expires_at
    assert restarted.persist
    assert restarted.check_token("secret")
    assert not restarted.check_token("wrong")


def test_settings_are_per_app(tmp_path):
    RemoteAccess("one", tmp_path).configure("full", persist=True)
    assert RemoteAccess("two", tmp_path).mode is AccessMode.OFF


def test_saved_file_is_private_and_has_no_token(tmp_path):
    access = RemoteAccess("test", tmp_path)
    access.configure("full", persist=True, token="secret")
    if os.name == "posix":
        assert stat.S_IMODE(os.stat(access.filename).st_mode) == 0o600
    assert "secret" not in access.filename.read_text()


def test_expired_saved_settings_are_removed(tmp_path):
    access = RemoteAccess("test", tmp_path)
    access.configure("full", "1h", persist=True)
    data = json.loads(access.filename.read_text())
    data["expires_at"] = time.time() - 1
    access.filename.write_text(json.dumps(data))

    restarted = RemoteAccess("test", tmp_path)
    assert restarted.mode is AccessMode.OFF
    assert not access.filename.exists()


def test_turning_off_removes_saved_settings(tmp_path):
    access = RemoteAccess("test", tmp_path)
    access.configure("full", persist=True)
    access.configure("off", persist=True)
    assert not access.filename.exists()


@pytest.mark.parametrize(
    "content", ["not json", "{}", '{"mode": "everything"}', "[]", BAD_TIME]
)
def test_invalid_saved_settings_leave_it_off(tmp_path, content):
    access = RemoteAccess("test", tmp_path)
    access.configure("full", persist=True)
    access.filename.write_text(content)
    assert RemoteAccess("test", tmp_path).mode is AccessMode.OFF


def test_token(access):
    assert access.check_token(None)
    token = generate_token()
    access.configure("full", token=token)
    assert access.check_token(token)
    assert not access.check_token("wrong")
    assert not access.check_token(None)
    assert not access.check_token(5)
    access.configure("full")
    assert access.check_token(token)
    access.configure("full", token="")
    assert access.check_token(None)


@pytest.mark.parametrize("request_", [GET, SET, {"command": "list_instruments"}])
def test_off_blocks_everything(app, request_):
    response = app._process_ipc_command(request_)
    assert response["status"] == "error"
    assert "off" in response["message"]
    assert app.zmq_publisher.messages == []


def test_unknown_command_is_blocked_when_off(app):
    assert "off" in app._process_ipc_command({"command": "nope"})["message"]


def test_read_only(app):
    app.remote_access.configure("read-only")
    assert app._process_ipc_command(GET)["status"] == "success"
    response = app._process_ipc_command(SET)
    assert "read-only" in response["message"]
    assert app.zmq_publisher.messages == []


def test_full(app):
    app.remote_access.configure("full")
    assert app._process_ipc_command(SET)["data"][0]["status"] == "success"
    assert len(app.zmq_publisher.messages) == 1


def test_token_is_checked_first(app):
    app.remote_access.configure("full", token="secret")
    assert "token" in app._process_ipc_command(GET)["message"]
    assert "token" in app._process_ipc_command({**SET, "token": "no"})["message"]
    assert app.zmq_publisher.messages == []
    response = app._process_ipc_command({**SET, "token": "secret"})
    assert response["data"][0]["status"] == "success"


def test_access_info(app):
    info = app._process_ipc_command({"command": "access_info"})["data"]
    assert info == {
        "access_mode": "off",
        "token_required": False,
        "token_valid": True,
    }


def test_access_info_hides_mode_without_token(app):
    app.remote_access.configure("full", token="secret")
    info = app._process_ipc_command({"command": "access_info"})["data"]
    assert info["access_mode"] is None
    assert info["token_valid"] is False


CALL = {
    "command": "call_commands",
    "commands": [{"instrument": "PSU", "command": "ON"}],
}


def call(app, **kwargs):
    item = {"instrument": "PSU", "command": "ON", **kwargs}
    return app._process_ipc_command({"command": "call_commands", "commands": [item]})


def test_commands_need_full_access(app):
    assert "off" in app._process_ipc_command(CALL)["message"]
    app.remote_access.configure("read-only")
    assert "read-only" in app._process_ipc_command(CALL)["message"]
    assert app.zmq_publisher.messages == []


def test_call_command(app):
    app.remote_access.configure("full")
    assert call(app)["data"][0]["status"] == "success"
    assert app.zmq_publisher.messages == ["PSU 1 command ON"]


@pytest.mark.parametrize(
    "kwargs, reason",
    [
        ({"instrument": "NOPE"}, "Unknown instrument"),
        ({"command": "NOPE"}, "Unknown command"),
        ({"command": "V_SET"}, "Unknown command"),
    ],
)
def test_call_command_rejected(app, kwargs, reason):
    app.remote_access.configure("full")
    entry = call(app, **kwargs)["data"][0]
    assert entry["status"] == "error"
    assert reason in entry["error"]
    assert app.zmq_publisher.messages == []


def test_call_command_offline(app):
    app.remote_access.configure("full")
    app._data["PSU"]["ONLINE"]["read_value"] = "False"
    assert "offline" in call(app)["data"][0]["error"]


def test_call_command_blocked_by_hook(app):
    def interlock(value):
        return None

    app.remote_access.configure("full")
    app._data["PSU"]["ON"]["pre_call_hooks"].append(interlock)
    assert "interlock" in call(app)["data"][0]["error"]
    assert app.zmq_publisher.messages == []


def test_public_call_is_unchanged(app):
    assert app.call_instrument_command("PSU", "ON") is None
    assert app.zmq_publisher.messages == ["PSU 1 command ON"]
