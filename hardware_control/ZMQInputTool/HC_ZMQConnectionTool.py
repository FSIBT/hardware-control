#
# This defines the OscilloscopeControl and OscilloscopeComm classes. By passing
# an instance of a SCPI command wrapper class to an OscilloscpeControl objcet,
# you can easily create GUIs for oscilloscopes.
#

from typing import List
import numpy as np
import json
import pkg_resources

import time  # Get rid of this guy!

from hardware_control.base import HC_Instrument, HC_Comm, setButtonState
import pyqtgraph as pg
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QDoubleValidator, QPixmap, QIcon
from PyQt5.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QWidget,
    QFormLayout,
    QGridLayout,
    QComboBox,
)
import copy
import zmq


class HC_ZMQConnectionTool(HC_Instrument):
    def __init__(
        self,
        window,
        name: str = "ZMQ Input",
        port: str = "tcp://*:5555",
        update_period: int = 500,
    ):

        super().__init__(window, name)

        self.port = port

        # Create ZMQ context, socket, poller
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind("tcp://*:5555")
        #
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

        # Create GUI
        #
        self.port_label = QLabel(f"Port: {self.port}")
        self.received_label = QLabel("Last Message: --")
        #
        self.panel = QGridLayout()
        self.panel.addWidget(self.port_label, 0, 0)
        self.panel.addWidget(self.received_label, 1, 0)
        #
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.panel, 0, 0)
        #
        self.setLayout(self.master_layout)

        self.log_note("Initalized")

        self.settings = self.default_state()

        # Create timer to query voltages
        self.service_timer = QTimer(self)
        self.service_timer.timeout.connect(self.service_commands)
        self.service_timer.start(update_period)

    def service_commands(self):
        """This is the command that gets called every 'x' seconds to check
        if a message is available and services the messages, if available."""

        # Check for events
        events = dict(self.poller.poll(10))

        # If event found...
        if len(events) > 0:

            message = self.socket.recv()  # Receive message...

            mess_str = message.decode("utf-8")  # Convert from byte array to utf-8

            self.received_label.setText(f"Last Message: {mess_str}")  # Update label

            rval = process_hc_command(self.window.app, mess_str)

            self.socket.send(message)  # Send reply

    def default_state(self):
        return {}


def process_hc_command(app, command: str):
    """Accepts a text command, and executes it on the app"""

    tokens = command.split(":")  # Split the command up into tokens

    # Check if too few commands are given
    if len(tokens) < 1:
        app.add_log(
            "HC-Command Processor",
            "NO-HARDWARE-BACKEND",
            "WARNING",
            f"Invalid HC-Command received. No tokens. Command: '{command}'",
        )
        return "WARNING: Couldn't process command"

    # Find out the 'mode' of the command
    if (
        tokens[0] == "SET"
    ):  # THis indicates that the command provides arguments for an instrument's update_settings() function

        # Make sure the correct number of arguments are given
        if len(tokens) != 4:  # Requires: MODE:INSTRUMENT:PARAMETER:VALUE
            app.add_log(
                "HC-Command Processor",
                "NO-HARDWARE-BACKEND",
                "WARNING",
                f"Invalid HC-Command received. Wrong number of tokens. Command: '{command}'",
            )
            return "WARNING: Couldn't process command"

        instr_str = tokens[1]
        setting_str = tokens[2]
        value_str = tokens[3]

        # If instrument exists...
        if instr_str in [x.name for x in app.instruments]:

            # Find instrument....
            for inst in app.instruments:
                if instr_str == inst.name:
                    inst.update_setting(setting_str, value_str)
        else:
            print(f"Instrument: {instr_str} not present")
            for inst_key in app.instruments:
                print(f"\t{inst_key}")

        print(
            f"Executing Setting Update:\n\tInstrument: {instr_str}\n\tSetting: {setting_str}\n\tValue: {value_str}"
        )

    elif (
        tokens[0] == "CMD"
    ):  # This indicates the command provides arguments for an instrument's command() function

        # Recalculate tokens, with max of 2 splits. This allows colons to appear in the command
        tokens = command.split(":", 2)

        # Make sure the correct number of arguments are given
        if len(tokens) != 3:  # Requires: MODE:INSTRUMENT:PARAMETER:VALUE
            app.add_log(
                "HC-Command Processor",
                "NO-HARDWARE-BACKEND",
                "WARNING",
                f"Invalid HC-Command received. Wrong number of tokens. Command: '{command}'",
            )
            return "WARNING: Couldn't process command"

        instr_str = tokens[1]
        command_str = tokens[2]

        # Find instrument....
        if instr_str in [x.name for x in self.instruments]:
            app.instruments[instr_str].command(command_str)
        else:
            print(f"Instrument: {instr_str} not present")
            for inst_key in app.instruments:
                print(f"\t{inst_key}")

        print(
            f"Executing Command:\n\tInstrument: {instr_str}\n\tCommand: {command_str}"
        )

    else:
        app.add_log(
            "HC-Command Processor",
            "NO-HARDWARE-BACKEND",
            "WARNING",
            f"Invalid HC-Command received. Unrecognized mode token. Command: '{command}'",
        )
        return "WARNING: Couldn't process command"

    return "Complete"
