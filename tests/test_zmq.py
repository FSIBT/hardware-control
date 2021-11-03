"""Test ZMQ related functions"""
import pytest

from hardware_control.base.zmq_helper import add_ZMQ_message_to_queue


class Adapter:
    def __init__(self):
        self.name = "Test_Adapater"
        self.zmq_topic_length = len(self.name) + 1
        self.priority_queue = {0: [], 1: [], 2: []}


class Test:
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
