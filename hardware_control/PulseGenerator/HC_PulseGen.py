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
from hardware_control.base import HC_Instrument, HC_Comm
import copy


class HC_PulseGen(HC_Instrument):
    def __init__(
        self,
        scpi_instr,
        window,
        name: str = "Pulse Generator Control",
        initialize_with: str = "INSTRUMENT",
        save_on_close: str = False,
    ):

        super().__init__(window, name)

        self.settings = {}
        self.save_on_close = save_on_close
        self.name = name

        self.comm = HC_Comm(scpi_instr, self)
        self.filename = ""

        # Initialize state to correct values
        if initialize_with == "INSTRUMENT":
            self.save_on_close = False
            # Can't save without filename
            self.settings = self.initialize_gui_instrument()
        elif initialize_with == "DEFAULT":
            self.save_on_close = False
            # Can't save without filename
            self.settings = self.default_state()
        else:
            self.load_state(initialize_with)
            self.filename = initialize_with

        # Create GUI
        self.command_label = QLabel("Trigger Command: ")
        #
        self.command_edit = QLineEdit()
        self.command_edit.editingFinished.connect(
            lambda: self.comm.update_setting("command", self.command_edit.text())
        )
        self.command_edit.setText(self.settings["command"])
        #
        self.trig_but = QPushButton()
        self.trig_but.setText("Trigger")
        self.trig_but.setIcon(
            QIcon(
                (
                    QPixmap(
                        pkg_resources.resource_filename(
                            "hardware_control", "PulseGenerator/graphics/pulse.png"
                        )
                    )
                )
            )
        )
        self.trig_but.setCheckable(False)
        self.trig_but.clicked.connect(lambda: self.comm.command("TRIGGER"))
        #
        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.command_label, 0, 0, 1, 1)
        self.master_layout.addWidget(self.command_edit, 0, 1, 1, 1)
        self.master_layout.addWidget(self.trig_but, 1, 0, 1, 1)
        #
        self.setLayout(self.master_layout)

        # Write state to scope - synch scope with GUI
        self.send_state()

    def default_state(self):
        """Create the defualt state variable"""

        dflt = {}

        dflt["command"] = ":SS"

        return dflt
