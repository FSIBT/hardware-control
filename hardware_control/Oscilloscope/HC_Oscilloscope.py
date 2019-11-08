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

#
# This is a 4-channel oscilloscope control progam. It defines a UI for a 4-ch
# scope and has the sockets and signals to interface with a OscilloscopeComm
# instance, which facilitates communication with the instrument. The Osc.Comm
# object requires an object (originally passed to the control object) which
# fascilitates communication with the scope. An example of such a program is
# the Key4000XSCPI class for Keysight 4000X series oscilloscopes. These classes
# mostly just wrap SCPI commands so this UI+Communication code knows how to
# interface with any specific scope model.
#
# All instrument parameters are saved in a 'settings' dictionary. When a function
# such as set_timebase() is called, it updates the settings object and sends it to
# the communicaiton object instance. The communication object finds the change
# and sends the correct SCPI commands to the instrument to impliment the change.
#
class HC_Oscilloscope(HC_Instrument):
    def __init__(
        self,
        scpi_instr,
        window,
        name: str = "Oscilloscope Control",
        initialize_with: str = "INSTRUMENT",
        save_on_close: str = False,
    ):

        super().__init__(window, name)

        self.settings = {}
        self.save_on_close = save_on_close

        self.comm = HC_Comm(scpi_instr, self)
        self.filename = ""

        # Initialize settings to correct values
        if initialize_with == "DEFAULT":
            self.save_on_close = False
            # Can't save without filename
            self.settings = self.default_state()
        else:
            self.load_state(initialize_with)
            self.filename = initialize_with

        # Create GUI
        #
        self.disp = OscilloscopeDisplayWidget(self, True)
        #
        self.horiz = OscilloscopeHorizontalWidget(self)
        #
        self.top_panel = QGridLayout()
        trig = OscilloscopeTriggerWidget(self)
        self.top_panel.addWidget(trig, 0, 0)
        #
        ch1 = OscillscopeChannelWidget(1, self, "yellow")
        ch2 = OscillscopeChannelWidget(2, self, "green")
        ch3 = OscillscopeChannelWidget(3, self, "blue")
        ch4 = OscillscopeChannelWidget(4, self, "red")
        self.channel_panel = QGridLayout()
        self.channel_panel.addWidget(ch1, 0, 0)
        self.channel_panel.addWidget(ch2, 0, 1)
        self.channel_panel.addWidget(ch3, 0, 2)
        self.channel_panel.addWidget(ch4, 0, 3)
        #

        #
        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.disp, 0, 0, 1, 2)
        self.master_layout.addWidget(self.horiz, 0, 2, 1, 1)
        self.master_layout.addLayout(self.top_panel, 0, 3, 1, 1)
        self.master_layout.addLayout(self.channel_panel, 1, 0, 1, 4)

        #
        self.setLayout(self.master_layout)

        # Write state to scope - synch scope with GUI
        self.send_state()

        self.log_note("Initalized")

    #
    # Create a default settings object if can't get settings from a file
    #
    def default_state(self):

        dflt = {}

        dflt["timebase"] = 1e-3
        #
        dflt["time_offset"] = 0
        #
        dflt["CH1_volts_div"] = 1
        dflt["CH2_volts_div"] = 1
        dflt["CH3_volts_div"] = 1
        dflt["CH4_volts_div"] = 1
        #
        dflt["CH1_volts_div"] = 1
        dflt["CH2_volts_div"] = 1
        dflt["CH3_volts_div"] = 1
        dflt["CH4_volts_div"] = 1
        #
        dflt["CH1_volts_div"] = 1
        dflt["CH2_volts_div"] = 1
        dflt["CH3_volts_div"] = 1
        dflt["CH4_volts_div"] = 1
        #
        dflt["CH1_offset"] = 0
        dflt["CH2_offset"] = 0
        dflt["CH3_offset"] = 0
        dflt["CH4_offset"] = 0
        #
        dflt["CH1_BW_lim"] = False
        dflt["CH2_BW_lim"] = False
        dflt["CH3_BW_lim"] = False
        dflt["CH4_BW_lim"] = False
        #
        dflt["CH1_active"] = True
        dflt["CH2_active"] = False
        dflt["CH3_active"] = False
        dflt["CH4_active"] = False
        #
        dflt["CH1_impedance"] = 1e6
        dflt["CH2_impedance"] = 1e6
        dflt["CH3_impedance"] = 1e6
        dflt["CH4_impedance"] = 1e6
        #
        dflt["CH1_label"] = "Channel 1"
        dflt["CH2_label"] = "Channel 2"
        dflt["CH3_label"] = "Channel 3"
        dflt["CH4_label"] = "Channel 4"
        #
        dflt["labels_enabled"] = False
        #
        dflt["CH1_invert"] = False
        dflt["CH2_invert"] = False
        dflt["CH3_invert"] = False
        dflt["CH4_invert"] = False
        #
        dflt["CH1_probe_atten"] = 10
        dflt["CH2_probe_atten"] = 10
        dflt["CH3_probe_atten"] = 10
        dflt["CH4_probe_atten"] = 10
        #
        dflt["CH1_coupling"] = "DC"
        dflt["CH2_coupling"] = "DC"
        dflt["CH3_coupling"] = "DC"
        dflt["CH4_coupling"] = "DC"
        #
        dflt["trigger_level"] = 1
        #
        dflt["trigger_coupling"] = "DC"
        #
        dflt["trigger_edge"] = "POS"
        #
        dflt["trigger_channel"] = 1

        return dflt


