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
import copy
from hardware_control.base import HC_Instrument, HC_Comm, setButtonState


class HC_MultiPowerSupply(HC_Instrument):
    def __init__(
        self,
        backend,
        window,
        channels: list,
        name: str = "Multi-Channel PSU",
        initialize_with: str = "INSTRUMENT",
        save_on_close: str = False,
    ):

        super().__init__(window, name)

        self.settings = {}
        self.save_on_close = save_on_close
        self.backend = backend
        self.comm = HC_Comm(backend, self)
        self.filename = ""

        # Check that the user provided valid channel request...
        if (len(channels) > backend.num_channels) or (
            max(channels) > self.backend.num_channels
        ):
            self.log_note(
                "WARNING: Requested channel not available on instrument. Ignoring extra channels."
            )

        # Add channels that are within range and not repeats
        self.channels = []
        for c in channels:
            if (c <= self.backend.num_channels) and (not c in self.channels):
                self.channels.append(c)

        # Initialize settings to correct values
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
        #
        #
        # Automatically create channel widgets and push them into a row
        self.channel_widgets = []
        self.channel_panel = QGridLayout()
        for idx, c in enumerate(self.channels):
            self.channel_widgets.append(MultiPowerSupplyChannel(c, self))
            self.channel_panel.addWidget(self.channel_widgets[-1], 0, idx)
        #
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.channel_panel, 0, 0)
        #
        self.setLayout(self.master_layout)

        # Write state to scope - synch scope with GUI
        self.send_state()

        # Create timer to query voltages
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(500)

    def close(self):  # Note: this is a complete duplicate of the 'close()' function
        # in HC_Instrument, except it adds readout_timer.stop()

        if self.comm is not None:
            self.comm.close()
        self.readout_timer.stop()

    def update_readout(self):
        """Queries the instrument for current readout data, then reads the most
        recent readout data from the inbox and pushes it to the GUI"""

        # Request updated readout data
        for idx, c in enumerate(self.channels):  # For each channel...
            self.comm.command(f"CH{c}_V_out?")
            self.comm.command(f"CH{c}_I_out?")
            self.comm.command(f"CH{c}_V_set?")
            self.comm.command(f"CH{c}_I_set?")

            # Get latest inbox entries for readout data...
            Vout = self.read_message(f"CH{c}_V_out")
            Iout = self.read_message(f"CH{c}_I_out")
            Vset = self.read_message(f"CH{c}_V_set")
            Iset = self.read_message(f"CH{c}_I_set")

            # Send newest data to GUI
            self.channel_widgets[idx].update_readout(Vout, Iout, Vset, Iset)

    #
    # Create a default state object if can't get state from a file
    #
    def default_state(self):

        dflt = {}

        for c in self.channels:
            dflt[f"CH{c}_enabled"] = False
            dflt[f"CH{c}_V_set"] = 0
            dflt[f"CH{c}_I_set"] = 0.5

        return dflt


