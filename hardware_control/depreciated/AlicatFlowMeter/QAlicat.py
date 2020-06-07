import sys

import pyvisa
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QLabel,
)

from .Alicat_control_test import Alicat

rm = pyvisa.ResourceManager()


class AlicatCommunication(QObject):
    # Handles communication with Alicat FlowMeter in own thread

    values_read = pyqtSignal(float)
    toggle_enable = pyqtSignal(bool)

    def __init__(self, port, address, dummy=False, parent=None):
        super().__init__()
        self.parent = parent
        self.port = port
        self.addr = address
        self.instrument = Alicat(self.port, self.addr, dummy=dummy)
        self.online = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.read)
        self.timer.start(5500)
        if self.parent:
            self.parent.write_value.connect(self.write)

    @pyqtSlot()
    def stop_thread(self):
        self.timer.stop()

    @pyqtSlot()
    def enabled(self):
        if self.online != self.instrument.online:
            self.online = self.instrument.online
            self.toggle_enable.emit(self.online)

    @pyqtSlot()
    def read(self):
        massflow = self.instrument.read()
        print("in comm read ALICAT")
        sys.stdout.flush()
        self.values_read.emit(massflow)

    @pyqtSlot()
    def write(self, channel, value):
        if self.online:
            if value < 0 or value > 100:
                print("WARNING: Alicat Mass Flow value out of range!!")

            self.instrument.write(channel, value)


class AlicatControl(QGroupBox):
    write_value = pyqtSignal(int, float)

    def __init__(
        self, port, address, parent=None, dummy=False, debug=False, massflow_limit=True
    ):
        super().__init__("Alicat")
        self.port = port
        self.addr = address
        self.massflow_setpoint = 0
        self.massflow = 0
        self.massflow_limit = massflow_limit
        self.instrument = Alicat(self.port, self.addr, dummy=dummy)
        self.debug = debug
        self.parent = parent
        self.hbox = QHBoxLayout()

        # list of values
        self.value_box = QVBoxLayout()
        self.massflow_label = QLabel("0 % Mass Flow")
        self.massflow_label.setAlignment(QtCore.Qt.AlignCenter)
        self.label = QLabel("")
        # add mass flow to value box
        self.value_box.addWidget(self.massflow_label)
        self.value_box.addWidget(self.label)
        self.value_box.addStretch(1)

        # controls
        self.refreshbutton = QPushButton("Refresh Mass Flow [%]")
        self.refreshbutton.clicked.connect(self.refresh)
        self.AlicatCommand = QLineEdit()
        self.AlicatCommand.setText("")
        self.AlicatCommand.setFixedWidth(100)
        self.AlicatCommand.setFont(QFont("Times New Roman", 18))
        self.Alicatsend_command = QPushButton("Send Command")
        self.Alicatsend_command.clicked.connect(self.send_command)
        self.AlicatReturn = QLabel("")

        # add controls to layout
        self.controls = QVBoxLayout()
        self.controls.addWidget(self.refreshbutton)
        if self.debug:
            self.controls.addWidget(self.AlicatCommand)
            self.controls.addWidget(self.Alicatsend_command)
            self.controls.addWidget(self.AlicatReturn)
        self.controls.addStretch(1)

        # add controls and values to HBox Layout
        self.hbox.addLayout(self.value_box)
        self.hbox.addLayout(self.controls)
        self.hbox.addStretch(1)

        if dummy:
            self.label.setText("dummy")
        # Make Hbox visible
        self.setLayout(self.hbox)

        # start communication with Alicat
        self.comm_thread = QThread()
        self.comm = AlicatCommunication(self.port, self.addr, dummy=dummy, parent=self)

        #        print("mic check mic check 1,2 1,2 (QAlicat)")
        sys.stdout.flush()

        self.comm.values_read.connect(self.read)

        # several lines have been commented out of QATM, at the moment I don't know if they are needed or not

    @pyqtSlot(bool)
    def toggle_enable(self, status):
        self.setEnabled(status)

    def try_reconnect(self):
        self.Alicat.try_connect()

    @pyqtSlot()
    def read(self):

        self.massflow = self.massflow
        self.massflow_label.setText(f"{self.massflow} %")

    #        print("Alicat read", self.massflow)

    def get_values(self):
        return self.massflow

    def close(self):
        self.Alicat.close()

    def refresh(self):
        data = self.instrument.read()
        print("read was called under AlicatControl", data)
        self.massflow_label.setText(f"{data}")

    def send_command(self):

        if self.AlicatCommand.text() != "$$6" and self.AlicatCommand.text() != "A":
            self.AlicatReturn.setText("WARNING: Not a Valid Command")

        else:
            text_cmd = self.AlicatCommand.text()
            self.instrument.write(text_cmd)
            self.AlicatReturn.setText(self.instrument.data)
