"""Test ZMQ related functions"""
from hardware_control.base.zmq_helper import (
    add_ZMQ_message_to_queue,
    handle_ZMQ_message_from_app,
)


class ZMQ_publisher:
    """A mock class for a zmq publisher that saves the zmq message in the adapter."""

    def __init__(self, adapter: "Adapter") -> None:
        self.adapter = adapter

    def send_string(self, msg: str) -> None:
        self.adapter.message = msg


class Instrument:
    """A mock class for an instrument."""

    def __init__(self, adapter: "Adapter") -> None:
        self.adapter = adapter
        self.name = "test_instrument"
        self.read_commands = {
            "TEST_A": 1,
            "TEST_B": 2,
            "TEST_C": "space in return",
        }

    def command(self, cmd: str) -> None:
        self.adapter.message = cmd

    def get_value(self, parameter: str) -> int:
        return self.read_commands[parameter]

    def __setitem__(self, parameter: str, value: str) -> None:
        self.adapter.message = f"{parameter} {value}"


class Adapter:
    """Mock adapter class"""

    def __init__(self) -> None:
        self.name = "Test_Adapater"
        self.zmq_topic_length = len(self.name) + 1
        self.priority_queue = {0: [], 1: [], 2: []}

        self.instrument = Instrument(self)
        self.zmq_publisher = ZMQ_publisher(self)

        self.message = ""


