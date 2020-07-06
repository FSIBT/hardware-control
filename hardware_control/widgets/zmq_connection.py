#
# This defines the OscilloscopeControl and OscilloscopeComm classes. By passing
# an instance of a SCPI command wrapper class to an OscilloscpeControl objcet,
# you can easily create GUIs for oscilloscopes.
#

import pkg_resources
import zmq
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QGroupBox,
    QLineEdit,
    QRadioButton,
    QPushButton,
    QLabel,
    QGridLayout,
)

from hardware_control.base import HC_Instrument
import logging

logger = logging.getLogger(__name__)


class HC_ZMQConnectionTool(HC_Instrument):
    def __init__(
        self,
        window,
        name: str = "ZMQ Input",
        port: str = "tcp://*:5555",
        update_period: int = 500,
    ):

        self.dummy = False

        self.socket = None
        self.poller = None

        super().__init__(window, name)

        self.settings = self.default_state()
        self.settings["port"] = port
        self.address = port

        # Note: unlike most HC_Instruments, this uses self.online to describe if
        # it is *enabled*, not if it is connected to an instrument becausee it has
        # no instruement to connect to. Instead, it uses self.socket_online to
        # describe if the socket exists and self.online to describe (only for the
        # ConnectionStatusTool's sake) if the instrument is enabled. This means
        # self.online will repeat the value of self.accept_commands.
        self.socket_online = False

        # Create ZMQ context, socket, poller
        self.context = zmq.Context()

        self.try_connect()
        # self.socket = self.context.socket(zmq.REP)
        # self.socket.bind(self.settings["port"])
        # #
        # self.poller = zmq.Poller()
        # self.poller.register(self.socket, zmq.POLLIN)

        self.ignore = False
        self.online_color = "Blue"
        self.accept_commands = False

        self.darkgrey_ind = QPixmap(
            pkg_resources.resource_filename(
                "hardware_control", "icons/ind_darkgrey.png"
            )
        )
        self.blue_ind = QPixmap(
            pkg_resources.resource_filename("hardware_control", "icons/ind_blue.png")
        )
        self.grey_ind = QPixmap(
            pkg_resources.resource_filename("hardware_control", "icons/ind_grey.png")
        )

        # Create GUI
        #

        self.port_edit_label = QLabel("Set Port:")
        self.port_edit_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.port_edit = QLineEdit()
        self.port_edit.textChanged.connect(
            lambda: self.update_setting("port", self.port_edit.text())
        )
        self.port_edit.setText(self.settings["port"])

        self.restart_port_but = QPushButton()
        self.restart_port_but.setText("Restart Port")
        self.restart_port_but.clicked.connect(lambda: self.restart_port())

        self.accept_cmd_button = QRadioButton()
        self.accept_cmd_button.setChecked(False)
        self.accept_cmd_button.setText("Accept Incoming Commands")
        self.accept_cmd_button.clicked.connect(
            lambda: self.connectionOnOff(self.accept_cmd_button)
        )
        #
        self.disable_cmd_button = QRadioButton()
        self.disable_cmd_button.setChecked(True)
        self.disable_cmd_button.setText("Disable Incoming Commands")
        self.disable_cmd_button.clicked.connect(
            lambda: self.connectionOnOff(self.disable_cmd_button)
        )
        self.online = False
        #
        pstr = self.settings["port"]
        self.port_label = QLabel(f"Port: {pstr}")
        self.received_label = QLabel("Last Message: --")

        self.status_box = QGroupBox("Status")
        self.status_grid = QGridLayout()
        self.status_label = QLabel("--")
        self.status_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.status_icon = QLabel()
        self.status_icon.setPixmap(self.grey_ind)
        self.status_grid.addWidget(self.status_label, 0, 0)
        self.status_grid.addWidget(self.status_icon, 0, 1)
        self.status_box.setLayout(self.status_grid)
        #
        self.panel = QGridLayout()
        self.panel.addWidget(self.port_edit_label, 0, 0)
        self.panel.addWidget(self.port_edit, 0, 1)
        self.panel.addWidget(self.restart_port_but, 0, 2)
        self.panel.addWidget(self.status_box, 0, 3)
        self.panel.addWidget(self.port_label, 1, 0, 1, 4)
        self.panel.addWidget(self.received_label, 2, 0, 1, 4)
        self.panel.addWidget(self.accept_cmd_button, 3, 0, 1, 3)
        self.panel.addWidget(self.disable_cmd_button, 4, 0, 1, 3)
        #
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.panel, 0, 0)
        #
        self.setLayout(self.master_layout)

        # Create timer to query voltages
        self.service_timer = QTimer(self)
        self.service_timer.timeout.connect(self.service_commands)
        self.service_timer.start(update_period)

    def restart_port(self):

        self.settings["port"] = self.port_edit.text()

        self.socket_online = False

        self.try_connect()

    def try_connect(self):  # TODO: Make sure this fucntion is working correctly

        if self.dummy:
            if self.socket_online:
                return True
            else:
                p_str = self.settings["port"]
                logger.debug(f"{self.ID}: creating dummy connection to {p_str}")
                self.socket_online = True
                return True

        if self.socket_online:
            # Todo: check that this will reconnect automatically, if not fix
            return True

        # Try to connect - restart socket
        if self.socket is not None:
            self.socket.close()
        self.socket = self.context.socket(zmq.REP)
        try:
            self.socket.bind(self.settings["port"])
        except:
            p_str = self.settings["port"]
            logger.error(f"Failed to bind to {p_str}", exc_info=True)

        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

        self.socket_online = True

        return True

    def connectionOnOff(self, button):

        if button.text() == "Accept Incoming Commands":
            self.accept_commands = True
            logger.info("Enabled incomming commands")
        else:
            self.accept_commands = False
            logger.info("Disabled incomming commands")

    def service_commands(self):
        """This is the command that gets called every 'x' seconds to check
        if a message is available and services the messages, if available."""

        if not self.accept_commands:
            self.received_label.setText("Last Message: --")
            self.status_label.setText("Disabled")
            self.status_icon.setPixmap(self.darkgrey_ind)
            self.online = False
            return

        self.status_label.setText("Enabled")
        self.status_icon.setPixmap(self.blue_ind)
        self.online = True

        # Check for events
        events = dict(self.poller.poll(10))

        # If event found...
        if len(events) > 0:

            logger.debug("ZMQConnectionTool received message")

            message = self.socket.recv()  # Receive message...

            mess_str = message.decode("utf-8")  # Convert from byte array to utf-8

            self.received_label.setText(f"Last Message: {mess_str}")  # Update label

            logger.info("Processing command '{mess_str}'")
            rval = self.window.app.process_hc_command(mess_str)

            if type(rval) == str:
                message = rval
            elif type(rval) == bool:
                message = str(rval)

            self.socket.send(bytes(message, "utf-8"))  # Send reply

        else:

            logger.debug("ZMQConnectionTool found no message on port")

    def default_state(self):
        dflt = {}
        dflt["port"] = "tcp://*:5555"
        return dflt

    def settings_to_UI(self):

        self.port_edit.setText(self.settings["port"])

        # if self.accept_commands:
        #     self.accept_cmd_button.setChecked(True)
        #     self.disable_cmd_button.setChecked(False)
        # else:
        #     self.accept_cmd_button.setChecked(False)
        #     self.disable_cmd_button.setChecked(True)

        pstr = self.settings["port"]
        self.port_label.setText(f"Port: {pstr}")
