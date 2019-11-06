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

        self.state = {}
        self.save_on_close = save_on_close

        self.comm = HC_Comm(backend)
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

        # Initialize state to correct values
        if initialize_with == "INSTRUMENT":
            self.save_on_close = False
            # Can't save without filename
            self.state = self.initialize_gui_instrument()
        elif initialize_with == "DEFAULT":
            self.save_on_close = False
            # Can't save without filename
            self.state = self.default_state()
        else:
            self.load_state(initialize_with)
            self.filename = initialize_with
        self.state["channel"] = channel_num

        # Create GUI
        #
        #
        # Automatically create channel widgets and push them into a row
        self.channel_widgets = []
        self.channel_panel = QGridLayout()
        for idx, c in enumerate(self.channel):
            self.channel_widgets.append(MultiPowerSupplyChannel(c, self))
            self.channel_panel.addWidget(ch1, 0, idx)
        #
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.channel_panel, 0, 0)
        #
        self.setLayout(self.master_layout)

        # Write state to scope - synch scope with GUI
        self.send_state()

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
    def __init__(self, channel: int, control, color):
        super().__init__()

        self.channel = channel

        # ************** DEFINE UI *********************#

        self.channel_label = QLabel()
        if color == "yellow":
            self.channel_label.setPixmap(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control", "Oscilloscope/graphics/channel1_yellow.png"
                    )
                )
            )
        elif color == "green":
            self.channel_label.setPixmap(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control", "Oscilloscope/graphics/channel2_green.png"
                    )
                )
            )
        elif color == "blue":
            self.channel_label.setPixmap(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control", "Oscilloscope/graphics/channel3_blue.png"
                    )
                )
            )
        elif color == "red":
            self.channel_label.setPixmap(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control", "Oscilloscope/graphics/channel4_red.png"
                    )
                )
            )
        else:
            self.channel_label.setText(f"Channel {channel}")

        # ****** DEFINE TEXT BOXES
        #
        self.v_div_edit = QLineEdit()
        self.v_div_edit.setValidator(QDoubleValidator())
        self.v_div_edit.editingFinished.connect(
            lambda: control.set_volts_div(channel, float(self.v_div_edit.text()))
        )
        self.v_div_edit.setText(str(control.state["volts_div"][f"CH{channel}"]))
        #
        self.offset_edit = QLineEdit()
        self.offset_edit.setValidator(QDoubleValidator())
        self.offset_edit.editingFinished.connect(
            lambda: control.set_offset(self.channel, float(self.offset_edit.text()))
        )
        self.offset_edit.setText(str(control.state["offset"][f"CH{channel}"]))
        #
        self.label_edit = QLineEdit()
        self.label_edit.editingFinished.connect(
            lambda: control.set_channel_label(self.channel, self.label_edit.text())
        )
        self.label_edit.setText(control.state["channel_label"][f"CH{channel}"])
        #
        self.form = QFormLayout()
        self.form.addRow("Volts/Div (V):", self.v_div_edit)
        self.form.addRow("Vert. Offset (V):", self.offset_edit)
        self.form.addRow("Label:", self.label_edit)

        self.lower_grid = QGridLayout()

        # ******* DEFINE BUTTONS + DROPDOWNS
        #
        self.active_but = QPushButton()
        self.active_but.setText("Channel On/Off")
        self.active_but.setCheckable(True)
        self.active_but.clicked.connect(
            lambda: control.set_channel_active(
                self.channel, self.active_but.isChecked()
            )
        )
        setButtonState(
            self.active_but, control.state["channel_active"][f"CH{self.channel}"]
        )
        #
        self.BW_but = QPushButton()
        self.BW_but.setText("BW Limit")
        self.BW_but.setCheckable(True)
        self.BW_but.clicked.connect(
            lambda: control.set_BW_lim(self.channel, self.BW_but.isChecked())
        )
        setButtonState(self.BW_but, control.state["BW_lim"][f"CH{self.channel}"])
        #
        self.Inv_but = QPushButton()
        self.Inv_but.setText("Invert")
        self.Inv_but.setCheckable(True)
        self.Inv_but.clicked.connect(
            lambda: control.set_channel_invert(self.channel, self.Inv_but.isChecked())
        )
        setButtonState(
            self.Inv_but, control.state["channel_invert"][f"CH{self.channel}"]
        )
        #
        #
        self.coupling_label = QLabel("Coupling:")
        self.coupling_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.coupling_drop = QComboBox()
        self.coupling_drop.addItems(["DC", "AC"])
        self.coupling_drop.currentIndexChanged.connect(
            lambda: control.set_channel_coupling(
                self.channel, self.coupling_drop.currentText()
            )
        )
        self.coupling_drop.setCurrentText(
            control.state["channel_coupling"][f"CH{self.channel}"]
        )
        #
        self.impedance_label = QLabel("Impedance:")
        self.impedance_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.impedance_drop = QComboBox()
        self.impedance_drop.addItems(["1e6", "50"])
        self.impedance_drop.currentIndexChanged.connect(
            lambda: control.set_channel_impedance(
                self.channel, float(self.impedance_drop.currentText())
            )
        )
        self.impedance_drop.setCurrentText(
            str(control.state["channel_impedance"][f"CH{self.channel}"])
        )
        #
        self.probe_label = QLabel("Probe attenutation: ")
        self.probe_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.probe_drop = QComboBox()
        self.probe_drop.addItems([".001", ".01", ".1", "1", "10", "100", "1000"])
        self.probe_drop.currentIndexChanged.connect(
            lambda: control.set_probe_atten(
                self.channel, float(self.probe_drop.currentText())
            )
        )
        self.probe_drop.setCurrentText(
            str(control.state["probe_atten"][f"CH{self.channel}"])
        )
        #
        # Add widgets to grid layout
        self.lower_grid.addWidget(self.active_but, 0, 0)
        self.lower_grid.addWidget(self.BW_but, 1, 0)
        self.lower_grid.addWidget(self.Inv_but, 1, 1)
        self.lower_grid.addWidget(self.coupling_label, 2, 0)
        self.lower_grid.addWidget(self.coupling_drop, 2, 1)
        self.lower_grid.addWidget(self.impedance_label, 3, 0)
        self.lower_grid.addWidget(self.impedance_drop, 3, 1)
        self.lower_grid.addWidget(self.probe_label, 4, 0)
        self.lower_grid.addWidget(self.probe_drop, 4, 1)
        #
        # self.lower_grid.addWidget(self.active_but, 0, 0);
        # self.lower_grid.addWidget(self.BW_but, 1, 0);
        # self.lower_grid.addWidget(self.Inv_but, 2, 0);
        # self.lower_grid.addWidget(self.coupling_label, 0, 1);
        # self.lower_grid.addWidget(self.coupling_drop, 1, 1);
        # self.lower_grid.addWidget(self.impedance_label, 2, 1);
        # self.lower_grid.addWidget(self.impedance_drop, 3, 1);
        # self.lower_grid.addWidget(self.probe_label, 4, 1);
        # self.lower_grid.addWidget(self.probe_drop, 5, 1);

        # ******* DEFINE OVERALL LAYOUT
        #
        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.channel_label, 0, 0)
        self.master_layout.addLayout(self.form, 1, 0)
        self.master_layout.addLayout(self.lower_grid, 2, 0)
        self.setLayout(self.master_layout)
