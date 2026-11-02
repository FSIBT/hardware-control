"""Tests for the MCP server, connected to it like an MCP client would be."""

import asyncio
import json

import pytest

pytest.importorskip("mcp")

from mcp import Client

from hardware_control.cli.hc_mcp import create_server
from test_remote import FakeApp


class DirectClient:
    """Pass requests directly to an App instead of going through a socket."""

    def __init__(self, app, token=None):
        self.app = app
        self.token = token

    def request(self, **kwargs):
        return self.app._process_ipc_command({**kwargs, "token": self.token})

    def get_access_info(self):
        return self.request(command="access_info")

    def list_instruments(self):
        return self.request(command="list_instruments")

    def list_parameters(self, instrument):
        return self.request(command="list_parameters", instrument=instrument)

    def get_parameters(self, queries):
        return self.request(command="get_parameters", queries=queries)

    def set_parameters(self, updates):
        return self.request(command="set_parameters", updates=updates)

    def call_commands(self, commands):
        return self.request(command="call_commands", commands=commands)


@pytest.fixture
def app(tmp_path):
    return FakeApp(directory=tmp_path)


def run(app, function, token=None):
    async def main():
        async with Client(create_server(DirectClient(app, token))) as client:
            return await function(client)

    return asyncio.run(main())


def tool_names(app):
    async def function(client):
        return [tool.name for tool in (await client.list_tools()).tools]

    return run(app, function)


def call(app, name, arguments=None, token=None):
    async def function(client):
        return await client.call_tool(name, arguments or {})

    return run(app, function, token)


SET = {"updates": [{"instrument": "PSU", "parameter": "V_SET", "value": 1.5}]}
GET = {"queries": [{"instrument": "PSU", "parameter": "V_READ"}]}
CALL = {"commands": [{"instrument": "PSU", "command": "ON"}]}


def test_tools_follow_the_access_mode(app):
    assert tool_names(app) == ["get_access_status"]
    app.remote_access.configure("read-only")
    assert "get_parameters" in tool_names(app)
    assert "set_parameters" not in tool_names(app)
    app.remote_access.configure("full")
    assert {"set_parameters", "call_commands"} <= set(tool_names(app))


def test_status_works_when_off(app):
    result = call(app, "get_access_status")
    assert not result.is_error
    assert result.structured_content["data"]["access_mode"] == "off"


def test_off_is_refused_by_the_app(app):
    result = call(app, "get_parameters", GET)
    assert result.is_error
    assert "off" in result.structured_content["message"]


def test_read_only_refuses_writes(app):
    app.remote_access.configure("read-only")
    for name, arguments in [("set_parameters", SET), ("call_commands", CALL)]:
        result = call(app, name, arguments)
        assert result.is_error
        assert "read-only" in result.structured_content["message"]
    assert app.zmq_publisher.messages == []


def test_read_returns_json(app):
    app.remote_access.configure("read-only")
    app._data["PSU"]["V_READ"]["read_value"] = "3"
    result = call(app, "get_parameters", GET)
    assert not result.is_error
    assert json.loads(result.content[0].text)["data"][0]["value"] == "3"


def test_full_control(app):
    app.remote_access.configure("full")
    assert not call(app, "set_parameters", SET).is_error
    assert not call(app, "call_commands", CALL).is_error
    assert app.zmq_publisher.messages == ["PSU 1 set V_SET 1.5", "PSU 1 command ON"]


def test_failed_entry_is_an_error(app):
    app.remote_access.configure("full")
    bad = {"updates": [{"instrument": "PSU", "parameter": "V_READ", "value": 1}]}
    assert call(app, "set_parameters", bad).is_error


def test_token(app):
    app.remote_access.configure("full", token="secret")
    assert tool_names(app) == ["get_access_status"]
    assert call(app, "set_parameters", SET).is_error
    assert not call(app, "set_parameters", SET, token="secret").is_error


def test_unknown_tool(app):
    app.remote_access.configure("full")
    assert call(app, "nope").is_error