#
# Defines a UI for oscilloscope channels
#
class OscillscopeChannelWidget(QWidget):
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
            lambda: control.comm.update_setting(
                f"CH{channel}_volts_div", self.v_div_edit.text()
            )
        )
        self.v_div_edit.setText(str(control.settings[f"CH{channel}_volts_div"]))
        #
        self.offset_edit = QLineEdit()
        self.offset_edit.setValidator(QDoubleValidator())
        self.offset_edit.editingFinished.connect(
            lambda: control.comm.update_setting(
                f"CH{channel}_offset", self.offset_edit.text()
            )
        )
        self.offset_edit.setText(str(control.settings[f"CH{channel}_offset"]))
        #
        self.label_edit = QLineEdit()
        self.label_edit.editingFinished.connect(
            lambda: control.comm.update_setting(
                f"CH{channel}_label", self.label_edit.text()
            )
        )
        self.label_edit.setText(control.settings[f"CH{channel}_label"])
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
            lambda: control.comm.update_setting(
                f"CH{channel}_active", str(self.active_but.isChecked())
            )
        )
        setButtonState(self.active_but, control.settings[f"CH{channel}_active"])
        #
        self.BW_but = QPushButton()
        self.BW_but.setText("BW Limit")
        self.BW_but.setIcon(
            QIcon(
                (
                    QPixmap(
                        pkg_resources.resource_filename(
                            "hardware_control", "Oscilloscope/graphics/BWlim.png"
                        )
                    )
                )
            )
        )
        self.BW_but.setCheckable(True)
        self.BW_but.clicked.connect(
            lambda: control.comm.update_setting(
                f"CH{channel}_BW_lim", str(self.BW_but.isChecked())
            )
        )
        setButtonState(self.BW_but, control.settings[f"CH{channel}_BW_lim"])
        #
        self.Inv_but = QPushButton()
        self.Inv_but.setText("Invert")
        self.Inv_but.setCheckable(True)
        self.Inv_but.setIcon(
            QIcon(
                (
                    QPixmap(
                        pkg_resources.resource_filename(
                            "hardware_control", "Oscilloscope/graphics/invert.png"
                        )
                    )
                )
            )
        )
        self.Inv_but.clicked.connect(
            lambda: control.comm.update_setting(
                f"CH{channel}_invert", str(self.Inv_but.isChecked())
            )
        )
        setButtonState(self.Inv_but, control.settings[f"CH{channel}_invert"])
        #
        #
        self.coupling_label = QLabel("Coupling:")
        self.coupling_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.coupling_drop = QComboBox()
        self.coupling_drop.addItems(["DC", "AC"])
        self.coupling_drop.currentIndexChanged.connect(
            lambda: control.comm.update_setting(
                f"CH{channel}_coupling", self.coupling_drop.currentText()
            )
        )
        self.coupling_drop.setCurrentText(control.settings[f"CH{channel}_coupling"])
        #
        self.impedance_label = QLabel("Impedance:")
        self.impedance_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.impedance_drop = QComboBox()
        self.impedance_drop.addItems(["1e6", "50"])
        self.impedance_drop.currentIndexChanged.connect(
            lambda: control.comm.update_setting(
                f"CH{channel}_impedance", self.impedance_drop.currentText()
            )
        )
        self.impedance_drop.setCurrentText(
            str(control.settings[f"CH{channel}_impedance"])
        )
        #
        self.probe_label = QLabel("Probe attenutation: ")
        self.probe_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.probe_drop = QComboBox()
        self.probe_drop.addItems([".001", ".01", ".1", "1", "10", "100", "1000"])
        self.probe_drop.currentIndexChanged.connect(
            lambda: control.comm.update_setting(
                f"CH{channel}_probe_atten", self.probe_drop.currentText()
            )
        )
        self.probe_drop.setCurrentText(
            str(control.settings[f"CH{channel}_probe_atten"])
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

        # ******* DEFINE OVERALL LAYOUT
        #
        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.channel_label, 0, 0)
        self.master_layout.addLayout(self.form, 1, 0)
        self.master_layout.addLayout(self.lower_grid, 2, 0)
        self.setLayout(self.master_layout)


