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