class MultiPowerSupplyChannel(QWidget):
    def __init__(self, channel: int, control):
        super().__init__()

        self.channel = channel

        # ************** DEFINE UI *********************#
        #
        self.channel_label = QLabel()
        if self.channel <= 20:
            self.channel_label.setPixmap(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control",
                        f"PowerSupply/graphics/channel_{self.channel}.png",
                    )
                )
            )
        else:
            self.channel_label.setText(f"Channel {channel}")
            self.channel_label.setAlignment(
                QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter
            )

        # ****** DEFINE READOUTS
        #
        self.V_set_label = QLabel("Vset:")
        self.V_set_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.V_set_label_val = QLabel("-------")
        self.V_set_label_val.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        #
        self.I_set_label = QLabel("Iset:")
        self.I_set_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.I_set_label_val = QLabel("-------")
        self.I_set_label_val.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        #
        #
        #
        self.V_out_label = QLabel("Vout:")
        self.V_out_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.V_out_label_val = QLabel("-------")
        self.V_out_label_val.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        #
        self.I_out_label = QLabel("Iout:")
        self.I_out_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.I_out_label_val = QLabel("-------")
        self.I_out_label_val.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        #
        #
        #
        self.P_out_label = QLabel("Pout:")
        self.P_out_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.P_out_label_val = QLabel("-------")
        self.P_out_label_val.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Layout readout
        self.readout_grid = QGridLayout()
        self.readout_grid.addWidget(self.V_set_label, 0, 0)
        self.readout_grid.addWidget(self.V_set_label_val, 0, 1)
        self.readout_grid.addWidget(self.I_set_label, 1, 0)
        self.readout_grid.addWidget(self.I_set_label_val, 1, 1)
        #
        self.readout_grid.addWidget(self.V_out_label, 0, 2)
        self.readout_grid.addWidget(self.V_out_label_val, 0, 3)
        self.readout_grid.addWidget(self.I_out_label, 1, 2)
        self.readout_grid.addWidget(self.I_out_label_val, 1, 3)
        #
        self.readout_grid.addWidget(self.P_out_label, 2, 2)
        self.readout_grid.addWidget(self.P_out_label_val, 2, 3)

        # ****** DEFINE CONTROLS
        #
        self.V_ctrl_label = QLabel("Voltage (V):")
        self.V_ctrl_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.I_ctrl_label = QLabel("Current (A): ")
        self.I_ctrl_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        #
        self.V_edit = QLineEdit()
        self.V_edit.setValidator(QDoubleValidator())
        self.V_edit.editingFinished.connect(
            lambda: control.update_setting(
                f"CH{self.channel}_V_set", (self.V_edit.text())
            )
        )
        self.V_edit.setText(str(control.settings[f"CH{channel}_V_set"]))
        #
        self.I_edit = QLineEdit()
        self.I_edit.setValidator(QDoubleValidator())
        self.I_edit.editingFinished.connect(
            lambda: control.update_setting(
                f"CH{self.channel}_I_set", (self.I_edit.text())
            )
        )
        self.I_edit.setText(str(control.settings[f"CH{channel}_I_set"]))
        #
        self.enabled_but = QPushButton()
        self.enabled_but.setText("On/Off")
        self.enabled_but.setCheckable(True)
        self.enabled_but.clicked.connect(
            lambda: control.update_setting(
                f"CH{channel}_enabled", str(self.enabled_but.isChecked())
            )
        )
        setButtonState(self.enabled_but, control.settings[f"CH{channel}_enabled"])
        #
        self.controls_grid = QGridLayout()
        self.controls_grid.addWidget(self.V_ctrl_label, 0, 0)
        self.controls_grid.addWidget(self.V_edit, 0, 1)
        self.controls_grid.addWidget(self.I_ctrl_label, 1, 0)
        self.controls_grid.addWidget(self.I_edit, 1, 1)
        self.controls_grid.addWidget(self.enabled_but, 2, 1)

        # ******* DEFINE OVERALL LAYOUT
        #
        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.channel_label, 0, 0)
        self.master_layout.addLayout(self.readout_grid, 1, 0)
        self.master_layout.addLayout(self.controls_grid, 2, 0)
        self.setLayout(self.master_layout)

    def update_readout(self, Vout, Iout, Vset, Iset):

        if Vout == None:
            Vout = "-----"
        if Iout == None:
            Iout = "-----"
        if Vset == None:
            Vset = "-----"
        if Iset == None:
            Iset = "-----"

        self.V_set_label_val.setText(f"{Vset} V")
        self.V_out_label_val.setText(f"{Vout} V")
        self.I_set_label_val.setText(f"{Iset} A")
        self.I_out_label_val.setText(f"{Iout} A")
        if Vout is not None and Iout is not None:
            try:
                pwr = str(float(Vout) * float(Iout))
                self.P_out_label_val.setText(f"{pwr} W")
            except Exception as e:
                self.P_out_label_val.setText("-----")
                # print(e)
        else:
            self.P_out_label_val.setText("-----")