#
# Defines a UI for oscilloscope channels
#
class OscilloscopeTriggerWidget(QWidget):
    def __init__(self, control):
        super().__init__()

        # ************** DEFINE UI *********************#

        self.trigger_label_box = QHBoxLayout()
        self.trigger_label = QLabel()
        self.trigger_label.setPixmap(
            QPixmap(
                pkg_resources.resource_filename(
                    "hardware_control", "Oscilloscope/graphics/trigger_label.png"
                )
            )
        )
        self.trigger_label_box.addWidget(self.trigger_label)

        # ****** DEFINE TEXT BOXES
        #
        self.level_edit = QLineEdit()
        self.level_edit.setValidator(QDoubleValidator())
        self.level_edit.editingFinished.connect(
            lambda: control.comm.update_setting(
                "trigger_level", str(self.level_edit.currentText())
            )
        )
        self.level_edit.setText(str(control.settings["trigger_level"]))
        #
        self.form = QFormLayout()
        self.form.addRow("Trigger Level (V):", self.level_edit)

        self.lower_grid = QGridLayout()

        # ******* DEFINE BUTTONS + DROPDOWNS
        #
        self.trig_chan_label = QLabel("Channel: ")
        self.trig_chan_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.trig_chan_drop = QComboBox()
        self.trig_chan_drop.addItems(["1", "2", "3", "4"])
        self.trig_chan_drop.currentIndexChanged.connect(
            lambda: control.comm.update_setting(
                "trigger_channel", self.trig_chan_drop.currentText()
            )
        )
        self.trig_chan_drop.setCurrentText(str(control.settings["trigger_channel"]))
        #
        self.coupling_label = QLabel("Coupling:")
        self.coupling_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.coupling_drop = QComboBox()
        self.coupling_drop.addItems(["DC", "AC"])
        self.coupling_drop.currentIndexChanged.connect(
            lambda: control.comm.update_setting(
                "trigger_coupling", self.coupling_drop.currentText()
            )
        )
        self.coupling_drop.setCurrentText(control.settings["trigger_coupling"])
        #
        self.edge_label = QLabel("Edge:")
        self.edge_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.edge_drop = QComboBox()
        self.edge_drop.addItems(["POS", "NEG", "EITH", "ALT"])
        self.edge_drop.currentIndexChanged.connect(
            lambda: control.comm.update_setting(
                "trigger_edge", self.edge_drop.currentText()
            )
        )
        self.edge_drop.setCurrentText(str(control.settings["trigger_edge"]))
        #
        self.single_but = QPushButton()
        self.single_but.setText("Single")
        self.single_but.clicked.connect(
            lambda: control.comm.command("ACTION:SINGLE_TRIGGER")
        )
        #
        self.run_but = QPushButton()
        self.run_but.setText("Run")
        self.run_but.clicked.connect(lambda: control.comm.command("ACTION:RUN"))
        #
        self.stop_but = QPushButton()
        self.stop_but.setText("Stop")
        self.stop_but.clicked.connect(lambda: control.comm.command("ACTION:STOP"))

        # Add widgets to grid layout
        self.lower_grid.addWidget(self.trig_chan_label, 0, 0)
        self.lower_grid.addWidget(self.trig_chan_drop, 0, 1)
        self.lower_grid.addWidget(self.coupling_label, 1, 0)
        self.lower_grid.addWidget(self.coupling_drop, 1, 1)
        self.lower_grid.addWidget(self.edge_label, 2, 0)
        self.lower_grid.addWidget(self.edge_drop, 2, 1)
        self.lower_grid.addWidget(self.single_but, 3, 0)
        self.lower_grid.addWidget(self.run_but, 3, 1)
        self.lower_grid.addWidget(self.stop_but, 4, 1)

        # ******* DEFINE OVERALL LAYOUT
        #
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.trigger_label_box, 0, 0)
        self.master_layout.addLayout(self.form, 1, 0)
        self.master_layout.addLayout(self.lower_grid, 2, 0)
        self.setLayout(self.master_layout)