class TestHelper:
    def test_handle_ZMQ_message_from_app_get_value(self):
        adapter = Adapter()

        # test requesting a value in different queues
        adapter.priority_queue[0] = ["get TEST_A"]
        adapter.priority_queue[1] = []
        adapter.priority_queue[2] = []
        handle_ZMQ_message_from_app(adapter)
        assert adapter.message == "test_instrument TEST_A 1"

        adapter.priority_queue[0] = []
        adapter.priority_queue[1] = ["get TEST_A"]
        adapter.priority_queue[2] = []
        handle_ZMQ_message_from_app(adapter)
        assert adapter.message == "test_instrument TEST_A 1"

        adapter.priority_queue[0] = []
        adapter.priority_queue[1] = []
        adapter.priority_queue[2] = ["get TEST_A"]
        handle_ZMQ_message_from_app(adapter)
        assert adapter.message == "test_instrument TEST_A 1"

        # test that no spaces are returned
        adapter.priority_queue[0] = []
        adapter.priority_queue[1] = []
        adapter.priority_queue[2] = ["get TEST_C"]
        handle_ZMQ_message_from_app(adapter)
        assert adapter.message == "test_instrument TEST_C spaceinreturn"

        # if multiple commands are in different queues, test that the correct one gets excuted
        adapter.priority_queue[0] = ["get TEST_A"]
        adapter.priority_queue[1] = ["get TEST_B"]
        adapter.priority_queue[2] = []
        handle_ZMQ_message_from_app(adapter)
        assert adapter.message == "test_instrument TEST_B 2"

        adapter.priority_queue[0] = ["get TEST_A"]
        adapter.priority_queue[1] = []
        adapter.priority_queue[2] = ["get TEST_C"]
        handle_ZMQ_message_from_app(adapter)
        assert adapter.message == "test_instrument TEST_C spaceinreturn"

    def test_handle_ZMQ_message_from_app_set_value(self):
        adapter = Adapter()

        # test requesting a value in different queues
        adapter.priority_queue[0] = ["set TEST_A 3"]
        adapter.priority_queue[1] = []
        adapter.priority_queue[2] = []
        handle_ZMQ_message_from_app(adapter)
        assert adapter.message == "TEST_A 3"

        adapter.priority_queue[0] = []
        adapter.priority_queue[1] = ["set TEST_A 3"]
        adapter.priority_queue[2] = []
        handle_ZMQ_message_from_app(adapter)
        assert adapter.message == "TEST_A 3"

        adapter.priority_queue[0] = []
        adapter.priority_queue[1] = []
        adapter.priority_queue[2] = ["set TEST_A 3"]
        handle_ZMQ_message_from_app(adapter)
        assert adapter.message == "TEST_A 3"

        # if multiple commands are in different queues, test that the correct one gets excuted
        adapter.priority_queue[0] = ["set TEST_A 3"]
        adapter.priority_queue[1] = ["set TEST_B 4"]
        adapter.priority_queue[2] = []
        handle_ZMQ_message_from_app(adapter)
        assert adapter.message == "TEST_B 4"

        adapter.priority_queue[0] = ["set TEST_A 3"]
        adapter.priority_queue[1] = []
        adapter.priority_queue[2] = ["set TEST_C 4"]
        handle_ZMQ_message_from_app(adapter)
        assert adapter.message == "TEST_C 4"

    def test_handle_ZMQ_message_from_app_command(self):
        adapter = Adapter()

        # test requesting a value in different queues
        adapter.priority_queue[0] = ["command TEST_A"]
        adapter.priority_queue[1] = []
        adapter.priority_queue[2] = []
        handle_ZMQ_message_from_app(adapter)
        assert adapter.message == "TEST_A"

        adapter.priority_queue[0] = []
        adapter.priority_queue[1] = ["command TEST_A"]
        adapter.priority_queue[2] = []
        handle_ZMQ_message_from_app(adapter)
        assert adapter.message == "TEST_A"

        adapter.priority_queue[0] = []
        adapter.priority_queue[1] = []
        adapter.priority_queue[2] = ["command TEST_A"]
        handle_ZMQ_message_from_app(adapter)
        assert adapter.message == "TEST_A"

        # if multiple commands are in different queues, test that the correct one commands excuted
        adapter.priority_queue[0] = ["command TEST_A"]
        adapter.priority_queue[1] = ["command TEST_B"]
        adapter.priority_queue[2] = []
        handle_ZMQ_message_from_app(adapter)
        assert adapter.message == "TEST_B"

        adapter.priority_queue[0] = ["command TEST_A"]
        adapter.priority_queue[1] = []
        adapter.priority_queue[2] = ["command TEST_C"]
        handle_ZMQ_message_from_app(adapter)
        assert adapter.message == "TEST_C"

    def test_add_ZMQ_message_to_queue(self):

        adapter = Adapter()

        # add some low priority items
        msg = "Test_Adapater 0 command trigger"
        add_ZMQ_message_to_queue(adapter, msg)
        assert adapter.priority_queue[0] == ["command trigger"]

        msg = "Test_Adapater 0 command clear"
        add_ZMQ_message_to_queue(adapter, msg)
        assert adapter.priority_queue[0] == ["command trigger", "command clear"]

        # ensure that priority 0 doesn't add a command twice
        msg = "Test_Adapater 0 command trigger"
        add_ZMQ_message_to_queue(adapter, msg)
        assert adapter.priority_queue[0] == ["command trigger", "command clear"]

        # add priority 1 item
        msg = "Test_Adapater 1 get voltage"
        add_ZMQ_message_to_queue(adapter, msg)
        assert adapter.priority_queue[0] == ["command trigger", "command clear"]
        assert adapter.priority_queue[1] == ["get voltage"]

        # add priority 2 item
        msg = "Test_Adapater 2 set voltage 3"
        add_ZMQ_message_to_queue(adapter, msg)
        assert adapter.priority_queue[0] == ["command trigger", "command clear"]
        assert adapter.priority_queue[1] == ["get voltage"]
        assert adapter.priority_queue[2] == ["set voltage 3"]

        # priority 2 should allow handling the same command twice
        msg = "Test_Adapater 2 set voltage 3"
        add_ZMQ_message_to_queue(adapter, msg)
        assert adapter.priority_queue[0] == ["command trigger", "command clear"]
        assert adapter.priority_queue[1] == ["get voltage"]
        assert adapter.priority_queue[2] == ["set voltage 3", "set voltage 3"]

        # ensure that priority 0 doesn't add a set command twice independ of value
        msg = "Test_Adapater 0 set voltage 1"
        add_ZMQ_message_to_queue(adapter, msg)
        assert adapter.priority_queue[0] == [
            "command trigger",
            "command clear",
            "set voltage 1",
        ]
        msg = "Test_Adapater 0 set voltage 1"
        add_ZMQ_message_to_queue(adapter, msg)
        assert adapter.priority_queue[0] == [
            "command trigger",
            "command clear",
            "set voltage 1",
        ]

        # if we change the value, the new value should be in the queue
        msg = "Test_Adapater 0 set voltage 3"
        add_ZMQ_message_to_queue(adapter, msg)
        assert adapter.priority_queue[0] == [
            "command trigger",
            "command clear",
            "set voltage 3",
        ]
