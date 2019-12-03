#
#

from typing import List
import numpy as np
import json

import pyqtgraph as pg
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QDoubleValidator, QPixmap
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
from hardware_control.base import HC_Instrument, HC_Comm, setButtonState
import copy

#
#
class HC_FlowController(HC_Instrument):
    def __init__(
        self,
        scpi_instr,
        window,
        name: str = "Flow Controller",
        initialize_with: str = "INSTRUMENT",
        save_on_close: str = False,
        dummy=False,
    ):

        super().__init__(window, name)

        self.settings = {}
        self.save_on_close = save_on_close
        self.name = name

        self.comm = HC_Comm(scpi_instr, self)
        self.filename = ""

        # Initialize state to correct values
        if initialize_with == "DEFAULT":
            self.save_on_close = False
            # Can't save without filename
            self.settings = self.default_state()
        else:
            self.load_state(initialize_with)
            self.filename = initialize_with

        # *************************Create GUI************************

        # ****** DEFINE TEXT BOXES
        #
        self.rate_edit = QLineEdit()
        self.rate_edit.setValidator(QDoubleValidator())
        self.rate_edit.editingFinished.connect(
            lambda: self.comm.update_setting("rate", self.rate_edit.text())
        )
        self.rate_edit.setText(str(self.settings["rate"]))
        #
        self.form = QFormLayout()
        self.form.addRow("Flow rate (CFM?):", self.rate_edit)

        self.lower_grid = QGridLayout()
        #
        # ******* DEFINE DROPDOWNS + READOUT
        #
        self.gas_label = QLabel("Gas:")
        self.gas_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.gas_drop = QComboBox()
        self.gas_drop.addItems(["Argon", "Helium", "Hydrogen", "Air"])
        self.gas_drop.currentIndexChanged.connect(
            lambda: self.comm.update_setting("gas", self.gas_drop.currentText())
        )
        self.gas_drop.setCurrentText(self.settings["gas"])
        #
        self.pressure_label_fix0 = QLabel("Pressure: ")
        self.pressure_label_fix0.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        #
        self.pressure_label_readout = QLabel("--")
        self.pressure_label_readout.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        #
        self.pressure_label_fix1 = QLabel(" Torr?")
        self.pressure_label_fix1.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        #
        #
        self.flow_label_fix0 = QLabel("Flow: ")
        self.flow_label_fix0.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.flow_label_readout = QLabel("--")
        self.flow_label_readout.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        #
        self.flow_label_fix1 = QLabel(" CFM?")
        self.flow_label_fix1.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        #
        # Add widgets to grid layout
        self.lower_grid.addWidget(self.gas_label, 0, 0, 1, 1)
        self.lower_grid.addWidget(self.gas_drop, 0, 1, 1, 2)
        self.lower_grid.addWidget(self.pressure_label_fix0, 1, 0, 1, 1)
        self.lower_grid.addWidget(self.pressure_label_readout, 1, 1, 1, 1)
        self.lower_grid.addWidget(self.pressure_label_fix1, 1, 2, 1, 1)
        self.lower_grid.addWidget(self.flow_label_fix0, 2, 0, 1, 1)
        self.lower_grid.addWidget(self.flow_label_readout, 2, 1, 1, 1)
        self.lower_grid.addWidget(self.flow_label_fix1, 2, 2, 1, 1)

        # ******* DEFINE OVERALL LAYOUT
        #
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.form, 0, 0)
        self.master_layout.addLayout(self.lower_grid, 1, 0)
        self.setLayout(self.master_layout)

        # Write state to scope - synch scope with GUI
        self.send_state()

        # Create timer to query voltages
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(self.globalRefreshRate)

        self.log_note("Initalized")

    def close(self):  # Note: this is a complete duplicate of the 'close()' function
        # in HC_Instrument, except it adds readout_timer.stop()

        if self.comm is not None:
            self.comm.close()
        self.readout_timer.stop

    def update_readout(self):
        """Queries the instrument for current readout data, then reads the most
        recent readout data from the inbox and pushes it to the GUI"""

        # Request updated readout data
        self.comm.command(f"rate?")
        self.comm.command(f"pressure?")

        # Get latest inbox entries for readout data...
        flow_meas = self.read_message(f"rate=")
        press_meas = self.read_message(f"pressure=")

        # Update labels
        self.pressure_label_readout.setText(press_meas)
        self.flow_label_readout.setText(flow_meas)

    #
    # Create a default state object if can't get state from a file
    #
    def default_state(self):

        dflt = {}

        dflt["gas"] = "Argon"
        dflt["rate"] = 0.0

        return dflt