#
# Defines a UI for oscilloscope channels
#
class OscilloscopeHorizontalWidget(QWidget):
    def __init__(self, control):
        super().__init__()

        # ************** DEFINE UI *********************#

        self.horizontal_label_box = QHBoxLayout()
        self.horizontal_label = QLabel()
        self.horizontal_label.setPixmap(
            QPixmap(
                pkg_resources.resource_filename(
                    "hardware_control", "Oscilloscope/graphics/horizontal_label.png"
                )
            )
        )
        self.horizontal_label_box.addWidget(self.horizontal_label)

        # ****** DEFINE TEXT BOXES
        #
        self.timebase_edit = QLineEdit()
        self.timebase_edit.setValidator(QDoubleValidator())
        self.timebase_edit.editingFinished.connect(
            lambda: control.comm.update_setting("timebase", self.timebase_edit.text())
        )
        self.timebase_edit.setText(str(control.settings["timebase"]))
        #
        self.time_offset_edit = QLineEdit()
        self.time_offset_edit.setValidator(QDoubleValidator())
        self.time_offset_edit.editingFinished.connect(
            lambda: control.comm.update_setting(
                "time_offset", self.time_offset_edit.text()
            )
        )
        self.time_offset_edit.setText(str(control.settings["time_offset"]))
        #
        self.form = QFormLayout()
        self.form.addRow("Time/Div (s):", self.timebase_edit)
        self.form.addRow("Offset (s): ", self.time_offset_edit)

        # ******* DEFINE OVERALL LAYOUT
        #
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.horizontal_label_box, 0, 0)
        self.master_layout.addLayout(self.form, 1, 0)
        self.setLayout(self.master_layout)


class OscilloscopeDisplayWidget(QWidget):
    def __init__(self, control, show_controls: bool = False, refresh: float = 0.2):

        super().__init__()

        self.control = control

        self.single_trig_mode = False

        # ************** DEFINE UI *********************#
        #
        self.display = pg.PlotWidget()
        #
        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.display, 0, 0, 1, 5)
        #
        self.lineCH1 = pg.mkPen(color=(100, 100, 255), style=QtCore.Qt.DashLine)
        self.lineCH2 = pg.mkPen(color=(255, 100, 100), style=QtCore.Qt.DashLine)
        self.lineCH3 = pg.mkPen(color=(100, 255, 100), style=QtCore.Qt.DashLine)
        self.lineCH4 = pg.mkPen(color=(200, 200, 200), style=QtCore.Qt.DashLine)
        #
        self.CH1 = self.display.plot(pen=self.lineCH1, symbol=None)
        self.CH2 = self.display.plot(pen=self.lineCH2, symbol=None)
        self.CH3 = self.display.plot(pen=self.lineCH3, symbol=None)
        self.CH4 = self.display.plot(pen=self.lineCH4, symbol=None)
        #
        if show_controls:
            self.refresh_rate_label = QLabel("Refresh Rate (Hz): ")
            #
            self.refresh_rate_edit = QLineEdit()
            self.refresh_rate_edit.setValidator(QDoubleValidator())
            self.refresh_rate_edit.editingFinished.connect(
                lambda: self.refresh_rate(float(self.refresh_rate_edit.text()))
            )
            self.refresh_rate_edit.setText(str(refresh))
            #
            self.refresh_but = QPushButton()
            self.refresh_but.setText("Refresh")
            # self.refresh_but.clicked.connect(control.query_waveforms)
            #
            self.refresh_mode_label = QLabel("Refresh Mode: ")
            #
            self.refresh_mode_drop = QComboBox()
            self.refresh_mode_drop.addItems(["Timer", "Single Trig", "Manual"])
            self.refresh_mode_drop.currentIndexChanged.connect(
                lambda: self.set_refresh_mode(self.refresh_mode_drop.currentText())
            )
            self.refresh_mode_drop.setCurrentText("Timer")
            #
            #
            self.master_layout.addWidget(self.refresh_mode_label, 1, 0)
            self.master_layout.addWidget(self.refresh_mode_drop, 1, 1)
            self.master_layout.addWidget(self.refresh_rate_label, 1, 2)
            self.master_layout.addWidget(self.refresh_rate_edit, 1, 3)
            self.master_layout.addWidget(self.refresh_but, 1, 4)

        self.setLayout(self.master_layout)

        self.update_timer = QTimer(self)
        # self.update_timer.timeout.connect(control.query_waveforms)
        self.update_timer.start(1000 / refresh)

    # Set refresh rate (in Hz)
    def refresh_rate(self, rate: float):
        self.update_timer.setInterval(1000 / rate)

    # Set refresh rate (in ms)
    def refresh_period(self, period: float):
        self.update_timer.setInterval(period)

    def set_refresh_mode(self, mode: str):
        if mode == "Timer":
            if not self.update_timer.isActive():
                self.update_timer.start()
            single_trig_mode = False
        elif mode == "Single Trig":
            if self.update_timer.isActive():
                self.update_timer.stop()
            self.single_trig_mode = True
        else:
            if self.update_timer.isActive():
                self.update_timer.stop()
                print("Stop!")
            single_trig_mode = False

    def update_display(self, wvfms: dict):
        start_time = time.time()
        if "CH1" in wvfms:
            self.CH1.setData(wvfms["CH1"][1], wvfms["CH1"][0])
        else:
            pass

        if "CH2" in wvfms:
            self.CH2.setData(wvfms["CH2"][1], wvfms["CH2"][0])
        else:
            pass

        if "CH3" in wvfms:
            self.CH3.setData(wvfms["CH3"][1], wvfms["CH3"][0])
        else:
            pass

        if "CH4" in wvfms:
            self.CH4.setData(wvfms["CH4"][1], wvfms["CH4"][0])
        else:
            pass
